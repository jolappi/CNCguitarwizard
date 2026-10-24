"""Tests for each setting's picture: where it shows on the guitar."""

import re

import pytest

from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.render.svg import render_plan_view_svg
from cncguitarwizard.setting_pictures import NO_PICTURE, SETTING_PICTURES
from cncguitarwizard.webapp import parameter_schema, setting_variation, setting_views

FIELDS = [
    field["name"]
    for part in ("prototype", "machining")
    for group in parameter_schema()[part]
    for field in group["fields"]
]


def _names(views: dict[str, str]) -> dict[str, list[str]]:
    return {
        view: re.findall(r"<title>(.*?)</title>", svg) for view, svg in views.items()
    }


def _found(names: dict[str, list[str]], setting: str) -> str | None:
    """The pattern the setting's picture picks its parts with, or None."""
    view, patterns = SETTING_PICTURES[setting]
    return next(
        (p for p in patterns if any(re.search(p, n) for n in names[view])), None
    )


def test_every_setting_has_a_picture_or_none_on_purpose() -> None:
    assert [
        n for n in FIELDS if n not in SETTING_PICTURES and n not in NO_PICTURE
    ] == []
    assert [n for n in (*SETTING_PICTURES, *NO_PICTURE) if n not in FIELDS] == []
    assert not set(SETTING_PICTURES) & NO_PICTURE
    for view, patterns in SETTING_PICTURES.values():
        assert view in ("plan", "neck", "fretboard") and patterns
        for pattern in patterns:
            re.compile(pattern)


def test_every_picture_finds_its_parts_on_the_default_guitar() -> None:
    views = setting_views({"prototype": {}})

    assert set(views) == {"plan", "neck", "fretboard"}
    names = _names(views)
    assert [s for s in SETTING_PICTURES if _found(names, s) is None] == []
    # The parts a setting shapes, not the whole: its first pattern.
    assert _found(names, "tuner_hole_diameter") == r"^Tuner hole"
    assert _found(names, "first_fret_thickness") == r"^Fret 1: the neck$"
    assert _found(names, "fret_count") == r"^(Fret slot \d+|Zero fret slot)$"


@pytest.mark.parametrize(
    ("values", "setting", "part"),
    [
        ({"body_battery_box": True}, "body_battery_cavity_depth", "Battery cavity"),
        ({}, "body_battery_cavity_depth", "Body"),
        ({"body_arm_contour_depth": 10.0}, "body_arm_contour_width", "Arm contour"),
        ({"neck_carbon_rods": True}, "neck_carbon_rod_depth", "Carbon fibre rod"),
    ],
)
def test_a_part_the_design_has_not_got_falls_back_to_where_it_would_be(
    values: dict[str, object], setting: str, part: str
) -> None:
    names = _names(setting_views({"prototype": values}))

    pattern = _found(names, setting)
    assert pattern is not None and re.search(pattern, part)


def test_a_design_that_does_not_build_has_no_views() -> None:
    assert "error" in setting_views({"prototype": {"nut_width": -1.0}})


def test_a_setting_is_drawn_changed_on_the_designs_own_frame() -> None:
    # 20 % more: the nut wider, on the same page as the design's own view.
    nut = setting_variation({"prototype": {}}, "nut_width")
    assert nut["now"] == 42.0 and nut["value"] == pytest.approx(50.4)
    plain = setting_views({"prototype": {}})["neck"]
    assert nut["view"].split(">", 1)[0] == plain.split(">", 1)[0]
    # A radius 20 % flatter hardly shows: it is drawn further, at half.
    radius = setting_variation({"prototype": {}}, "fretboard_radius")
    assert radius["value"] == pytest.approx(215.0)
    # A tick box the other way, a choice the next one.
    assert setting_variation({"prototype": {}}, "body_battery_box")["value"] is True
    assert setting_variation({"prototype": {}}, "body_controls")["value"] == "gibson_4"
    # A whole number by the setting's kind, whatever the design wrote.
    extension = setting_variation(
        {"prototype": {"fretboard_end_extension": 4}}, "fretboard_end_extension"
    )
    assert isinstance(extension["value"], float)


def test_a_setting_that_moves_nothing_drawn_says_so() -> None:
    # The body's thickness does not show from the front; a machine setting
    # changes how a part is cut, not its shape.
    assert setting_variation({"prototype": {}}, "body_thickness") == {"same": True}
    assert setting_variation({"prototype": {}}, "tool_diameter") == {"same": True}
    assert "error" in setting_variation({"prototype": {"nut_width": -1.0}}, "nut_width")


def test_another_designs_frame_lays_one_drawing_over_the_other() -> None:
    plain = Prototype001Parameters().build()
    longer = Prototype001Parameters(scale_length=700.0).build()

    # Drawn on the plain design's page, the longer one keeps its size.
    framed = render_plan_view_svg(longer, frame_of=plain)
    assert framed.split(">", 1)[0] == render_plan_view_svg(plain).split(">", 1)[0]
    assert framed != render_plan_view_svg(longer)
