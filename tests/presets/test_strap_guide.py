"""Tests for the optional flame strap guide on the body's back."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.cam import plan_body_machining, plan_cover_machining
from cncguitarwizard.cam.parameters import MachiningParameters
from cncguitarwizard.geometry.body import outlines_overlap
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import (
    YOUR_DESIGN_TEMPLATES,
    DesignByJoneShape,
    YourDesignShape,
    mirrored_shape,
    widened_shape,
)
from cncguitarwizard.webapp import body_editor_layout, feature_programs


def with_guide(**overrides: object) -> Prototype001Parameters:
    return replace(Prototype001Parameters(), body_strap_guide=True, **overrides)


UNPLACED = replace(
    DesignByJoneShape(),
    strap_guide_offset=None,
    strap_guide_y=None,
    strap_guide_angle_degrees=None,
)


def placed(x: float, y: float, angle: float) -> DesignByJoneShape:
    return replace(
        DesignByJoneShape(),
        strap_guide_offset=x,
        strap_guide_y=y,
        strap_guide_angle_degrees=angle,
    )


def test_the_strap_guide_is_off_by_default() -> None:
    parameters = Prototype001Parameters()
    geometry = parameters.build()

    assert parameters.body_layout().strap_guide is None
    assert geometry.body.strap_guide == ()
    assert all(not cover.name.startswith("Strap") for cover in geometry.covers)


def test_the_guide_is_screwed_on_the_back_over_its_spacers() -> None:
    parameters = with_guide(body_strap_width=30.0, body_strap_guide_gap=4.0)
    guide = parameters.body_layout().strap_guide
    geometry = parameters.build()

    assert guide is not None
    assert guide.strap_width == 30.0 and guide.gap == 4.0
    assert geometry.body.strap_guide == guide.outline
    names = [cover.name for cover in geometry.covers]
    assert names[-3:] == [
        "Strap guide plate",
        "Strap guide spacer 1",
        "Strap guide spacer 2",
    ]
    pilots = [
        mark
        for mark in geometry.body.control_back_marks
        if mark.name.startswith("Strap")
    ]
    assert [mark.center for mark in pilots] == list(guide.screws)


def test_the_guide_goes_where_the_shape_places_it() -> None:
    parameters = with_guide(body_shape=placed(90.0, -45.0, -10.0))
    layout = parameters.body_layout()
    guide = layout.strap_guide

    assert guide is not None
    assert guide.centre == Point2D(layout.heel_end + 90.0, -45.0)
    assert guide.angle_degrees == -10.0
    parameters.build()


def tail_button(layout) -> Point2D:  # type: ignore[no-untyped-def]
    """The strap's usual button: where the tail crosses the centreline."""
    points = layout.outline.points
    crossings = [
        a.x + (b.x - a.x) * (0.0 - a.y) / (b.y - a.y)
        for a, b in zip(points, (*points[1:], points[0]), strict=True)
        if a.y * b.y <= 0.0 and a.y != b.y
    ]
    return Point2D(max(crossings), 0.0)


def strap_leaving(layout, bass_sign: float) -> float:  # type: ignore[no-untyped-def]
    """The way the strap leaves the guide, square to its bar: in degrees
    from the neck's axis toward the bass side, toward the neck."""
    guide = layout.strap_guide
    bar = math.radians(guide.angle_degrees)
    # Square to the bar, toward the bass side.
    across = (-math.sin(bar), math.cos(bar))
    if across[1] * bass_sign < 0.0:
        across = (-across[0], -across[1])
    return math.degrees(math.atan2(abs(across[1]), -across[0]))


def test_the_design_by_jone_guide_is_where_the_guitar_has_it() -> None:
    # Read off a photograph of its back: on the bass side of the tail, on
    # the strap's way from its button in the tail's middle, turning the
    # strap nearly straight up over the bass edge.
    layout = with_guide().body_layout()
    guide = layout.strap_guide

    assert guide is not None
    assert guide.centre == Point2D(layout.heel_end + 216.0, -106.0)
    assert guide.angle_degrees == -10.0
    assert strap_leaving(layout, -1.0) == pytest.approx(80.0, abs=0.5)
    assert layout.problems == ()
    with_guide().build()


def test_an_unplaced_guide_sits_on_the_straps_way_from_its_tail_button() -> None:
    parameters = with_guide(body_shape=UNPLACED)
    layout = parameters.body_layout()
    guide = layout.strap_guide

    assert guide is not None
    assert layout.problems == ()
    # The strap runs from its button over the back toward the bass edge,
    # 60 degrees from the neck's axis, to the guide near the edge, which
    # turns it nearly straight up over it (80 degrees).
    button = tail_button(layout)
    assert guide.centre.y * parameters.bass_sign > 100.0
    assert guide.centre.x < button.x
    way = math.degrees(
        math.atan2(abs(guide.centre.y - button.y), button.x - guide.centre.x)
    )
    assert way == pytest.approx(60.0, abs=0.5)
    assert strap_leaving(layout, parameters.bass_sign) == pytest.approx(80.0, abs=0.5)


def test_a_guide_placed_only_in_part_is_placed_afresh() -> None:
    shape = replace(UNPLACED, strap_guide_offset=90.0)

    partly = with_guide(body_shape=shape).body_layout().strap_guide

    unplaced = with_guide(body_shape=UNPLACED).body_layout()
    assert partly == unplaced.strap_guide


BODIES = {
    "design_by_jone_shape": DesignByJoneShape(),
    "new_drawing": YourDesignShape(),
    **{key: shape for key, (_, shape) in YOUR_DESIGN_TEMPLATES.items()},
}


@pytest.mark.parametrize("name", list(BODIES))
def test_every_body_has_room_for_its_unplaced_guide(name: str) -> None:
    instrument = "bass_guitar" if "bass" in name else "electric_guitar"
    parameters = replace(
        Prototype001Parameters.for_instrument(instrument),
        body_shape=BODIES[name],
        body_strap_guide=True,
    )
    for handedness in ("right", "left"):
        geometry = replace(parameters, handedness=handedness).build()
        assert geometry.body.strap_guide


@pytest.mark.parametrize("name", ["design_by_jone_shape", "stratocaster"])
def test_an_unplaced_guide_keeps_off_a_belly_cut(name: str) -> None:
    shape = UNPLACED if name == "design_by_jone_shape" else BODIES[name]
    parameters = with_guide(body_shape=shape, body_belly_cut_depth=10.0)
    layout = parameters.body_layout()
    (belly,) = [c for c in layout.contours if c.name == "Belly cut"]

    assert layout.strap_guide is not None
    assert not outlines_overlap(layout.strap_guide.outline, belly.region())
    parameters.build()


def test_a_mirrored_or_widened_body_takes_its_guide_with_it() -> None:
    shape = placed(150.0, 60.0, 10.0)

    mirrored = mirrored_shape(shape)
    assert mirrored.strap_guide_y == -60.0
    assert mirrored.strap_guide_angle_degrees == -10.0
    assert widened_shape(shape, 12.0).strap_guide_y == pytest.approx(66.0)
    assert mirrored_shape(UNPLACED).strap_guide_y is None


def test_a_guide_off_the_flat_back_is_rejected() -> None:
    with pytest.raises(BodyGeometryError, match="strap guide must keep"):
        with_guide(body_shape=placed(150.0, 400.0, 0.0)).build()


def test_a_guide_over_a_cover_is_rejected() -> None:
    layout = with_guide().body_layout()
    assert layout.control_cavity is not None
    recess = layout.control_cavity.cover_recess.outline
    x = sum(point.x for point in recess) / len(recess) - layout.heel_end
    y = sum(point.y for point in recess) / len(recess)

    over = with_guide(body_shape=placed(x, y, 0.0))

    # The body editor draws it there, saying why it does not fit.
    assert any("strap guide must lie" in p for p in over.body_layout().problems)
    with pytest.raises(BodyGeometryError, match="strap guide overlaps"):
        over.build()


def test_the_pilots_and_the_sheet_parts_have_their_programs() -> None:
    geometry = with_guide().build()
    machining = MachiningParameters()

    plan = plan_body_machining(geometry.body, machining)
    assert plan.back_small_holes is not None
    drilled = [path.name for path in plan.back_small_holes.toolpaths]
    assert any("Strap guide screw 1 pilot" in name for name in drilled)
    assert any("Strap guide screw 2 pilot" in name for name in drilled)
    covers = plan_cover_machining(geometry.covers, machining)
    assert covers is not None
    programs = {setup.name: setup for setup in covers.setups}
    assert {
        "Cover_strap_guide_plate",
        "Cover_strap_guide_spacer_1",
        "Cover_strap_guide_spacer_2",
    } <= set(programs)
    assert any(
        "strap runs under" in note for note in programs["Cover_strap_guide_plate"].notes
    )


def test_the_body_editor_draws_and_drags_the_guide() -> None:
    payload = {"prototype": {"body_strap_guide": True}}
    layout = body_editor_layout(payload)

    (plate,) = [p for p in layout["polygons"] if p["role"] == "strap_guide"]
    assert plate["group"] == "strap_guide"
    pilots = [c for c in layout["circles"] if c["name"].startswith("Strap guide")]
    assert len(pilots) == 2 and all(c["group"] == "strap_guide" for c in pilots)
    guide = Prototype001Parameters(body_strap_guide=True).body_layout().strap_guide
    assert guide is not None
    assert layout["strap_guide"] == {
        "x": round(guide.centre.x - layout["heel_end"], 1),
        "y": round(guide.centre.y, 1),
        "angle": round(guide.angle_degrees, 1),
    }
    assert body_editor_layout({"prototype": {}})["strap_guide"] is None
    programs = feature_programs(payload, "strap_guide")
    names = [file["name"] for file in programs["files"]]
    assert "Feature_strap_guide_back_small_holes.nc" in names
    assert "Cover_strap_guide_plate.nc" in names
