"""Tests for the neck's and the fretboard's drawings for their pages."""

import re
from dataclasses import replace

from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.render.svg import render_fretboard_svg, render_neck_svg
from cncguitarwizard.webapp import part_views


def titles(svg: str) -> list[str]:
    return re.findall(r"<title>([^<]*)</title>", svg)


def test_the_neck_is_drawn_from_above_from_the_side_and_in_section() -> None:
    geometry = Prototype001Parameters().build()

    svg = render_neck_svg(geometry)

    assert svg.startswith("<svg") and svg.endswith("</svg>")
    named = titles(svg)
    for part in ("The headstock", "The neck", "The fretboard", "The nut"):
        assert part in named
    assert named.count("Tuner hole") == len(geometry.tuner_layout.holes)
    assert "The neck from the side" in named
    assert "Fret 1: the neck" in named and "Fret 12: the fretboard" in named
    # The sections say the neck's width and depth there.
    assert "At fret 1: 43.0 wide, 17.0 deep" in svg
    assert "From the side (height x3)" in svg


def test_a_scalloped_board_shows_its_scallops_from_above_and_hollowed() -> None:
    plain = render_fretboard_svg(Prototype001Parameters().build())
    scalloped_geometry = replace(
        Prototype001Parameters(), fretboard_scalloped=True
    ).build()
    scalloped = render_fretboard_svg(scalloped_geometry)

    assert not [name for name in titles(plain) if name.startswith("Scallop")]
    spaces = [name for name in titles(scalloped) if name.startswith("Scallop")]
    assert len(spaces) == len(scalloped_geometry.fretboard_scallops.fret_numbers)
    assert "scalloped from fret 15" in scalloped
    # The side view dips where the scallops are: its outline differs.
    side = re.compile(
        r'<polygon points="([^"]*)"[^>]*><title>The fretboard from the side'
    )
    plain_side = side.search(plain)
    scalloped_side = side.search(scalloped)
    assert plain_side is not None and scalloped_side is not None
    assert plain_side.group(1) != scalloped_side.group(1)


def test_blind_slots_are_drawn_as_they_are_cut() -> None:
    through = render_fretboard_svg(Prototype001Parameters().build())
    blind = render_fretboard_svg(
        replace(Prototype001Parameters(), fret_slot_end_inset=2.5).build()
    )

    assert through.count("<line") == blind.count("<line")
    assert through != blind


def test_the_web_app_gets_both_drawings_or_why_not() -> None:
    views = part_views({"prototype": {"fretboard_scalloped": True}})

    assert set(views) == {"neck", "fretboard"}
    assert views["neck"].startswith("<svg")
    assert "Scallop after fret 15" in views["fretboard"]
    assert "error" in part_views({"prototype": {"fret_slot_end_inset": 9.0}})
