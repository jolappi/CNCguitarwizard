"""Tests for a Stratocaster's controls from the back, no pickguard needed
(``body_controls`` "strat_rear")."""

import math
from dataclasses import replace
from functools import cache
from pathlib import Path

import pytest

from cncguitarwizard.geometry.body import HardtailSpec, outlines_overlap
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Geometry, Prototype001Parameters
from cncguitarwizard.presets.controls import (
    BLADE_SWITCH_POCKET,
    BLADE_SWITCH_TOP_WALL,
)
from cncguitarwizard.setting_conditions import APPLIES_WHEN
from cncguitarwizard.webapp import load_design, parameter_schema, style_design

ROOT = Path(__file__).resolve().parents[2]

STRAT = load_design(style_design("electric_guitar", "stratocaster")).parameters
REAR = replace(
    STRAT, body_controls="strat_rear", body_pickguard=False, body_jack="side"
)


def heel_end(parameters: Prototype001Parameters) -> float:
    outline = parameters.neck_outline()
    return outline.last_fret_position + outline.heel_length


def pots(geometry: Prototype001Geometry) -> list[Point2D]:
    return [hole.center for hole in geometry.body.holes if "pot" in hole.name]


@cache
def hardtail() -> Prototype001Geometry:
    """Return the Stratocaster with a hardtail, its controls from the back."""
    return replace(REAR, body_bridge=HardtailSpec()).build()


@cache
def tremolo() -> Prototype001Geometry:
    """Return the Stratocaster with its tremolo, its controls from the back."""
    return REAR.build()


def test_the_controls_go_where_the_guard_puts_them_from_the_back() -> None:
    geometry = hardtail()
    body = geometry.body
    end = heel_end(REAR)
    # Nothing in the way: the knobs where the Stratocaster's guard has
    # them, its three pots' shafts through the top into a rear cavity.
    drawn = STRAT.body_shape.pickguard_controls
    assert [(p.x - end, p.y) for p in pots(geometry)] == [
        (pytest.approx(x), pytest.approx(y)) for x, y in drawn[1:]
    ]
    rear = body.control_cavity
    assert rear is not None
    assert rear.cavity.depth == REAR.body_thickness - REAR.body_rear_cavity_top_wall
    assert all(point_in_polygon(p, rear.cavity.outline) for p in pots(geometry))
    # The 5-way blade switch from the back too: its pocket leaving its top
    # wall, its lever's slot and its two screws through the top.
    (pocket,) = rear.steps
    assert pocket.name == "Control switch pocket"
    assert pocket.depth == REAR.body_thickness - BLADE_SWITCH_TOP_WALL
    assert pocket.max_x - pocket.min_x >= BLADE_SWITCH_POCKET[1]
    assert [cavity.name for cavity in body.through_cavities] == ["Control switch slot"]
    screws = [hole for hole in body.holes if hole.name.startswith("Control switch")]
    assert len(screws) == 2
    # Under a cover cut from sheet; no pickguard.
    assert [cover.name for cover in geometry.covers] == ["Control cavity cover"]


def test_with_a_tremolo_they_turn_clear_of_its_cover() -> None:
    geometry = tremolo()
    body = geometry.body
    rear = body.control_cavity
    assert rear is not None
    (spring,) = [r for r in body.rear_cavities if r.cover_on_back]
    # From the back the guard's places put the volume pot over the
    # tremolo's cover: the controls move and turn off it, and stay clear
    # of the edge's roundover.
    assert not outlines_overlap(rear.cover_recess.outline, spring.cover_recess.outline)
    moved = [(p.x - heel_end(REAR), p.y) for p in pots(geometry)]
    drawn = STRAT.body_shape.pickguard_controls[1:]
    assert any(
        math.hypot(x - dx, y - dy) > 5.0
        for (x, y), (dx, dy) in zip(moved, drawn, strict=True)
    )
    # The pots' spacing kept: moved and turned as one.
    gaps = [math.dist(a, b) for a, b in zip(moved, moved[1:], strict=False)]
    drawn_gaps = [math.dist(a, b) for a, b in zip(drawn, drawn[1:], strict=False)]
    assert gaps == pytest.approx(drawn_gaps)


@pytest.mark.parametrize("bridge", ["hardtail", "tremolo"])
def test_the_jack_goes_in_the_edge_bored_square_into_the_cavity(bridge: str) -> None:
    geometry = hardtail() if bridge == "hardtail" else tremolo()
    body = geometry.body
    jack = body.jack_hole
    assert jack is not None
    rear = body.control_cavity
    assert rear is not None
    # On the edge, bored square into it, and on into the cavity.
    start = Point2D(jack.start_x, jack.start_y)
    outline = body.outline.points
    assert min(math.dist((start.x, start.y), (p.x, p.y)) for p in outline) < 2.0
    radians = math.radians(jack.direction_degrees)
    end = Point2D(
        start.x + math.cos(radians) * jack.depth,
        start.y + math.sin(radians) * jack.depth,
    )
    assert point_in_polygon(end, rear.cavity.outline)
    # On the lower bout, behind the knobs, as a side jack is: no further
    # from the Stratocaster's own jack than the cavity makes it.
    assert start.x > max(p.x for p in pots(geometry)) - 20.0
    # No jack cavity on the top.
    assert not any("Jack" in cavity.name for cavity in body.top_cavities)


def test_the_form_offers_it_and_sets_what_it_needs() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    labels = fields["body_controls"]["labels"]
    assert labels["strat_rear"].startswith("Stratocaster's controls from the back")
    assert "strat_rear" in APPLIES_WHEN["body_pickguard"][0]["body_controls"]
    script = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    assert 'event.target.value === "strat_rear"' in script
    assert "setControlValue(guard, false);" in script
    assert 'setControlValue(jack, "side");' in script
