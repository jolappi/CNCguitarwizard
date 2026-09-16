"""Build all current Prototype001 FreeCAD deliverables."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..backends.freecad import FreeCADScriptExporter
from ..cam import (
    BodyMachiningPlan,
    FretboardMachiningParameters,
    FretboardMachiningPlan,
    GRBLWriter,
    MachiningParameters,
    NeckMachiningParameters,
    NeckMachiningPlan,
    plan_body_machining,
    plan_fretboard_machining,
    plan_neck_machining,
    render_setup_svg,
)
from ..presets import Prototype001Geometry, Prototype001Parameters
from ..version import PROJECT_MARK, PROJECT_NAME, __version__
from .exceptions import BuildWorkflowError, FreeCADExecutionError


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
    gcode_paths: tuple[Path, ...] = ()
    toolpath_preview_paths: tuple[Path, ...] = ()


class Prototype001Build:
    """A Prototype001 build split into stages a user interface can step through.

    ``build_prototype001`` runs every stage in one call. The browser front
    end instead calls ``advance()`` once per stage so it can repaint a
    progress bar in between — Pyodide runs Python on the page's own
    thread, so a single long call would freeze the page.

    Args:
        output_directory: Directory receiving all build artifacts.
        parameters: Optional parameter overrides for Prototype001.
        run_freecad: Execute FreeCAD and create `.FCStd` and `.step`.
        freecad_command: Optional explicit FreeCAD command-line executable.
        machining: Optional tool and feed overrides for the body G-code.
        neck_machining: Optional tool, blank and surfacing overrides for
            the neck G-code.
        fretboard_machining: Optional tool and blank overrides for the
            fretboard G-code.
    """

    def __init__(
        self,
        output_directory: Path,
        parameters: Prototype001Parameters | None = None,
        *,
        run_freecad: bool = True,
        freecad_command: Path | None = None,
        machining: MachiningParameters | None = None,
        neck_machining: NeckMachiningParameters | None = None,
        fretboard_machining: FretboardMachiningParameters | None = None,
    ) -> None:
        self.parameters = parameters or Prototype001Parameters()
        self.machining = machining or MachiningParameters()
        self.neck_machining = neck_machining or NeckMachiningParameters()
        self.fretboard_machining = fretboard_machining or FretboardMachiningParameters()
        self.run_freecad = run_freecad
        self.freecad_command = freecad_command
        self.destination = output_directory.expanduser().resolve()
        self.geometry: Prototype001Geometry | None = None
        self._plans: list[
            tuple[str, BodyMachiningPlan | NeckMachiningPlan | FretboardMachiningPlan]
        ] = []
        self._gcode_paths: list[Path] = []
        self._preview_paths: list[Path] = []
        self._gcode_report: dict[str, object] = {}
        self._stock_report: dict[str, object] = {}
        self._report: dict[str, object] = {}
        self._macro_path = self.destination / "Prototype001.FCMacro"
        self._python_path = self.destination / "Prototype001_freecad.py"
        self._fcstd_path = self.destination / "Prototype001.FCStd"
        self._step_path = self.destination / "Prototype001.step"
        self._report_path = self.destination / "build.json"
        self._freecad_log_path = self.destination / "freecad.log"
        self._stages: list[tuple[str, Callable[[], None]]] = [
            ("Building the geometry", self._build_geometry),
            ("Planning the body toolpaths", self._plan_body),
            ("Planning the neck toolpaths", self._plan_neck),
            ("Planning the fretboard toolpaths", self._plan_fretboard),
            ("Writing G-code and toolpath previews", self._write_gcode),
            ("Writing the FreeCAD script and report", self._write_script_and_report),
        ]
        if run_freecad:
            self._stages.append(("Running FreeCAD", self._run_freecad))
        self._completed = 0

    @property
    def labels(self) -> tuple[str, ...]:
        """Return every stage's label in running order."""
        return tuple(label for label, _ in self._stages)

    @property
    def completed(self) -> int:
        """Return how many stages have run."""
        return self._completed

    @property
    def done(self) -> bool:
        """Return whether every stage has run."""
        return self._completed >= len(self._stages)

    def advance(self) -> bool:
        """Run the next stage; return ``True`` while stages remain afterwards."""
        if self.done:
            return False
        _, stage = self._stages[self._completed]
        stage()
        self._completed += 1
        return not self.done

    @property
    def result(self) -> Prototype001BuildResult:
        """Return the finished build's artifact paths."""
        if not self.done:
            raise BuildWorkflowError("The build has not finished yet.")
        return Prototype001BuildResult(
            self.destination,
            self._macro_path,
            self._python_path,
            self._fcstd_path,
            self._step_path,
            self._report_path,
            self._freecad_log_path,
            gcode_paths=tuple(self._gcode_paths),
            toolpath_preview_paths=tuple(self._preview_paths),
        )

    # -- stages -----------------------------------------------------------

    def _build_geometry(self) -> None:
        self.geometry = self.parameters.build()
        self.destination.mkdir(parents=True, exist_ok=True)

    def _plan_body(self) -> None:
        assert self.geometry is not None
        self._plans.append(
            ("Body", plan_body_machining(self.geometry.body, self.machining))
        )

    def _plan_neck(self) -> None:
        assert self.geometry is not None
        self._plans.append(
            ("Neck", plan_neck_machining(self.geometry, self.neck_machining))
        )

    def _plan_fretboard(self) -> None:
        assert self.geometry is not None
        self._plans.append(
            (
                "Fretboard",
                plan_fretboard_machining(self.geometry, self.fretboard_machining),
            )
        )

    def _write_gcode(self) -> None:
        writer = GRBLWriter()
        for part, plan in self._plans:
            for setup, outline in zip(plan.setups, plan.preview_outlines, strict=True):
                gcode_path = self.destination / f"{setup.name}.nc"
                gcode_path.write_text(
                    writer.render(setup, self.machining), encoding="utf-8"
                )
                self._gcode_paths.append(gcode_path)
                preview_path = self.destination / f"{setup.name}.svg"
                preview_path.write_text(
                    render_setup_svg(setup, outline), encoding="utf-8"
                )
                self._preview_paths.append(preview_path)
                tool = setup.tool or self.machining
                self._gcode_report[setup.name] = {
                    "part": part,
                    "file": gcode_path.name,
                    "preview": preview_path.name,
                    "tool": f"{tool.tool_diameter:g} mm {tool.tool_tip}",
                    "operations": [path.name for path in setup.toolpaths],
                    "cutting_length_mm": round(setup.cutting_length(), 1),
                    "estimated_minutes": round(
                        setup.estimated_minutes(self.machining), 1
                    ),
                }
            self._stock_report[part] = {
                "length_mm": round(plan.stock_length, 1),
                "width_mm": round(plan.stock_width, 1),
                "thickness_mm": plan.stock_thickness,
                "work_origin_model_xy": [
                    round(plan.origin_x, 2),
                    round(plan.origin_y, 2),
                ],
                "index_pins_model_xy": [
                    [round(x, 2), round(y, 2)] for x, y in plan.index_pin_positions
                ],
                "index_pins_machine_xy": [
                    [round(x - plan.origin_x, 2), round(y - plan.origin_y, 2)]
                    for x, y in plan.index_pin_positions
                ],
            }

    def _write_script_and_report(self) -> None:
        assert self.geometry is not None
        exporter = FreeCADScriptExporter()
        source = exporter.render_prototype001(
            self.geometry,
            fcstd_path=self._fcstd_path,
            step_path=self._step_path,
        )
        exporter.write_script(self._macro_path, source)
        exporter.write_script(self._python_path, source)
        self._report = {
            "project": PROJECT_NAME,
            "mark": PROJECT_MARK,
            "version": __version__,
            "model": "Prototype001",
            "status": "freecad_pending" if self.run_freecad else "scripts_only",
            "generated_utc": datetime.now(UTC).isoformat(),
            "parameters": asdict(self.parameters),
            "script_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "generated_files": {
                "freecad_macro": self._macro_path.name,
                "freecad_python": self._python_path.name,
            },
            "freecad_targets": {
                "document": self._fcstd_path.name,
                "step": self._step_path.name,
            },
            "freecad_log": self._freecad_log_path.name,
            "machining": asdict(self.machining),
            "gcode": self._gcode_report,
            "stock": self._stock_report,
        }
        _write_report(self._report_path, self._report)

    def _run_freecad(self) -> None:
        try:
            executable = self.freecad_command or _find_freecad_command()
            self._fcstd_path.unlink(missing_ok=True)
            self._step_path.unlink(missing_ok=True)
            _execute_freecad(
                executable,
                self._python_path,
                self._fcstd_path,
                self._step_path,
                self._freecad_log_path,
            )
        except FreeCADExecutionError as error:
            self._report["status"] = "failed"
            self._report["error"] = str(error)
            _write_report(self._report_path, self._report)
            raise
        self._report["status"] = "complete"
        _write_report(self._report_path, self._report)


def build_prototype001(
    output_directory: Path,
    parameters: Prototype001Parameters | None = None,
    *,
    run_freecad: bool = True,
    freecad_command: Path | None = None,
    machining: MachiningParameters | None = None,
    neck_machining: NeckMachiningParameters | None = None,
    fretboard_machining: FretboardMachiningParameters | None = None,
) -> Prototype001BuildResult:
    """Generate scripts, FreeCAD models, G-code, and a traceable JSON report.

    Runs every stage of a ``Prototype001Build`` and returns the paths of
    every generated or FreeCAD-targeted artifact; see the class for the
    arguments.
    """
    build = Prototype001Build(
        output_directory,
        parameters,
        run_freecad=run_freecad,
        freecad_command=freecad_command,
        machining=machining,
        neck_machining=neck_machining,
        fretboard_machining=fretboard_machining,
    )
    while build.advance():
        pass
    return build.result


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
