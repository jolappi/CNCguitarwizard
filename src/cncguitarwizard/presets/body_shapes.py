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

from ..geometry.exceptions import BodyGeometryError, GeometryException
from ..geometry.primitives import (
    DrawnPoint,
    Point2D,
    closed_catmull_rom,
    drawn_points,
    moved,
)
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


def narrow_y(y: float, widening: float) -> float:
    """Undo ``widen_y``: move a lateral coordinate back in by ``widening / 2``.

    A point within ``widening / 2`` of the centreline goes onto it.
    """
    half = widening / 2.0
    return y - half if y > half else y + half if y < -half else 0.0


def widen_points(
    points: tuple[tuple[float, float], ...], widening: float
) -> tuple[tuple[float, float], ...]:
    """Return ``points`` with every Y moved out by ``widening / 2``."""
    if widening == 0.0:
        return points
    return tuple((x, widen_y(y, widening)) for x, y in points)


def widen_drawn(
    points: tuple[DrawnPoint, ...], widening: float
) -> tuple[DrawnPoint, ...]:
    """Return drawn ``points`` widened as ``widen_points``, marks kept."""
    if widening == 0.0:
        return points
    return tuple(moved(p, p[0], widen_y(p[1], widening)) for p in points)


def flipped_drawn(points: tuple[DrawnPoint, ...]) -> tuple[DrawnPoint, ...]:
    """Return drawn ``points`` mirrored across the centreline, marks kept."""
    return tuple(moved(p, p[0], -p[1]) for p in points)


def _side_drawn(
    points: tuple[DrawnPoint, ...], mirrored: bool
) -> tuple[DrawnPoint, ...]:
    """Return a drawn outline, mirrored (order reversed) if asked, as ``_side``."""
    if not mirrored:
        return points
    return tuple(reversed(flipped_drawn(points)))


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
        strap_guide_offset: The flame strap guide's centre X from the heel
            end (used with ``Prototype001Parameters.body_strap_guide``);
            empty (or ``strap_guide_y`` or ``strap_guide_angle_degrees``)
            on the strap's way from its button in the tail's middle.
            By default where the guide is on the Design by Jone guitar,
            read off a photograph of its back: on the bass side of the
            tail near the edge, on the strap's way from the button (61
            degrees from the neck's axis), its bar nearly along the neck
            (-10 degrees) so the strap leaves it nearly straight up over
            the bass edge.
        strap_guide_y: The strap guide's centre Y.
        strap_guide_angle_degrees: The strap guide's bar from the neck's
            axis, counter-clockwise; the strap runs square to it.
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
        pickguard_controls: Where a pickguard's controls go (the
            ``"pickguard"`` layout), as on the original: the blade switch's
            slot centre, then the three pots (X from the heel end, Y); the
            cavity under them is routed round them. Empty: a row of pots
            along the neck turned and moved to fit under the guard.
        pickguard_switch_degrees: The switch slot's direction, counter-
            clockwise from the neck's axis, with ``pickguard_controls``.
        pickguard_cavity_points: The cavity under ``pickguard_controls``
            as drawn (X from the heel end, Y), as on the original; empty
            for one routed round them.
        rear_pots: Where a generated rear cavity's pots go, as on the
            original (``"gibson_4"``, ``"rear_3"``, ``"volume_1"``,
            ``"active_4"`` with that many pots): (X from the heel end, Y);
            the cavity and its cover are routed round them (and round a
            jack mounted in the top). Empty, or another count: the
            layout's own row or square of pots.
        switch_in_control_cavity: Whether the selector switch shares
            the ``rear_pots`` cavity and its cover, as on an SG (one cavity
            for all the electronics) instead of a round cavity of its own;
            a switch close beside the pots shares it anyway.
        jack_inset: How far in from the edge, along the jack's line, a
            ``"strat"`` jack's cavity centre sits; empty for just in from
            the edge.
        arm_contour_points: Where a drawn arm contour starts on the top:
            an open line's control points (X from the heel end, Y), its
            ends on the body's edge; empty for the automatic contour (used
            with ``Prototype001Parameters.body_arm_contour_depth``).
        belly_cut_points: The same for a drawn belly cut on the back (seen
            from the top, as the outline is), used with
            ``Prototype001Parameters.body_belly_cut_depth``.
        leg_contour_points: The same for a drawn leg contour on the back
            of the treble-side waist, used with
            ``Prototype001Parameters.body_leg_contour_depth``.
        heel_relief_points: The same for a drawn heel relief on the back,
            where the neck joins (used with
            ``Prototype001Parameters.body_heel_relief``).
        top_round_points: Points on the edge in pairs (X from the heel
            end, Y): a top bevel all round
            (``Prototype001Parameters.body_top_bevel_width``) leaves the
            edge between the two of each pair, the shorter way round, to
            the edge's roundover; empty, it runs all round.
        back_round_points: The same for a back bevel all round.
        step_points: A drawn stepped top's step lines (used with
            ``Prototype001Parameters.body_stepped_top``): one closed
            polygon of points (X from the heel end, Y) per step, joined by
            straight lines but rounded through a point marked ``"round"``
            (``spline.drawn_polygon``), the outermost first, each inside
            the one before; empty for steps the ``body_top_step_insets`` in
            from the edge.
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
    strap_guide_offset: float | None = 216.0
    strap_guide_y: float | None = -106.0
    strap_guide_angle_degrees: float | None = -10.0
    control_angle_degrees: float = 0.0
    control_stretch: float = 0.0
    control_stretch_across: float = 0.0
    pickguard_points: tuple[DrawnPoint, ...] = ()
    pickguard_controls: tuple[tuple[float, float], ...] = ()
    pickguard_switch_degrees: float = 0.0
    pickguard_cavity_points: tuple[tuple[float, float], ...] = ()
    rear_pots: tuple[tuple[float, float], ...] = ()
    switch_in_control_cavity: bool = False
    jack_inset: float | None = None
    arm_contour_points: tuple[DrawnPoint, ...] = ()
    belly_cut_points: tuple[DrawnPoint, ...] = ()
    leg_contour_points: tuple[DrawnPoint, ...] = ()
    heel_relief_points: tuple[DrawnPoint, ...] = ()
    top_round_points: tuple[DrawnPoint, ...] = ()
    back_round_points: tuple[DrawnPoint, ...] = ()
    step_points: tuple[tuple[DrawnPoint, ...], ...] = ()
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
        strap_guide_offset: The flame strap guide's centre X from the heel
            end (used with ``Prototype001Parameters.body_strap_guide``);
            empty (or ``strap_guide_y`` or ``strap_guide_angle_degrees``)
            on the strap's way from its button in the tail's middle.
        strap_guide_y: The strap guide's centre Y.
        strap_guide_angle_degrees: The strap guide's bar from the neck's
            axis, counter-clockwise; the strap runs square to it.
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
        pickguard_controls: Where a pickguard's controls go (the
            ``"pickguard"`` layout), as on the original: the blade switch's
            slot centre, then the three pots (X from the heel end, Y); the
            cavity under them is routed round them. Empty: a row of pots
            along the neck turned and moved to fit under the guard.
        pickguard_switch_degrees: The switch slot's direction, counter-
            clockwise from the neck's axis, with ``pickguard_controls``.
        pickguard_cavity_points: The cavity under ``pickguard_controls``
            as drawn (X from the heel end, Y), as on the original; empty
            for one routed round them.
        rear_pots: Where a generated rear cavity's pots go, as on the
            original (``"gibson_4"``, ``"rear_3"``, ``"volume_1"``,
            ``"active_4"`` with that many pots): (X from the heel end, Y);
            the cavity and its cover are routed round them (and round a
            jack mounted in the top). Empty, or another count: the
            layout's own row or square of pots.
        switch_in_control_cavity: Whether the selector switch shares
            the ``rear_pots`` cavity and its cover, as on an SG (one cavity
            for all the electronics) instead of a round cavity of its own;
            a switch close beside the pots shares it anyway.
        jack_inset: How far in from the edge, along the jack's line, a
            ``"strat"`` jack's cavity centre sits; empty for just in from
            the edge.
        arm_contour_points: Where a drawn arm contour starts on the top:
            an open line's control points (X from the heel end, Y), its
            ends on the body's edge; empty for the automatic contour (used
            with ``Prototype001Parameters.body_arm_contour_depth``).
        belly_cut_points: The same for a drawn belly cut on the back (seen
            from the top, as the outline is), used with
            ``Prototype001Parameters.body_belly_cut_depth``.
        leg_contour_points: The same for a drawn leg contour on the back
            of the treble-side waist, used with
            ``Prototype001Parameters.body_leg_contour_depth``.
        heel_relief_points: The same for a drawn heel relief on the back,
            where the neck joins (used with
            ``Prototype001Parameters.body_heel_relief``).
        top_round_points: Points on the edge in pairs (X from the heel
            end, Y): a top bevel all round
            (``Prototype001Parameters.body_top_bevel_width``) leaves the
            edge between the two of each pair, the shorter way round, to
            the edge's roundover; empty, it runs all round.
        back_round_points: The same for a back bevel all round.
        step_points: A drawn stepped top's step lines (used with
            ``Prototype001Parameters.body_stepped_top``): one closed
            polygon of points (X from the heel end, Y) per step, joined by
            straight lines but rounded through a point marked ``"round"``
            (``spline.drawn_polygon``), the outermost first, each inside
            the one before; empty for steps the ``body_top_step_insets`` in
            from the edge.

    Raises:
        BodyGeometryError: For fewer than four or non-finite control points.
    """

    kind: Literal["your_design"] = "your_design"
    control_points: tuple[DrawnPoint, ...] = YOUR_DESIGN_START_POINTS
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
    strap_guide_offset: float | None = None
    strap_guide_y: float | None = None
    strap_guide_angle_degrees: float | None = None
    control_angle_degrees: float = 0.0
    control_stretch: float = 0.0
    control_stretch_across: float = 0.0
    pickguard_points: tuple[DrawnPoint, ...] = ()
    pickguard_controls: tuple[tuple[float, float], ...] = ()
    pickguard_switch_degrees: float = 0.0
    pickguard_cavity_points: tuple[tuple[float, float], ...] = ()
    rear_pots: tuple[tuple[float, float], ...] = ()
    switch_in_control_cavity: bool = False
    jack_inset: float | None = None
    arm_contour_points: tuple[DrawnPoint, ...] = ()
    belly_cut_points: tuple[DrawnPoint, ...] = ()
    leg_contour_points: tuple[DrawnPoint, ...] = ()
    heel_relief_points: tuple[DrawnPoint, ...] = ()
    top_round_points: tuple[DrawnPoint, ...] = ()
    back_round_points: tuple[DrawnPoint, ...] = ()
    step_points: tuple[tuple[DrawnPoint, ...], ...] = ()
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
        try:
            points, _ = drawn_points(self.control_points)
        except GeometryException as error:
            raise BodyGeometryError(
                "Your design's control points must be finite (x, y) pairs, or "
                f'(x, y, "corner") for a sharp corner: {error}'
            ) from error
        if not all(math.isfinite(p.x) and math.isfinite(p.y) for p in points):
            raise BodyGeometryError(
                "Your design's control points must be finite (x, y) pairs."
            )

    def outline_points(
        self, heel_end: float, widening: float = 0.0
    ) -> tuple[Point2D, ...]:
        """Return the spline outline placed relative to ``heel_end``.

        ``widening`` moves the control points out from the centreline
        before the spline is drawn (see ``widen_points``); a point marked
        ``"corner"`` is sharp, the outline straight between two.
        """
        points, corners = drawn_points(widen_drawn(self.control_points, widening))
        return closed_catmull_rom(
            tuple(Point2D(p.x + heel_end, p.y) for p in points),
            OUTLINE_SAMPLES_PER_SEGMENT,
            corners,
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
        strap_guide_y=None if shape.strap_guide_y is None else -shape.strap_guide_y,
        strap_guide_angle_degrees=(
            None
            if shape.strap_guide_angle_degrees is None
            else -shape.strap_guide_angle_degrees
        ),
        control_angle_degrees=-shape.control_angle_degrees,
        pickguard_points=_side_drawn(shape.pickguard_points, True),
        pickguard_controls=flipped(shape.pickguard_controls),
        pickguard_switch_degrees=-shape.pickguard_switch_degrees,
        pickguard_cavity_points=tuple(
            (x, -y) for x, y in reversed(shape.pickguard_cavity_points)
        ),
        rear_pots=flipped(shape.rear_pots),
        arm_contour_points=flipped_drawn(shape.arm_contour_points),
        belly_cut_points=flipped_drawn(shape.belly_cut_points),
        leg_contour_points=flipped_drawn(shape.leg_contour_points),
        heel_relief_points=flipped_drawn(shape.heel_relief_points),
        top_round_points=flipped_drawn(shape.top_round_points),
        back_round_points=flipped_drawn(shape.back_round_points),
        step_points=tuple(_side_drawn(polygon, True) for polygon in shape.step_points),
        mirrored=not shape.mirrored,
    )
    if isinstance(mirrored, YourDesignShape):
        mirrored = replace(
            mirrored, control_points=_side_drawn(mirrored.control_points, True)
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
        strap_guide_y=(
            None
            if shape.strap_guide_y is None
            else widen_y(shape.strap_guide_y, widening)
        ),
        control_shift=(shift_x, moved_almond - almond_y),
        pickguard_points=widen_drawn(shape.pickguard_points, widening),
        pickguard_controls=widen_points(shape.pickguard_controls, widening),
        pickguard_cavity_points=widen_points(shape.pickguard_cavity_points, widening),
        rear_pots=widen_points(shape.rear_pots, widening),
        arm_contour_points=widen_drawn(shape.arm_contour_points, widening),
        belly_cut_points=widen_drawn(shape.belly_cut_points, widening),
        leg_contour_points=widen_drawn(shape.leg_contour_points, widening),
        heel_relief_points=widen_drawn(shape.heel_relief_points, widening),
        top_round_points=widen_drawn(shape.top_round_points, widening),
        back_round_points=widen_drawn(shape.back_round_points, widening),
        step_points=tuple(
            widen_drawn(polygon, widening) for polygon in shape.step_points
        ),
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
    (-73.8, -23.1),
    (-73.0, -24.4),
    (-72.2, -25.7),
    (-71.3, -26.9),
    (-69.9, -27.5),
    (-67.7, -28.0),
    (-64.9, -29.1),
    (-59.7, -32.2),
    (-56.0, -37.0),
    (-55.0, -39.9),
    (-54.2, -42.8),
    (-54.0, -48.9),
    (-54.8, -54.8),
    (-56.4, -60.7),
    (-58.9, -66.2),
    (-65.4, -75.6),
    (-74.6, -83.5),
    (-79.3, -86.1),
    (-85.0, -88.2),
    (-96.8, -90.8),
    (-108.2, -91.4),
    (-120.3, -92.2),
    (-125.9, -94.3),
    (-128.3, -96.1),
    (-130.2, -98.5),
    (-132.2, -104.2),
    (-132.4, -110.3),
    (-131.1, -115.4),
    (-128.3, -120.7),
    (-124.1, -125.2),
    (-119.3, -128.9),
    (-109.2, -134.1),
    (-97.6, -137.8),
    (-86.3, -139.4),
    (-74.1, -139.8),
    (-49.8, -138.3),
    (-26.7, -134.6),
    (-4.0, -128.8),
    (18.3, -121.0),
    (30.0, -117.4),
    (41.7, -114.7),
    (53.0, -113.6),
    (65.1, -114.5),
    (87.9, -119.8),
    (109.7, -129.0),
    (132.5, -137.8),
    (154.4, -146.9),
    (165.1, -150.9),
    (176.7, -154.4),
    (187.7, -157.2),
    (199.6, -159.3),
    (223.8, -162.0),
    (247.4, -160.8),
    (270.3, -155.6),
    (290.4, -143.6),
    (299.2, -135.2),
    (306.6, -125.6),
    (317.8, -104.8),
    (324.0, -82.2),
    (325.9, -58.7),
    (326.3, -34.1),
    (326.3, 13.5),
    (326.3, 37.4),
    (326.3, 62.0),
    (325.9, 73.4),
    (324.6, 85.5),
    (321.8, 96.5),
    (317.2, 107.8),
    (311.6, 117.7),
    (304.4, 127.5),
    (296.0, 136.4),
    (286.6, 144.1),
    (277.1, 150.4),
    (266.1, 155.7),
    (255.1, 158.4),
    (243.1, 159.8),
    (219.4, 160.2),
    (207.3, 159.2),
    (195.4, 157.1),
    (172.8, 150.7),
    (150.6, 142.5),
    (128.9, 133.1),
    (106.7, 122.7),
    (96.2, 118.2),
    (84.4, 115.3),
    (73.0, 114.9),
    (60.9, 116.2),
    (50.0, 119.2),
    (38.7, 123.9),
    (16.2, 133.5),
    (5.5, 137.3),
    (-6.3, 140.2),
    (-17.5, 141.8),
    (-29.7, 141.6),
    (-34.9, 140.8),
    (-40.8, 139.5),
    (-52.3, 135.5),
    (-62.9, 129.4),
    (-66.9, 124.9),
    (-69.0, 119.3),
    (-68.9, 114.0),
    (-67.0, 108.3),
    (-63.1, 103.7),
    (-57.8, 100.9),
    (-46.8, 98.2),
    (-35.2, 94.9),
    (-24.9, 90.0),
    (-15.6, 82.2),
    (-9.6, 71.6),
    (-7.3, 59.8),
    (-8.7, 48.5),
    (-12.8, 37.0),
    (-20.2, 28.6),
    (-32.3, 27.6),
    (-43.8, 27.4),
    (-56.1, 27.3),
    (-62.2, 27.2),
    (-68.3, 27.1),
    (-71.3, 26.5),
    (-73.3, 24.4),
    (-73.9, 18.4),
    (-73.9, 13.0),
    (-73.9, 6.8),
    (-73.9, -5.5),
    (-73.9, -10.9),
    (-73.9, -17.0),
    (-73.9, -20.1),
)
"""An offset double cutaway, the Stratocaster's outline.

Traced from a reference DXF drawing of the original (the body's outermost
edge, aligned on the drawing's neck pocket: the round end of its pocket is
the heel end, its middle the centreline; already right-handed, the long
bass horn at -Y), its neck end's face straight across as drawn. 127
control points, within 0.25 mm of the drawing."""


_JACKSON_RR_POINTS: tuple[tuple[float, float], ...] = (
    (-63.5, 5.6),
    (-63.5, 11.5),
    (-63.5, 18.2),
    (-63.5, 21.5),
    (-63.5, 24.9),
    (-63.2, 28.1),
    (-60.0, 28.6),
    (-54.5, 30.4),
    (-48.6, 33.3),
    (-43.3, 37.1),
    (-38.7, 41.9),
    (-35.4, 46.6),
    (-33.8, 49.4),
    (-32.7, 50.4),
    (-31.3, 51.0),
    (-28.2, 52.0),
    (-25.2, 53.2),
    (-19.0, 55.4),
    (-6.9, 59.8),
    (5.1, 64.4),
    (28.7, 72.8),
    (52.1, 81.5),
    (99.9, 98.9),
    (194.5, 133.7),
    (241.4, 150.8),
    (289.0, 168.3),
    (312.6, 176.8),
    (323.9, 181.0),
    (335.9, 185.4),
    (341.2, 187.4),
    (347.3, 189.5),
    (350.4, 190.7),
    (351.9, 190.7),
    (353.0, 189.6),
    (353.0, 188.2),
    (352.1, 186.8),
    (349.8, 184.4),
    (345.4, 179.5),
    (341.1, 174.5),
    (332.6, 164.4),
    (316.7, 144.6),
    (309.4, 134.7),
    (301.8, 124.1),
    (288.1, 102.9),
    (274.6, 80.6),
    (262.7, 58.2),
    (251.7, 35.5),
    (246.7, 24.3),
    (244.2, 18.2),
    (242.9, 15.3),
    (242.4, 13.7),
    (243.1, 12.3),
    (244.9, 9.6),
    (246.7, 6.9),
    (250.3, 1.4),
    (257.6, -9.4),
    (272.3, -30.1),
    (287.8, -50.9),
    (320.6, -91.2),
    (355.2, -129.2),
    (392.5, -166.3),
    (411.6, -183.5),
    (430.9, -200.3),
    (440.4, -208.2),
    (450.7, -216.3),
    (455.8, -220.5),
    (461.0, -224.4),
    (463.6, -226.4),
    (466.2, -228.4),
    (468.5, -230.7),
    (467.3, -233.3),
    (461.8, -231.7),
    (455.7, -229.5),
    (443.7, -225.2),
    (420.3, -216.6),
    (372.5, -198.8),
    (278.1, -164.2),
    (183.5, -129.3),
    (88.9, -94.6),
    (42.1, -77.4),
    (18.4, -68.7),
    (-5.6, -59.7),
    (-16.9, -55.7),
    (-29.0, -51.1),
    (-34.4, -49.2),
    (-40.4, -47.0),
    (-43.4, -46.0),
    (-46.5, -44.8),
    (-49.4, -43.6),
    (-50.4, -40.6),
    (-52.8, -35.4),
    (-57.4, -30.8),
    (-60.2, -29.0),
    (-63.2, -27.8),
    (-63.5, -24.5),
    (-63.5, -21.1),
    (-63.5, -14.5),
    (-63.5, -7.8),
)
"""An offset V, the Jackson Randy Rhoads' outline.

Traced from a reference render of the original (its silhouette, scaled at
3.215 px/mm to the earlier tracing's unchanged edges: 532 mm from the neck
joint to the bass wing's tip), its body ending where the shoulders' arcs
meet the neck's sides, and the jack on the V's inner edge left out. The
long pointed wing is on the bass side, the controls on the treble wing and
the selector switch on the bass wing. 98 control points, within
0.25 mm of the silhouette."""


_MUSIC_MAN_AXIS_POINTS: tuple[tuple[float, float], ...] = (
    (-37.3, 26.5),
    (-36.3, 27.4),
    (-34.8, 27.4),
    (-31.8, 27.4),
    (-25.8, 28.5),
    (-20.0, 30.1),
    (-14.7, 32.8),
    (-9.9, 36.6),
    (-6.0, 41.1),
    (-5.4, 42.5),
    (-4.7, 43.8),
    (-3.2, 46.5),
    (-1.3, 52.2),
    (-0.6, 64.1),
    (-3.9, 75.7),
    (-10.9, 85.5),
    (-20.4, 92.9),
    (-30.9, 98.8),
    (-34.2, 103.8),
    (-34.4, 106.8),
    (-34.2, 109.8),
    (-32.6, 115.5),
    (-29.1, 120.5),
    (-24.4, 124.2),
    (-18.8, 126.5),
    (-6.9, 128.1),
    (5.0, 126.3),
    (16.5, 122.6),
    (27.4, 117.4),
    (38.7, 113.3),
    (50.7, 111.8),
    (62.6, 113.1),
    (74.0, 117.0),
    (84.1, 123.6),
    (93.8, 130.8),
    (103.6, 137.9),
    (113.9, 144.2),
    (124.7, 149.6),
    (136.1, 153.8),
    (147.7, 156.8),
    (159.6, 158.7),
    (171.7, 159.1),
    (183.7, 158.7),
    (195.7, 157.1),
    (207.4, 154.2),
    (218.7, 150.1),
    (229.4, 144.5),
    (239.8, 138.3),
    (249.5, 131.1),
    (258.4, 122.9),
    (266.4, 113.8),
    (273.6, 104.2),
    (279.9, 93.9),
    (285.2, 83.0),
    (289.4, 71.7),
    (292.6, 60.1),
    (295.3, 48.3),
    (297.3, 36.4),
    (298.6, 24.5),
    (299.6, 12.5),
    (299.6, 0.4),
    (299.6, -11.7),
    (298.6, -23.7),
    (297.2, -35.6),
    (295.1, -47.5),
    (292.5, -59.3),
    (289.4, -70.9),
    (285.3, -82.3),
    (280.2, -93.2),
    (274.0, -103.6),
    (267.0, -113.4),
    (259.0, -122.5),
    (250.2, -130.7),
    (240.6, -138.1),
    (230.4, -144.5),
    (219.6, -149.9),
    (208.3, -154.3),
    (196.7, -157.6),
    (184.9, -159.8),
    (172.9, -160.8),
    (160.8, -160.8),
    (148.8, -159.5),
    (137.0, -157.3),
    (125.4, -153.8),
    (114.2, -149.3),
    (103.3, -144.2),
    (92.5, -138.8),
    (82.0, -132.7),
    (71.6, -126.7),
    (61.2, -120.5),
    (50.3, -115.1),
    (39.1, -110.8),
    (27.3, -108.1),
    (15.3, -107.1),
    (3.3, -107.8),
    (-8.5, -110.3),
    (-19.9, -114.4),
    (-31.2, -118.7),
    (-42.6, -122.5),
    (-54.3, -125.4),
    (-66.3, -126.8),
    (-78.3, -125.8),
    (-89.4, -121.1),
    (-98.3, -113.0),
    (-104.1, -102.5),
    (-105.0, -96.6),
    (-105.0, -90.5),
    (-104.6, -84.6),
    (-102.5, -78.9),
    (-96.3, -68.5),
    (-88.9, -59.0),
    (-85.1, -54.3),
    (-81.4, -49.6),
    (-78.5, -44.3),
    (-78.0, -38.4),
    (-80.2, -32.8),
    (-81.6, -30.1),
    (-81.9, -27.2),
    (-75.5, -19.5),
    (-69.2, -11.9),
    (-62.8, -4.2),
    (-56.4, 3.5),
    (-50.0, 11.2),
    (-43.7, 18.8),
)
"""A Music Man Axis's outline: a single cutaway, its bass horn reaching up
beside the neck.

Traced from a straight-on product photo (zZounds' Axis listing, "Body
Straight Front"), scaled from its frets (2.997 px/mm, the 11th to the
22nd fret within 0.5 px of a 25.5 in scale's) and placed with the last
fret 4 mm ahead of the heel end: its strap buttons and the jack plate on
its edge left out, the outline across the neck straight from where the
bass horn meets it to where the treble cutaway does (points every 10 mm
along it, so the spline runs straight). 404.6 by 319.9 mm; 124 control
points, within 0.3 mm of the silhouette."""


_MOCKINGBIRD_POINTS: tuple[tuple[float, float], ...] = (
    (-70.0, -16.0),
    (-65.5, -30.5),
    (-57.7, -35.0),
    (-50.9, -47.1),
    (-51.1, -60.1),
    (-58.8, -72.9),
    (-70.8, -77.6),
    (-85.0, -77.9),
    (-72.4, -102.6),
    (-50.8, -121.4),
    (-26.2, -134.7),
    (0.1, -142.8),
    (28.5, -146.0),
    (48.3, -144.8),
    (53.4, -136.2),
    (54.0, -125.2),
    (57.2, -111.6),
    (70.2, -103.6),
    (88.9, -100.3),
    (117.2, -103.4),
    (142.6, -114.6),
    (167.4, -127.1),
    (192.1, -140.0),
    (216.8, -152.6),
    (241.6, -165.3),
    (266.9, -176.5),
    (302.7, -187.0),
    (322.9, -170.4),
    (332.9, -144.2),
    (339.5, -117.0),
    (341.4, -88.0),
    (340.5, -58.6),
    (337.0, -30.1),
    (330.4, -2.6),
    (320.9, 24.4),
    (309.5, 49.7),
    (296.2, 74.1),
    (280.5, 97.6),
    (263.9, 121.3),
    (241.0, 148.3),
    (225.1, 160.0),
    (207.2, 171.1),
    (191.1, 166.0),
    (171.4, 151.4),
    (153.4, 139.4),
    (129.2, 125.5),
    (103.0, 116.1),
    (75.6, 109.8),
    (46.2, 108.3),
    (17.2, 110.7),
    (-10.6, 115.8),
    (-37.2, 124.2),
    (-62.4, 135.7),
    (-84.4, 143.9),
    (-122.0, 157.5),
    (-109.8, 128.7),
    (-99.3, 117.6),
    (-80.6, 104.3),
    (-57.6, 87.6),
    (-32.9, 74.8),
    (-19.2, 66.8),
    (-10.7, 57.8),
    (-7.8, 44.1),
    (-15.9, 32.8),
    (-23.8, 30.0),
    (-44.2, 29.3),
    (-63.0, 28.6),
    (-70.0, 16.0),
    (-70.0, 0.0),
)
"""A Mockingbird style mockup — not the original outline.

Traced from a straight-on product photo of a B.C. Rich Mockingbird (its
edge as photographed, the strap button and the jack's rim left out),
scaled from its 24 frets and placed with its 24th fret 4 mm ahead of the
heel end, as the default neck's is; the neck crossed off 70 mm ahead of
the heel end, where the bass horn's notch meets it. Then reshaped by
hand in the body editor: the long curved horn on the treble side drawn
longer and sharper, the treble beak below it redrawn, the front of the
bass side's deep scoop and its lower lobe drawn out. The notched short
horn is on the bass side. 69 control points. A genre starting point,
free to use and change, not a reproduction of any maker's body."""


_TELECASTER_POINTS: tuple[tuple[float, float], ...] = (
    (-73.0, -17.0),
    (-67.6, -28.5),
    (-61.3, -32.4),
    (-59.1, -38.5),
    (-61.8, -46.4),
    (-67.8, -56.9),
    (-73.9, -71.4),
    (-76.2, -78.5),
    (-78.5, -81.0),
    (-78.0, -92.5),
    (-78.2, -98.3),
    (-76.8, -108.7),
    (-69.0, -124.5),
    (-59.7, -132.4),
    (-45.1, -138.1),
    (-16.1, -139.9),
    (11.2, -133.4),
    (37.0, -123.4),
    (63.9, -115.9),
    (92.4, -118.5),
    (118.1, -129.0),
    (143.1, -140.9),
    (168.9, -151.2),
    (195.6, -159.2),
    (224.0, -162.9),
    (253.0, -160.6),
    (278.9, -150.6),
    (301.1, -132.8),
    (317.1, -109.4),
    (325.4, -82.9),
    (328.9, -54.3),
    (330.2, -24.9),
    (330.5, 5.0),
    (329.9, 34.7),
    (327.9, 63.9),
    (323.5, 92.1),
    (313.2, 117.8),
    (294.9, 140.0),
    (271.9, 154.9),
    (249.4, 162.6),
    (220.2, 164.0),
    (192.1, 159.4),
    (165.7, 150.8),
    (140.2, 139.9),
    (115.2, 128.0),
    (89.4, 117.8),
    (60.8, 116.3),
    (34.2, 124.6),
    (8.2, 134.2),
    (-19.4, 140.0),
    (-48.2, 137.3),
    (-62.7, 131.1),
    (-71.1, 122.2),
    (-71.9, 108.4),
    (-62.5, 98.2),
    (-36.3, 89.0),
    (-26.2, 84.4),
    (-12.7, 73.4),
    (-5.1, 59.6),
    (-4.6, 47.1),
    (-9.3, 37.1),
    (-23.7, 28.3),
    (-52.5, 27.3),
    (-68.0, 26.0),
    (-73.0, 13.0),
    (-73.0, -3.0),
)
"""A single-cutaway mockup in the Telecaster genre — not the original.

Traced from a straight-on product photo (its edge as photographed, both
strap buttons left out), scaled from its frets and placed with its 22nd
fret 4 mm ahead of the heel end, as a 22-fret neck's would be; the neck
crossed off 73 mm ahead of the heel end. 66 control points. A genre
starting point, free to use and change, not a reproduction of any
maker's body."""


_SG_POINTS: tuple[tuple[float, float], ...] = (
    (-70.4, -26.9),
    (-62.7, -27.2),
    (-40.9, -27.6),
    (-25.0, -28.1),
    (-12.2, -30.9),
    (-9.0, -33.3),
    (-3.5, -37.1),
    (1.5, -41.6),
    (4.4, -45.4),
    (7.8, -58.9),
    (4.6, -72.6),
    (-3.7, -81.9),
    (-18.2, -88.1),
    (-46.3, -84.6),
    (-51.0, -85.6),
    (-38.8, -104.5),
    (-16.3, -121.3),
    (9.3, -132.0),
    (37.4, -136.6),
    (66.7, -135.0),
    (94.0, -128.7),
    (119.6, -117.9),
    (131.1, -114.4),
    (147.4, -114.5),
    (158.9, -118.1),
    (172.4, -126.6),
    (194.6, -144.8),
    (218.6, -159.5),
    (245.9, -166.0),
    (274.8, -164.0),
    (300.4, -153.4),
    (321.6, -133.7),
    (336.9, -110.0),
    (346.5, -84.0),
    (352.5, -56.5),
    (355.7, -27.8),
    (356.8, 1.5),
    (355.3, 30.9),
    (352.3, 59.7),
    (346.3, 87.2),
    (336.8, 113.2),
    (320.4, 136.5),
    (297.6, 153.5),
    (270.8, 161.4),
    (241.9, 161.5),
    (214.8, 154.6),
    (190.3, 141.4),
    (167.8, 123.3),
    (159.3, 117.2),
    (142.9, 112.4),
    (115.2, 118.2),
    (89.9, 129.5),
    (62.4, 135.5),
    (33.3, 134.2),
    (6.8, 125.8),
    (-17.1, 111.3),
    (-31.7, 95.4),
    (-26.5, 93.2),
    (-16.9, 92.3),
    (-6.4, 88.5),
    (-0.6, 83.7),
    (5.0, 75.0),
    (7.3, 57.4),
    (3.0, 46.1),
    (-8.7, 34.9),
    (-20.7, 30.1),
    (-36.0, 28.4),
    (-65.3, 27.5),
    (-70.4, 26.6),
    (-70.6, 2.7),
    (-70.7, -18.3),
)
"""A double-cutaway mockup in the SG genre — not the original outline.

Traced from a straight-on product photo (its edge as photographed, the
strap button left out), scaled from its frets and placed with its 22nd
fret 4 mm ahead of the heel end; the horns meet the neck near its end, so
the outline runs on along the neck's sides to 71 mm ahead of the heel end
to hold a bolt-on neck's pocket. Two pointed horns, the bass one the
longer. 71 control points. A genre starting point, free to use and
change, not a reproduction of any maker's body."""


_EXPLORER_POINTS: tuple[tuple[float, float], ...] = (
    (-58.0, -28.0),
    (-46.0, -28.4),
    (-34.1, -28.7),
    (-19.4, -35.1),
    (-13.2, -44.5),
    (-2.7, -70.1),
    (2.2, -78.1),
    (10.6, -90.1),
    (46.4, -84.3),
    (75.0, -80.8),
    (103.5, -77.2),
    (132.3, -75.2),
    (157.6, -86.7),
    (181.0, -101.0),
    (204.6, -115.0),
    (228.1, -129.0),
    (245.6, -139.1),
    (251.4, -141.3),
    (274.9, -155.9),
    (299.1, -170.0),
    (323.1, -184.0),
    (347.3, -197.9),
    (371.4, -211.2),
    (395.3, -225.5),
    (438.0, -240.1),
    (435.8, -204.8),
    (431.7, -176.5),
    (426.7, -148.7),
    (420.8, -121.1),
    (414.2, -93.8),
    (406.9, -66.9),
    (398.7, -40.3),
    (389.9, -14.0),
    (379.9, 13.1),
    (369.5, 38.8),
    (358.4, 64.2),
    (349.4, 83.5),
    (347.8, 89.5),
    (344.7, 95.3),
    (341.1, 105.5),
    (335.1, 113.8),
    (321.1, 137.8),
    (305.8, 161.4),
    (294.1, 162.7),
    (279.2, 159.1),
    (257.1, 151.4),
    (231.1, 142.3),
    (206.2, 133.5),
    (179.9, 124.4),
    (153.7, 115.3),
    (146.7, 112.9),
    (145.2, 111.6),
    (129.0, 110.7),
    (102.5, 119.1),
    (76.2, 128.3),
    (50.0, 137.5),
    (23.9, 146.7),
    (-2.3, 155.9),
    (-28.5, 165.1),
    (-54.7, 174.3),
    (-81.0, 183.4),
    (-92.4, 184.2),
    (-111.0, 182.4),
    (-109.5, 172.2),
    (-102.0, 163.2),
    (-90.5, 149.0),
    (-71.4, 127.4),
    (-52.2, 105.8),
    (-33.4, 84.3),
    (-23.2, 71.5),
    (-18.9, 60.3),
    (-21.3, 43.5),
    (-27.9, 34.5),
    (-34.1, 29.5),
    (-41.4, 27.9),
    (-55.4, 27.9),
    (-63.8, 18.0),
    (-63.8, 2.0),
    (-63.8, -14.0),
)
"""An Explorer genre mockup — not the original outline.

Traced from a straight-on product photo (its edge as photographed, the
strap button left out), scaled from its frets and placed with its 22nd
fret 4 mm ahead of the heel end; the neck crossed off 64 mm ahead of the
heel end. Then reshaped by hand in the body editor: the bass shoulder,
the long bottom corner and the wing's tip drawn sharper, the tip
further forward. The long wing reaches forward on the treble side, the
long bottom corner is on the bass side. 79 control points. A genre
starting point, free to use and change, not a reproduction of any
maker's body."""


_FLYING_V_POINTS: tuple[tuple[float, float], ...] = (
    (-66.0, -28.0),
    (-46.7, -31.2),
    (-30.3, -39.9),
    (-23.4, -46.5),
    (-17.4, -52.7),
    (1.0, -59.1),
    (27.2, -68.2),
    (53.4, -77.5),
    (79.6, -86.6),
    (105.8, -95.6),
    (132.1, -104.7),
    (158.3, -113.8),
    (184.6, -122.8),
    (210.8, -131.9),
    (237.1, -140.9),
    (263.3, -150.0),
    (289.7, -158.8),
    (316.0, -167.6),
    (342.3, -176.6),
    (368.6, -185.6),
    (394.9, -194.3),
    (421.1, -203.5),
    (448.0, -211.0),
    (457.2, -209.1),
    (463.7, -203.4),
    (467.8, -194.1),
    (465.3, -180.3),
    (455.7, -169.9),
    (433.6, -150.9),
    (411.3, -132.3),
    (389.1, -113.4),
    (366.9, -94.5),
    (344.9, -75.8),
    (322.4, -56.6),
    (300.2, -37.9),
    (280.9, -16.5),
    (278.6, 11.5),
    (294.6, 34.8),
    (316.8, 53.6),
    (338.9, 72.6),
    (361.0, 91.6),
    (383.1, 110.6),
    (405.2, 129.7),
    (427.2, 148.7),
    (449.2, 167.8),
    (461.9, 179.8),
    (466.0, 190.1),
    (461.9, 205.4),
    (452.1, 212.9),
    (439.9, 213.7),
    (424.9, 208.9),
    (398.8, 199.5),
    (372.6, 190.4),
    (346.4, 181.2),
    (320.2, 171.9),
    (294.0, 162.7),
    (267.9, 153.4),
    (241.7, 144.1),
    (215.6, 134.8),
    (189.4, 125.5),
    (163.3, 116.2),
    (137.1, 106.9),
    (111.0, 97.6),
    (84.8, 88.3),
    (58.7, 78.9),
    (32.6, 69.5),
    (6.5, 60.2),
    (-16.5, 52.8),
    (-19.4, 50.5),
    (-21.7, 47.4),
    (-26.3, 42.4),
    (-41.3, 32.7),
    (-60.3, 27.8),
    (-74.8, 14.0),
    (-74.8, -2.0),
    (-74.8, -16.0),
)
"""A Flying V genre mockup — not the original outline.

Traced from a straight-on product photo (its edge as photographed, the
jack on the bass wing's inner edge left out), scaled from its frets and
placed with its 22nd fret 4 mm ahead of the heel end; the neck crossed
off 75 mm ahead of the heel end. Two straight wings and a rounded
notch. 76 control points. A genre starting point, free to use and
change, not a reproduction of any maker's body."""


_RAZORBACK_POINTS: tuple[DrawnPoint, ...] = (
    (-92.8, -28.1, "corner"),
    (-77.4, -33.3, "corner"),
    (-68.2, -40.4),
    (-57.9, -39.7),
    (-40.1, -46.1),
    (-21.8, -62.5),
    (-15.0, -72.7),
    (-4.0, -86.2),
    (15.9, -92.5),
    (40.7, -100.5),
    (67.1, -109.2),
    (106.0, -121.5),
    (136.8, -130.4, "corner"),
    (139.2, -121.4),
    (131.9, -113.8),
    (111.4, -95.3),
    (98.6, -85.1, "corner"),
    (115.2, -89.0),
    (146.2, -100.0),
    (187.5, -114.0),
    (209.5, -121.3),
    (234.2, -129.3),
    (272.8, -142.3),
    (296.6, -150.1),
    (321.9, -159.1),
    (348.4, -167.6),
    (385.3, -180.2),
    (409.9, -188.4),
    (442.0, -199.1),
    (467.5, -207.6),
    (497.9, -217.7),
    (515.1, -223.3),
    (538.0, -230.7),
    (547.5, -223.8, "corner"),
    (538.7, -214.7),
    (517.9, -198.5),
    (495.8, -181.8),
    (482.7, -171.4),
    (471.2, -162.6),
    (446.4, -142.2, "corner"),
    (450.5, -142.7),
    (457.5, -142.8),
    (463.5, -135.4, "corner"),
    (442.1, -116.1),
    (429.3, -106.0),
    (403.0, -85.0),
    (376.3, -63.7),
    (365.5, -54.9),
    (345.2, -38.8),
    (327.5, -24.9),
    (316.9, -13.5),
    (315.5, 4.3),
    (334.4, 21.8),
    (361.1, 45.0),
    (387.2, 68.1),
    (400.8, 80.2),
    (433.1, 108.9),
    (450.1, 123.7),
    (457.2, 136.6, "corner"),
    (444.2, 133.4),
    (438.2, 137.1, "corner"),
    (465.7, 160.6),
    (500.0, 189.9),
    (509.9, 205.4, "corner"),
    (481.8, 197.2),
    (456.4, 188.5),
    (426.5, 178.8),
    (394.0, 167.9),
    (364.9, 158.7),
    (332.4, 147.9),
    (306.1, 139.1),
    (276.7, 129.1),
    (256.0, 122.3),
    (218.2, 110.0),
    (192.8, 101.4),
    (172.4, 95.2),
    (143.0, 86.4),
    (129.8, 90.6),
    (93.4, 103.2),
    (69.0, 111.9),
    (42.2, 120.8),
    (22.6, 127.8),
    (-8.6, 138.3),
    (-45.1, 151.6),
    (-76.2, 162.4),
    (-107.5, 172.6, "corner"),
    (-108.5, 161.8),
    (-96.4, 150.5),
    (-69.3, 129.3),
    (-39.9, 105.0, "corner"),
    (-49.0, 105.6, "corner"),
    (-49.4, 93.4),
    (-22.9, 71.6),
    (-8.1, 54.5),
    (-8.2, 38.7),
    (-19.0, 29.3, "corner"),
)
"""A Razorback genre mockup — not the original outline.

Traced from a straight-on product photo of a Dean Razorback X (its edge
as photographed, the strap button on the bass wing's inner edge left
out), scaled from its frets (24.75 in) and placed with its 22nd fret
4 mm ahead of the heel end; the neck crossed off from where the bass
shoulder meets it, 93 mm ahead of the heel end, to where the treble horn
does, 19 mm ahead. The ML's long treble horn and V tail, a razor notch
in the bass shoulder and a tooth on each tail wing's inner edge, their
points sharp (14 of the 96 control points corners). A genre
starting point, free to use and change, not a reproduction of any
maker's body."""


_FANTOMEN_POINTS: tuple[DrawnPoint, ...] = (
    (-51.9, -28.7, "corner"),
    (-47.7, -40.0),
    (-45.9, -51.3),
    (-44.8, -63.8),
    (-41.6, -84.5),
    (-34.6, -106.1),
    (-28.4, -115.5),
    (-10.7, -129.5),
    (13.2, -134.6),
    (31.4, -131.3),
    (43.9, -126.5),
    (71.4, -113.3),
    (94.7, -104.4),
    (114.2, -100.7),
    (134.4, -100.2),
    (152.5, -101.3),
    (174.7, -105.7),
    (191.5, -109.8),
    (206.9, -114.9),
    (219.9, -119.8),
    (235.4, -126.9),
    (257.0, -138.7),
    (280.9, -153.5),
    (304.3, -169.4),
    (329.6, -185.5),
    (351.8, -199.6),
    (377.0, -212.6),
    (390.1, -215.8),
    (404.2, -213.7),
    (416.1, -205.0),
    (421.2, -197.1),
    (425.6, -187.4),
    (430.8, -166.6),
    (433.7, -144.8),
    (434.2, -133.0),
    (434.2, -108.0),
    (433.7, -80.7),
    (432.0, -59.4),
    (431.5, -49.1),
    (429.9, -28.8),
    (428.3, -12.0),
    (425.2, 8.9),
    (421.8, 33.1),
    (418.9, 48.4),
    (415.8, 65.1),
    (411.8, 82.0),
    (406.1, 103.6),
    (401.2, 119.1),
    (394.7, 136.4),
    (389.4, 148.2),
    (376.8, 169.0),
    (367.3, 180.1),
    (353.8, 189.7),
    (339.4, 194.6),
    (328.4, 194.7),
    (303.8, 187.7),
    (276.4, 175.3),
    (251.7, 161.3),
    (228.0, 147.3),
    (213.4, 139.2),
    (202.2, 133.5),
    (178.3, 122.5),
    (160.1, 115.8),
    (143.6, 112.3),
    (123.2, 110.7),
    (95.9, 112.4),
    (66.6, 118.9),
    (43.9, 126.8),
    (15.1, 139.4),
    (-7.0, 148.8),
    (-26.3, 154.2),
    (-38.3, 155.3),
    (-51.9, 154.3),
    (-69.6, 147.7),
    (-81.7, 138.3),
    (-86.2, 130.6),
    (-87.0, 125.5),
    (-82.1, 118.8),
    (-60.9, 113.2),
    (-43.3, 102.7),
    (-35.4, 94.8),
    (-28.1, 80.8),
    (-27.1, 65.2),
    (-31.9, 51.7),
    (-42.7, 37.7),
    (-52.9, 28.6, "corner"),
)
"""A Fantomen genre mockup — not the original outline.

Traced from a straight-on product photo of a Hagström Fantomen (its edge
and binding as photographed, the strap button at the tail left out),
scaled from its frets (25.5 in) and placed with its 22nd fret 4 mm ahead
of the heel end; the neck crossed off where the bass shoulder and the
treble cutaway meet it, 52 mm ahead of the heel end. An asymmetric
single cut: the pointed treble horn over a deep cutaway, the bass
shoulder's corner, the waist and the wide, flat-cut tail. 86 control
points. A genre starting point, free to use and change, not a
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

_STRATOCASTER_CONTROL_CAVITY: tuple[tuple[float, float], ...] = (
    (107.1, 75.4),
    (105.0, 78.2),
    (103.9, 81.5),
    (103.8, 85.0),
    (104.9, 88.3),
    (106.9, 91.1),
    (139.2, 117.8),
    (141.7, 119.3),
    (144.4, 120.3),
    (147.3, 120.6),
    (150.1, 120.3),
    (153.2, 119.4),
    (156.7, 119.0),
    (160.2, 119.4),
    (163.5, 120.5),
    (192.7, 138.2),
    (195.5, 139.5),
    (198.4, 140.2),
    (201.4, 140.2),
    (204.3, 139.7),
    (207.1, 138.5),
    (209.6, 136.8),
    (211.6, 134.6),
    (213.1, 132.0),
    (214.1, 129.1),
    (214.5, 126.2),
    (214.2, 123.2),
    (213.3, 120.3),
    (211.8, 117.7),
    (181.9, 83.8),
    (162.5, 48.0),
    (158.0, 46.4),
    (149.0, 46.0),
    (140.0, 46.6),
    (135.6, 48.0),
)
"""The Stratocaster style template's control cavity, under its guard: the
user's Stratocaster drawing's (stratbody.dxf, aligned on its neck
pocket's end), its point toward the bridge pickup cut off 2.5 mm short of
the pickup's route (the drawing joins the two; here the pickup's lead
has a hole of its own)."""

_STRATOCASTER_PICKGUARD_POINTS: tuple[tuple[float, float], ...] = (
    (-54.1, 114.9),
    (-48.8, 119.7),
    (-38.1, 123.2),
    (-27.4, 124.5),
    (-16.7, 124.5),
    (-6.0, 122.9),
    (4.7, 120.0),
    (15.4, 116.2),
    (26.1, 112.2),
    (35.9, 108.2),
    (42.6, 105.8),
    (49.3, 103.9),
    (56.0, 102.3),
    (62.7, 101.3),
    (69.3, 100.5),
    (76.0, 100.5),
    (82.7, 100.7),
    (89.4, 101.8),
    (96.0, 103.4),
    (102.7, 105.5),
    (109.4, 107.9),
    (116.1, 110.9),
    (122.8, 113.8),
    (129.4, 116.8),
    (136.1, 120.0),
    (142.8, 122.9),
    (149.5, 125.8),
    (156.2, 128.8),
    (162.8, 131.7),
    (169.5, 134.4),
    (176.2, 137.1),
    (182.9, 139.5),
    (189.6, 141.6),
    (196.2, 143.7),
    (202.9, 145.3),
    (209.6, 146.4),
    (216.3, 146.7),
    (224.8, 144.3),
    (229.1, 140.0),
    (231.0, 133.6),
    (229.1, 127.2),
    (221.9, 117.0),
    (214.9, 109.0),
    (208.4, 101.0),
    (202.1, 93.0),
    (197.0, 85.0),
    (193.3, 76.9),
    (190.8, 68.9),
    (189.4, 60.9),
    (188.9, 52.9),
    (188.6, 44.9),
    (189.0, 36.9),
    (176.7, 36.1),
    (176.7, -39.5),
    (191.2, -41.1),
    (190.1, -50.8),
    (185.3, -61.4),
    (179.7, -66.8),
    (169.3, -72.1),
    (160.2, -74.5),
    (149.5, -76.1),
    (138.8, -75.9),
    (128.1, -74.3),
    (117.4, -71.6),
    (106.7, -68.4),
    (96.0, -64.4),
    (85.4, -60.1),
    (74.7, -56.1),
    (64.0, -52.6),
    (53.3, -50.2),
    (42.6, -48.6),
    (31.9, -47.8),
    (21.2, -47.6),
    (10.6, -48.4),
    (-0.1, -50.0),
    (-10.8, -52.1),
    (-21.5, -54.2),
    (-29.8, -52.1),
    (-32.2, -45.7),
    (-30.6, -39.3),
    (-27.9, -32.9),
    (-7.0, -28.7),
    (-1.1, -21.5),
    (-0.1, -14.0),
    (0.5, -6.3),
    (0.6, 0.0),
    (0.4, 8.2),
    (-0.3, 15.9),
    (-1.5, 23.4),
    (-7.0, 28.7),
    (0.5, 33.4),
    (3.7, 41.4),
    (6.0, 49.4),
    (7.1, 57.4),
    (6.8, 65.5),
    (5.1, 73.5),
    (1.9, 81.5),
    (-3.2, 89.5),
    (-11.9, 98.3),
    (-17.2, 101.8),
    (-23.1, 104.5),
    (-30.1, 106.6),
    (-38.1, 108.7),
    (-46.1, 110.1),
)
"""The Stratocaster style template's pickguard: a vintage style SSS guard
traced from a straight-on photo of a Stratocaster (Wikimedia Commons,
"Fender Stratocaster Relic FCS AvR.png", its body outline fitted to this
template's to within 3 mm): the treble horn's point, the bridge's notch,
the long bass side, and a notch round the neck pocket's round end 0.6 mm
out from it. Its controls are the template's ``pickguard_controls``."""

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

_ALEXI_HEXED_STEP_POINTS: tuple[tuple[tuple[float, float], ...], ...] = (
    (
        (-51.9, -16.3),
        (-49.6, -41.3),
        (350.5, -168.5),
        (219.2, 14.8),
        (311.1, 163.4),
        (-49.6, 41.3),
        (-51.9, 16.3),
    ),
    (
        (-43.5, 0.2),
        (-49.4, -42.3),
        (249.4, -109.9),
        (215.4, 13.1),
        (234.8, 111.3),
        (-49.4, 42.3),
    ),
)
"""The Alexi Hexed style template's two step lines, drawn in the body editor
after the original's pinstripes: two nested arrows from the edge beside
the neck pocket out into the wings, each tail a sharp V at the notch, the
inner one's point 4 mm inside the outer's (a narrow band between them, as
the pinstripes run there). Beside the neck they converge on the edge, the
bass horn's as drawn and the treble horn's its mirror image — X from the
heel end, straight lines between the points; their points in the neck
pocket fall in its route and do not matter."""

_DESIGN_BY_JONE = DesignByJoneShape()

SG_PICKGUARDS: dict[str, tuple[DrawnPoint, ...]] = {
    # A '61 style small guard on the treble side, about 176 x 92 mm, its
    # sizes from Electric Herald's and Ploutone's dimension drawings: its
    # tongue between the pickups' rings (46 x 26 mm), its bass edges
    # butting their treble ends, its neck end following the treble
    # cutaway up to a point toward the horn, an S-curve along the treble
    # side and a point toward the toggle at the bridge end.
    "sg_small": (
        (-4.0, 95.0, "corner"),
        (8.0, 106.0),
        (35.0, 114.0),
        (65.0, 114.0),
        (95.0, 106.0),
        (125.0, 96.0),
        (148.0, 92.0),
        (172.0, 98.0, "corner"),
        (158.0, 64.0),
        (157.0, 48.0, "corner"),
        (106.0, 48.0, "corner"),
        (104.0, 22.0, "corner"),
        (60.0, 22.0, "corner"),
        (58.0, 48.0, "corner"),
        (6.0, 48.0, "corner"),
        (12.0, 60.0),
        (12.0, 74.0),
        (5.0, 86.0),
    ),
    # A 1966 on batwing (full-face) guard, about 200 x 184 mm (156 mm on
    # the bass side), from Ploutone's and WD's dimension drawings: a tab at
    # the neck, scallops following both cutaways out to the wings' tips,
    # the bass edge straight down, an S-curve up the treble side and a
    # wave below the Tune-o-matic's posts, which go through it as the
    # pickups do.
    "sg_batwing": (
        (2.0, 29.0, "corner"),
        (2.0, -29.0, "corner"),
        (8.0, -38.0),
        (13.0, -50.0),
        (15.0, -60.0),
        (13.0, -70.0),
        (11.0, -80.0),
        (10.0, -92.0, "corner"),
        (90.0, -93.0),
        (166.0, -92.0, "corner"),
        (178.0, -62.0),
        (188.0, -40.0),
        (190.0, -22.0),
        (186.0, 0.0),
        (190.0, 22.0),
        (192.0, 40.0),
        (192.0, 66.0),
        (190.0, 92.0, "corner"),
        (165.0, 95.0),
        (140.0, 90.0),
        (115.0, 94.0),
        (85.0, 104.0),
        (55.0, 108.0),
        (25.0, 106.0),
        (6.0, 98.0, "corner"),
        (8.0, 86.0),
        (12.0, 74.0),
        (14.0, 62.0),
        (12.0, 50.0),
        (8.0, 38.0),
    ),
}
"""The SG's two drawn guards (``body_pickguard_style`` "sg_small",
"sg_batwing"): control points (X from the heel end, Y, the treble side at
+Y; ``"corner"`` a sharp one) on the SG template, its pickups, its
Tune-o-matic and inside its bevels — mockups from dimension drawings, not
the originals."""

_MOCKINGBIRD_ROUND_POINTS: tuple[DrawnPoint, ...] = (
    (302.7, -187.0),
    (207.2, 171.1),
    (-122.0, 157.5),
    (48.3, -144.8),
)
"""Where the Mockingbird's edge is rounded over, not bevelled, in pairs:
its tail, from the bass side's lower bout round to the treble side's, and
its neck end, from the treble horn's tip round the cutaways to the bass
horn's root. Its two sides between are bevelled."""


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
            strap_guide_offset=_DESIGN_BY_JONE.strap_guide_offset,
            strap_guide_y=_DESIGN_BY_JONE.strap_guide_y,
            strap_guide_angle_degrees=_DESIGN_BY_JONE.strap_guide_angle_degrees,
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
            # Its four pots as on a '59 reissue (Wikimedia Commons, "Full
            # front R9 Les Paul.jpg", its outline fitted to this one's to
            # within 4 mm): the two volumes nearer the strings, the tones
            # out toward the edge and each pair stepped back, the cavity
            # routed round them; the jack into the treble side's rim
            # behind them, aimed into the cavity.
            rear_pots=((208.2, 110.5), (233.8, 67.9), (268.3, 109.1), (294.8, 66.9)),
            # The almond and its two pots (the other layouts) there too,
            # and the battery box beside them.
            pot_offsets=((231.3, 88.1), (271.3, 89.1)),
            control_shift=(49.8, 2.9),
            battery_offset=289.5,
            battery_y=39.0,
            jack_offset=285.0,
            jack_y=100.0,
            jack_direction_degrees=236.8,
        ),
    ),
    "stratocaster": (
        "Stratocaster style (traced from the original)",
        YourDesignShape(
            control_points=_STRATOCASTER_POINTS,
            pickguard_points=_STRATOCASTER_PICKGUARD_POINTS,
            # As on the original: the blade switch angled out ahead of the
            # volume pot and the two tone pots stepping out toward the
            # lower edge (from the same photo); the jack's cavity in its
            # angled plate where the user's Stratocaster drawing has it
            # (stratbody.dxf, aligned on its neck pocket's end).
            pickguard_controls=(
                (132.2, 94.5),
                (154.0, 58.5),
                (175.6, 95.6),
                (201.8, 125.5),
            ),
            pickguard_switch_degrees=42.8,
            pickguard_cavity_points=_STRATOCASTER_CONTROL_CAVITY,
            jack_offset=241.1,
            jack_y=93.8,
            jack_direction_degrees=232.5,
            jack_inset=67.5,
            # The neck bolts spread like the bass's: the pair at the
            # pocket's mouth out near the body's edge, the rear pair's
            # ferrules wholly over the pocket.
            neck_bolts=((-63.5, -20.0), (-7.5, -20.0), (-63.5, 20.0), (-7.5, 20.0)),
        ),
    ),
    "jackson_rr": (
        "Jackson RR style (traced from the original)",
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
            # With three pots (rear_3), as on a Jackson Rhoads (Wikimedia
            # Commons, "Jackson Rhoads (2017-11 by Alexander Lesnitsky).jpg",
            # scaled from its frets, its outline fitted to this one's to
            # within 2 mm): two down the treble wing, the third out toward
            # its tip, the cavity routed round them.
            rear_pots=((136.4, 61.3), (189.5, 61.9), (213.6, 111.6)),
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
    "alexi_hexed": (
        "ESP LTD Alexi Hexed style (on the RR's outline)",
        YourDesignShape(
            # ESP's Alexi body is an offset V after Alexi Laiho's Jackson
            # RRs: the RR style outline and placements, with no guard of
            # its own (the Hexed has none) and its one volume pot where
            # the RR's pots are.
            control_points=_JACKSON_RR_POINTS,
            switch_cavity_offset=230.0,
            switch_cavity_y=-85.0,
            switch_cover_offset=230.0,
            switch_cover_y=-85.0,
            pot_offsets=((170.8, 86.0), (210.8, 87.0)),
            control_shift=(-10.0, 0.0),
            jack_offset=175.2,
            jack_y=126.5,
            jack_direction_degrees=291.8,
            neck_bolts=((-50.0, -20.0), (-7.5, -20.0), (-44.0, 20.0), (-7.5, 20.0)),
            battery_offset=271.0,
            battery_y=120.0,
            battery_angle_degrees=60.0,
            step_points=_ALEXI_HEXED_STEP_POINTS,
        ),
    ),
    "music_man_axis": (
        "Music Man Axis style (traced from a product photo)",
        YourDesignShape(
            control_points=_MUSIC_MAN_AXIS_POINTS,
            # Where every layout fits: the switch on the lower bass bout,
            # the pots (and the almond under them) behind the bridge on
            # the treble side, the jack in the treble edge aimed at them.
            # The Music Man Axis style puts the volume and the toggle side
            # by side where the photographed one's are (STYLES).
            rear_pots=((150.3, 75.6),),
            pot_offsets=((190.0, 70.0), (230.0, 70.0)),
            control_shift=(13.0, -17.0),
            switch_cavity_offset=180.0,
            switch_cavity_y=-105.0,
            switch_cover_offset=180.0,
            switch_cover_y=-105.0,
            jack_offset=204.1,
            jack_y=155.2,
            jack_direction_degrees=274.0,
            # The neck pocket's front edge slants with the body's across
            # the neck: the bass pair further forward than the treble.
            neck_bolts=((-55.0, -18.0), (-8.0, -18.0), (-30.0, 18.0), (-8.0, 18.0)),
            # The battery box behind the bridge, in from the controls.
            battery_offset=256.0,
            battery_y=19.2,
            battery_angle_degrees=15.0,
        ),
    ),
    "mockingbird": (
        "Mockingbird style (mockup, not the original)",
        YourDesignShape(
            control_points=_MOCKINGBIRD_POINTS,
            # The switch a little in from the narrow treble waist; the jack
            # in the lower treble edge, where the original's is.
            switch_cavity_offset=90.0,
            switch_cavity_y=75.0,
            switch_cover_offset=90.0,
            switch_cover_y=75.0,
            jack_offset=205.0,
            jack_y=92.0,
            jack_direction_degrees=225.0,
            # The battery box behind the bridge, square to the neck, where
            # the tail narrows past the control cavity.
            battery_offset=265.0,
            battery_y=35.0,
            battery_angle_degrees=0.0,
            # Its bevels along each side's outer edge, its neck end and its
            # tail rounded over, top and back.
            top_round_points=_MOCKINGBIRD_ROUND_POINTS,
            back_round_points=_MOCKINGBIRD_ROUND_POINTS,
        ),
    ),
    "telecaster": (
        "Telecaster style (mockup, not the original)",
        YourDesignShape(
            control_points=_TELECASTER_POINTS,
            # As on a '52 (TELE_PLATE), from a straight-on photo of one
            # whose body outline fits this template's to within 3 mm: the
            # control plate's centre 197 mm behind the heel end, 92.5 mm
            # out on the treble side, its rear end turned 1.2 degrees in
            # toward the strings; the almond and its pots follow it.
            pot_offsets=((177.4, 102.0), (217.4, 103.0)),
            control_shift=(-3.4, 16.0),
            control_angle_degrees=-1.2,
            # The jack into the treble side about level with the tone pot,
            # angled forward into the cavity.
            jack_offset=235.0,
            jack_y=95.0,
            jack_direction_degrees=250.0,
        ),
    ),
    "sg": (
        "SG style (mockup, not the original)",
        YourDesignShape(
            control_points=_SG_POINTS,
            jack_offset=197.0,
            jack_y=87.0,
            jack_direction_degrees=309.0,
            # As on a '61 reissue (Wikimedia Commons, "Gibson SG 61 Reissue
            # 2007 (front).jpg", its outline fitted to this one's to within
            # 3 mm; the four 10 mm forward and in, so the cover keeps off
            # the edge): the four pots low on the treble side, each pair
            # stepped out, the cavity routed round them (the SG style puts
            # the toggle up on the treble horn and the jack in the top).
            rear_pots=((259.4, 90.1), (261.3, 129.2), (306.5, 76.4), (307.7, 113.6)),
            # Its bevels on along both lower bouts to their widest, the
            # tail rounded over; on the back only to the treble side's
            # waist, its control cavity's lower bout rounded over too.
            top_round_points=((274.8, -164.0), (270.8, 161.4)),
            back_round_points=((274.8, -164.0), (167.8, 123.3)),
        ),
    ),
    "explorer": (
        "Explorer style (mockup, not the original)",
        YourDesignShape(
            control_points=_EXPLORER_POINTS,
            # As on a 1976 style Explorer (Wikimedia Commons,
            # "Gibson-Explorer noBG.png", its outline fitted to this one's
            # to within 5 mm): the toggle up on the treble horn, the three
            # pots (rear_3) in a row along the lower treble edge, the cavity
            # routed round them, the jack up into it from the lower edge.
            switch_cavity_offset=-34.6,
            switch_cavity_y=134.8,
            switch_cover_offset=-34.6,
            switch_cover_y=134.8,
            rear_pots=((220.9, 88.5), (269.4, 72.1), (317.0, 56.6)),
            # The almond and its two pots (the other layouts) there too,
            # and the battery box beside them.
            pot_offsets=((249.1, 71.9), (289.1, 72.9)),
            control_shift=(67.6, -13.3),
            battery_offset=273.2,
            battery_y=18.5,
            jack_offset=317.0,
            jack_y=56.6,
            jack_direction_degrees=180.0,
        ),
    ),
    "flying_v": (
        "Flying V style (mockup, not the original)",
        YourDesignShape(
            control_points=_FLYING_V_POINTS,
            # Everything on the treble wing, as on the original: the switch
            # behind the bridge, the control cavity turned along the wing
            # (a Tele plate there too), the jack into its outer edge and
            # the battery box on past them toward the wing's tip.
            switch_cavity_offset=190.0,
            switch_cavity_y=88.0,
            switch_cover_offset=190.0,
            switch_cover_y=88.0,
            pot_offsets=((280.8, 116.0), (320.8, 117.0)),
            control_shift=(100.0, 30.0),
            control_angle_degrees=20.0,
            jack_offset=297.0,
            jack_y=117.0,
            jack_direction_degrees=290.0,
            battery_offset=394.0,
            battery_y=162.0,
            battery_angle_degrees=30.0,
        ),
    ),
    "razorback": (
        "Razorback style (traced from a product photo)",
        YourDesignShape(
            control_points=_RAZORBACK_POINTS,
            # As photographed: the toggle on the treble horn and the three
            # pots down the treble wing (rear_3, their cavity routed round
            # them).
            switch_cavity_offset=11.5,
            switch_cavity_y=100.7,
            switch_cover_offset=11.5,
            switch_cover_y=100.7,
            # A Gibson toggle's 38 mm cavity under a 50 mm cover: the
            # horn is too narrow for the default ones.
            switch_cavity_diameter=38.0,
            switch_cover_diameter=50.0,
            rear_pots=((224.2, 66.3), (265.6, 84.6), (306.9, 103.6)),
            # The almond and its two pots (the other layouts) behind the
            # bridge, clear of the wing's edge; a pickguard's switch and
            # three pots in a row up the wing beside and behind the bridge,
            # where the guard reaches past it.
            pot_offsets=((210.8, 70.0), (250.8, 71.0)),
            control_shift=(30.0, -16.0),
            pickguard_controls=(
                (286.5, 65.5),
                (315.0, 75.0),
                (343.4, 84.6),
                (371.8, 94.2),
            ),
            pickguard_switch_degrees=18.6,
            # A bolt-on neck's bolts: the treble horn meets the neck only
            # 19 mm ahead of the heel end, so the treble front bolt sits
            # back and in, its ferrule 1 mm or more inside the edge across
            # the neck.
            neck_bolts=((-50.0, -20.0), (-7.5, -20.0), (-28.0, 10.0), (-7.5, 20.0)),
            # A jack in the edge: in from the treble wing's edge beside
            # the almond, square to it (the Razorback style mounts it in
            # the top beyond the pots, as photographed).
            jack_offset=240.0,
            jack_y=117.0,
            jack_direction_degrees=288.0,
            # The battery box behind the almond on the treble wing, turned
            # along it, so its lead's channel to the controls stays short.
            battery_offset=310.0,
            battery_y=40.0,
            battery_angle_degrees=24.0,
        ),
    ),
    "fantomen": (
        "Fantomen style (traced from a product photo)",
        YourDesignShape(
            control_points=_FANTOMEN_POINTS,
            # As photographed: the toggle on the bass shoulder, the four
            # pots in a diamond on the lower treble bout (gibson_4, the
            # cavity routed round them) and the jack in the treble edge at
            # the tail's corner, aimed at them.
            switch_cavity_offset=12.7,
            switch_cavity_y=-84.5,
            switch_cover_offset=12.7,
            switch_cover_y=-84.5,
            rear_pots=((282.5, 105.0), (312.3, 52.2), (308.2, 152.5), (339.3, 99.5)),
            jack_offset=341.9,
            jack_y=194.0,
            jack_direction_degrees=251.1,
            # The almond and its two pots (the other layouts) on the jack's
            # way in too, and the battery box beside them, clear of the
            # almond's cover.
            pot_offsets=((298.3, 131.0), (338.3, 132.0)),
            control_shift=(117.5, 45.0),
            battery_offset=300.0,
            battery_y=82.0,
            battery_angle_degrees=0.0,
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
treble wing; the ESP LTD Alexi Hexed style one is that outline too (ESP's
Alexi body is an offset V after Alexi Laiho's Jackson RRs), with no guard
of its own — loading it in the web app also sets the Hexed's look
(``prototype001.BODY_TEMPLATE_VALUES``: one bridge humbucker, one volume
pot, a Floyd Rose and its graphic as a top stepped down in two bands
along the edge). The Mockingbird, Telecaster, SG, Explorer and Flying V
style ones are traced from straight-on product photos, scaled from their
frets and placed with their last fret 4 mm ahead of the heel end, as the
default neck's is (and the Razorback and Fantomen style ones, their
switches, pots and jacks where the photographed ones' are) — genre
mockups, the Mockingbird reshaped by hand at
its horn, beak and bass lobe, the Explorer at its shoulder, bottom
corner and wing tip; the Flying V's switch,
controls (turned along the wing) and battery box all on its treble
wing. The Jazz Bass style
one, a mockup the same way, is the bass
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
