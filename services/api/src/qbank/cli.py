"""Administrative commands (``qbank``). Run inside the stack, e.g.:

    docker compose run --rm migrate qbank create-platform-admin --email you@example.com

Commands that create privileged accounts connect as the table owner (MIGRATION_DATABASE_URL),
because the runtime role is deliberately not allowed to do that.
"""

import argparse
import getpass
import os
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError

from qbank.core.db import Database
from qbank.core.errors import Conflict
from qbank.modules.identity.service import create_platform_admin

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qbank", description="Question bank admin commands")
    commands = parser.add_subparsers(dest="command")
    admin = commands.add_parser("create-platform-admin", help="Create a platform admin account")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", help="Display name (asked if omitted)")
    admin.set_defaults(handler=_create_platform_admin)

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
