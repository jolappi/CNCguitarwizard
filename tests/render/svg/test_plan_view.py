"""Tests for the whole-instrument plan view."""

import re
from dataclasses import replace

from cncguitarwizard.geometry.body import FloydRoseSpec
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.render.svg import render_plan_view_svg


def test_plan_view_draws_every_feature_once() -> None:
    geometry = Prototype001Parameters().build()

    svg = render_plan_view_svg(geometry)

    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    # 24 frets and the centreline, 4 wire holes (two pickups, the switch
    # and the ground), 12 inlay markers, 6 tuner holes + 7 body holes +
    # jack, 4 neck-bolt ferrules with their bolt holes on the back, and
    # 4 + 3 cover-screw spots.
    assert svg.count("<line") == 24 + 1 + 4
    assert svg.count('fill="#e8e2d0"') == 12
    assert svg.count("<circle") == 6 + 7 + 1 + 8 + 7
    # Body outline, headstock, neck, fretboard, the nut, 4 top cavities
    # and the truss-rod access notch, 2 rear cavities with their covers.
    assert svg.count("<path") == 5 + 12 + 4 + 4 + 1


def test_plan_view_draws_the_nut_and_the_board_under_a_slotted_one() -> None:
    plain = render_plan_view_svg(Prototype001Parameters().build())
    slotted = render_plan_view_svg(
        replace(Prototype001Parameters(), nut_style="slot").build()
    )
    floyd = render_plan_view_svg(
        replace(Prototype001Parameters(), body_bridge=FloydRoseSpec()).build()
    )

    bone = 'fill="#efe8d6"'
    assert plain.count(bone) == 1 and slotted.count(bone) == 1
    assert 'fill="#3c3c3c"' in floyd and bone not in floyd
    # The board runs on behind a slotted nut, a line where it slopes down.
    slope = 'stroke="#7a6040"'
    assert plain.count(slope) == 0 and floyd.count(slope) == 0
    assert slotted.count(slope) == 1
    assert plain.count("<line") + 1 == slotted.count("<line")


def test_every_part_of_the_plan_view_says_what_it_is() -> None:
    svg = render_plan_view_svg(Prototype001Parameters().build())

    names = re.findall(r"<title>([^<]*)</title>", svg)
    for name in (
        "Body",
        "Headstock",
        "Neck",
        "Fretboard",
        "Nut",
        "Inlay, fret 3",
        "Tuner hole, bass 1",
        "Neck pocket",
        "Control cavity (back)",
        "Output jack",
    ):
        assert name in names
    # Every drawn part but the frets and the centreline carries a name.
    shapes = svg.count("<path") + svg.count("<circle")
    assert len(names) == shapes + svg.count("<line") - 24 - 1
