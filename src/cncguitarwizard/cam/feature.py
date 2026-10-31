"""Programs for single body features, zeroed on the feature itself.

When a feature was left out of a body already cut — a battery box, say —
it can be cut on its own: these programs hold only that feature's
pockets and holes, with the work zero at the centre of the feature
rather than at the body's index pins, so the operator zeroes the machine
on the spot marked on the body. A feature on the back is cut with the
body flipped about its centerline, as ``Body_back`` is (Y mirrored).
Its cover plates, if any, get their own sheet programs as usual.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence

from ..geometry.body import BodySolid, CoverPlate, DrilledHole
from ..geometry.primitives import Point2D
from .body import (
    _drill_hole,
    _drill_rear_hole,
    _Frame,
    _listed,
    _pocket_outline,
    _rear_pockets,
    _tool_fits,
    _top_corners,
    _top_pocket,
)
from .covers import plan_cover_machining
from .exceptions import ToolpathError
from .gcode import Setup
from .parameters import MachiningParameters
from .toolpath import Toolpath


def plan_feature_machining(
    body: BodySolid,
    covers: Sequence[CoverPlate],
    keep: Callable[[str], bool],
    title: str,
    parameters: MachiningParameters,
) -> tuple[Setup, ...]:
    """Return the programs that cut only the features ``keep`` names.

    Args:
        body: The body the features belong to.
        covers: Every cover plate; those ``keep`` names get their programs.
        keep: Whether a feature (cavity, hole, cover) by name is cut.
        title: What the features are, e.g. ``"battery box"``; it names the
            programs (``Feature_battery_box_back``).
        parameters: Tool and feeds, as for the whole body.

    Returns:
        The top face's programs, then the back's, then the covers', each
        only when it has something to cut.

    Raises:
        ToolpathError: When ``keep`` names nothing on the body.
    """
    top_cavities = [cavity for cavity in body.top_cavities if keep(cavity.name)]
    top_holes = [
        hole for hole in (*body.holes, *body.control_top_marks) if keep(hole.name)
    ]
    rears = [rear for rear in body.rear_cavities if keep(rear.cavity.name)]
    rear_holes = [
        hole for hole in (*body.rear_holes, *body.control_back_marks) if keep(hole.name)
    ]
    kept_covers = [cover for cover in covers if keep(cover.name)]
    points = [
        *(p for cavity in top_cavities for p in cavity.outline),
        *(p for rear in rears for p in rear.cover_recess.outline),
        *(hole.center for hole in (*top_holes, *rear_holes)),
    ]
    if not points:
        raise ToolpathError(f"Nothing on the body to cut for the {title}.")
    centre = Point2D(
        (min(p.x for p in points) + max(p.x for p in points)) / 2.0,
        (min(p.y for p in points) + max(p.y for p in points)) / 2.0,
    )
    stem = "Feature_" + re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    small = parameters.tool_diameter - 1e-6
    small_tool = parameters.small_cutter
    zero = (
        f"X/Y zero at the centre of the {title} ({centre.x:.1f}, {centre.y:.1f} "
        "in the model: from the nut along the neck, from the centerline), "
        "X along the neck toward the bridge; Z zero on the face being cut."
    )
    setups: list[Setup] = []

    def add(
        name: str,
        description: str,
        paths: list[Toolpath],
        notes: tuple[str, ...],
        tool: MachiningParameters | None = None,
    ) -> None:
        if paths:
            setups.append(
                Setup(name, description, tuple(paths), notes, tool=tool, work_zero=zero)
            )

    top = _Frame(centre.x, centre.y, mirror_y=False)
    big_top = [hole for hole in top_holes if hole.diameter >= small]
    # A route the main tool fits nowhere in goes to the small end mill, as
    # in the whole body's programs, and so do the corners it leaves
    # (``corner_cleanup``).
    wide_top = [
        cavity
        for cavity in top_cavities
        if _tool_fits(_pocket_outline(cavity), parameters)
    ]
    narrow_top = [
        _top_pocket(cavity, body, top, small_tool)
        for cavity in top_cavities
        if cavity not in wide_top
    ]
    corners_top = [
        path
        for cavity in wide_top
        for path in _top_corners(cavity, body, top, parameters)
    ]
    small_top = _small(
        top_holes, small, lambda h: _drill_hole(h, body, top, small_tool)
    )
    add(
        f"{stem}_top",
        f"The {title} on its own - top face",
        [
            *(_top_pocket(cavity, body, top, parameters) for cavity in wide_top),
            *(_drill_hole(hole, body, top, parameters) for hole in big_top),
        ],
        ("Body top face up.",),
    )
    add(
        f"{stem}_top_small_holes",
        f"The {title} on its own - top face, "
        f"{_small_contents(narrow_top, corners_top, small_top)}",
        [*narrow_top, *corners_top, *small_top],
        (
            "Same zero as the top program; change to the small "
            f"{'end mill' if narrow_top or corners_top else 'drill'}.",
        ),
        small_tool,
    )
    back = _Frame(centre.x, centre.y, mirror_y=True)
    big_back = [hole for hole in rear_holes if hole.diameter >= small]
    wide_back: list[Toolpath] = []
    narrow_back: list[Toolpath] = []
    corners_back: list[Toolpath] = []
    for rear in rears:
        wide, narrow, corners = _rear_pockets(rear, body, back, parameters)
        wide_back += wide
        narrow_back += narrow
        corners_back += corners
    small_back = _small(
        rear_holes, small, lambda h: _drill_rear_hole(h, body, back, small_tool)
    )
    add(
        f"{stem}_back",
        f"The {title} on its own - back face",
        [
            *wide_back,
            *(_drill_rear_hole(hole, body, back, parameters) for hole in big_back),
        ],
        (
            "Body back face up, flipped about the neck centerline as for "
            "Body_back (Y mirrored).",
        ),
    )
    add(
        f"{stem}_back_small_holes",
        f"The {title} on its own - back face, "
        f"{_small_contents(narrow_back, corners_back, small_back)}",
        [*narrow_back, *corners_back, *small_back],
        (
            "Same zero as the back program; change to the small "
            f"{'end mill' if narrow_back or corners_back else 'drill'}.",
        ),
        small_tool,
    )
    cover_plan = plan_cover_machining(kept_covers, parameters)
    if cover_plan is not None:
        setups.extend(cover_plan.setups)
    return tuple(setups)


def _small(
    holes: Sequence[DrilledHole],
    small: float,
    drill_one: Callable[[DrilledHole], Toolpath],
) -> list[Toolpath]:
    """Return the holes narrower than the main tool, drilled with the small one."""
    return [drill_one(hole) for hole in holes if hole.diameter < small]


def _small_contents(
    routes: Sequence[Toolpath],
    corners: Sequence[Toolpath],
    holes: Sequence[Toolpath],
) -> str:
    """Return what a small-drill program cuts: narrow routes, pockets'
    corners, small holes, or some of them."""
    return _listed(
        [
            what
            for what, there in (
                ("narrow routes", routes),
                ("pocket corners", corners),
                ("small holes", holes),
            )
            if there
        ]
    )
