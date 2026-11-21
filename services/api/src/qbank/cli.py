"""Administrative commands (``qbank``). Run inside the stack, e.g.:

    docker compose run --rm migrate qbank create-platform-admin --email you@example.com

Commands that create privileged accounts connect as the table owner (MIGRATION_DATABASE_URL),
because the runtime role is deliberately not allowed to do that.

``qbank export-openapi`` is a developer command (``make openapi``): it writes the API contract.
"""

import argparse
import getpass
import os
import sys
from pathlib import Path
from uuid import UUID

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import text

from qbank.core.db import Database
from qbank.core.errors import Conflict
from qbank.core.secretbox import build_keyring
from qbank.core.tenancy import TenantContext
from qbank.modules.ai.public import KeyUnreadable, reseal_all
from qbank.modules.identity.service import create_platform_admin
from qbank.modules.questions.public import reindex_bank

MIN_PASSWORD_LENGTH = 12
_email = TypeAdapter(EmailStr)


def _ask_password() -> str:
    while True:
        password = getpass.getpass("Password (min 12 characters): ")
        if len(password) < MIN_PASSWORD_LENGTH:
            print("Too short, try again.", file=sys.stderr)
            continue
        if getpass.getpass("Repeat password: ") != password:
            print("Passwords do not match, try again.", file=sys.stderr)
            continue
        return password


def _create_platform_admin(args: argparse.Namespace) -> int:
    try:
        email = _email.validate_python(args.email)
    except ValidationError:
        print(f"Not a valid email address: {args.email}", file=sys.stderr)
        return 2
    owner_url = os.environ.get("MIGRATION_DATABASE_URL")
    if not owner_url:
        print("Set MIGRATION_DATABASE_URL (table-owner connection).", file=sys.stderr)
        return 2
    name = args.name or input("Display name: ").strip()
    if not 1 <= len(name) <= 200:
        print("Display name must be 1-200 characters.", file=sys.stderr)
        return 2
    database = Database(owner_url)
    try:
        user_id = create_platform_admin(database, email, name, _ask_password())
    except Conflict as exc:
        print(exc.message, file=sys.stderr)
        return 1
    finally:
        database.dispose()
    print(f"Platform admin created: {email} (user id {user_id})")
    return 0


def _reindex_bank(args: argparse.Namespace) -> int:
    """Rebuild the bank index from the questions: after a fix or a change to what is indexed."""
    owner_url = os.environ.get("MIGRATION_DATABASE_URL")
    if not owner_url:
        print("Set MIGRATION_DATABASE_URL (table-owner connection).", file=sys.stderr)
        return 2
    only: UUID | None = None
    if args.organization:
        try:
            only = UUID(args.organization)
        except ValueError:
            print(f"Not a coaching id: {args.organization}", file=sys.stderr)
            return 2
    database = Database(owner_url)
    try:
        if only is not None:
            organizations = [only]
        else:
            with database.transaction(TenantContext(is_platform=True)) as session:
                organizations = list(
                    session.scalars(text("SELECT id FROM organizations ORDER BY id"))
                )
        for organization_id in organizations:
            rebuilt, after = 0, None
            while True:
                # One transaction per batch, so a long rebuild never holds one open.
                with database.transaction(
                    TenantContext(organization_id=organization_id)
                ) as session:
                    done, after = reindex_bank(session, organization_id, after=after)
                rebuilt += done
                if after is None:
                    break
            print(f"Coaching {organization_id}: {rebuilt} questions indexed")
    finally:
        database.dispose()
    return 0


def _rotate_ai_keys(args: argparse.Namespace) -> int:
    """Seal every stored AI key again under the current master key (ADR-0023). Add the new key as
    AI_KEYS_MASTER_KEY with a new AI_KEYS_MASTER_KEY_ID, put the old one in AI_KEYS_PREVIOUS, run
    this, then remove the old one."""
    owner_url = os.environ.get("MIGRATION_DATABASE_URL")
    if not owner_url:
        print("Set MIGRATION_DATABASE_URL (table-owner connection).", file=sys.stderr)
        return 2
    try:
        keyring = build_keyring(
            os.environ.get("AI_KEYS_MASTER_KEY"),
            os.environ.get("AI_KEYS_MASTER_KEY_ID", "k1"),
            os.environ.get("AI_KEYS_PREVIOUS"),
        )
    except ValueError as problem:
        print(f"AI_KEYS_MASTER_KEY / AI_KEYS_PREVIOUS: {problem}", file=sys.stderr)
        return 2
    if keyring is None:
        print("Set AI_KEYS_MASTER_KEY first.", file=sys.stderr)
        return 2
    database = Database(owner_url)
    failed = 0
    try:
        with database.transaction(TenantContext(is_platform=True)) as session:
            organizations = list(session.scalars(text("SELECT id FROM organizations ORDER BY id")))
        for organization_id in organizations:
            try:
                with database.transaction(
                    TenantContext(organization_id=organization_id)
                ) as session:
                    resealed, current = reseal_all(session, keyring, organization_id)
            except KeyUnreadable:
                failed += 1
                print(
                    f"Coaching {organization_id}: a key could not be opened with the keys given;"
                    " nothing was changed for it.",
                    file=sys.stderr,
                )
                continue
            if resealed or current:
                print(f"Coaching {organization_id}: {resealed} resealed, {current} already current")
    finally:
        database.dispose()
    return 1 if failed else 0


def _export_openapi(args: argparse.Namespace) -> int:
    # Builds the whole app, so it is imported only when this command runs.
    from qbank.contract import OPENAPI_FILE, render_openapi

    target = Path(args.output) if args.output else OPENAPI_FILE
    document = render_openapi()
    if args.check:
        if not target.is_file() or target.read_text(encoding="utf-8") != document:
            print(f"{target} is out of date: run `make openapi` and commit it.", file=sys.stderr)
            return 1
        print(f"{target} matches the code.")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    print(f"Wrote {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qbank", description="Question bank admin commands")
    commands = parser.add_subparsers(dest="command")
    admin = commands.add_parser("create-platform-admin", help="Create a platform admin account")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", help="Display name (asked if omitted)")
    admin.set_defaults(handler=_create_platform_admin)

    reindex = commands.add_parser(
        "reindex-bank", help="Rebuild the bank index (the question list) from the questions"
    )
    reindex.add_argument("--organization", help="Only this coaching (its id); default: all")
    reindex.set_defaults(handler=_reindex_bank)

    rotate = commands.add_parser(
        "rotate-ai-keys",
        help="Seal every stored AI provider key again under the current master key",
    )
    rotate.set_defaults(handler=_rotate_ai_keys)

    openapi = commands.add_parser("export-openapi", help="Write the API contract (OpenAPI JSON)")
    openapi.add_argument("--output", help="Default: api/openapi.json in the repository")
    openapi.add_argument("--check", action="store_true", help="Fail if the file is out of date")
    openapi.set_defaults(handler=_export_openapi)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    exit_code: int = args.handler(args)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())


def run() -> None:
    """Console-script entry point (``qbank``)."""
    sys.exit(main())
