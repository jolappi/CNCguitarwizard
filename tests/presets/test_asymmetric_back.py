"""Tests for a heel and a volute whose two sides differ."""

from dataclasses import replace

import pytest

from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import headstock_editor_layout, heel_editor_layout

# A heel carved further back on the treble side (+Y, the bass at -Y): its
# rounding runs 45 mm onto the neck on the bass side, 85 mm on the treble.
TREBLE_CUT = replace(
    Prototype001Parameters(),
    heel_root_style="drawn",
    heel_root_neck_points=(
        (45.0, -33.0),
        (55.0, -15.0),
        (60.0, 0.0),
        (75.0, 15.0),
        (85.0, 33.0),
    ),
)


def _reach(line: tuple, side: float) -> float:  # type: ignore[type-arg]
    """How far toward the nut a line reaches out on one side."""
    return min(point.x for point in line if point.y * side > 20.0)


def test_a_heel_carved_further_on_the_treble_side() -> None:
    neck = TREBLE_CUT.build().neck_surface.heel_drawn
    assert neck is not None
    block = TREBLE_CUT.neck_outline().last_fret_position

    # Measured from the block's flat start, 85 and 45 mm onto the neck.
    assert _reach(neck.neck, 1.0) < _reach(neck.neck, -1.0) - 30.0
    assert _reach(neck.neck, 1.0) < block
    # Left-handed, the treble side is -Y: the deeper cut goes with it.
    left = replace(TREBLE_CUT, handedness="left").build().neck_surface.heel_drawn
    assert left is not None
    assert _reach(left.neck, -1.0) == pytest.approx(_reach(neck.neck, 1.0))


def test_the_editors_say_which_lines_are_whole_and_where_the_treble_is() -> None:
    values = {
        "heel_root_style": "drawn",
        "heel_root_neck_points": [list(p) for p in TREBLE_CUT.heel_root_neck_points],
    }
    heel = heel_editor_layout({"prototype": values})["heel"]
    assert heel["lines"]["neck"]["whole"] and not heel["lines"]["flat"]["whole"]
    assert heel["treble"] == 1.0

    volute = {
        "headstock_pointed_volute": True,
        "headstock_volute_points": [[0, -21], [-11, -12], [-7, 0], [-5, 12], [0, 21]],
    }
    layout = headstock_editor_layout({"prototype": volute})["volute"]
    assert layout["lines"]["crest"]["whole"]
    assert not layout["lines"]["neck"]["whole"]
    # Its crest as drawn, side to side: the -Y side reaches 11 mm onto the
    # neck, the +Y side 5.
    crest = layout["lines"]["crest"]["line"]
    assert max(x for x, y in crest if y < -5) > max(x for x, y in crest if y > 5) + 4
