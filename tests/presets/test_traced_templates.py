"""Tests for the body and neck templates traced from product photos."""

from dataclasses import replace

import pytest

from cncguitarwizard.geometry.primitives import Point2D
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.presets.prototype001 import NECK_TEMPLATES
from cncguitarwizard.webapp import parameter_schema

TRACED_BODIES = ("mockingbird", "telecaster", "sg", "explorer", "flying_v")


def _span(key: str) -> tuple[float, float, float, float]:
    points = YOUR_DESIGN_TEMPLATES[key][1].outline_points(0.0)
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return min(xs), max(xs), min(ys), max(ys)


def _front(key: str, side: float, out: float = 1000.0) -> float:
    """How far ahead of the heel end the outline reaches on one side,
    between 35 mm and ``out`` from the centreline."""
    points = YOUR_DESIGN_TEMPLATES[key][1].outline_points(0.0)
    return min(p.x for p in points if 35.0 < p.y * side < out)


@pytest.mark.parametrize(
    ("key", "label", "size"),
    [
        ("mockingbird", "Mockingbird style", (464.0, 358.0)),
        ("telecaster", "Telecaster style", (409.0, 327.0)),
        ("sg", "SG style", (428.0, 329.0)),
        ("explorer", "Explorer style", (553.0, 425.0)),
        ("flying_v", "Flying V style", (543.0, 425.0)),
    ],
)
def test_the_traced_bodies_keep_the_photographed_size(
    key: str, label: str, size: tuple[float, float]
) -> None:
    name, _ = YOUR_DESIGN_TEMPLATES[key]
    assert name == f"{label} (mockup, not the original)"
    x0, x1, y0, y1 = _span(key)
    # Scaled from the photo's frets: neck crossing to tail, and across.
    assert x1 - x0 == pytest.approx(size[0], abs=3.0)
    assert y1 - y0 == pytest.approx(size[1], abs=3.0)


def test_each_traced_body_keeps_its_own_horns() -> None:
    # The Mockingbird's long curved horn is on the treble side.
    assert _front("mockingbird", 1.0) < _front("mockingbird", -1.0) - 25.0
    # The Telecaster's single cutaway leaves the treble side short beside
    # the neck.
    assert _front("telecaster", -1.0, 60.0) < _front("telecaster", 1.0, 60.0) - 40.0
    # The SG's bass horn reaches a little further than its treble one.
    assert _front("sg", -1.0) < _front("sg", 1.0)
    # The Explorer's wing reaches forward on the treble side, its long
    # bottom corner back on the bass side.
    assert _front("explorer", 1.0) < -100.0
    points = YOUR_DESIGN_TEMPLATES["explorer"][1].outline_points(0.0)
    assert max(p.x for p in points if p.y < -200.0) > 430.0


def test_the_flying_v_has_its_notch_and_everything_on_the_treble_wing() -> None:
    shape = YOUR_DESIGN_TEMPLATES["flying_v"][1]
    points = shape.outline_points(0.0)
    # The notch: the tail crosses the centreline only at its apex, far
    # short of the wing tips.
    apex = max(p.x for p in points if abs(p.y) < 5.0)
    assert 270.0 < apex < 290.0
    assert min(max(p.x for p in points if p.y * s > 150.0) for s in (1, -1)) > 460.0
    assert shape.switch_cavity_y > 0.0
    assert all(y > 0.0 for _, y in shape.pot_offsets)
    assert shape.battery_y > 0.0 and shape.control_angle_degrees > 0.0
    layout = replace(
        Prototype001Parameters(), body_shape=shape, body_battery_box=True
    ).body_layout()
    battery = layout.controls.battery_cavity
    assert battery is not None and layout.control_cavity is not None
    # Past the control cavity, toward the wing's tip.
    assert min(p.x for p in battery.cavity.outline) > min(
        p.x for p in layout.control_cavity.cavity.outline
    )


def _crossings(points: tuple[Point2D, ...]) -> list[int]:
    """Return the outline segments another (not adjacent) segment crosses."""

    def side(p: Point2D, q: Point2D, r: Point2D) -> float:
        return (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x)

    count = len(points)
    hits = []
    for i in range(count):
        a, b = points[i], points[(i + 1) % count]
        for j in range(i + 2, count):
            if (j + 1) % count == i:
                continue
            c, d = points[j], points[(j + 1) % count]
            if (side(c, d, a) > 0) != (side(c, d, b) > 0) and (side(a, b, c) > 0) != (
                side(a, b, d) > 0
            ):
                hits.append(i)
    return hits


@pytest.mark.parametrize("key", list(YOUR_DESIGN_TEMPLATES))
@pytest.mark.parametrize("widening", [0.0, 24.0])
def test_no_template_outline_crosses_itself(key: str, widening: float) -> None:
    """Regression: closely spaced control points where the outline crossed
    the neck made the spline loop there, and FreeCAD refused the body."""
    shape = YOUR_DESIGN_TEMPLATES[key][1]
    assert _crossings(shape.outline_points(0.0, widening)) == []


@pytest.mark.parametrize("key", TRACED_BODIES)
def test_the_traced_bodies_build_left_handed_and_neck_through(key: str) -> None:
    shape = YOUR_DESIGN_TEMPLATES[key][1]
    base = replace(Prototype001Parameters(), body_shape=shape)
    replace(base, handedness="left").build()
    replace(base, neck_joint="neck_through").build()


NEW_NECKS = ("stratocaster", "gibson", "flying_v", "explorer", "mockingbird")


@pytest.mark.parametrize("key", NEW_NECKS)
def test_every_neck_template_builds_on_a_six_string_guitar(key: str) -> None:
    label, values = NECK_TEMPLATES[key]
    assert label.endswith("(mockup, not the original)")
    parameters = replace(Prototype001Parameters(), **values)
    # Every tuner hole keeps tuner_edge_offset to the drawn edges.
    plan, tuners = parameters.headstock_design()
    assert plan.length == values["headstock_bass_edge"][-1][0]
    assert len(tuners.holes) == 6
    parameters.build()
    replace(parameters, handedness="left").build()


def test_the_web_form_offers_every_neck_template() -> None:
    schema = parameter_schema()
    fields = {
        field["name"] for group in schema["prototype"] for field in group["fields"]
    }
    templates = schema["neck_templates"]
    assert list(templates) == ["telecaster", *NEW_NECKS]
    for key in NEW_NECKS:
        assert templates[key]["label"] == NECK_TEMPLATES[key][0]
        assert set(templates[key]["values"]) <= fields


def test_the_neck_templates_keep_their_heads_shapes() -> None:
    gibson = NECK_TEMPLATES["gibson"][1]
    assert gibson["headstock_style"] == "3+3"
    assert gibson["headstock_angle"] == 17.0
    # The open book: a notch in the middle of the top between two humps.
    tip = dict((y, past) for past, y in gibson["headstock_tip_points"])
    assert tip[0.0] < tip[5.2] and tip[0.0] < tip[-5.2]

    v = NECK_TEMPLATES["flying_v"][1]
    # The posts close in up the narrowing headstock.
    offsets = v["tuner_side_offsets"]
    assert list(offsets) == sorted(offsets, reverse=True)

    strat = replace(Prototype001Parameters(), **NECK_TEMPLATES["stratocaster"][1])
    _, tuners = strat.headstock_design()
    stations = sorted(-hole.center.x for hole in tuners.holes)
    assert stations[0] == pytest.approx(51.0)
    assert stations[1] - stations[0] == pytest.approx(22.5)
    assert {hole.side for hole in tuners.holes} == {"bass"}

    mockingbird = NECK_TEMPLATES["mockingbird"][1]
    # The top rises to a point in the middle.
    peak = max(mockingbird["headstock_tip_points"])
    assert peak[1] == 0.0


def test_the_explorer_neck_runs_its_tuners_along_the_steep_edge() -> None:
    values = NECK_TEMPLATES["explorer"][1]
    parameters = replace(Prototype001Parameters(), **values)
    plan, tuners = parameters.headstock_design()
    posts = sorted(
        ((-hole.center.x, hole.center.y) for hole in tuners.holes),
        key=lambda post: post[0],
    )
    # 18.7 mm apart from 48 mm, in a straight row across the centreline
    # (low E on the bass side, high E far out on the treble side) — not on
    # the strings' lines.
    assert [round(d, 1) for d, _ in posts] == [48.0, 66.7, 85.4, 104.1, 122.8, 141.5]
    assert [round(y, 1) for _, y in posts] == [-24.4, -11.0, 2.4, 15.8, 29.2, 42.6]
    # Every post keeps the edge offset across the neck to the tuner edge.
    for d, y in posts:
        assert y - plan.edge_y(d, -1.0) >= parameters.tuner_edge_offset - 0.5
    # The tip hooks over to the treble side.
    tip = values["headstock_bass_edge"][-1]
    assert -tip[1] > 70.0 and tip[0] == plan.length


def test_given_inline_offsets_place_a_row_and_must_match_it() -> None:
    from cncguitarwizard.geometry.exceptions import NeckGeometryError

    base = replace(
        Prototype001Parameters(),
        headstock_style="6_inline",
        headstock_outline="fitted",
        tuner_inline_offsets=(20.0, 12.0, 4.0, -4.0, -12.0, -20.0),
    )
    _, tuners = base.headstock_design()
    assert [round(h.center.y, 1) for h in tuners.holes] == [
        -20.0,
        -12.0,
        -4.0,
        4.0,
        12.0,
        20.0,
    ]
    # A treble-side row: offsets toward the treble side.
    reverse = replace(base, headstock_style="6_inline_reverse")
    _, tuners = reverse.headstock_design()
    assert tuners.holes[0].center.y == pytest.approx(20.0)
    with pytest.raises(NeckGeometryError, match="needs 6 tuner_inline_offsets"):
        replace(base, tuner_inline_offsets=(20.0, 12.0)).build()
    with pytest.raises(NeckGeometryError, match="has none"):
        replace(base, headstock_style="3+3").build()
    # The editors lay the headstock out before the build checks it: the
    # same message, not an IndexError (the Explorer's six on a 7-in-line).
    with pytest.raises(NeckGeometryError, match="needs 7 tuner_inline_offsets"):
        replace(base, headstock_style="7_inline").headstock_design()
