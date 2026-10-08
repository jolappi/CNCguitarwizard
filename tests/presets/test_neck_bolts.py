"""Tests for the bolt-on neck's ferrules and bolt holes."""

import math
from dataclasses import replace

import pytest

from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters, YourDesignShape


def ferrules(body):  # type: ignore[no-untyped-def]
    return [hole for hole in body.rear_holes if hole.name.endswith("ferrule")]


def neck_half_width(parameters, x: float) -> float:  # type: ignore[no-untyped-def]
    outline = parameters.neck_outline()
    if x >= outline.last_fret_position:
        return outline.heel_width / 2.0
    fraction = x / outline.last_fret_position
    return (
        outline.nut_width + (outline.last_fret_width - outline.nut_width) * fraction
    ) / 2.0


def rim_in_body(body, hole, reach: float) -> bool:  # type: ignore[no-untyped-def]
    return all(
        point_in_polygon(
            Point2D(
                hole.center_x + reach * math.cos(math.pi * step / 18.0),
                hole.center_y + reach * math.sin(math.pi * step / 18.0),
            ),
            body.outline.points,
        )
        for step in range(36)
    )


def test_every_bolt_moves_out_to_leave_5_mm_to_the_neck_edge() -> None:
    parameters = replace(Prototype001Parameters(), body_shape=YourDesignShape())
    body = parameters.build().body
    heel_end = body.neck_pocket.max_x

    assert len(ferrules(body)) == 4
    for ferrule in ferrules(body):
        wall = neck_half_width(parameters, ferrule.center_x) - abs(ferrule.center_y)
        assert wall - 2.5 == pytest.approx(5.0)
    # Tail pair 2.5 + 3 mm from the pocket end, 32 mm apart along the neck.
    assert sorted(round(f.center_x - heel_end, 1) for f in ferrules(body)) == [
        -37.5,
        -37.5,
        -5.5,
        -5.5,
    ]
    hole = next(h for h in body.rear_holes if h.name == "Neck bolt 1 hole")
    assert (hole.diameter, hole.depth) == (5.0, pytest.approx(44.0 - 20.0))


def test_near_the_body_edge_a_ferrule_keeps_1_mm_of_wood() -> None:
    body = Prototype001Parameters().build().body
    heel_end = body.neck_pocket.max_x
    by_name = {hole.name: hole for hole in ferrules(body)}

    # Design by Jone: the treble pair sits by the deep cutaway, moved out
    # as far as their ferrules stay 1 mm inside the body.
    front, back = by_name["Neck bolt 3 ferrule"], by_name["Neck bolt 4 ferrule"]
    assert round(front.center_x - heel_end, 1) == -24.0
    assert round(back.center_x - heel_end, 1) == -5.5
    for ferrule in (front, back):
        assert ferrule.center_y > 9.0
        assert rim_in_body(body, ferrule, 7.0 + 1.0)
        assert not rim_in_body(
            body,
            ferrule.__class__(
                ferrule.name,
                ferrule.center_x,
                ferrule.center_y + 0.5,
                ferrule.diameter,
                ferrule.depth,
            ),
            7.0 + 1.0,
        )
    # Every ferrule lies in the body, even where it runs past the pocket.
    for ferrule in ferrules(body):
        assert rim_in_body(body, ferrule, 7.0 + 1.0)


def test_bolts_keep_clear_of_the_truss_rod_the_neck_edge_and_each_other() -> None:
    fixed = replace(Prototype001Parameters(), body_neck_bolts_outward=False)
    with pytest.raises(BodyGeometryError, match="to the neck's edge"):
        replace(
            fixed, body_shape=YourDesignShape(), body_neck_bolt_spacing_y=46.0
        ).build()
    near_rod = YourDesignShape(
        neck_bolts=((-30.0, -19.0), (-8.0, -19.0), (-30.0, 6.0), (-8.0, 6.0))
    )
    with pytest.raises(BodyGeometryError, match="within 3 mm of the truss rod"):
        replace(fixed, body_shape=near_rod).build()
    crowded = YourDesignShape(
        neck_bolts=((-20.0, -19.0), (-8.0, -19.0), (-30.0, 19.0), (-8.0, 19.0))
    )
    with pytest.raises(BodyGeometryError, match="ferrules overlap"):
        replace(fixed, body_shape=crowded).build()
    # Too far into the Design by Jone treble cutaway for any ferrule.
    cutaway = replace(
        Prototype001Parameters().body_shape,
        neck_bolts=((-40.0, -20.0), (-8.0, -20.0), (-40.0, 20.0), (-8.0, 20.0)),
    )
    with pytest.raises(BodyGeometryError, match="has no room"):
        replace(Prototype001Parameters(), body_shape=cutaway).build()
    with pytest.raises(BodyGeometryError, match="narrower than its ferrule"):
        replace(Prototype001Parameters(), body_neck_bolt_hole_diameter=14.0).build()


def test_no_bolt_comes_closer_to_the_heel_end_than_the_end_wall() -> None:
    # The tail bolts sit as close to the pocket's end as 3 mm of wood
    # allows: spread along the neck, the bolts hold it better.
    shape = replace(
        YourDesignShape(),
        neck_bolts=((-40.0, -20.0), (-5.0, -20.0), (-40.0, 20.0), (-5.5, 20.0)),
    )
    with pytest.raises(BodyGeometryError, match=r"Neck bolt 2 .* 2\.5 mm of wood"):
        replace(Prototype001Parameters(), body_shape=shape).build()

    looser = replace(
        Prototype001Parameters(), body_shape=shape, body_neck_bolt_end_wall=2.5
    )
    assert len(ferrules(looser.build().body)) == 4


@pytest.mark.parametrize("thickness", (5.0, 20.0))
def test_a_body_no_thicker_than_the_pocket_names_the_pocket_not_a_bolt(
    thickness: float,
) -> None:
    # Regression: the bolt holes, the body's thickness less the pocket's
    # depth deep, were left no depth and named instead.
    parameters = replace(Prototype001Parameters(), body_thickness=thickness)

    with pytest.raises(
        BodyGeometryError,
        match=rf"^Neck pocket depth \(20 mm, the heel thickness\) .* "
        rf"{thickness:g} mm thick body\.$",
    ):
        parameters.build()
    # Thicker than the pocket, the bolts reach its floor.
    hole = next(
        h
        for h in replace(parameters, body_thickness=44.0).build().body.rear_holes
        if h.name == "Neck bolt 1 hole"
    )
    assert hole.depth == pytest.approx(44.0 - 20.0)
