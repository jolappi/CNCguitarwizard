"""Tests for the left-handed option: the instrument built as its mirror image."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.geometry.body import FloydRoseSpec, TuneOMaticSpec
from cncguitarwizard.geometry.primitives import Point2D
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import (
    GUITAR_BODY,
    YOUR_DESIGN_TEMPLATES,
    mirrored_shape,
)
from cncguitarwizard.webapp import (
    body_editor_layout,
    headstock_editor_layout,
    parameter_schema,
)

RIGHT = Prototype001Parameters()
LES_PAUL = replace(
    RIGHT,
    body_shape=YOUR_DESIGN_TEMPLATES["les_paul"][1],
    body_bridge=TuneOMaticSpec(),
    body_thickness=50.8,
    body_carved_top=True,
)


def centre(points: tuple[Point2D, ...]) -> tuple[float, float]:
    """Return the polygon's area centroid (its vertices may be spaced unevenly)."""
    area = cx = cy = 0.0
    for a, b in zip(points, (*points[1:], points[0]), strict=True):
        cross = a.x * b.y - b.x * a.y
        area += cross
        cx += (a.x + b.x) * cross
        cy += (a.y + b.y) * cross
    return cx / (3.0 * area), cy / (3.0 * area)


def features(body) -> dict[str, tuple[float, float]]:  # type: ignore[no-untyped-def]
    found = {
        cavity.name: centre(cavity.outline)
        for cavity in (*body.top_cavities, *body.through_cavities)
    }
    for rear in body.rear_cavities:
        found[rear.cavity.name] = centre(rear.cavity.outline)
    for hole in body.holes:
        found[hole.name] = (hole.center_x, hole.center_y)
    return found


@pytest.mark.parametrize("right", [RIGHT, LES_PAUL])
def test_a_left_handed_body_is_the_mirror_image(right) -> None:  # type: ignore[no-untyped-def]
    left = replace(right, handedness="left")
    assert (right.bass_sign, left.bass_sign) == (-1.0, 1.0)
    built_right, built_left = right.build().body, left.build().body
    mine, theirs = features(built_right), features(built_left)
    assert mine.keys() == theirs.keys() and len(mine) > 10
    for name, (x, y) in mine.items():
        assert theirs[name] == pytest.approx((x, -y), abs=0.01), name
    # The outline too (the same curve, its mirror), and a carved top's
    # fall with it.
    mirrored = [Point2D(p.x, -p.y) for p in built_right.outline.points]
    assert len(mirrored) == len(built_left.outline.points)
    for point in built_left.outline.points:
        assert min(math.hypot(point.x - q.x, point.y - q.y) for q in mirrored) < 1e-6
    if built_right.carved_top is not None:
        assert built_left.carved_top is not None
        for x, y in ((520.0, 60.0), (450.0, -40.0), (700.0, 120.0)):
            # Within its grid's sampling and relaxation (which run from -Y).
            assert built_left.carved_top.drop_at(x, -y) == pytest.approx(
                built_right.carved_top.drop_at(x, y), abs=0.1
            )


def test_the_neck_and_headstock_follow() -> None:
    right = replace(
        RIGHT,
        bass_scale_length=647.7,
        headstock_style="6_inline",
        headstock_outline="drawn",
        headstock_tip_points=((3.5, 27.0), (4.5, 33.0)),
    )
    left = replace(right, handedness="left")
    built_right, built_left = right.build(), left.build()
    # The tuners on the other side.
    for a, b in zip(
        built_right.tuner_layout.holes, built_left.tuner_layout.holes, strict=True
    ):
        assert (b.center.x, b.center.y) == pytest.approx((a.center.x, -a.center.y))
    # The drawn tip, mirrored and still ordered from -Y to +Y.
    assert left.built_tip_points() == ((4.5, -33.0), (3.5, -27.0))
    # A fan's long (bass) side on the other side too.
    assert left.fret_skew.at(0.0) == pytest.approx(-right.fret_skew.at(0.0))
    assert left.fret_skew.bass_sign == -right.fret_skew.bass_sign


def test_a_floyd_rose_arm_goes_to_the_treble_side() -> None:
    right = replace(RIGHT, body_bridge=FloydRoseSpec())
    mine = features(right.build().body)
    theirs = features(replace(right, handedness="left").build().body)
    recesses = [name for name in mine if "Floyd" in name or "recess" in name.lower()]
    assert recesses
    for name in recesses:
        assert theirs[name] == pytest.approx((mine[name][0], -mine[name][1]), abs=1e-6)


def test_the_headstock_lettering_is_set_again_not_mirrored() -> None:
    right = replace(RIGHT, headstock_engraving_text="Jone", headstock_engraving_y=4.0)
    left = replace(right, handedness="left")
    built_right, built_left = right.build(), left.build()
    assert built_right.headstock_engraving is not None
    assert built_left.headstock_engraving is not None
    assert left.headstock_engraving_direction() == 180.0 - 90.0
    points_right = [p for line in built_right.headstock_engraving.lines for p in line]
    points_left = [p for line in built_left.headstock_engraving.lines for p in line]
    # Where the right-handed text's mirror image lies...
    assert min(p.y for p in points_left) == pytest.approx(
        -max(p.y for p in points_right), abs=0.5
    )
    assert min(p.x for p in points_left) == pytest.approx(
        min(p.x for p in points_right), abs=0.5
    )
    # ... but set again, reading the right way round: not its mirror image.
    mirrored = {(round(p.x, 3), round(-p.y, 3)) for p in points_right}
    assert {(round(p.x, 3), round(p.y, 3)) for p in points_left} != mirrored


def test_mirroring_a_shape_twice_gives_it_back() -> None:
    for shape in (GUITAR_BODY, *(s for _, s in YOUR_DESIGN_TEMPLATES.values())):
        once = mirrored_shape(shape)
        assert once != shape and once.mirrored != shape.mirrored
        assert mirrored_shape(once) == shape


def test_the_web_form_and_editors() -> None:
    fields = {
        field["name"]: (group["title"], field)
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    title, field = fields["handedness"]
    assert title == "Instrument" and not field["advanced"]
    assert field["options"] == ["right", "left"]
    # The editors draw the design as drawn and show it mirrored.
    payload = {"prototype": {"handedness": "left", "headstock_engraving_text": "Jone"}}
    right = body_editor_layout({"prototype": {}})
    left = body_editor_layout(payload)
    assert (right["mirrored"], left["mirrored"]) == (False, True)
    assert left["polygons"] == right["polygons"]
    headstock = headstock_editor_layout(payload)
    drawn = headstock_editor_layout({"prototype": {"headstock_engraving_text": "Jone"}})
    assert headstock["mirrored"] and headstock["holes"] == drawn["holes"]
    # Its lettering, as built, mirrored back into the drawn frame: the
    # mirrored view shows it reading the right way round.
    assert headstock["lettering"]["centre"] == drawn["lettering"]["centre"]
    assert headstock["lettering"]["lines"] != drawn["lettering"]["lines"]
