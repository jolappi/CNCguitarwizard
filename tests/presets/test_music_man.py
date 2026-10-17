"""Tests for the Music Man Axis style: its body and its neck, traced."""

from dataclasses import replace

import pytest

from cncguitarwizard.geometry.body import FloydRoseSpec
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.presets.prototype001 import NECK_TEMPLATES
from cncguitarwizard.webapp import (
    body_editor_layout,
    design_problems,
    load_design,
    style_design,
)


def test_the_axis_body_keeps_the_photographed_size_and_horn() -> None:
    label, shape = YOUR_DESIGN_TEMPLATES["music_man_axis"]
    assert label == "Music Man Axis style (traced from a product photo)"
    points = shape.outline_points(0.0)
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    # Scaled from the photo's frets: neck crossing to tail, and across.
    assert max(xs) - min(xs) == pytest.approx(404.6, abs=1.0)
    assert max(ys) - min(ys) == pytest.approx(319.9, abs=1.0)
    # The bass horn reaches up beside the neck, well past the treble
    # cutaway's edge there.
    beside = [p for p in points if 30.0 < abs(p.y) < 60.0]
    bass = min(p.x for p in beside if p.y < 0.0)
    treble = min(p.x for p in beside if p.y > 0.0)
    assert bass < treble - 30.0
    # Straight across the neck between the two corners.
    corners = [p for p in shape.control_points if len(p) == 3]
    assert len(corners) == 2
    # The volume pot and the jack on the treble side, as photographed;
    # the template's switch where every layout clears it.
    assert shape.rear_pots[0][1] > 0.0 and shape.jack_y > 0.0
    assert shape.switch_cavity_y < 0.0


def test_the_music_man_neck_puts_its_posts_where_the_photos_are() -> None:
    label, values = NECK_TEMPLATES["music_man"]
    assert label == "Music Man neck (mockup, not the original)"
    assert values["headstock_style"] == "4+2"
    assert values["headstock_angle"] == 0.0
    assert values["truss_rod_adjustment"] == "heel"
    parameters = replace(Prototype001Parameters(), **values)
    plan, tuners = parameters.headstock_design()
    # Four on the bass side (-Y as drawn), two on the treble side.
    sides = sorted(hole.side for hole in tuners.holes)
    assert sides == ["bass"] * 4 + ["treble"] * 2
    posts = sorted((-hole.center.x, hole.center.y) for hole in tuners.holes)
    assert [round(d, 1) for d, _ in posts] == [42.4, 55.4, 67.8, 80.2, 93.2, 118.0]
    # Each keeps the tuner edge offset to its own edge.
    for distance, y in posts:
        side = -1.0 if y < 1.5 else 1.0
        assert abs(plan.edge_y(distance, side) - y) >= 12.0 - 0.5
    assert plan.length == pytest.approx(146.0)
    parameters.build()
    replace(parameters, handedness="left").build()


def test_the_axis_style_builds_as_photographed() -> None:
    design = style_design("electric_guitar", "music_man_axis", "axis")
    assert design_problems(design) == []
    parameters = load_design(design).parameters
    assert parameters.scale_length == pytest.approx(647.7)
    assert parameters.fret_count == 22
    assert parameters.body_pickups == "HH"
    assert isinstance(parameters.body_bridge, FloydRoseSpec)
    assert parameters.body_controls == "volume_1"
    # The toggle beside the volume pot, as photographed.
    shape = parameters.body_shape
    assert (shape.switch_cavity_offset, shape.switch_cavity_y) == (149.3, 120.6)
    assert parameters.headstock_style == "4+2"
    # The Floyd Rose's locking nut, as on the photographed one.
    assert parameters.locking_nut_kind == "r2"
    geometry = parameters.build()
    assert len(geometry.tuner_layout.holes) == 6
    # The jack's bore ends in the control cavity, as the editor checks.
    assert body_editor_layout(design)["jack"]["reaches_controls"]
    replace(parameters, handedness="left").build()
    replace(parameters, body_battery_box=True).build()
