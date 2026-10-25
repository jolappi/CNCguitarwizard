"""The built FreeCAD model checked against the design's parameter sheet.

After FreeCAD has made ``Prototype001.FCStd`` and its STEP, the build
measures them in FreeCAD (``backends.freecad.measure``) and checks what
was found here: the model holds its parts, each a valid solid; the STEP,
read back, holds the same solids in the same place; the model holds its
``Parameters`` spreadsheet; and a bolt-on or set neck's body solid is as
long, as wide and as deep as the sheet says. Like the sheet, the result
is ``READY FOR HUMAN REVIEW`` at best: a person still reviews the model.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from ..presets import Prototype001Parameters
from .exceptions import FreeCADExecutionError
from .parameter_sheet import DECIMALS, ParameterSheet, SheetCheck, review_status

MODEL_TOLERANCE = 0.01
"""How far, in mm, a measured size may lie from the expected one."""

NECK_PARTS = ("NeckBack", "Fretboard")
"""The parts every model holds, by their FreeCAD names."""


@dataclass(frozen=True, slots=True)
class MeasuredShape:
    """A shape as FreeCAD measured it.

    Args:
        valid: Whether FreeCAD finds the shape valid (``isValid``).
        solids: How many solids it holds.
        box: Its bounding box, ``(xmin, ymin, zmin, xmax, ymax, zmax)``
            in mm.
    """

    valid: bool
    solids: int
    box: tuple[float, ...]

    def as_dict(self) -> dict[str, object]:
        """Return the shape as JSON-ready data, its box to ``DECIMALS``."""
        return {
            "valid": self.valid,
            "solids": self.solids,
            "box": [round(value, DECIMALS) for value in self.box],
        }


@dataclass(frozen=True, slots=True)
class MeasuredModel:
    """The finished model as FreeCAD measured it.

    Args:
        parts: Each solid part shown in the model, by its FreeCAD name.
        step: The STEP, read back into a shape of its own.
        has_sheet: Whether the model holds its ``Parameters`` spreadsheet.
    """

    parts: Mapping[str, MeasuredShape]
    step: MeasuredShape
    has_sheet: bool


@dataclass(frozen=True, slots=True)
class ModelCheck:
    """The measured model and the checks of it.

    Args:
        model: What FreeCAD measured.
        checks: The checks of it (see ``model_check``).
    """

    model: MeasuredModel
    checks: tuple[SheetCheck, ...]

    @property
    def status(self) -> str:
        """Return the checks' ``review_status``."""
        return review_status(self.checks)

    def as_dict(self) -> dict[str, object]:
        """Return the check as JSON-ready data, for ``build.json``.

        Returns:
            ``{"status", "checks", "parts", "step", "sheet"}``.
        """
        return {
            "status": self.status,
            "checks": [check.as_dict() for check in self.checks],
            "parts": {
                name: shape.as_dict() for name, shape in self.model.parts.items()
            },
            "step": self.model.step.as_dict(),
            "sheet": self.model.has_sheet,
        }


def measured_model(found: Mapping[str, Any]) -> MeasuredModel:
    """Return what the measuring script printed as a ``MeasuredModel``.

    Args:
        found: The script's JSON object (``read_measured``).

    Returns:
        The measured model.

    Raises:
        FreeCADExecutionError: If the measurements do not read.
    """
    try:
        return MeasuredModel(
            parts={
                str(name): _measured_shape(shape)
                for name, shape in found["parts"].items()
            },
            step=_measured_shape(found["step"]),
            has_sheet=bool(found["sheet"]),
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise FreeCADExecutionError(
            f"FreeCAD's measurements of the model do not read: {error!r}"
        ) from error


def model_check(
    model: MeasuredModel,
    parameters: Prototype001Parameters,
    sheet: ParameterSheet,
) -> ModelCheck:
    """Return the checks of a measured model against its design.

    Args:
        model: What FreeCAD measured.
        parameters: The design the model was built from.
        sheet: The design's parameter sheet.

    Returns:
        The model and its checks: its parts are there and valid, the STEP
        matches it, the spreadsheet is in it and, for a neck in a pocket
        (bolt-on or set), the body's length, width and depth.
    """
    wanted = NECK_PARTS if parameters.neck_runs_through else (*NECK_PARTS, "Body")
    if parameters.cap_thickness > 0.0:
        # The core is the Body; its separate top a part of its own.
        wanted = (*wanted, "Top")
    parts = model.parts
    checks = [
        _count(
            "model_holds_its_parts",
            f"The model holds {', '.join(wanted)}.",
            len(wanted),
            sum(name in parts for name in wanted),
        ),
        _count(
            "model_parts_are_valid",
            "Every solid part of the model is a valid shape.",
            len(parts),
            sum(shape.valid for shape in parts.values()),
        ),
        _count(
            "step_is_valid",
            "The STEP, read back, is a valid shape.",
            1,
            int(model.step.valid),
        ),
        _count(
            "step_holds_the_model_solids",
            "The STEP, read back, holds as many solids as the model's parts.",
            sum(shape.solids for shape in parts.values()),
            model.step.solids,
        ),
        _count(
            "model_holds_its_parameters",
            "The model holds its Parameters spreadsheet.",
            1,
            int(model.has_sheet),
        ),
    ]
    if parts:
        checks.append(
            SheetCheck(
                name="step_lies_where_the_model_does",
                description=(
                    "The largest difference between the STEP's box and "
                    "the model's: no part moved or scaled on export."
                ),
                expected=0.0,
                actual=_box_difference(_union(parts.values()), model.step.box),
                tolerance=MODEL_TOLERANCE,
                unit="mm",
            )
        )
    body = parts.get("Body")
    if body is not None and not parameters.neck_runs_through:
        xmin, ymin, zmin, xmax, ymax, _ = body.box
        checks += [
            SheetCheck(
                name="body_length_in_model",
                description="The body solid is as long as body_length.",
                expected=_sheet_number(sheet, "body_length"),
                actual=xmax - xmin,
                tolerance=MODEL_TOLERANCE,
                unit="mm",
            ),
            SheetCheck(
                name="body_width_in_model",
                description="The body solid is as wide as body_width.",
                expected=_sheet_number(sheet, "body_width"),
                actual=ymax - ymin,
                tolerance=MODEL_TOLERANCE,
                unit="mm",
            ),
            SheetCheck(
                name="body_back_at_thickness",
                description=(
                    "The body's back lies body_thickness below its top "
                    "(Z = 0); a carved top rises above it."
                ),
                expected=_sheet_number(sheet, "body_thickness"),
                actual=-zmin,
                tolerance=MODEL_TOLERANCE,
                unit="mm",
            ),
        ]
    return ModelCheck(model=model, checks=tuple(checks))


def _measured_shape(found: Mapping[str, Any]) -> MeasuredShape:
    """Return one measured shape, its box six numbers."""
    box = tuple(float(value) for value in found["box"])
    if len(box) != 6:
        raise ValueError(f"a box has six values, not {len(box)}")
    return MeasuredShape(
        valid=bool(found["valid"]), solids=int(found["solids"]), box=box
    )


def _count(name: str, description: str, expected: int, actual: int) -> SheetCheck:
    """Return a check that two counts are equal."""
    return SheetCheck(
        name=name,
        description=description,
        expected=float(expected),
        actual=float(actual),
        tolerance=0.0,
        unit="",
    )


def _union(shapes: Iterable[MeasuredShape]) -> tuple[float, ...]:
    """Return the box holding every shape's box."""
    boxes = [shape.box for shape in shapes]
    return (
        *(min(box[axis] for box in boxes) for axis in range(3)),
        *(max(box[axis] for box in boxes) for axis in range(3, 6)),
    )


def _box_difference(first: tuple[float, ...], second: tuple[float, ...]) -> float:
    """Return the largest difference between two boxes' corresponding values."""
    return max(abs(a - b) for a, b in zip(first, second, strict=True))


def _sheet_number(sheet: ParameterSheet, name: str) -> float:
    """Return a number on the sheet, by its name."""
    value = next(row.value for row in sheet.rows if row.name == name)
    if not isinstance(value, int | float):
        raise TypeError(f"{name} is not a number on the parameter sheet.")
    return float(value)
