"""Build all current Prototype001 FreeCAD deliverables."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..backends.freecad import FreeCADScriptExporter
from ..presets import Prototype001Parameters
from ..version import PROJECT_MARK, PROJECT_NAME, __version__


@dataclass(frozen=True, slots=True)
class Prototype001BuildResult:
    """List the files created by one Prototype001 build."""

    output_directory: Path
    macro_path: Path
    python_path: Path
    fcstd_path: Path
    step_path: Path
    report_path: Path


def build_prototype001(
    output_directory: Path,
    parameters: Prototype001Parameters | None = None,
) -> Prototype001BuildResult:
    """Generate FreeCAD scripts and a traceable JSON build report.

    The `.FCStd` and `.step` paths are targets embedded in the generated
    scripts. FreeCAD creates those two files when either script is executed.

    Args:
        output_directory: Directory receiving all build artifacts.
        parameters: Optional parameter overrides for Prototype001.

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
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return Prototype001BuildResult(
        destination,
        macro_path,
        python_path,
        fcstd_path,
        step_path,
        report_path,
    )
