"""Tests for the bolt-on neck's ferrules and bolt holes."""

from dataclasses import replace

import pytest

from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.presets import Prototype001Parameters, YourDesignShape


def bolts(body):  # type: ignore[no-untyped-def]
    heel_end = body.neck_pocket.max_x
    return {
        hole.name: (round(hole.center_x - heel_end, 1), hole.center_y, hole)
        for hole in body.rear_holes
    }


def test_the_design_by_jone_body_uses_its_own_bolt_pattern() -> None:
    body = Prototype001Parameters().build().body
    found = bolts(body)

    assert len(body.rear_holes) == 8
    ferrule = found["Neck bolt 1 ferrule"][2]
    assert (ferrule.diameter, ferrule.depth) == (14.0, 5.0)
    hole = found["Neck bolt 1 hole"][2]
    assert hole.diameter == 5.0
    assert hole.depth == pytest.approx(44.0 - 20.0)
    assert [found[f"Neck bolt {i} ferrule"][:2] for i in range(1, 5)] == [
        (-40.0, -20.0),
        (-8.0, -20.0),
        (-28.0, 6.0),
        (-8.0, 6.0),
    ]


def test_an_empty_pattern_is_a_rectangle_near_the_heel_end() -> None:
    body = replace(Prototype001Parameters(), body_shape=YourDesignShape()).build().body
    found = bolts(body)

    # Tail pair 2.5 + 4 mm from the pocket end, 32 x 40 mm apart.
    assert sorted(found[f"Neck bolt {i} ferrule"][:2] for i in range(1, 5)) == [
        (-38.5, -20.0),
        (-38.5, 20.0),
        (-6.5, -20.0),
        (-6.5, 20.0),
    ]


def test_bolts_must_hit_the_pocket_and_ferrules_the_wood() -> None:
    base = replace(Prototype001Parameters(), body_shape=YourDesignShape())
    with pytest.raises(BodyGeometryError, match="misses the neck pocket"):
        replace(base, body_neck_bolt_spacing_y=70.0).build()
    with pytest.raises(BodyGeometryError, match="runs out of the body"):
        replace(
            Prototype001Parameters(),
            body_shape=replace(
                Prototype001Parameters().body_shape,
                neck_bolts=((-40.0, -20.0), (-8.0, -20.0), (-40.0, 20.0), (-8.0, 20.0)),
            ),
        ).build()
    with pytest.raises(BodyGeometryError, match="narrower than its ferrule"):
        replace(base, body_neck_bolt_hole_diameter=14.0).build()
