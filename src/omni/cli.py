"""Command line interface for OmniMemory."""

from __future__ import annotations

import argparse
import sys

from omni import __version__
from omni.config import ensure_project_layout


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="omni")
    parser.add_argument("--version", action="version", version=f"omni {__version__}")

    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("init", help="Create a project-local .omni layout")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        result = ensure_project_layout()
        print(f"Initialized OmniMemory at {result.omni_dir}")
        if result.gitignore_updated:
            print(f"Updated {result.root / '.gitignore'}")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
