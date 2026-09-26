"""Interchangeable body shapes: the outline and where its electronics go.

A body shape is a small frozen dataclass (a *spec*) naming a silhouette
and carrying the placements that belong to that silhouette rather than to
the neck or the bridge: the round switch cavity, the pot shaft holes and
the output jack. Everything is measured from the neck pocket's end (the
heel end) along X and from the centerline along Y, so a shape rides with
whatever neck it receives. The almond control cavity (with its cover
ledge) is the Design by Jone drawing's own shape on every body; a shape
only says where it sits.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any, Literal

from ..geometry.exceptions import BodyGeometryError
from ..geometry.primitives import Point2D, closed_catmull_rom
from ._omarunko_outline import (
    OMARUNKO_CONTROL_CAVITY_POINTS,
    OMARUNKO_CONTROL_COVER_POINTS,
    OMARUNKO_HEEL_END_X,
    OMARUNKO_OUTLINE_POINTS,
)

OUTLINE_SAMPLES_PER_SEGMENT = 8
"""Outline points per spline segment of a drawn body."""


def _translated(
    points: tuple[tuple[float, float], ...], dx: float, dy: float
) -> tuple[Point2D, ...]:
    return tuple(Point2D(x + dx, y + dy) for x, y in points)


@dataclass(frozen=True, slots=True)
class DesignByJoneShape:
    """The user's own body, digitised from ``assets/reference/omarunko.dxf``.

    Every default is the drawing's own placement; see
    ``_omarunko_outline.py`` for the tracing and its alignment.

    Args:
        switch_cavity_offset: Switch cavity centre X from the heel end.
        switch_cavity_y: Switch cavity centre Y.
        switch_cavity_diameter: Switch cavity diameter.
        switch_cover_offset: Switch cover recess centre X from the heel end.
        switch_cover_y: Switch cover recess centre Y.
        switch_cover_diameter: Switch cover recess diameter.
        pot_offsets: Pot shaft holes as (X from the heel end, Y) pairs.
        jack_offset: Jack bore start X from the heel end, on the body edge.
        jack_y: Jack bore start Y.
        jack_direction_degrees: Direction the bore runs in, in the plan.
        control_shift: Translation (X, Y) applied to the traced almond
            control cavity and its cover, from their drawn position.
    """

    kind: Literal["design_by_jone"] = "design_by_jone"
    switch_cavity_offset: float = -4.005
    switch_cavity_y: float = -70.565
    switch_cavity_diameter: float = 43.972
    switch_cover_offset: float = -3.211
    switch_cover_y: float = -70.3
    switch_cover_diameter: float = 59.452
    pot_offsets: tuple[tuple[float, float], ...] = ((180.8, 86.0), (220.8, 87.0))
    jack_offset: float = 280.8
    jack_y: float = 107.5
    jack_direction_degrees: float = 202.5
    control_shift: tuple[float, float] = (0.0, 0.0)

    def outline_points(self, heel_end: float) -> tuple[Point2D, ...]:
        """Return the outline placed so its pocket end sits at ``heel_end``."""
        return _translated(
            OMARUNKO_OUTLINE_POINTS, heel_end - OMARUNKO_HEEL_END_X, 0.0
        )

    def control_cavity_points(self, heel_end: float) -> tuple[Point2D, ...]:
        """Return the almond control cavity outline on this body."""
        return _control_points(
            OMARUNKO_CONTROL_CAVITY_POINTS, heel_end, self.control_shift
        )

    def control_cover_points(self, heel_end: float) -> tuple[Point2D, ...]:
        """Return the control cavity's cover ledge outline on this body."""
        return _control_points(
            OMARUNKO_CONTROL_COVER_POINTS, heel_end, self.control_shift
        )


YOUR_DESIGN_START_POINTS: tuple[tuple[float, float], ...] = (
    (-52.0, -12.0), (-54.0, -34.0), (-66.0, -46.0), (-92.0, -58.0),
    (-120.0, -74.0), (-136.0, -88.0), (-144.0, -100.0), (-140.0, -108.0),
    (-124.0, -120.0), (-95.0, -136.0), (-55.0, -150.0), (-10.0, -158.0),
    (40.0, -155.0), (85.0, -143.0), (120.0, -132.0), (150.0, -132.0),
    (185.0, -144.0), (225.0, -158.0), (265.0, -156.0), (298.0, -132.0),
    (322.0, -90.0), (330.0, -40.0), (330.0, 30.0), (318.0, 90.0),
    (290.0, 132.0), (250.0, 156.0), (205.0, 162.0), (160.0, 150.0),
    (130.0, 134.0), (105.0, 132.0), (75.0, 140.0), (40.0, 150.0),
    (5.0, 150.0), (-30.0, 138.0), (-58.0, 120.0), (-76.0, 105.0),
    (-84.0, 95.0), (-82.0, 84.0), (-72.0, 66.0), (-62.0, 48.0),
    (-54.0, 34.0), (-52.0, 12.0),
)
"""A Stratocaster-inspired offset double cutaway to start drawing from.

Control points relative to the heel end, in the model frame of this
left-handed body: the long upper horn at -Y, the controls at +Y. The loop
closes across the horn gap about 52 mm ahead of the pocket end, so the
neck pocket opens onto the gap as the Design by Jone body's does.
"""


@dataclass(frozen=True, slots=True)
class YourDesignShape:
    """A body the user draws: a smooth loop through movable control points.

    The outline is a closed Catmull-Rom spline through ``control_points``
    (X from the heel end, Y from the centerline), so it always passes
    through every point and is smooth between them. The web app edits the
    points by dragging them over the fixed features — neck pocket, pickup
    and bridge routes, control and switch cavities — which do not move.
    The electronics keep the Design by Jone cavity shapes; their places
    are the other fields, as for ``DesignByJoneShape``. The default points
    draw a Stratocaster-inspired starting shape.

    Args:
        control_points: The outline's control points, in order around the
            loop; at least four.
        switch_cavity_offset: Switch cavity centre X from the heel end.
        switch_cavity_y: Switch cavity centre Y.
        switch_cavity_diameter: Switch cavity diameter.
        switch_cover_offset: Switch cover recess centre X from the heel end.
        switch_cover_y: Switch cover recess centre Y.
        switch_cover_diameter: Switch cover recess diameter.
        pot_offsets: Pot shaft holes as (X from the heel end, Y) pairs.
        jack_offset: Jack bore start X from the heel end, on the body edge.
        jack_y: Jack bore start Y.
        jack_direction_degrees: Direction the bore runs in, in the plan.
        control_shift: Translation (X, Y) applied to the traced almond
            control cavity and its cover, from their drawn position.

    Raises:
        BodyGeometryError: For fewer than four or non-finite control points.
    """

    kind: Literal["your_design"] = "your_design"
    control_points: tuple[tuple[float, float], ...] = YOUR_DESIGN_START_POINTS
    switch_cavity_offset: float = 95.0
    switch_cavity_y: float = 80.0
    switch_cavity_diameter: float = 43.972
    switch_cover_offset: float = 95.0
    switch_cover_y: float = 80.0
    switch_cover_diameter: float = 59.452
    pot_offsets: tuple[tuple[float, float], ...] = ((180.8, 86.0), (220.8, 87.0))
    jack_offset: float = 284.0
    jack_y: float = 134.0
    jack_direction_degrees: float = 230.0
    control_shift: tuple[float, float] = (0.0, 0.0)

    def __post_init__(self) -> None:
        """Reject a control polygon that cannot describe a body."""
        if len(self.control_points) < 4:
            raise BodyGeometryError(
                "Your design needs at least four outline control points."
            )
        if not all(
            len(point) == 2 and all(math.isfinite(value) for value in point)
            for point in self.control_points
        ):
            raise BodyGeometryError(
                "Your design's control points must be finite (x, y) pairs."
            )

    def outline_points(self, heel_end: float) -> tuple[Point2D, ...]:
        """Return the spline outline placed relative to ``heel_end``."""
        return closed_catmull_rom(
            _translated(self.control_points, heel_end, 0.0),
            OUTLINE_SAMPLES_PER_SEGMENT,
        )

    def control_cavity_points(self, heel_end: float) -> tuple[Point2D, ...]:
        """Return the almond control cavity outline on this body."""
        return _control_points(
            OMARUNKO_CONTROL_CAVITY_POINTS, heel_end, self.control_shift
        )

    def control_cover_points(self, heel_end: float) -> tuple[Point2D, ...]:
        """Return the control cavity's cover ledge outline on this body."""
        return _control_points(
            OMARUNKO_CONTROL_COVER_POINTS, heel_end, self.control_shift
        )


def _control_points(
    points: tuple[tuple[float, float], ...],
    heel_end: float,
    shift: tuple[float, float],
) -> tuple[Point2D, ...]:
    dx, dy = shift
    return _translated(points, heel_end - OMARUNKO_HEEL_END_X + dx, dy)


BodyShapeSpec = DesignByJoneShape | YourDesignShape

BODY_SHAPE_KINDS: dict[str, type[Any]] = {
    "design_by_jone": DesignByJoneShape,
    "your_design": YourDesignShape,
}

BODY_SHAPE_LABELS: dict[str, str] = {
    "design_by_jone": "Design by Jone (traced DXF)",
    "your_design": "Your design (draw it)",
}


def body_shape_from_dict(data: Mapping[str, Any]) -> BodyShapeSpec:
    """Rebuild a body shape spec from its ``dataclasses.asdict`` form.

    The ``kind`` entry selects the spec class; every other entry must be
    one of its fields. Lists stand in for the tuple fields.

    Raises:
        BodyGeometryError: For an unknown kind or field.
    """
    kind = data.get("kind")
    if kind not in BODY_SHAPE_KINDS:
        raise BodyGeometryError(
            f"Unknown body shape {kind!r}; choose one of {', '.join(BODY_SHAPE_KINDS)}."
        )
    spec_class = BODY_SHAPE_KINDS[kind]
    names = {field.name for field in fields(spec_class)}
    values: dict[str, Any] = {}
    for name, value in data.items():
        if name == "kind":
            continue
        if name not in names:
            raise BodyGeometryError(f"Unknown {kind} body shape field {name!r}.")
        values[name] = _tuplify(value)
    spec: BodyShapeSpec = spec_class(**values)
    return spec


def _tuplify(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_tuplify(item) for item in value)
    return value
