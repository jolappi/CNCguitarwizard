"""Tests for the humbucker frames: placed, turned, screwed and cut."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.cam.covers import plan_cover_machining
from cncguitarwizard.cam.parameters import MachiningParameters
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets._omarunko_outline import (
    OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS,
)
from cncguitarwizard.presets.pickup_frames import (
    FRAME_POINTS,
    FRAME_SCREW_ROOM,
    HEIGHT_SCREW_ACCESS,
    frame_outline,
    frame_placing,
)
from cncguitarwizard.webapp import body_editor_layout, parameter_schema

HORNS = replace(Prototype001Parameters(), body_pickup_frame="horns")
BRIDGE_ONLY = replace(HORNS, body_pickups="H")


def _frames(parameters: Prototype001Parameters):  # type: ignore[no-untyped-def]
    return {frame.position: frame for frame in parameters.body_layout().pickup_frames}


@pytest.mark.parametrize("style", ["horns", "hook"])
def test_a_traced_frame_is_scaled_round_the_humbucker(style: str) -> None:
    points = FRAME_POINTS[style]
    outline = frame_outline(points, frame_placing(0.0, -1.0, 0.0, 0.0, False))
    along = [p.x for p in outline]
    across = [p.y for p in outline]
    # The drawing scaled so its opening is the humbucker's: 57 mm along the
    # neck, 146 to 163 mm across, round the whole route with its ears.
    assert max(along) - min(along) == pytest.approx(57.0, abs=0.5)
    assert 145.0 < max(across) - min(across) < 164.0
    assert all(
        point_in_polygon(Point2D(x, y), outline)
        for x, y in OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS
    )
    # The horns reach toward the neck (negative along).
    reach = [p for p in outline if abs(p.y) > 60.0]
    assert min(p.x for p in reach) < -25.0


def test_a_frame_turns_mirrors_and_opens_with_its_pickup() -> None:
    placing = frame_placing(100.0, -1.0, 10.0, 0.0, False)
    a, c = placing.to_frame(placing.to_model(-20.0, 50.0))
    assert (a, c) == pytest.approx((-20.0, 50.0))
    # Turned round: the same point is on the other side of the pickup.
    turned = frame_placing(100.0, -1.0, 0.0, 0.0, True)
    assert turned.to_model(-20.0, 50.0).x == pytest.approx(120.0)
    assert turned.to_model(-20.0, 50.0).y == pytest.approx(-50.0)
    # Left-handed (the bass side +Y): mirrored across the centreline.
    left = frame_placing(100.0, 1.0, 0.0, 0.0, False)
    assert left.to_model(-20.0, 50.0).y == pytest.approx(-50.0)
    # Seven strings: opened across by the pickup's stretch.
    seven = frame_placing(100.0, -1.0, 0.0, 9.0, False)
    assert seven.to_model(0.0, 50.0).y == pytest.approx(54.5)
    assert seven.to_frame(Point2D(100.0, 54.5)) == pytest.approx((0.0, 50.0))


def test_auto_turns_a_frame_that_only_fits_turned_round() -> None:
    frames = _frames(HORNS)
    # On the default body the bridge frame's treble horn runs off the body
    # toward the neck, so it is turned; the neck frame fits neither way.
    assert frames["bridge"].turned and frames["bridge"].problem is None
    assert frames["neck"].problem == "The neck pickup's frame runs off the body."
    with pytest.raises(BodyGeometryError, match="neck pickup's frame runs off"):
        HORNS.build()
    toward_neck = _frames(replace(HORNS, body_pickup_frame_direction="neck"))
    assert not toward_neck["bridge"].turned
    assert "runs off the body" in str(toward_neck["bridge"].problem)
    toward_bridge = _frames(replace(HORNS, body_pickup_frame_direction="bridge"))
    assert toward_bridge["neck"].turned and toward_bridge["bridge"].turned


def test_a_frame_is_cut_from_sheet_and_screwed_past_the_ears() -> None:
    geometry = BRIDGE_ONLY.build()
    (frame,) = [c for c in geometry.covers if c.name == "Bridge pickup frame"]
    assert not frame.recessed and frame.thickness == 2.5
    # Its opening is the pickup's own, 70.5 x 39 mm.
    (opening,) = frame.slots
    xs = [p.x for p in opening.outline]
    ys = [p.y for p in opening.outline]
    assert (max(xs) - min(xs), max(ys) - min(ys)) == pytest.approx((39.0, 70.5))
    access = [h for h in frame.holes if "height screw" in h.name]
    screws = [h for h in frame.holes if h.name.startswith("Screw")]
    assert [h.diameter for h in access] == [HEIGHT_SCREW_ACCESS] * 2
    assert len(screws) == 2
    # On the pickup's long axis, past its ears, with frame all round.
    centre = sum(xs) / 4.0
    for screw in screws:
        assert screw.center_x == pytest.approx(centre, abs=0.01)
        assert abs(screw.center_y) > 43.0 + FRAME_SCREW_ROOM
    spots = [h for h in geometry.body.control_top_marks if "frame screw" in h.name]
    assert len(spots) == 2
    (setup,) = [
        s
        for s in plan_cover_machining(geometry.covers, MachiningParameters()).setups
        if s.name == "Cover_bridge_pickup_frame"
    ]
    assert "Body_top_small_holes" in " ".join(setup.notes)


def test_the_hook_frame_screws_off_the_axis_where_its_hook_leaves_no_room() -> None:
    frames = _frames(replace(BRIDGE_ONLY, body_pickup_frame="hook"))
    frame = frames["bridge"]
    spots = [frame.placing.to_axes(s.center) for s in frame.screw_spots]
    (bass,) = [spot for spot in spots if spot[1] < 0]
    (treble,) = [spot for spot in spots if spot[1] > 0]
    assert treble[0] == pytest.approx(0.0, abs=1e-6)
    assert bass[0] != pytest.approx(0.0, abs=1.0)


def test_each_pickup_has_its_own_drawn_frame() -> None:
    shrunk = tuple((a * 0.5, c * 0.5) for a, c in FRAME_POINTS["horns"])
    drawn = replace(HORNS, body_neck_frame_points=shrunk)
    frames = _frames(drawn)
    assert frames["neck"].points == shrunk
    assert frames["bridge"].points == FRAME_POINTS["horns"]
    # Too small for its screws past the ears now.
    assert "no room for its screw" in str(frames["neck"].problem)
    with pytest.raises(BodyGeometryError, match="at least four points"):
        replace(HORNS, body_bridge_frame_points=((0, 0), (1, 1), (0, 2))).body_layout()


def test_seven_strings_open_the_frame_with_the_pickup() -> None:
    seven = replace(
        Prototype001Parameters.for_instrument("seven_string_guitar"),
        body_pickup_frame="horns",
        body_pickups="H",
    )
    six = _frames(BRIDGE_ONLY)["bridge"].plate.outline
    wider = _frames(seven)["bridge"].plate.outline
    span = lambda outline: max(p.y for p in outline) - min(p.y for p in outline)  # noqa: E731
    assert span(wider) > span(six) + 5.0
    assert math.isfinite(span(wider))


def test_the_editor_draws_each_frame_and_the_form_offers_the_styles() -> None:
    layout = body_editor_layout(
        {"prototype": {"body_pickup_frame": "horns", "body_pickups": "H"}}
    )
    (frame,) = layout["frames"]
    assert (
        frame["position"] == "bridge" and frame["field"] == "body_bridge_frame_points"
    )
    assert len(frame["handles"]) == len(frame["points"]) == len(FRAME_POINTS["horns"])
    assert frame["problem"] is None
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    assert fields["body_pickup_frame"]["options"] == ["none", "horns", "hook"]
    assert fields["body_pickup_frame"]["advanced"] is False
    assert fields["body_neck_frame_points"]["type"] == "json"
