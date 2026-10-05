"""Command-line entry point for CNCguitarwizard."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from cncguitarwizard.exceptions import CNCGuitarWizardError
from cncguitarwizard.version import (
    MOTTO,
    PROJECT_MARK,
    PROJECT_NAME,
    __version__,
)
from cncguitarwizard.webapp import LoadedDesign, load_design
from cncguitarwizard.workflows import FreeCADExecutionError, build_prototype001


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
    build_parser.add_argument(
        "--design",
        type=Path,
        help=(
            "A design saved with the web app's Save design (JSON) to build "
            "instead of the default Prototype001."
        ),
    )
    build_parser.add_argument(
        "--scripts-only",
        action="store_true",
        help="Create FreeCAD scripts without executing FreeCAD.",
    )
    build_parser.add_argument(
        "--freecad-command",
        type=Path,
        help="Explicit path to freecadcmd or FreeCADCmd.",
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


def _read_design(parser: argparse.ArgumentParser, path: Path) -> LoadedDesign:
    """Read a saved design, or end with the reason it cannot be built."""
    try:
        design = load_design(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, CNCGuitarWizardError, TypeError, ValueError) as error:
        parser.error(f"{path}: {error}")
    print(f"Design: {path.name}" + (f" ({design.name})" if design.name else ""))
    if design.skipped:
        print(
            "Skipped settings this version does not know: " + ", ".join(design.skipped)
        )
    return design


def main(argv: Sequence[str] | None = None) -> None:
    """Run the selected CNCguitarwizard command."""
    parser = _create_parser()
    arguments = parser.parse_args(argv)
    if arguments.command is None:
        _print_banner()
        return

    if arguments.command == "build-prototype001":
        design = None
        if arguments.design is not None:
            design = _read_design(parser, arguments.design)
        try:
            result = build_prototype001(
                arguments.output,
                design.parameters if design else None,
                run_freecad=not arguments.scripts_only,
                freecad_command=arguments.freecad_command,
                machining=design.machining if design else None,
            )
        except FreeCADExecutionError as error:
            parser.error(str(error))
        except CNCGuitarWizardError as error:
            parser.error(f"{arguments.design or 'Prototype001'}: {error}")
        print("Prototype001 build package created.")
        print(f"Output: {result.output_directory}")
        print(f"Macro:  {result.macro_path.name}")
        print(f"Python: {result.python_path.name}")
        print(f"Report: {result.report_path.name}")
        print(f"Log:    {result.freecad_log_path.name}")
        print("G-code: " + ", ".join(path.name for path in result.gcode_paths))
        print("DXF:    " + ", ".join(path.name for path in result.dxf_paths))
        if arguments.scripts_only:
            print("FCStd and STEP will be created when a script runs in FreeCAD.")
        else:
            print(f"FCStd:  {result.fcstd_path.name}")
            print(f"STEP:   {result.step_path.name}")


if __name__ == "__main__":
    main()
