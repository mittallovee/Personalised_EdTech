"""Administrative command-line entry point (``qbank``). Commands are added in later PRs."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="qbank", description="Question bank admin commands")
    parser.add_subparsers(dest="command")
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
