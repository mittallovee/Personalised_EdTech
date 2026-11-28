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
from qbank.modules.ai.public import (
    BatchProvider,
    KeyUnreadable,
    Provider,
    open_key,
    provider_for,
    reseal_all,
    smoke,
    smoke_batch,
)
from qbank.modules.identity.service import create_platform_admin
from qbank.modules.ingestion.golden import live_reader, measure
from qbank.modules.ingestion.models import GoldenCase, GoldenSet
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


def _ai_smoke(args: argparse.Namespace) -> int:
    """Try one provider with the coaching's stored key (ADR-0023). CI never calls a provider, so
    this is how to learn that an adapter and a key really work. Prints what happened, never the
    key."""
    owner_url = os.environ.get("MIGRATION_DATABASE_URL")
    if not owner_url:
        print("Set MIGRATION_DATABASE_URL (table-owner connection).", file=sys.stderr)
        return 2
    try:
        organization_id = UUID(args.organization)
        provider = Provider(args.provider.upper())
        keyring = build_keyring(
            os.environ.get("AI_KEYS_MASTER_KEY"),
            os.environ.get("AI_KEYS_MASTER_KEY_ID", "k1"),
            os.environ.get("AI_KEYS_PREVIOUS"),
        )
    except ValueError as problem:
        print(f"Cannot use those values: {problem}", file=sys.stderr)
        return 2
    database = Database(owner_url)
    try:
        with database.transaction(TenantContext(organization_id=organization_id)) as session:
            try:
                key = open_key(session, keyring, organization_id, provider)
            except KeyUnreadable:
                print(
                    "The stored key could not be opened with the master keys given.",
                    file=sys.stderr,
                )
                return 1
    finally:
        database.dispose()
    if key is None:
        print(f"This coaching has no {provider.value} key stored.", file=sys.stderr)
        return 1
    adapter = provider_for(provider)
    if args.batch:
        if not isinstance(adapter, BatchProvider):
            print(f"{provider.value} has no batch service we can use: Economy is not offered.")
            return 1
        if not args.model:
            print("Name the model to try with --model.", file=sys.stderr)
            return 2
        worked, lines = smoke_batch(adapter, key, args.model, wait_seconds=args.wait)
    else:
        worked, lines = smoke(adapter, key, args.model)
    print(f"{provider.value}:")
    for line in lines:
        print(f"  {line}")
    return 0 if worked else 1


def _ingest_measure(args: argparse.Namespace) -> int:
    """Score a model's reading of the pages in a golden set against the key (M6 6j, K-14). Run it
    before and after a change to the prompt or the model; it calls the real provider with the
    coaching's stored key and prints what it found, never the key."""
    from sqlalchemy import select

    from qbank.core.config import get_settings

    owner_url = os.environ.get("MIGRATION_DATABASE_URL")
    if not owner_url:
        print("Set MIGRATION_DATABASE_URL (table-owner connection).", file=sys.stderr)
        return 2
    try:
        organization_id = UUID(args.organization)
        provider = Provider(args.provider.upper())
        keyring = build_keyring(
            os.environ.get("AI_KEYS_MASTER_KEY"),
            os.environ.get("AI_KEYS_MASTER_KEY_ID", "k1"),
            os.environ.get("AI_KEYS_PREVIOUS"),
        )
    except ValueError as problem:
        print(f"Cannot use those values: {problem}", file=sys.stderr)
        return 2
    database = Database(owner_url)
    try:
        with database.transaction(TenantContext(organization_id=organization_id)) as session:
            golden = session.scalar(select(GoldenSet).where(GoldenSet.name == args.set))
            if golden is None:
                print(f"This coaching has no golden set called {args.set!r}.", file=sys.stderr)
                return 1
            cases = list(session.scalars(select(GoldenCase).where(GoldenCase.set_id == golden.id)))
            if not cases:
                print("That set has no questions yet.", file=sys.stderr)
                return 1
            try:
                key = open_key(session, keyring, organization_id, provider)
            except KeyUnreadable:
                print(
                    "The stored key could not be opened with the master keys given.",
                    file=sys.stderr,
                )
                return 1
            if key is None:
                print(f"This coaching has no {provider.value} key stored.", file=sys.stderr)
                return 1
            reader = live_reader(
                session,
                get_settings().storage(),
                provider_for(provider),
                key,
                args.model,
            )
            report = measure(cases, reader)
    finally:
        database.dispose()
    print(f"Golden set {args.set!r}, model {args.model} ({provider.value}):")
    for line in report.lines():
        print(f"  {line}")
    return 0


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

    smoke_check = commands.add_parser(
        "ai-smoke", help="Try one AI provider with a coaching's stored key (not run in CI)"
    )
    smoke_check.add_argument("--organization", required=True, help="The coaching's id")
    smoke_check.add_argument(
        "--provider", required=True, help="anthropic, openai, google or openrouter"
    )
    smoke_check.add_argument("--model", help="Also ask this model for a tiny answer")
    smoke_check.add_argument(
        "--batch",
        action="store_true",
        help="Try Economy instead: send one tiny batch (needs --model), find it, read its state",
    )
    smoke_check.add_argument(
        "--wait",
        type=int,
        default=0,
        metavar="SECONDS",
        help="With --batch: wait up to this long for the answer, else cancel the batch",
    )
    smoke_check.set_defaults(handler=_ai_smoke)

    measure_cmd = commands.add_parser(
        "ingest-measure",
        help="Score a model's reading of a golden set (calls the real provider; not run in CI)",
    )
    measure_cmd.add_argument("--organization", required=True, help="The coaching's id")
    measure_cmd.add_argument("--set", required=True, help="The golden set's name")
    measure_cmd.add_argument(
        "--provider", required=True, help="anthropic, openai, google or openrouter"
    )
    measure_cmd.add_argument("--model", required=True, help="The provider's model id")
    measure_cmd.set_defaults(handler=_ingest_measure)

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
