"""Tests for multiscale (fanned) frets."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.cam import FretboardMachiningParameters, plan_fretboard_machining
from cncguitarwizard.geometry.body import HardtailSpec, TuneOMaticSpec
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.fretboard import FretSkew
from cncguitarwizard.presets import Prototype001Parameters

SEVEN = replace(
    Prototype001Parameters.for_instrument("seven_string_guitar"),
    scale_length=647.7,
    bass_scale_length=685.8,
    body_pickups="HSH",
)


@pytest.fixture(scope="module")
def fanned():  # type: ignore[no-untyped-def]
    return SEVEN.build()


def string_ends(parameters: Prototype001Parameters, index: int):  # type: ignore[no-untyped-def]
    """Return the nut and bridge points of string ``index`` (0 = bass)."""
    skew = parameters.fret_skew
    u = (parameters.string_count - 1) / 2.0 - index
    nut_y = skew.bass_sign * u * parameters.nut_string_spacing
    bridge_y = skew.bass_sign * u * parameters.bridge_string_spacing
    nut = (skew.at(0.0) * nut_y, nut_y)
    bridge = (
        parameters.centre_scale + skew.at(parameters.centre_scale) * bridge_y,
        bridge_y,
    )
    return nut, bridge


def test_the_outer_strings_get_their_own_scales() -> None:
    bass_nut, bass_bridge = string_ends(SEVEN, 0)
    treble_nut, treble_bridge = string_ends(SEVEN, SEVEN.string_count - 1)

    # Measured along each string, which runs slightly across the neck.
    assert math.dist(bass_nut, bass_bridge) == pytest.approx(685.8, abs=0.2)
    assert math.dist(treble_nut, treble_bridge) == pytest.approx(647.7, abs=0.2)
    assert SEVEN.centre_scale == pytest.approx((647.7 + 685.8) / 2.0)


def test_every_fret_sits_at_its_exact_place_on_every_string(fanned) -> None:  # type: ignore[no-untyped-def]
    for index in range(SEVEN.string_count):
        (nut_x, nut_y), (bridge_x, bridge_y) = string_ends(SEVEN, index)
        for number, slot in enumerate(fanned.fret_layout.slots, start=1):
            fraction = 1.0 - 2.0 ** (-number / 12.0)
            x = nut_x + (bridge_x - nut_x) * fraction
            y = nut_y + (bridge_y - nut_y) * fraction
            t = (y - slot.start.y) / (slot.end.y - slot.start.y)
            slot_x = slot.start.x + (slot.end.x - slot.start.x) * t
            assert slot_x == pytest.approx(x, abs=1e-6)


def test_the_perpendicular_fret_is_square_and_the_bass_side_is_longer(fanned) -> None:  # type: ignore[no-untyped-def]
    seventh = fanned.fret_layout.slots[6]
    assert seventh.start.x == pytest.approx(seventh.end.x)
    first, last = fanned.fret_layout.slots[0], fanned.fret_layout.slots[-1]
    # The bass side (-Y on the left-handed default): nut-ward before the
    # perpendicular fret, bridge-ward after it.
    bass_first = min((first.start, first.end), key=lambda p: p.y)
    treble_first = max((first.start, first.end), key=lambda p: p.y)
    assert bass_first.x < treble_first.x
    bass_last = min((last.start, last.end), key=lambda p: p.y)
    treble_last = max((last.start, last.end), key=lambda p: p.y)
    assert bass_last.x > treble_last.x
    at_nut = replace(SEVEN, perpendicular_fret=0.0).fret_skew
    assert at_nut.at(0.0) == pytest.approx(0.0)


def test_the_pickups_fan_and_the_bridge_stays_square(fanned) -> None:  # type: ignore[no-untyped-def]
    body = fanned.body
    holes = [hole for hole in body.holes if hole.name.startswith("String")]
    # The bridge stays square on the centerline scale; the saddles are set.
    assert len({round(hole.center_x, 6) for hole in holes}) == 1
    for route in (body.neck_pickup, body.bridge_pickup):
        assert route is not None
        bass_end = min(route.outline, key=lambda p: p.y)
        treble_end = max(route.outline, key=lambda p: p.y)
        assert bass_end.x > treble_end.x
    plain = replace(SEVEN, bass_scale_length=None).build().body
    assert plain.neck_pickup is not None and body.neck_pickup is not None
    # The turned neck pickup keeps its gap to the neck pocket.
    gap = body.neck_pickup.min_x - body.neck_pocket.max_x
    plain_gap = plain.neck_pickup.min_x - plain.neck_pocket.max_x
    assert gap == pytest.approx(plain_gap, abs=0.5)


def test_a_tune_o_matic_always_turns_with_the_fan() -> None:
    parameters = replace(
        Prototype001Parameters(), body_bridge=TuneOMaticSpec(), bass_scale_length=647.7
    )
    assert parameters.bridge_follows_fan
    holes = {h.name: h for h in parameters.build().body.holes}
    bass, treble = holes["Bridge post bass"], holes["Bridge post treble"]
    lean = parameters.fret_skew.at(parameters.centre_scale)
    run = (treble.center_x - bass.center_x) / (treble.center_y - bass.center_y)
    # The fan's lean, and the bass post's setback across the posts.
    spec = TuneOMaticSpec()
    assert run == pytest.approx(lean - spec.bass_setback / spec.post_spacing, rel=0.03)
    # The bass post (-Y) sits further back, with the longer bass scale.
    assert bass.center_x > treble.center_x
    # The stop-bar studs stay square, and so do the pickups by default.
    studs = [h for name, h in holes.items() if name.startswith("Tailpiece stud")]
    assert len({round(h.center_x, 6) for h in studs}) == 1
    assert not parameters.pickups_follow_fan
    body = parameters.build().body
    assert body.bridge_pickup is not None
    xs = [p.x for p in body.bridge_pickup.outline]
    plain = replace(parameters, bass_scale_length=None).build().body
    assert plain.bridge_pickup is not None
    assert max(xs) - min(xs) == pytest.approx(
        max(p.x for p in plain.bridge_pickup.outline)
        - min(p.x for p in plain.bridge_pickup.outline)
    )
    turned = replace(parameters, body_pickups_follow_fan="yes")
    assert turned.pickups_follow_fan
    assert turned.build().body.bridge_pickup != body.bridge_pickup


def test_a_hardtail_can_follow_the_fan() -> None:
    parameters = replace(SEVEN, body_bridge_follows_fan=True)
    holes = sorted(
        (h for h in parameters.build().body.holes if h.name.startswith("String")),
        key=lambda hole: hole.center_y,
    )
    # String-through holes: the bass end (-Y) further back.
    assert holes[0].center_x > holes[-1].center_x
    lean = parameters.fret_skew.at(parameters.centre_scale)
    run = (holes[-1].center_x - holes[0].center_x) / (
        holes[-1].center_y - holes[0].center_y
    )
    assert run == pytest.approx(lean, rel=0.02)


def test_the_nut_shelf_grows_with_the_nut_lean(fanned) -> None:  # type: ignore[no-untyped-def]
    reach = abs(SEVEN.fret_skew.at(0.0)) * SEVEN.nut_width / 2.0
    assert fanned.neck_surface.nut_shelf_length == pytest.approx(5.0 + reach)
    rows = fanned.fretboard_surface.mesh.rows
    assert min(point.x for point in rows[0]) == pytest.approx(-reach)


def test_the_fretboard_program_cuts_fanned_slots(fanned) -> None:  # type: ignore[no-untyped-def]
    plan = plan_fretboard_machining(fanned, FretboardMachiningParameters())
    first = [m for m in plan.slots.toolpaths[0].moves if not m.rapid]
    last = [m for m in plan.slots.toolpaths[-1].moves if not m.rapid]

    def lean(moves):  # type: ignore[no-untyped-def]
        low = min(moves, key=lambda m: m.y)
        high = max(moves, key=lambda m: m.y)
        return (high.x - low.x) / (high.y - low.y)

    assert lean(first) > 0.0 > lean(last)


def test_multiscale_rules() -> None:
    with pytest.raises(NeckGeometryError, match="longer than the treble"):
        replace(SEVEN, bass_scale_length=600.0).build()
    with pytest.raises(NeckGeometryError, match="perpendicular fret"):
        replace(SEVEN, perpendicular_fret=30.0).build()
    # Any bridge takes a multiscale; a Kahler cannot follow the fan.
    kahler = replace(Prototype001Parameters(), bass_scale_length=647.7)
    kahler.build()
    assert not kahler.bridge_follows_fan and kahler.pickups_follow_fan
    # Switched off, the pickups keep their square shape.
    straight = replace(kahler, body_pickups_follow_fan="no").build().body
    square = replace(kahler, bass_scale_length=None).build().body
    assert straight.neck_pickup is not None and square.neck_pickup is not None

    def shape(route):  # type: ignore[no-untyped-def]
        left = min(p.x for p in route.outline)
        return [(round(p.x - left, 6), round(p.y, 6)) for p in route.outline]

    assert shape(straight.neck_pickup) == shape(square.neck_pickup)
    with pytest.raises(NeckGeometryError, match="Only the hardtail"):
        replace(kahler, body_bridge_follows_fan=True).build()
    six = replace(kahler, body_bridge=HardtailSpec(), body_bridge_follows_fan=True)
    six.build()
    assert FretSkew().is_square and not six.fret_skew.is_square


def principal_lean(outline) -> float:  # type: ignore[no-untyped-def]
    """Return dx/dy of an outline's long axis (its principal direction)."""
    cx = sum(p.x for p in outline) / len(outline)
    cy = sum(p.y for p in outline) / len(outline)
    sxx = sum((p.x - cx) ** 2 for p in outline)
    syy = sum((p.y - cy) ** 2 for p in outline)
    sxy = sum((p.x - cx) * (p.y - cy) for p in outline)
    angle = 0.5 * math.atan2(2.0 * sxy, sxx - syy)  # from the X axis
    return 1.0 / math.tan(angle)


def test_block_inlays_keep_their_front_edge_along_the_fret() -> None:
    geometry = replace(SEVEN, inlay_style="block").build()
    skew = SEVEN.fret_skew
    for marker in geometry.inlay_layout.markers:
        top = max(p.y for p in marker.outline)
        bottom = min(p.y for p in marker.outline)
        high = min((p for p in marker.outline if p.y > top - 3.0), key=lambda p: p.x)
        low = min((p for p in marker.outline if p.y < bottom + 3.0), key=lambda p: p.x)
        lean = (high.x - low.x) / (high.y - low.y)
        assert lean == pytest.approx(skew.at((high.x + low.x) / 2.0), abs=0.03), (
            marker.fret_number
        )


def test_barbed_wire_inlays_turn_with_the_fanned_frets() -> None:
    parameters = replace(SEVEN, inlay_style="barbed_wire")
    geometry = parameters.build()
    skew = parameters.fret_skew
    for marker in geometry.inlay_layout.markers:
        if (
            len(
                [
                    m
                    for m in geometry.inlay_layout.markers
                    if m.position == marker.position
                ]
            )
            > 1
        ):
            continue  # the short double markers have no clear long axis
        cx = sum(p.x for p in marker.outline) / len(marker.outline)
        assert principal_lean(marker.outline) == pytest.approx(skew.at(cx), abs=0.03), (
            marker.fret_number
        )


def test_dots_sit_on_the_line_between_their_frets() -> None:
    geometry = replace(SEVEN, inlay_style="dot").build()
    skew = SEVEN.fret_skew
    pair = [m for m in geometry.inlay_layout.markers if m.fret_number == 12]
    (a, b) = (
        (
            sum(p.x for p in m.outline) / len(m.outline),
            sum(p.y for p in m.outline) / len(m.outline),
        )
        for m in pair
    )
    lean = (b[0] - a[0]) / (b[1] - a[1])
    assert lean == pytest.approx(skew.at((a[0] + b[0]) / 2.0), abs=0.01)
