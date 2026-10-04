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
from dataclasses import dataclass, fields, replace
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

BODY_WIDENING_PER_STRING = 12.0
"""Body width added along the centreline for every string past six.

The shapes are drawn for a six-string neck; a seven- or eight-string heel
is 10 mm wider per string and its pickups 12 mm longer, so each half of
the body moves out by half this much per extra string.
"""


def widen_y(y: float, widening: float) -> float:
    """Move a lateral coordinate out from the centreline by ``widening / 2``.

    A point on the centreline stays there, so the body opens along it.
    """
    half = widening / 2.0
    return y + half if y > 0.0 else y - half if y < 0.0 else y


def widen_points(
    points: tuple[tuple[float, float], ...], widening: float
) -> tuple[tuple[float, float], ...]:
    """Return ``points`` with every Y moved out by ``widening / 2``."""
    if widening == 0.0:
        return points
    return tuple((x, widen_y(y, widening)) for x, y in points)


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
        neck_bolts: Neck-bolt centres as (X from the heel end, Y) pairs;
            empty for the preset's rectangular pattern. This body's deep
            treble cutaway leaves wood for a ferrule only near the heel
            end on that side, so its treble pair sits there (the preset
            moves every bolt out from the truss rod as far as it fits).
        battery_offset: 9 V battery box centre X from the heel end (used
            with ``Prototype001Parameters.body_battery_box``).
        battery_y: Battery box centre Y.
        battery_angle_degrees: The box's long axis from the neck's axis.
        control_angle_degrees: How far the control cavity, its cover and
            the layout's own pots (or the Tele plate) are turned about the
            cavity's centre, counter-clockwise in the plan.
        control_stretch: How much longer (negative: shorter) the control
            cavity and its cover are made along their long axis, from
            their centre; the layout's pots, the Tele plate's screws and
            switch slot move out with the ends.
        control_stretch_across: Likewise across the long axis: the cavity
            and its cover get that much wider (negative: narrower), the
            Gibson layout's two rows of pots move apart with the sides.
        pickguard_points: A drawn pickguard's control points (X from the
            heel end, Y); empty for the automatic guard (used with
            ``Prototype001Parameters.body_pickguard``).
        arm_contour_points: Where a drawn arm contour starts on the top:
            an open line's control points (X from the heel end, Y), its
            ends on the body's edge; empty for the automatic contour (used
            with ``Prototype001Parameters.body_arm_contour_depth``).
        belly_cut_points: The same for a drawn belly cut on the back (seen
            from the top, as the outline is), used with
            ``Prototype001Parameters.body_belly_cut_depth``.
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
    neck_bolts: tuple[tuple[float, float], ...] = (
        (-40.0, -20.0),
        (-5.5, -20.0),
        (-24.0, 10.0),
        (-5.5, 18.0),
    )
    # The battery box behind the bridge, near the control cavity so its
    # lead's channel stays short, nearly across the neck and with 10 mm
    # of wood between its cover and the tail's edge.
    battery_offset: float = 242.5
    battery_y: float = 2.5
    battery_angle_degrees: float = 85.0
    control_angle_degrees: float = 0.0
    control_stretch: float = 0.0
    control_stretch_across: float = 0.0
    pickguard_points: tuple[tuple[float, float], ...] = ()
    arm_contour_points: tuple[tuple[float, float], ...] = ()
    belly_cut_points: tuple[tuple[float, float], ...] = ()
    # Whether the traced outline and almond cavity (constants drawn
    # right-handed) are mirrored: set by mirrored_shape, with every other
    # field mirrored there.
    mirrored: bool = False

    def outline_points(
        self, heel_end: float, widening: float = 0.0
    ) -> tuple[Point2D, ...]:
        """Return the outline placed so its pocket end sits at ``heel_end``.

        ``widening`` opens the body along the centreline (see
        ``widen_points``).
        """
        return _translated(
            widen_points(_side(OMARUNKO_OUTLINE_POINTS, self.mirrored), widening),
            heel_end - OMARUNKO_HEEL_END_X,
            0.0,
        )

    def control_cavity_points(self, heel_end: float) -> tuple[Point2D, ...]:
        """Return the almond control cavity outline on this body."""
        return _control_points(
            _side(OMARUNKO_CONTROL_CAVITY_POINTS, self.mirrored),
            heel_end,
            self.control_shift,
        )

    def control_cover_points(self, heel_end: float) -> tuple[Point2D, ...]:
        """Return the control cavity's cover ledge outline on this body."""
        return _control_points(
            _side(OMARUNKO_CONTROL_COVER_POINTS, self.mirrored),
            heel_end,
            self.control_shift,
        )


YOUR_DESIGN_START_POINTS: tuple[tuple[float, float], ...] = (
    (-52.0, -12.0),
    (-54.0, -34.0),
    (-66.0, -46.0),
    (-92.0, -58.0),
    (-120.0, -74.0),
    (-136.0, -88.0),
    (-144.0, -100.0),
    (-140.0, -108.0),
    (-124.0, -120.0),
    (-95.0, -136.0),
    (-55.0, -150.0),
    (-10.0, -158.0),
    (40.0, -155.0),
    (85.0, -143.0),
    (120.0, -132.0),
    (150.0, -132.0),
    (185.0, -144.0),
    (225.0, -158.0),
    (265.0, -156.0),
    (298.0, -132.0),
    (322.0, -90.0),
    (330.0, -40.0),
    (330.0, 30.0),
    (318.0, 90.0),
    (290.0, 132.0),
    (250.0, 156.0),
    (205.0, 162.0),
    (160.0, 150.0),
    (130.0, 134.0),
    (105.0, 132.0),
    (75.0, 140.0),
    (40.0, 150.0),
    (5.0, 150.0),
    (-30.0, 138.0),
    (-58.0, 120.0),
    (-76.0, 105.0),
    (-84.0, 95.0),
    (-82.0, 84.0),
    (-72.0, 66.0),
    (-62.0, 48.0),
    (-54.0, 34.0),
    (-52.0, 12.0),
)
"""A Stratocaster-inspired offset double cutaway to start drawing from.

Control points relative to the heel end, in the model frame of this
right-handed body: the long upper horn at -Y, the controls at +Y. The loop
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
        neck_bolts: Neck-bolt centres as (X from the heel end, Y) pairs;
            empty for the preset's rectangular pattern.
        battery_offset: 9 V battery box centre X from the heel end (used
            with ``Prototype001Parameters.body_battery_box``).
        battery_y: Battery box centre Y.
        battery_angle_degrees: The box's long axis from the neck's axis.
        control_angle_degrees: How far the control cavity, its cover and
            the layout's own pots (or the Tele plate) are turned about the
            cavity's centre, counter-clockwise in the plan.
        control_stretch: How much longer (negative: shorter) the control
            cavity and its cover are made along their long axis, from
            their centre; the layout's pots, the Tele plate's screws and
            switch slot move out with the ends.
        control_stretch_across: Likewise across the long axis: the cavity
            and its cover get that much wider (negative: narrower), the
            Gibson layout's two rows of pots move apart with the sides.
        pickguard_points: A drawn pickguard's control points (X from the
            heel end, Y); empty for the automatic guard (used with
            ``Prototype001Parameters.body_pickguard``).
        arm_contour_points: Where a drawn arm contour starts on the top:
            an open line's control points (X from the heel end, Y), its
            ends on the body's edge; empty for the automatic contour (used
            with ``Prototype001Parameters.body_arm_contour_depth``).
        belly_cut_points: The same for a drawn belly cut on the back (seen
            from the top, as the outline is), used with
            ``Prototype001Parameters.body_belly_cut_depth``.

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
    neck_bolts: tuple[tuple[float, float], ...] = ()
    # The battery box behind the bridge, beside the control cavity (as
    # near as the two covers allow), so its lead's channel stays short.
    battery_offset: float = 281.0
    battery_y: float = 47.5
    battery_angle_degrees: float = 15.0
    control_angle_degrees: float = 0.0
    control_stretch: float = 0.0
    control_stretch_across: float = 0.0
    pickguard_points: tuple[tuple[float, float], ...] = ()
    arm_contour_points: tuple[tuple[float, float], ...] = ()
    belly_cut_points: tuple[tuple[float, float], ...] = ()
    # Whether the traced outline and almond cavity (constants drawn
    # right-handed) are mirrored: set by mirrored_shape, with every other
    # field mirrored there.
    mirrored: bool = False

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

    def outline_points(
        self, heel_end: float, widening: float = 0.0
    ) -> tuple[Point2D, ...]:
        """Return the spline outline placed relative to ``heel_end``.

        ``widening`` moves the control points out from the centreline
        before the spline is drawn (see ``widen_points``).
        """
        return closed_catmull_rom(
            _translated(widen_points(self.control_points, widening), heel_end, 0.0),
            OUTLINE_SAMPLES_PER_SEGMENT,
        )

    def control_cavity_points(self, heel_end: float) -> tuple[Point2D, ...]:
        """Return the almond control cavity outline on this body."""
        return _control_points(
            _side(OMARUNKO_CONTROL_CAVITY_POINTS, self.mirrored),
            heel_end,
            self.control_shift,
        )

    def control_cover_points(self, heel_end: float) -> tuple[Point2D, ...]:
        """Return the control cavity's cover ledge outline on this body."""
        return _control_points(
            _side(OMARUNKO_CONTROL_COVER_POINTS, self.mirrored),
            heel_end,
            self.control_shift,
        )


def _control_points(
    points: tuple[tuple[float, float], ...],
    heel_end: float,
    shift: tuple[float, float],
) -> tuple[Point2D, ...]:
    dx, dy = shift
    return _translated(points, heel_end - OMARUNKO_HEEL_END_X + dx, dy)


def _side(
    points: tuple[tuple[float, float], ...], mirrored: bool
) -> tuple[tuple[float, float], ...]:
    """Return ``points``, mirrored across the centreline (order reversed) if asked."""
    if not mirrored:
        return points
    return tuple((x, -y) for x, y in reversed(points))


BodyShapeSpec = DesignByJoneShape | YourDesignShape


def mirrored_shape(shape: BodyShapeSpec) -> BodyShapeSpec:
    """Return ``shape``'s mirror image across the centreline (left-handed).

    Every placement's Y and every angle in the plan change sign; drawn
    outlines run the other way round (so they keep their winding), open
    lines keep their order; the traced constants are mirrored by the
    ``mirrored`` flag. Mirroring twice gives ``shape`` back.
    """

    def flipped(
        points: tuple[tuple[float, float], ...],
    ) -> tuple[tuple[float, float], ...]:
        return tuple((x, -y) for x, y in points)

    shift_x, shift_y = shape.control_shift
    mirrored = replace(
        shape,
        switch_cavity_y=-shape.switch_cavity_y,
        switch_cover_y=-shape.switch_cover_y,
        pot_offsets=flipped(shape.pot_offsets),
        jack_y=-shape.jack_y,
        jack_direction_degrees=-shape.jack_direction_degrees,
        control_shift=(shift_x, -shift_y),
        neck_bolts=flipped(shape.neck_bolts),
        battery_y=-shape.battery_y,
        battery_angle_degrees=-shape.battery_angle_degrees,
        control_angle_degrees=-shape.control_angle_degrees,
        pickguard_points=_side(shape.pickguard_points, True),
        arm_contour_points=flipped(shape.arm_contour_points),
        belly_cut_points=flipped(shape.belly_cut_points),
        mirrored=not shape.mirrored,
    )
    if isinstance(mirrored, YourDesignShape):
        mirrored = replace(
            mirrored, control_points=_side(mirrored.control_points, True)
        )
    return mirrored


def widened_shape(shape: BodyShapeSpec, widening: float) -> BodyShapeSpec:
    """Return ``shape`` with its switch, pots, jack, almond and battery moved out.

    Each placement moves out from the centreline by ``widening / 2`` with
    its half of the body; pass the same ``widening`` to
    ``outline_points``. The neck bolts stay with the neck pocket.
    """
    if widening == 0.0:
        return shape
    almond = _side(OMARUNKO_CONTROL_CAVITY_POINTS, shape.mirrored)
    almond_y = sum(y for _, y in almond) / len(almond)
    shift_x, shift_y = shape.control_shift
    moved_almond = widen_y(almond_y + shift_y, widening)
    return replace(
        shape,
        switch_cavity_y=widen_y(shape.switch_cavity_y, widening),
        switch_cover_y=widen_y(shape.switch_cover_y, widening),
        pot_offsets=widen_points(shape.pot_offsets, widening),
        jack_y=widen_y(shape.jack_y, widening),
        battery_y=widen_y(shape.battery_y, widening),
        control_shift=(shift_x, moved_almond - almond_y),
        pickguard_points=widen_points(shape.pickguard_points, widening),
        arm_contour_points=widen_points(shape.arm_contour_points, widening),
        belly_cut_points=widen_points(shape.belly_cut_points, widening),
    )


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


def _resampled(
    points: tuple[tuple[float, float], ...], count: int, dx: float
) -> tuple[tuple[float, float], ...]:
    """Return count points spaced evenly along a closed polygon, shifted."""
    closed = [(x + dx, y) for x, y in points]
    lengths = [
        math.dist(closed[index], closed[(index + 1) % len(closed)])
        for index in range(len(closed))
    ]
    step = sum(lengths) / count
    result: list[tuple[float, float]] = []
    segment = 0
    walked = 0.0
    for sample in range(count):
        target = sample * step
        while walked + lengths[segment] < target:
            walked += lengths[segment]
            segment += 1
        t = (target - walked) / lengths[segment]
        (ax, ay), (bx, by) = closed[segment], closed[(segment + 1) % len(closed)]
        result.append((round(ax + (bx - ax) * t, 1), round(ay + (by - ay) * t, 1)))
    return tuple(result)


_LES_PAUL_POINTS: tuple[tuple[float, float], ...] = (
    (371.7, 20.6),
    (370.5, -1.6),
    (367.9, -23.7),
    (364.1, -45.6),
    (358.3, -67.1),
    (349.7, -87.5),
    (338.4, -106.6),
    (324.1, -123.6),
    (307.4, -138.3),
    (288.5, -150.0),
    (267.7, -157.5),
    (246.4, -163.1),
    (224.2, -164.0),
    (202.2, -161.0),
    (181.4, -153.9),
    (161.9, -143.4),
    (144.1, -130.1),
    (127.4, -115.3),
    (109.8, -101.7),
    (89.2, -94.0),
    (67.5, -98.0),
    (47.6, -108.0),
    (27.5, -117.5),
    (5.6, -119.9),
    (-15.8, -114.6),
    (-33.6, -101.4),
    (-47.0, -83.7),
    (-56.6, -63.7),
    (-59.6, -47.8),
    (-59.4, -29.8),
    (-51.5, 8.6),
    (-44.6, 25.5),
    (-29.3, 28.5),
    (-9.8, 38.2),
    (-1.7, 58.5),
    (-7.5, 79.6),
    (-18.6, 95.9),
    (-35.8, 107.8),
    (-3.1, 113.9),
    (18.6, 109.5),
    (39.1, 100.8),
    (59.6, 92.3),
    (81.5, 88.7),
    (101.7, 96.6),
    (119.2, 110.5),
    (135.8, 125.2),
    (153.7, 138.4),
    (172.9, 149.5),
    (193.6, 157.5),
    (214.9, 162.4),
    (237.1, 164.0),
    (259.2, 162.3),
    (280.4, 156.9),
    (300.9, 148.5),
    (320.0, 137.1),
    (337.2, 123.1),
    (351.0, 105.6),
    (361.6, 86.1),
    (368.1, 64.8),
    (371.2, 42.8),
)
"""A single-cutaway mockup in the Les Paul genre — not the original outline.

Traced from a reference render (the top face's edge scaled to 442 × 328 mm,
the render's perspective evened out across the body) and then reshaped by
hand in the body editor: the neck joint's face and the treble horn moved,
the neck entering at about 55 mm ahead of the heel end. 60 control points.
A genre starting point, free to use and change, not a reproduction of any
maker's body."""

_STRATOCASTER_POINTS: tuple[tuple[float, float], ...] = (
    (-74.6, -13.2),
    (-68.8, -28.4),
    (-50.9, -35.3),
    (-51.5, -61.0),
    (-68.6, -77.8),
    (-85.7, -88.0),
    (-105.5, -91.1),
    (-125.3, -93.4),
    (-139.7, -103.7),
    (-122.7, -127.1),
    (-104.9, -136.2),
    (-85.2, -139.7),
    (-65.1, -139.7),
    (-45.0, -137.9),
    (-25.2, -134.4),
    (-5.8, -129.5),
    (13.2, -123.0),
    (32.4, -116.9),
    (52.2, -113.8),
    (72.2, -116.0),
    (91.4, -121.6),
    (109.9, -129.6),
    (128.7, -136.8),
    (147.3, -144.4),
    (166.0, -151.6),
    (185.4, -157.0),
    (205.2, -160.4),
    (225.2, -162.0),
    (245.3, -161.2),
    (265.0, -157.6),
    (283.1, -148.9),
    (298.5, -136.0),
    (310.2, -119.7),
    (319.0, -101.7),
    (323.8, -82.2),
    (325.5, -62.2),
    (326.1, -42.1),
    (326.1, -22.0),
    (326.1, -1.9),
    (326.1, 18.3),
    (326.1, 38.4),
    (326.1, 58.5),
    (325.3, 78.6),
    (321.2, 98.2),
    (312.4, 116.3),
    (300.3, 132.2),
    (285.1, 145.3),
    (267.6, 155.3),
    (248.0, 159.5),
    (228.0, 160.6),
    (207.9, 159.5),
    (188.2, 155.8),
    (169.0, 149.9),
    (150.2, 142.8),
    (131.6, 134.9),
    (113.4, 126.4),
    (95.1, 118.3),
    (75.3, 115.0),
    (55.5, 117.6),
    (36.7, 124.8),
    (18.2, 132.8),
    (-0.8, 139.2),
    (-20.7, 142.2),
    (-40.6, 139.9),
    (-59.2, 132.6),
    (-72.1, 112.3),
    (-59.5, 101.0),
    (-40.0, 96.1),
    (-16.3, 87.4),
    (-3.7, 70.2),
    (-5.7, 51.1),
    (-16.2, 33.1),
    (-34.7, 28.2),
    (-54.8, 28.2),
    (-74.3, 27.1),
    (-74.6, 7.0),
)
"""An offset double-cutaway mockup in the Stratocaster genre — not the original.

Traced from a reference DXF drawing (the body's outermost edge, aligned on
the drawing's neck pocket: its end wall is the heel end, its middle the
centreline; already right-handed, the long bass horn at -Y) and then
reshaped by hand in the body editor at both horns and the neck joint. 76
control points. A genre starting point, free to use and change, not a
reproduction of any maker's body."""


_JACKSON_RR_POINTS: tuple[tuple[float, float], ...] = (
    (-63.2, 2.1),
    (-48.9, 31.4),
    (-37.9, 41.5),
    (-30.0, 51.3),
    (-5.7, 60.3),
    (18.3, 69.0),
    (42.6, 78.0),
    (66.6, 86.7),
    (90.9, 95.6),
    (114.8, 104.4),
    (139.1, 113.3),
    (163.1, 122.1),
    (187.4, 131.0),
    (211.4, 139.8),
    (235.6, 148.6),
    (259.6, 157.4),
    (283.9, 166.3),
    (307.9, 175.1),
    (331.9, 183.9),
    (343.6, 189.0),
    (385.2, 189.2),
    (364.8, 175.6),
    (348.4, 162.0),
    (320.0, 142.4),
    (303.5, 119.1),
    (288.8, 96.1),
    (277.5, 76.5),
    (264.1, 60.8),
    (251.4, 37.9),
    (248.1, 14.7),
    (253.7, -9.0),
    (270.2, -26.0),
    (284.4, -39.3),
    (304.7, -65.5),
    (318.8, -82.8),
    (336.2, -103.0),
    (354.3, -122.9),
    (370.7, -139.9),
    (387.4, -156.6),
    (406.2, -169.7),
    (424.6, -185.6),
    (438.9, -196.2),
    (460.8, -205.4),
    (485.3, -219.0),
    (453.5, -225.4),
    (436.6, -222.5),
    (404.4, -210.6),
    (372.2, -198.8),
    (340.1, -186.9),
    (307.9, -175.1),
    (275.7, -163.3),
    (243.5, -151.4),
    (211.4, -139.6),
    (178.9, -127.6),
    (146.7, -115.8),
    (114.5, -103.9),
    (82.3, -92.1),
    (50.2, -80.2),
    (18.0, -68.4),
    (-14.2, -56.6),
    (-46.4, -44.7),
    (-48.4, -42.7),
    (-49.2, -39.0),
    (-63.7, -19.3),
)
"""An offset V mockup in the Jackson Randy Rhoads genre — not the original
outline.

Traced from a reference render (the silhouette scaled from its humbucker
covers, the neck joint placed from the neck pickup) and then reshaped by
hand in the body editor: the neck joint's face moved forward, both wing
tips and the V notch redrawn. The long pointed wing is on the bass side,
the controls on the treble wing and the selector switch on the bass wing.
64 control points. A genre starting point, free to use and change, not a
reproduction of any maker's body."""


_JAZZ_BASS_POINTS: tuple[tuple[float, float], ...] = (
    (-161.3, -103.5),
    (-163.6, -90.4),
    (-155.9, -80.7),
    (-144.9, -73.9),
    (-119.5, -75.3),
    (-90.2, -71.9),
    (-77.4, -63.8),
    (-68.9, -57.6),
    (-66.4, -50.8),
    (-67.1, -45.2),
    (-75.3, -32.5),
    (-76.3, -6.4),
    (-76.8, 19.2),
    (-74.4, 26.7),
    (-38.0, 28.5),
    (-27.3, 30.7),
    (-18.4, 34.7),
    (-10.9, 43.1),
    (-8.8, 51.5),
    (-9.8, 58.6),
    (-19.0, 72.0),
    (-38.3, 81.6),
    (-64.9, 80.4),
    (-79.2, 90.3),
    (-82.6, 102.0),
    (-73.3, 121.1),
    (-56.7, 128.7),
    (-43.1, 134.7),
    (-31.9, 137.0),
    (-9.5, 141.1),
    (13.0, 141.7),
    (52.1, 133.6),
    (75.6, 126.5),
    (99.0, 118.0),
    (125.4, 116.0),
    (151.5, 122.0),
    (179.4, 139.4),
    (206.9, 156.5),
    (219.9, 162.9),
    (243.5, 169.9),
    (257.2, 171.9),
    (280.7, 170.7),
    (301.2, 164.1),
    (316.5, 154.3),
    (331.9, 136.9),
    (338.4, 123.4),
    (342.8, 105.5),
    (346.2, 68.6),
    (346.2, 47.0),
    (344.0, 19.1),
    (340.8, -8.7),
    (336.3, -31.5),
    (331.4, -54.2),
    (321.0, -85.4),
    (314.2, -99.9),
    (305.0, -114.3),
    (290.7, -130.2),
    (268.2, -146.2),
    (252.6, -153.0),
    (231.6, -158.5),
    (209.4, -160.9),
    (185.9, -159.0),
    (156.5, -151.0),
    (127.1, -141.3),
    (94.6, -127.6),
    (62.7, -113.2),
    (46.4, -109.9),
    (33.3, -110.1),
    (17.0, -117.7),
    (-4.7, -125.2),
    (-44.3, -134.1),
    (-76.3, -138.4),
    (-105.3, -137.5),
    (-128.4, -132.1),
    (-149.7, -122.5),
    (-158.6, -113.7),
)
"""An offset-waist bass mockup in the Jazz Bass genre — not the original
outline.

Traced from a reference render (its top face straightened on the body's
centre stripe, scaled from the bridge pickup's cover and placed so the
neck pocket opens through the face between the horns) and then reshaped
by hand in the body editor: the bass horn's tip, the treble horn and its
cutaway and both horns' roots. About 510 × 333 mm, 76 control points. A
genre starting point, free to use and change, not a reproduction of any
maker's body."""

_JAZZ_BASS_PICKGUARD_POINTS: tuple[tuple[float, float], ...] = (
    (-59.4, 112.5),
    (-47.6, 119.0),
    (-33.5, 124.6),
    (-14.1, 129.9),
    (7.5, 132.5),
    (30.7, 129.0),
    (55.4, 121.7),
    (80.2, 114.5),
    (82.6, 116.4),
    (104.3, 111.0),
    (127.0, 110.1),
    (141.1, 113.6),
    (155.2, 117.1),
    (175.0, 129.5),
    (194.7, 142.0),
    (208.9, 147.7),
    (225.8, 152.8),
    (242.7, 157.9),
    (259.6, 162.9),
    (276.1, 165.3),
    (285.6, 163.4),
    (302.9, 156.6),
    (313.9, 148.5),
    (310.3, 140.1),
    (293.2, 123.5),
    (276.1, 106.9),
    (264.3, 91.7),
    (257.2, 74.6),
    (256.6, 58.9),
    (256.1, 43.2),
    (239.5, 42.3),
    (236.0, 38.5),
    (236.0, 12.5),
    (236.0, -13.5),
    (236.0, -39.4),
    (239.5, -42.3),
    (256.1, -42.3),
    (254.9, -53.7),
    (247.8, -65.1),
    (237.2, -73.6),
    (220.7, -78.4),
    (204.1, -83.1),
    (181.7, -81.7),
    (159.3, -80.3),
    (138.1, -73.6),
    (116.8, -67.0),
    (95.6, -60.3),
    (76.7, -57.0),
    (57.8, -53.7),
    (39.3, -53.7),
    (20.8, -53.7),
    (2.4, -53.7),
    (-17.7, -57.5),
    (-37.8, -61.3),
    (-48.4, -58.4),
    (-51.9, -55.6),
    (-53.1, -47.0),
    (-46.0, -31.8),
    (-27.1, -31.8),
    (-8.3, -31.8),
    (-2.4, -27.1),
    (0.0, -13.8),
    (-0.6, 4.3),
    (-1.2, 22.3),
    (-3.5, 29.0),
    (-10.6, 32.8),
    (1.2, 52.7),
    (-3.1, 75.4),
    (-15.6, 88.1),
    (-25.9, 93.6),
    (-38.7, 94.8),
    (-52.4, 94.0),
    (-64.1, 98.2),
)
"""The Jazz Bass style template's pickguard: the Stratocaster's traced HH
guard (see ``_STRATOCASTER_PICKGUARD_POINTS``) fitted to this body —
stretched along the neck from the neck pocket's end to the bridge's front,
widened for the bass's pickups, its bass side stepping back clear of the
bridge and whatever ran past the outline 6 mm in brought back onto that
line, its small horn then reshaped by hand in the body editor — X from
the heel end."""

BASS_BODY = YourDesignShape(
    control_points=_JAZZ_BASS_POINTS,
    pickguard_points=_JAZZ_BASS_PICKGUARD_POINTS,
    # The bass's bridge pickup sits where a guitar's controls go, so the
    # pots and control cavity move 64 mm tail-ward onto the lower bout
    # behind it, and 5.5 mm out; the switch keeps the drawn body's place.
    pot_offsets=((244.8, 91.5), (284.8, 92.5)),
    control_shift=(64.0, 5.5),
    # The string-through holes fill the space behind the bridge, so the
    # battery box stands between the pickups on the treble side, just
    # ahead of the control cavity.
    battery_offset=170.0,
    battery_y=66.0,
    battery_angle_degrees=-15.0,
)
"""The bass guitar's default drawn body: the Jazz Bass style mockup (see
``_JAZZ_BASS_POINTS``)."""

_STRATOCASTER_PICKGUARD_POINTS: tuple[tuple[float, float], ...] = (
    (-58.2, 118.8),
    (-55.8, 124.0),
    (-41.0, 130.1),
    (-28.3, 130.9),
    (-15.6, 131.8),
    (-3.7, 128.3),
    (8.2, 124.8),
    (24.1, 118.2),
    (39.9, 111.5),
    (55.8, 104.8),
    (78.7, 105.7),
    (91.4, 110.1),
    (104.1, 114.4),
    (120.5, 122.2),
    (136.9, 130.1),
    (153.3, 137.9),
    (169.7, 145.7),
    (184.1, 149.6),
    (198.4, 153.6),
    (205.8, 153.6),
    (214.0, 150.1),
    (218.1, 144.0),
    (217.3, 130.9),
    (206.1, 115.3),
    (194.9, 99.6),
    (183.7, 84.0),
    (178.8, 68.3),
    (178.3, 53.9),
    (177.9, 39.6),
    (166.5, 38.7),
    (164.0, 35.2),
    (164.0, 11.5),
    (164.0, -12.3),
    (164.0, -36.1),
    (166.5, -38.7),
    (177.9, -38.7),
    (177.1, -49.2),
    (172.2, -59.6),
    (164.8, -67.4),
    (152.5, -73.5),
    (141.9, -76.1),
    (122.2, -76.1),
    (105.0, -71.8),
    (85.7, -63.5),
    (66.4, -55.2),
    (53.3, -52.2),
    (40.2, -49.2),
    (20.9, -49.2),
    (1.6, -49.2),
    (-12.3, -52.6),
    (-26.2, -56.1),
    (-33.6, -53.5),
    (-36.9, -43.1),
    (-32.0, -29.1),
    (-18.9, -29.1),
    (-5.7, -29.1),
    (-1.6, -24.8),
    (-0.8, -6.1),
    (0.0, 12.6),
    (-1.6, 24.8),
    (-7.4, 30.0),
    (0.8, 48.3),
    (2.5, 70.0),
    (-3.3, 87.4),
    (-18.9, 104.8),
    (-37.7, 113.5),
    (-54.9, 116.1),
)
"""The Stratocaster style template's pickguard: traced from a photo of a
Stratocaster's HH guard (its outline to about 1.6 mm), scaled to fit this
body — the notch on the neck pocket's end, the bass side's step on the
bridge's front, clear of the bridge — X from the heel end."""

_DESIGN_BY_JONE_PICKGUARD_POINTS: tuple[tuple[float, float], ...] = (
    (215.7, 128.3),
    (205.0, 113.5),
    (182.0, 103.4),
    (162.0, 85.5),
    (172.7, 69.0),
    (178.3, 53.9),
    (177.9, 39.6),
    (166.5, 38.7),
    (164.2, 35.5),
    (161.9, 35.5),
    (161.9, 27.6),
    (161.9, 19.7),
    (161.9, 11.8),
    (161.9, 4.0),
    (161.9, -3.9),
    (161.9, -11.8),
    (161.9, -19.7),
    (161.9, -27.6),
    (161.9, -35.5),
    (164.0, -35.5),
    (164.0, -36.1),
    (166.5, -38.7),
    (177.9, -38.7),
    (175.5, -53.5),
    (164.8, -67.4),
    (141.9, -76.1),
    (122.2, -76.1),
    (103.1, -69.6),
    (84.0, -63.1),
    (65.0, -56.5),
    (45.9, -50.0),
    (28.7, -49.2),
    (11.5, -48.3),
    (-7.4, -52.2),
    (-26.2, -56.1),
    (-35.7, -51.7),
    (-36.9, -43.1),
    (-32.0, -29.1),
    (-18.9, -29.1),
    (-5.7, -29.1),
    (-1.6, -24.8),
    (-1.7, -0.4),
    (-1.7, 24.0),
    (11.3, 40.0),
    (15.3, 57.3),
    (13.3, 71.5),
    (7.6, 80.8),
    (-5.6, 92.8),
    (-19.4, 102.2),
    (-30.7, 105.6),
    (-16.0, 113.8),
    (-2.4, 117.4),
    (10.7, 115.7),
    (23.8, 114.1),
    (35.7, 107.6),
    (47.6, 101.2),
    (59.9, 88.9),
    (72.2, 76.6),
    (95.7, 69.7),
    (109.6, 73.0),
    (119.2, 78.6),
    (124.4, 84.5),
    (130.0, 103.2),
    (146.9, 115.4),
    (165.1, 121.1),
    (183.3, 126.7),
    (199.5, 127.5),
)
"""The Design by Jone template's pickguard: the Stratocaster's traced HH
guard (see ``_STRATOCASTER_PICKGUARD_POINTS``), at the same scale on this
body — its notch on the neck pocket's end, its bass side stepping back
clear of the bridge — and wherever it ran past the outline 6 mm in, that
line instead (round the horn and the deep cutaway) — then reshaped by
hand in the body editor: its horn's tip turned along the body's edge, its
edge kept off the pots' knobs — X from the heel end."""

_JACKSON_RR_PICKGUARD_POINTS: tuple[tuple[float, float], ...] = (
    (-29.6, -37.5),
    (0.2, -40.9),
    (76.9, -47.5),
    (175.9, -55.2),
    (168.9, -35.5),
    (161.9, -35.5),
    (161.9, -27.6),
    (161.9, -19.7),
    (161.9, -11.8),
    (161.9, -3.9),
    (161.9, 4.0),
    (161.9, 11.8),
    (161.9, 19.7),
    (161.9, 27.6),
    (161.9, 35.5),
    (169.6, 35.5),
    (177.3, 35.5),
    (185.0, 35.5),
    (192.6, 35.5),
    (200.3, 35.5),
    (208.0, 35.5),
    (207.4, 55.3),
    (226.6, 92.7),
    (307.6, 166.1),
    (222.7, 137.5),
    (202.0, 130.0),
    (181.3, 122.4),
    (160.7, 114.8),
    (140.0, 107.2),
    (119.3, 99.7),
    (98.6, 92.0),
    (77.9, 84.5),
    (57.2, 76.9),
    (36.5, 69.4),
    (15.9, 61.7),
    (-4.9, 54.2),
    (-25.6, 46.8),
    (-41.0, 31.6),
    (-41.0, 28.7),
    (-20.5, 28.7),
    (0.0, 28.7),
    (0.0, 9.6),
    (0.0, -9.5),
    (0.0, -28.6),
    (-16.5, -28.6),
    (-33.0, -28.6),
)
"""The Jackson RR style template's pickguard, drawn in the body editor: a
narrow strip past the pickups on the longer wing's side, the shorter
wing's side running out along it toward its tip, stepped round the
bridge — X from the heel end."""

_LES_PAUL_PICKGUARD_POINTS: tuple[tuple[float, float], ...] = (
    (-30.1, -54.5),
    (-12.5, -43.0),
    (13.6, -45.5),
    (36.3, -48.2),
    (53.6, -52.2),
    (74.0, -58.3),
    (92.4, -65.2),
    (112.1, -73.5),
    (133.2, -76.0),
    (158.0, -72.5),
    (175.9, -55.2),
    (175.9, -35.5),
    (168.9, -35.5),
    (161.9, -35.5),
    (161.9, -27.6),
    (161.9, -19.7),
    (161.9, -11.8),
    (161.9, -3.9),
    (161.9, 4.0),
    (161.9, 11.8),
    (161.9, 19.7),
    (161.9, 27.6),
    (161.9, 35.5),
    (169.9, 35.5),
    (177.9, 35.5),
    (185.9, 35.5),
    (193.9, 35.5),
    (201.9, 35.5),
    (209.9, 35.5),
    (217.9, 35.5),
    (217.9, 46.7),
    (216.6, 69.0),
    (211.8, 97.8),
    (270.7, 145.4),
    (235.5, 155.6),
    (193.1, 150.8),
    (172.5, 142.6),
    (153.5, 131.0),
    (135.9, 117.4),
    (119.3, 102.6),
    (101.3, 89.5),
    (80.4, 82.6),
    (58.6, 86.4),
    (38.0, 94.8),
    (17.5, 103.5),
    (-4.1, 107.8),
    (-19.6, 103.9),
    (-4.9, 87.7),
    (3.4, 67.1),
    (1.4, 45.3),
    (-12.8, 28.7),
    (0.0, 28.7),
    (0.0, 9.6),
    (0.0, -9.5),
    (0.0, -28.6),
    (-16.5, -28.6),
    (-33.0, -28.6),
)
"""The Les Paul style template's pickguard, drawn in the body editor:
round the cutaway's horn on the treble side and down past the pickups,
widening toward the bridge on the bass side, stepped round the bridge —
X from the heel end."""

_DESIGN_BY_JONE = DesignByJoneShape()

YOUR_DESIGN_TEMPLATES: dict[str, tuple[str, YourDesignShape]] = {
    "design_by_jone": (
        "Design by Jone",
        YourDesignShape(
            control_points=_resampled(
                OMARUNKO_OUTLINE_POINTS, 64, -OMARUNKO_HEEL_END_X
            ),
            pickguard_points=_DESIGN_BY_JONE_PICKGUARD_POINTS,
            switch_cavity_offset=_DESIGN_BY_JONE.switch_cavity_offset,
            switch_cavity_y=_DESIGN_BY_JONE.switch_cavity_y,
            switch_cavity_diameter=_DESIGN_BY_JONE.switch_cavity_diameter,
            switch_cover_offset=_DESIGN_BY_JONE.switch_cover_offset,
            switch_cover_y=_DESIGN_BY_JONE.switch_cover_y,
            switch_cover_diameter=_DESIGN_BY_JONE.switch_cover_diameter,
            pot_offsets=_DESIGN_BY_JONE.pot_offsets,
            jack_offset=_DESIGN_BY_JONE.jack_offset,
            jack_y=_DESIGN_BY_JONE.jack_y,
            jack_direction_degrees=_DESIGN_BY_JONE.jack_direction_degrees,
            neck_bolts=_DESIGN_BY_JONE.neck_bolts,
            battery_offset=_DESIGN_BY_JONE.battery_offset,
            battery_y=_DESIGN_BY_JONE.battery_y,
            battery_angle_degrees=_DESIGN_BY_JONE.battery_angle_degrees,
        ),
    ),
    "les_paul": (
        "Les Paul style (mockup, not the original)",
        YourDesignShape(
            control_points=_LES_PAUL_POINTS,
            pickguard_points=_LES_PAUL_PICKGUARD_POINTS,
            # The selector switch on the bass-side upper bout, as on the
            # original; the neck bolts move out as far as the cutaway lets.
            switch_cavity_offset=2.0,
            switch_cavity_y=-78.0,
            switch_cover_offset=2.0,
            switch_cover_y=-78.0,
            neck_bolts=((-38.5, -20.0), (-5.5, -20.0), (-38.5, 12.0), (-5.5, 12.0)),
        ),
    ),
    "stratocaster": (
        "Stratocaster style (mockup, not the original)",
        YourDesignShape(
            control_points=_STRATOCASTER_POINTS,
            pickguard_points=_STRATOCASTER_PICKGUARD_POINTS,
            # The neck bolts spread like the bass's: the pair at the
            # pocket's mouth out near the body's edge, the rear pair's
            # ferrules wholly over the pocket.
            neck_bolts=((-63.5, -20.0), (-7.5, -20.0), (-63.5, 20.0), (-7.5, 20.0)),
        ),
    ),
    "jackson_rr": (
        "Jackson RR style (mockup, not the original)",
        YourDesignShape(
            control_points=_JACKSON_RR_POINTS,
            pickguard_points=_JACKSON_RR_PICKGUARD_POINTS,
            # The wings are narrow: the switch goes on the bass wing, the
            # pots and control cavity a little forward on the treble wing
            # and the jack into the treble wing's outer edge.
            switch_cavity_offset=230.0,
            switch_cavity_y=-85.0,
            switch_cover_offset=230.0,
            switch_cover_y=-85.0,
            pot_offsets=((170.8, 86.0), (210.8, 87.0)),
            control_shift=(-10.0, 0.0),
            # The jack in the treble wing's outer edge where it passes
            # nearest the control cavity, aimed at it (a 26 mm bore).
            jack_offset=175.2,
            jack_y=126.5,
            jack_direction_degrees=291.8,
            # The neck bolts' front pair as far out as the narrow wings
            # leave 3-5 mm of wood beside its ferrules (the treble wing is
            # the nearer), the rear pair's ferrules wholly over the pocket.
            neck_bolts=((-50.0, -20.0), (-7.5, -20.0), (-44.0, 20.0), (-7.5, 20.0)),
            # The battery box behind the control cavity, on the treble
            # wing, turned along it.
            battery_offset=271.0,
            battery_y=120.0,
            battery_angle_degrees=60.0,
        ),
    ),
    "jazz_bass": ("Jazz Bass style (mockup, not the original)", BASS_BODY),
}
"""Starting points for a drawn body: a label and a complete shape each.

"Design by Jone" is the traced DXF outline resampled to 64 evenly spaced
control points, with that body's own switch, pot and jack placements. The
Les Paul style and Stratocaster style ones are mockups — traced from a
reference render or drawing and then reshaped by hand, not the original
outlines — the Les Paul's selector switch on the bass-side upper bout. The
Jackson RR style one is a mockup the same way, with its switch
on the bass wing and its pots, control cavity and jack moved to fit the
treble wing; the Jazz Bass style one, a mockup the same way, is the bass
guitar's default body (``BASS_BODY``), its pots and control cavity moved
onto the lower bout behind the bridge pickup. The other templates share
the drawn body's default pot and jack placements.
The "Design by Jone" one is also the guitar's default body
(``GUITAR_BODY``).
Loading one in the web app replaces the outline and the placements, which
then stay editable.
"""

GUITAR_BODY = YOUR_DESIGN_TEMPLATES["design_by_jone"][1]
"""The guitar's default drawn body: the Design by Jone template."""
