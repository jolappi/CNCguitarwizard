"""Build all current Prototype001 FreeCAD deliverables."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..backends.freecad import FreeCADScriptExporter
from ..presets import Prototype001Parameters
from ..version import PROJECT_MARK, PROJECT_NAME, __version__
from .exceptions import FreeCADExecutionError


@dataclass(frozen=True, slots=True)
class Prototype001BuildResult:
    """List the files created by one Prototype001 build."""

    output_directory: Path
    macro_path: Path
    python_path: Path
    fcstd_path: Path
    step_path: Path
    report_path: Path
    freecad_log_path: Path


def build_prototype001(
    output_directory: Path,
    parameters: Prototype001Parameters | None = None,
    *,
    run_freecad: bool = True,
    freecad_command: Path | None = None,
) -> Prototype001BuildResult:
    """Generate scripts, FreeCAD models, and a traceable JSON report.

    Args:
        output_directory: Directory receiving all build artifacts.
        parameters: Optional parameter overrides for Prototype001.
        run_freecad: Execute FreeCAD and create `.FCStd` and `.step`.
        freecad_command: Optional explicit FreeCAD command-line executable.

    Returns:
        Paths for every generated or FreeCAD-targeted artifact.
    """
    selected_parameters = parameters or Prototype001Parameters()
    geometry = selected_parameters.build()
    destination = output_directory.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    macro_path = destination / "Prototype001.FCMacro"
    python_path = destination / "Prototype001_freecad.py"
    fcstd_path = destination / "Prototype001.FCStd"
    step_path = destination / "Prototype001.step"
    report_path = destination / "build.json"
    freecad_log_path = destination / "freecad.log"

    exporter = FreeCADScriptExporter()
    source = exporter.render_prototype001(
        geometry,
        fcstd_path=fcstd_path,
        step_path=step_path,
    )
    exporter.write_script(macro_path, source)
    exporter.write_script(python_path, source)

    report = {
        "project": PROJECT_NAME,
        "mark": PROJECT_MARK,
        "version": __version__,
        "model": "Prototype001",
        "status": "freecad_pending" if run_freecad else "scripts_only",
        "generated_utc": datetime.now(UTC).isoformat(),
        "parameters": asdict(selected_parameters),
        "script_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "generated_files": {
            "freecad_macro": macro_path.name,
            "freecad_python": python_path.name,
        },
        "freecad_targets": {
            "document": fcstd_path.name,
            "step": step_path.name,
        },
        "freecad_log": freecad_log_path.name,
    }
    _write_report(report_path, report)

    if run_freecad:
        try:
            executable = freecad_command or _find_freecad_command()
            fcstd_path.unlink(missing_ok=True)
            step_path.unlink(missing_ok=True)
            _execute_freecad(
                executable,
                python_path,
                fcstd_path,
                step_path,
                freecad_log_path,
            )
        except FreeCADExecutionError as error:
            report["status"] = "failed"
            report["error"] = str(error)
            _write_report(report_path, report)
            raise
        report["status"] = "complete"
        _write_report(report_path, report)

    return Prototype001BuildResult(
        destination,
        macro_path,
        python_path,
        fcstd_path,
        step_path,
        report_path,
        freecad_log_path,
    )


def _write_report(path: Path, report: Mapping[str, object]) -> None:
    """Write the current build state as formatted JSON."""
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _find_freecad_command() -> Path:
    """Return an available FreeCAD command-line executable."""
    configured = os.environ.get("FREECAD_CMD")
    if configured:
        executable = Path(configured).expanduser()
        if executable.is_file():
            return executable
        raise FreeCADExecutionError(
            f"FREECAD_CMD does not point to a file: {executable}"
        )

    for command_name in ("freecadcmd", "FreeCADCmd"):
        discovered = shutil.which(command_name)
        if discovered is not None:
            return Path(discovered)

    macos_command = Path(
        "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
    )
    if macos_command.is_file():
        return macos_command

    raise FreeCADExecutionError(
        "FreeCAD command-line tool was not found. Install FreeCAD, set "
        "FREECAD_CMD, pass --freecad-command, or use --scripts-only."
    )


def _execute_freecad(
    executable: Path,
    script_path: Path,
    fcstd_path: Path,
    step_path: Path,
    log_path: Path,
) -> None:
    """Run FreeCAD and verify that both requested model files exist."""
    command = [str(executable), str(script_path)]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        log_path.write_text(
            f"Command: {' '.join(command)}\nLaunch error: {error}\n",
            encoding="utf-8",
        )
        raise FreeCADExecutionError(
            f"FreeCAD could not be launched: {error}"
        ) from error

    log_path.write_text(
        (
            f"Command: {' '.join(command)}\n"
            f"Exit code: {completed.returncode}\n\n"
            f"STDOUT\n{completed.stdout}\n\n"
            f"STDERR\n{completed.stderr}\n"
        ),
        encoding="utf-8",
    )
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()
        raise FreeCADExecutionError(
            f"FreeCAD exited with code {completed.returncode}: {details}"
        )

    missing = [
        path.name for path in (fcstd_path, step_path) if not path.is_file()
    ]
    if missing:
        raise FreeCADExecutionError(
            "FreeCAD finished without creating: " + ", ".join(missing)
        )
