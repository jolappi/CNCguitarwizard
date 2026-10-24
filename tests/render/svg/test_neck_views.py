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


def test_a_neck_through_neck_is_drawn_paler_inside_the_body() -> None:
    # Regression: a neck-through neck (the Mockingbird style's) runs on
    # through the body as deep as it; drawn whole in the neck's colour it
    # looked like a huge heel.
    through = replace(Prototype001Parameters(), neck_joint="neck_through").build()
    assert through.neck_through is not None

    svg = render_neck_svg(through)

    named = titles(svg)
    assert "The neck from the side" in named
    assert "Inside the body: the neck runs on through it, as deep as it" in named
    assert "Where the body begins" in named
    assert "From the side (height x3), paler inside the body" in svg
    # The paler part starts where the body begins.
    line = re.search(r'<line x1="([\d.]+)"[^>]*><title>Where the body begins', svg)
    inside = re.search(r'<polygon points="([\d.]+),[^>]*><title>Inside the body', svg)
    assert line is not None and inside is not None
    assert line.group(1) == inside.group(1)
    # A bolt-on neck is drawn whole, as before.
    bolt_on = titles(render_neck_svg(Prototype001Parameters().build()))
    assert "Where the body begins" not in bolt_on


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


def test_the_fretboards_slots_and_section_carry_their_names() -> None:
    named = titles(render_fretboard_svg(Prototype001Parameters().build()))

    # Each slot from above and from the side, the section at the 12th:
    # the parts a setting's picture picks out (setting_pictures).
    assert "Fret slot 1" in named and "Fret slot 24" in named
    assert "Fret slot 12, from the side" in named
    assert "The fretboard at fret 12" in named
