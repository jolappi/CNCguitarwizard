"""Command-line entry point for CNCguitarwizard."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from cncguitarwizard.backends.freecad import EXPORT_FORMATS
from cncguitarwizard.design_tools import (
    DesignFileError,
    check_design,
    describe_settings,
    new_design,
    read_design,
    set_values,
    write_design,
)
from cncguitarwizard.exceptions import CNCGuitarWizardError
from cncguitarwizard.presets.prototype001 import INSTRUMENT_OVERRIDES
from cncguitarwizard.presets.styles import STYLES
from cncguitarwizard.version import (
    MOTTO,
    PROJECT_MARK,
    PROJECT_NAME,
    __version__,
)
from cncguitarwizard.webapp import LoadedDesign, load_design
from cncguitarwizard.workflows import (
    FreeCADExecutionError,
    build_prototype001,
    export_prototype001_formats,
)


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
    export_parser = subparsers.add_parser(
        "export-prototype001",
        help=(
            "Export a finished build's FreeCAD model to other 3D formats, each "
            "part a file and the whole model one, without building again."
        ),
    )
    export_parser.add_argument(
        "--output",
        type=Path,
        default=Path("build"),
        help="The build's folder, its Prototype001.FCStd made (default: ./build).",
    )
    export_parser.add_argument(
        "--format",
        dest="formats",
        action="append",
        choices=[*EXPORT_FORMATS, "all"],
        required=True,
        help=(
            "A format to export to, again for more: "
            + "; ".join(EXPORT_FORMATS.values())
            + "; all for every one."
        ),
    )
    export_parser.add_argument(
        "--freecad-command",
        type=Path,
        help="Explicit path to freecadcmd or FreeCADCmd.",
    )
    settings_parser = subparsers.add_parser(
        "settings",
        help="List the settings: type, default, value in a design and meaning.",
    )
    settings_parser.add_argument(
        "--design",
        type=Path,
        help="A design file: each setting's value in it, and whether it does "
        "anything there.",
    )
    settings_parser.add_argument(
        "--search",
        default="",
        help="Words every setting listed has in its name or meaning.",
    )
    settings_parser.add_argument(
        "--group",
        default="",
        help='Only one form group\'s settings ("Neck", "Machining").',
    )
    settings_parser.add_argument(
        "--changed",
        action="store_true",
        help="Only the settings the design changed from its defaults.",
    )
    settings_parser.add_argument("--json", action="store_true", help="Print JSON.")
    new_parser = subparsers.add_parser(
        "new-design",
        help="Start a design file from an instrument's defaults or one of its styles.",
    )
    new_parser.add_argument(
        "--instrument", required=True, choices=list(INSTRUMENT_OVERRIDES)
    )
    new_parser.add_argument(
        "--style",
        choices=list(STYLES),
        help="A style, offered for some instruments only: "
        + "; ".join(
            f"{key} ({', '.join(style.instruments)})" for key, style in STYLES.items()
        )
        + ".",
    )
    new_parser.add_argument("--name", default="", help="The guitar's name.")
    new_parser.add_argument("--output", type=Path, required=True)
    new_parser.add_argument(
        "--force", action="store_true", help="Replace a file already there."
    )
    new_parser.add_argument("--json", action="store_true", help="Print JSON.")
    set_parser = subparsers.add_parser(
        "set",
        help="Change a design's settings; kept only when it still builds and "
        "checks (or an unfinished design gets no worse).",
    )
    set_parser.add_argument("--design", type=Path, required=True)
    set_parser.add_argument(
        "--output",
        type=Path,
        help="Write the changed design here instead of over --design.",
    )
    set_parser.add_argument("--json", action="store_true", help="Print JSON.")
    set_parser.add_argument(
        "assignments",
        nargs="+",
        metavar="NAME=VALUE",
        help="A setting and its new value (scale_length=25.5in, "
        "body_bridge=floyd_rose, body_bridge.string_count=7).",
    )
    check_parser = subparsers.add_parser(
        "check",
        help="Check a design: it builds, no editor shows a problem, and its "
        "parameter sheet is ready for human review.",
    )
    check_parser.add_argument("--design", type=Path, required=True)
    check_parser.add_argument("--json", action="store_true", help="Print JSON.")
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
        report = json.loads(result.report_path.read_text(encoding="utf-8"))
        sheet_status = report["parameter_sheet"]["status"]
        print(f"Sheet:  {result.parameter_sheet_path.name} ({sheet_status})")
        print("G-code: " + ", ".join(path.name for path in result.gcode_paths))
        print("DXF:    " + ", ".join(path.name for path in result.dxf_paths))
        if arguments.scripts_only:
            print("FCStd and STEP will be created when a script runs in FreeCAD.")
        else:
            print(f"Log:    {result.freecad_log_path.name}")
            print(f"FCStd:  {result.fcstd_path.name}")
            print(f"STEP:   {result.step_path.name}")
            print(f"Check:  {result.model_check_status} (build.json, model_check)")
    elif arguments.command == "export-prototype001":
        formats = (
            list(EXPORT_FORMATS)
            if "all" in arguments.formats
            else list(dict.fromkeys(arguments.formats))
        )
        try:
            written = export_prototype001_formats(
                arguments.output,
                formats,
                freecad_command=arguments.freecad_command,
            )
        except (FreeCADExecutionError, CNCGuitarWizardError) as error:
            parser.error(str(error))
        print(f"Prototype001 exported to {', '.join(formats)}.")
        print(f"Output: {arguments.output}")
        for path in written:
            print(f"        {path.name}")
    else:
        try:
            _run_design_command(parser, arguments)
        except DesignFileError as error:
            parser.error(str(error))


def _run_design_command(
    parser: argparse.ArgumentParser, arguments: argparse.Namespace
) -> None:
    """Run ``settings``, ``new-design``, ``set`` or ``check``.

    ``set`` and ``check`` end with exit code 1 when the design is not kept
    or not OK.

    Raises:
        DesignFileError: If a design cannot be read, made or changed.
    """
    if arguments.command == "settings":
        if arguments.changed and arguments.design is None:
            parser.error("--changed needs --design.")
        design = read_design(arguments.design) if arguments.design else None
        entries = describe_settings(
            design, arguments.search, arguments.group, arguments.changed
        )
        if arguments.json:
            _print_json(entries)
        else:
            _print_settings(entries)
    elif arguments.command == "new-design":
        if arguments.output.exists() and not arguments.force:
            parser.error(f"{arguments.output} exists; --force replaces it.")
        design = new_design(arguments.instrument, arguments.style, arguments.name)
        write_design(arguments.output, design)
        check = check_design(design)
        if arguments.json:
            _print_json({"saved": str(arguments.output), "check": check})
        else:
            print(f"Saved {arguments.output}")
            _print_check(check)
    elif arguments.command == "set":
        result = set_values(read_design(arguments.design), arguments.assignments)
        path = arguments.output or arguments.design
        if result["keep"]:
            write_design(path, result["design"])
        if arguments.json:
            shown = {key: value for key, value in result.items() if key != "design"}
            _print_json({"saved": str(path) if result["keep"] else None, **shown})
        else:
            _print_changes(result)
            print(f"Saved {path}" if result["keep"] else f"Not saved: {path} as it was")
        if not result["keep"]:
            raise SystemExit(1)
    elif arguments.command == "check":
        check = check_design(read_design(arguments.design))
        if arguments.json:
            _print_json(check)
        else:
            _print_check(check)
        if not check["ok"]:
            raise SystemExit(1)


def _print_json(value: object) -> None:
    """Print ``value`` as indented JSON."""
    print(json.dumps(value, indent=2, ensure_ascii=False))


def _shown(value: object) -> str:
    """Return a setting's value as the command line shows it: a bridge or
    body shape by its kind (``--json`` shows its fields)."""
    if isinstance(value, dict) and "kind" in value:
        return f"{value['kind']} (+{len(value) - 1} fields)"
    return json.dumps(value, ensure_ascii=False)


def _needs(conditions: list[dict[str, list[Any]]]) -> str:
    """Return what a setting needs to do anything, in words: any one of its
    conditions, each the values other settings must have."""
    return "it needs " + " or ".join(
        " and ".join(
            f"{other} {'/'.join(map(str, allowed))}"
            for other, allowed in condition.items()
        )
        for condition in conditions
    )


def _print_settings(entries: list[dict[str, Any]]) -> None:
    """Print settings one to a line, each with its meaning's first sentence."""
    for entry in entries:
        value = entry.get("value", entry["default"])
        note = (
            ""
            if entry.get("applies", True)
            else f"  [does nothing here: {_needs(entry['applies_when'])}]"
        )
        print(
            f"{entry['name']} = {_shown(value)}  "
            f"({entry['type']}, default {_shown(entry['default'])}){note}"
        )
        for key in ("options", "kinds"):
            if isinstance(entry.get(key), list):
                print(f"    {key}: {', '.join(map(str, entry[key]))}")
        meaning = str(entry["help"]).split(". ")[0]
        if len(meaning) > 160:
            meaning = meaning[:160].rsplit(" ", 1)[0] + " ..."
        if meaning:
            print(f"    {meaning}")


def _print_check(check: dict[str, Any]) -> None:
    """Print a design's check, its verdict last."""
    print(f"Design: {check['name'] or '(no name)'} ({check['instrument']})")
    if check["error"]:
        print(f"Does not build: {check['error']}")
    for problem in check["problems"]:
        print(f"Problem: {problem}")
    if check["skipped"]:
        print("Skipped, unknown here: " + ", ".join(check["skipped"]))
    sheet = check["sheet"]
    if isinstance(sheet, dict):
        failed = [item["name"] for item in sheet["checks"] if not item["passed"]]
        print(
            f"Parameter sheet: {sheet['status']}"
            + (f" (failed: {', '.join(failed)})" if failed else "")
        )
    print(f"Changed from the instrument's defaults: {len(check['changed'])} settings")
    print("OK: ready for human review" if check["ok"] else "NOT OK")


def _print_changes(result: dict[str, Any]) -> None:
    """Print what ``set`` changed, refused and found."""
    for change in result["changes"]:
        print(f"{change['name']}: {_shown(change['from'])} -> {_shown(change['to'])}")
    if result["unchanged"]:
        print("Already so: " + ", ".join(result["unchanged"]))
    for idle in result["not_applied"]:
        print(f"{idle['name']} does nothing here: {_needs(idle['applies_when'])}")
    for refusal in result["rejected"]:
        print(f"Refused {refusal['assignment']}: {refusal['reason']}")
    if isinstance(result["check"], dict):
        _print_check(result["check"])


if __name__ == "__main__":
    main()
