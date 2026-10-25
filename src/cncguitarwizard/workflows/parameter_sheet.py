"""The design's key dimensions on one sheet, checked against its geometry.

A parameter sheet sums a design up for a person to review before cutting:
the settings that decide the instrument's size (scale, frets, neck, body),
where each value came from, a few values derived from the built geometry,
and deterministic checks of that geometry against the equal-tempered
formula. Its status says whether every check passed; it never says the
design is ready to cut, only that it is ready for a person to review.

The build writes it into ``build.json`` (``parameter_sheet``), as
``Prototype001_parameters.csv`` and into the FreeCAD model as its
``Parameters`` spreadsheet. All dimensions are millimetres, all angles
degrees.
"""

from __future__ import annotations

import csv
import io
import math
from collections.abc import Iterable
from dataclasses import dataclass

from ..geometry.primitives import Line2D
from ..presets import Prototype001Geometry, Prototype001Parameters

SHEET_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("Instrument", "instrument", ""),
    ("Instrument", "handedness", ""),
    ("Instrument", "string_count", ""),
    ("Scale and frets", "scale_length", "mm"),
    ("Scale and frets", "bass_scale_length", "mm"),
    ("Scale and frets", "fret_count", ""),
    ("Scale and frets", "frets_per_octave", ""),
    ("Scale and frets", "fret_slant_angle", "deg"),
    ("Neck", "neck_joint", ""),
    ("Neck", "nut_width", "mm"),
    ("Neck", "final_fret_width", "mm"),
    ("Neck", "heel_width", "mm"),
    ("Neck", "first_fret_thickness", "mm"),
    ("Neck", "twelfth_fret_thickness", "mm"),
    ("Neck", "neck_angle", "deg"),
    ("Neck", "headstock_angle", "deg"),
    ("Strings", "nut_string_spacing", "mm"),
    ("Strings", "bridge_string_spacing", "mm"),
    ("Fretboard", "fretboard_radius", "mm"),
    ("Fretboard", "fretboard_thickness", "mm"),
    ("Fretboard", "fret_slot_width", "mm"),
    ("Fretboard", "fret_slot_depth", "mm"),
    ("Fretboard", "fret_height", "mm"),
    ("Body", "body_shape", ""),
    ("Body", "body_bridge", ""),
    ("Body", "body_thickness", "mm"),
    ("Body", "body_cap_thickness", "mm"),
    ("Body", "body_neck_pocket_length", "mm"),
    ("Body", "body_neck_pocket_clearance", "mm"),
)
"""The settings on the sheet, in its order: ``(group, field name, unit)``.
A unit of ``""`` is a count or a choice."""

DEFAULT = "default"
"""Source of a setting at the plain Prototype001 default."""

INSTRUMENT = "instrument"
"""Source of a setting the chosen instrument's defaults set."""

DESIGN = "design"
"""Source of a setting the design itself changed (by hand or a style)."""

DERIVED = "derived"
"""Source of a value worked out from the built geometry."""

READY_FOR_REVIEW = "READY FOR HUMAN REVIEW"
"""Status of a sheet whose every check passed."""

REVIEW_REQUIRED = "REVIEW REQUIRED"
"""Status of a sheet with a check that failed."""

FRET_TOLERANCE = 0.01
"""How far, in mm, a fret slot may lie from its equal-tempered place."""

DECIMALS = 4
"""Decimals the derived values and checks are written with (0.1 µm)."""

TO_CONFIRM: tuple[str, ...] = (
    "Hardware: measure the bridge, pickups, tuners and controls in hand "
    "against their cutouts; the footprints are the generic ones.",
    "Intonation: the saddle line is nominal, the saddles at the middle of "
    "their travel; set the compensation on the finished instrument.",
    "Machining: check each program's units, work zero, tool and the "
    "machine's travel, simulate it and air-cut it before cutting stock.",
)
"""What a person must still confirm, whatever the checks say."""

CSV_COLUMNS = (
    "group",
    "name",
    "value",
    "unit",
    "source",
    "expected",
    "tolerance",
    "result",
)
"""The CSV file's columns."""

SheetValue = str | int | float | None
"""A value on the sheet: a choice, a count, a dimension or nothing."""


@dataclass(frozen=True, slots=True)
class SheetRow:
    """One value on the sheet.

    Args:
        group: The part of the instrument it belongs to ("Neck").
        name: The setting's field name, or the derived value's name.
        value: The value; ``None`` where the setting is left empty.
        unit: ``"mm"``, ``"deg"`` or ``""`` for a count or a choice.
        source: ``DEFAULT``, ``INSTRUMENT``, ``DESIGN`` or ``DERIVED``.
    """

    group: str
    name: str
    value: SheetValue
    unit: str
    source: str


@dataclass(frozen=True, slots=True)
class SheetCheck:
    """One deterministic check of the built geometry.

    Args:
        name: Short identifier, e.g. ``"octave_fret_at_half_scale"``.
        description: What is checked, in words.
        expected: The value the geometry must have.
        actual: The value it has.
        tolerance: How far ``actual`` may lie from ``expected``.
        unit: The unit of the three values.
    """

    name: str
    description: str
    expected: float
    actual: float
    tolerance: float
    unit: str

    @property
    def passed(self) -> bool:
        """Return whether ``actual`` lies within ``tolerance`` of ``expected``."""
        return abs(self.actual - self.expected) <= self.tolerance

    def as_dict(self) -> dict[str, object]:
        """Return the check as JSON-ready data, its values to ``DECIMALS``."""
        return {
            "name": self.name,
            "description": self.description,
            "expected": round(self.expected, DECIMALS),
            "actual": round(self.actual, DECIMALS),
            "tolerance": self.tolerance,
            "unit": self.unit,
            "passed": self.passed,
        }


def review_status(checks: Iterable[SheetCheck]) -> str:
    """Return ``READY_FOR_REVIEW`` if every check passed, else
    ``REVIEW_REQUIRED``."""
    if all(check.passed for check in checks):
        return READY_FOR_REVIEW
    return REVIEW_REQUIRED


@dataclass(frozen=True, slots=True)
class ParameterSheet:
    """A design's key dimensions, derived values and checks.

    Args:
        rows: The settings (``SHEET_FIELDS``) and the derived values.
        checks: The checks of the built geometry.
        to_confirm: What a person must still confirm (``TO_CONFIRM``).
    """

    rows: tuple[SheetRow, ...]
    checks: tuple[SheetCheck, ...]
    to_confirm: tuple[str, ...] = TO_CONFIRM

    @property
    def status(self) -> str:
        """Return the sheet's ``review_status``."""
        return review_status(self.checks)

    def as_dict(self) -> dict[str, object]:
        """Return the sheet as JSON-ready data, for ``build.json``.

        Returns:
            ``{"status", "rows", "checks", "to_confirm"}``.
        """
        return {
            "status": self.status,
            "rows": [
                {
                    "group": row.group,
                    "name": row.name,
                    "value": row.value,
                    "unit": row.unit,
                    "source": row.source,
                }
                for row in self.rows
            ],
            "checks": [check.as_dict() for check in self.checks],
            "to_confirm": list(self.to_confirm),
        }

    def as_table(self) -> tuple[tuple[str, ...], ...]:
        """Return the sheet as a table of text, one row a value.

        The first row is ``CSV_COLUMNS``. The status comes next, then the
        settings, the derived values, the checks (``source`` "check",
        ``value`` the actual value) and what is left to confirm. Every
        row's ``name`` (second column) names its ``value`` (third).

        Returns:
            The rows, each as long as ``CSV_COLUMNS``; an empty cell is
            ``""``.
        """
        table = [
            CSV_COLUMNS,
            ("Status", "status", self.status, "", "", "", "", ""),
        ]
        for row in self.rows:
            table.append(
                (row.group, row.name, _cell(row.value), row.unit, row.source)
                + ("", "", "")
            )
        for check in self.checks:
            table.append(
                (
                    "Check",
                    check.name,
                    _cell(round(check.actual, DECIMALS)),
                    check.unit,
                    "check",
                    _cell(round(check.expected, DECIMALS)),
                    _cell(check.tolerance),
                    "passed" if check.passed else "failed",
                )
            )
        for number, item in enumerate(self.to_confirm, start=1):
            table.append(("To confirm", f"confirm_{number}", item, "", "", "", "", ""))
        return tuple(table)

    def as_csv(self) -> str:
        """Return the sheet as CSV text: ``as_table``, one line a row.

        Returns:
            The CSV text, rows ending in ``\\n``.
        """
        buffer = io.StringIO()
        csv.writer(buffer, lineterminator="\n").writerows(self.as_table())
        return buffer.getvalue()


def parameter_sheet(
    parameters: Prototype001Parameters, geometry: Prototype001Geometry
) -> ParameterSheet:
    """Return the parameter sheet of a design and its built geometry.

    Args:
        parameters: The design's settings.
        geometry: ``parameters.build()``.

    Returns:
        The sheet: the settings in ``SHEET_FIELDS``, the derived values
        and the checks.
    """
    rows = _setting_rows(parameters) + _derived_rows(parameters, geometry)
    return ParameterSheet(rows=rows, checks=_checks(parameters, geometry))


def _setting_rows(parameters: Prototype001Parameters) -> tuple[SheetRow, ...]:
    """Return the ``SHEET_FIELDS`` settings, each with its source."""
    plain = Prototype001Parameters()
    instrument = Prototype001Parameters.for_instrument(parameters.instrument)
    rows = []
    for group, name, unit in SHEET_FIELDS:
        value = getattr(parameters, name)
        if value != getattr(instrument, name):
            source = DESIGN
        elif value != getattr(plain, name):
            source = INSTRUMENT
        else:
            source = DEFAULT
        rows.append(SheetRow(group, name, _sheet_value(value), unit, source))
    return tuple(rows)


def _derived_rows(
    parameters: Prototype001Parameters, geometry: Prototype001Geometry
) -> tuple[SheetRow, ...]:
    """Return the values worked out from the built geometry.

    Positions are along the centreline from the nut line (X = 0).
    """
    outline = geometry.body.outline.points
    xs = [point.x for point in outline]
    ys = [point.y for point in outline]
    values: tuple[tuple[str, float, str], ...] = (
        ("centre_scale", parameters.centre_scale, "mm"),
        ("last_fret_position", _centre_x(geometry.fret_layout.slots[-1]), "mm"),
        (
            "fretboard_end_position",
            geometry.fretboard_surface.station_positions[-1],
            "mm",
        ),
        ("saddle_line_position", parameters.bridge_scale_line(), "mm"),
        ("neck_angle_degrees", parameters.neck_angle_degrees, "deg"),
        ("body_length", max(xs) - min(xs), "mm"),
        ("body_width", max(ys) - min(ys), "mm"),
    )
    return tuple(
        SheetRow("Derived", name, round(value, DECIMALS), unit, DERIVED)
        for name, value, unit in values
    )


def _checks(
    parameters: Prototype001Parameters, geometry: Prototype001Geometry
) -> tuple[SheetCheck, ...]:
    """Return the checks of the built frets against the formula.

    The octave fret's check is left out of a neck too short to have one.
    """
    scale = parameters.centre_scale
    steps = parameters.frets_per_octave
    positions = [_centre_x(slot) for slot in geometry.fret_layout.slots]
    checks = []
    if len(positions) >= steps:
        checks.append(
            SheetCheck(
                name="octave_fret_at_half_scale",
                description=(
                    f"Fret {steps}, an octave up, lies half the scale length "
                    "from the nut, on the centreline."
                ),
                expected=scale / 2.0,
                actual=positions[steps - 1],
                tolerance=FRET_TOLERANCE,
                unit="mm",
            )
        )
    deviation = max(
        abs(position - scale * (1.0 - 2.0 ** (-number / steps)))
        for number, position in enumerate(positions, start=1)
    )
    checks.append(
        SheetCheck(
            name="frets_follow_equal_temperament",
            description=(
                "The largest distance between a fret slot and its place "
                "scale * (1 - 2 ** (-n / frets_per_octave)) from the nut."
            ),
            expected=0.0,
            actual=deviation,
            tolerance=FRET_TOLERANCE,
            unit="mm",
        )
    )
    return tuple(checks)


def _centre_x(slot: Line2D) -> float:
    """Return where a fret slot's line crosses the centreline (Y = 0).

    A slanted or fanned fret leans across the board, and a slot cut short
    at the board's end may stop before the centreline: its line is
    followed on to it either way.
    """
    start, end = slot.start, slot.end
    if math.isclose(start.y, end.y):
        return start.x
    return start.x + (end.x - start.x) * (0.0 - start.y) / (end.y - start.y)


def _sheet_value(value: object) -> SheetValue:
    """Return a setting's value as the sheet shows it.

    A bridge or body shape shows its kind; anything else is shown as it is.
    """
    kind = getattr(value, "kind", None)
    if isinstance(kind, str):
        return kind
    if value is None or isinstance(value, str | int | float):
        return value
    return str(value)


def _cell(value: SheetValue) -> str:
    """Return a value as a CSV cell: empty for ``None``."""
    if value is None:
        return ""
    return str(value)
