"""Tests for the interchangeable body shapes."""

import dataclasses
from dataclasses import replace

import pytest

from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import point_in_polygon
from cncguitarwizard.presets import (
    BODY_SHAPE_KINDS,
    DesignByJoneShape,
    Prototype001Parameters,
    YourDesignShape,
    body_shape_from_dict,
)
from cncguitarwizard.presets.body_shapes import GUITAR_BODY, YOUR_DESIGN_TEMPLATES


def test_the_default_body_is_the_drawn_design_by_jone_template() -> None:
    parameters = Prototype001Parameters()
    body = parameters.build().body

    assert parameters.body_shape == GUITAR_BODY
    assert GUITAR_BODY == YOUR_DESIGN_TEMPLATES["design_by_jone"][1]
    assert [hole.name for hole in body.holes[:3]] == [
        "Switch shaft hole",
        "Pot 1 shaft hole",
        "Pot 2 shaft hole",
    ]
    assert body.jack_hole.start_y == 107.5


@pytest.mark.parametrize("kind", list(BODY_SHAPE_KINDS))
def test_every_body_shape_builds_with_its_features_inside(kind: str) -> None:
    shape = BODY_SHAPE_KINDS[kind]()
    body = replace(Prototype001Parameters(), body_shape=shape).build().body

    for hole in body.holes:
        assert point_in_polygon(hole.center, body.outline.points), hole.name
    assert {rear.name for rear in body.rear_cavities} >= {
        "Control cavity",
        "Switch cavity",
    }


def test_your_design_body_follows_the_heel_end() -> None:
    short = replace(Prototype001Parameters(), body_shape=YourDesignShape()).build()
    long = replace(
        Prototype001Parameters(), body_shape=YourDesignShape(), scale_length=647.7
    ).build()
    shift = long.body.neck_pocket.max_x - short.body.neck_pocket.max_x

    assert shift > 0
    assert long.body.outline.points[0].x - short.body.outline.points[0].x == (
        pytest.approx(shift)
    )
    assert long.body.jack_hole.start_x - short.body.jack_hole.start_x == (
        pytest.approx(shift)
    )
    # The pocket's tail wall sits in wood; its nut-ward end opens on the gap.
    pocket = short.body.neck_pocket
    assert pocket.max_x < max(point.x for point in short.body.outline.points)


def test_your_design_starts_as_a_left_handed_double_cutaway() -> None:
    parameters = replace(Prototype001Parameters(), body_shape=YourDesignShape())
    body = parameters.build().body
    heel_end = body.neck_pocket.max_x
    horns = [point for point in body.outline.points if point.x < heel_end - 100.0]

    # The long upper horn lies on the bass side (-Y) of this left-handed body.
    assert horns and all(point.y < 0 for point in horns)
    assert max(point.y for point in body.outline.points) > 150.0
    assert min(point.y for point in body.outline.points) < -150.0


def test_body_shapes_round_trip_through_dicts() -> None:
    for kind, shape_class in BODY_SHAPE_KINDS.items():
        shape = shape_class()
        rebuilt = body_shape_from_dict(dataclasses.asdict(shape))
        assert rebuilt == shape and rebuilt.kind == kind
    moved = body_shape_from_dict(
        {"kind": "your_design", "pot_offsets": [[170.0, 90.0]], "jack_y": 130.0}
    )
    assert moved == YourDesignShape(pot_offsets=((170.0, 90.0),), jack_y=130.0)
    with pytest.raises(BodyGeometryError, match="Unknown body shape"):
        body_shape_from_dict({"kind": "banjo"})
    with pytest.raises(BodyGeometryError, match="Unknown your_design body shape"):
        body_shape_from_dict({"kind": "your_design", "wings": 2})


def test_your_design_outline_passes_through_its_control_points() -> None:
    points = (
        (-50.0, -30.0),
        (200.0, -150.0),
        (330.0, 0.0),
        (200.0, 150.0),
        (-50.0, 30.0),
    )
    shape = YourDesignShape(control_points=points)
    outline = shape.outline_points(400.0)

    for x, y in points:
        assert any(
            abs(point.x - (x + 400.0)) < 1e-9 and abs(point.y - y) < 1e-9
            for point in outline
        )
    assert len(outline) == len(points) * 8


def test_moving_a_control_point_reshapes_the_body() -> None:
    start = YourDesignShape()
    wider = list(start.control_points)
    index = max(range(len(wider)), key=lambda i: wider[i][1])
    wider[index] = (wider[index][0], wider[index][1] + 20.0)
    body = (
        replace(
            Prototype001Parameters(),
            body_shape=YourDesignShape(control_points=tuple(wider)),
        )
        .build()
        .body
    )

    assert max(point.y for point in body.outline.points) == pytest.approx(
        max(y for _, y in wider), abs=1.0
    )


def test_your_design_rejects_too_few_or_bad_points() -> None:
    with pytest.raises(BodyGeometryError, match="at least four"):
        YourDesignShape(control_points=((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)))
    with pytest.raises(BodyGeometryError, match="finite"):
        YourDesignShape(
            control_points=((0.0, 0.0), (1.0, 0.0), (0.0, float("nan")), (1.0, 1.0))
        )


def test_an_outline_that_misses_a_feature_is_rejected_by_the_build() -> None:
    small = ((-50.0, -40.0), (60.0, -60.0), (120.0, 0.0), (60.0, 60.0), (-50.0, 40.0))
    with pytest.raises(BodyGeometryError, match="outside the body outline"):
        replace(
            Prototype001Parameters(), body_shape=YourDesignShape(control_points=small)
        ).build()


@pytest.mark.parametrize("key", list(YOUR_DESIGN_TEMPLATES))
def test_every_your_design_template_builds_with_its_features_inside(key: str) -> None:
    _, shape = YOUR_DESIGN_TEMPLATES[key]
    body = replace(Prototype001Parameters(), body_shape=shape).build().body

    for hole in body.holes:
        assert point_in_polygon(hole.center, body.outline.points), hole.name


def test_the_design_by_jone_template_follows_the_traced_outline() -> None:
    _, template = YOUR_DESIGN_TEMPLATES["design_by_jone"]
    heel_end = 461.2
    traced = DesignByJoneShape().outline_points(heel_end)
    drawn = template.outline_points(heel_end)

    assert len(template.control_points) == 64
    # The spline stays within a few millimetres of the traced silhouette.
    for axis in ("x", "y"):
        for pick in (min, max):
            assert pick(getattr(p, axis) for p in drawn) == pytest.approx(
                pick(getattr(p, axis) for p in traced), abs=4.0
            )
    # It keeps that body's own electronics placements.
    assert template.switch_cavity_y == DesignByJoneShape().switch_cavity_y
    assert template.jack_offset == DesignByJoneShape().jack_offset
