"""Command-line entry point for CNCguitarwizard."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from cncguitarwizard.version import (
    MOTTO,
    PROJECT_MARK,
    PROJECT_NAME,
    __version__,
)
from cncguitarwizard.workflows import build_prototype001


def _create_parser() -> argparse.ArgumentParser:
    """Return the CNCguitarwizard command-line parser."""
    parser = argparse.ArgumentParser(prog="cncguitarwizard")
    subparsers = parser.add_subparsers(dest="command")
    build_parser = subparsers.add_parser(
        "build-prototype001",
        help="Generate the complete Prototype001 FreeCAD build package.",
    )
    build_parser.add_argument(
        "--output",
        type=Path,
        default=Path("build"),
        help="Output directory (default: ./build).",
    )
    return parser


def _print_banner() -> None:
    """Print the original project status banner."""
    print("=" * 60)
    print(f" {PROJECT_NAME}")
    print(f" {PROJECT_MARK}")
    print()
    print(f" {MOTTO}")
    print("=" * 60)
    print()
    print(f"Version : {__version__}")
    print("Status  : GREEN BUILD")
    print()
    print("Lift-off successful.")
    print()
    print("Rolling on the river...")


def main(argv: Sequence[str] | None = None) -> None:
    """Run the selected CNCguitarwizard command."""
    parser = _create_parser()
    arguments = parser.parse_args(argv)
    if arguments.command is None:
        _print_banner()
        return

    if arguments.command == "build-prototype001":
        result = build_prototype001(arguments.output)
        print("Prototype001 build package created.")
        print(f"Output: {result.output_directory}")
        print(f"Macro:  {result.macro_path.name}")
        print(f"Python: {result.python_path.name}")
        print(f"Report: {result.report_path.name}")


if __name__ == "__main__":
    main()
