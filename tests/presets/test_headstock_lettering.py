"""Tests for the headstock's engraved lettering and its single-stroke font."""

from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam.neck import NeckMachiningParameters, plan_neck_machining
from cncguitarwizard.geometry.exceptions import GeometryException, NeckGeometryError
from cncguitarwizard.geometry.lettering import GLYPHS, text_lines, text_width
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import headstock_editor_layout


def test_the_font_sets_letters_digits_and_punctuation() -> None:
    for character in "AZaz09.-&":
        assert character in GLYPHS
    lines = text_lines("Jone", 10.0, Point2D(0.0, 0.0), 0.0)
    xs = [p.x for line in lines for p in line]
    ys = [p.y for line in lines for p in line]
    # Centred both ways, capitals 10 tall.
    assert min(xs) == pytest.approx(-max(xs), abs=0.5)
    assert max(ys) == pytest.approx(5.0) and min(ys) == pytest.approx(-5.0)
    assert text_width("AB") > text_width("A")
    with pytest.raises(GeometryException, match="no glyph"):
        text_lines("Jöne", 10.0, Point2D(0.0, 0.0), 0.0)


def test_lettering_turned_90_reads_across_the_headstock() -> None:
    lines = text_lines("AB", 10.0, Point2D(-30.0, 0.0), 90.0)
    points = [p for line in lines for p in line]
    # Across the neck (along Y), the letters' tops toward the tip (-X).
    assert max(p.y for p in points) - min(p.y for p in points) > 10.0
    assert min(p.x for p in points) == pytest.approx(-35.0)
    assert max(p.x for p in points) == pytest.approx(-25.0)


def test_the_headstock_gets_its_lettering_on_its_face() -> None:
    parameters = replace(Prototype001Parameters(), headstock_engraving_text="Jone")
    geometry = parameters.build()
    lettering = geometry.headstock_engraving
    assert lettering is not None and lettering.depth == 1.0
    face = geometry.headstock.plan.boundary
    for line in lettering.lines:
        for p in line:
            assert point_in_polygon(p, face)
            assert p.x < -geometry.headstock.nut_seat_length
    assert Prototype001Parameters().build().headstock_engraving is None


@pytest.mark.parametrize(
    ("changes", "problem"),
    [
        ({"headstock_engraving_text": "JONE LAPPI"}, "runs off the face"),
        ({"headstock_engraving_x": -55.0, "headstock_engraving_y": 15.0}, "tuner hole"),
        ({"headstock_engraving_x": -8.0}, "nut's seat"),
        ({"headstock_engraving_text": "Jöne"}, "no glyph"),
    ],
)
def test_lettering_that_does_not_fit_is_refused(
    changes: dict[str, object], problem: str
) -> None:
    parameters = replace(
        Prototype001Parameters(),
        **{"headstock_engraving_text": "Jone", **changes},  # type: ignore[arg-type]
    )
    with pytest.raises(NeckGeometryError, match=problem):
        parameters.build()


@pytest.mark.parametrize("blank", ["solid", "laminated"])
def test_the_lettering_is_engraved_right_after_the_face(blank: str) -> None:
    geometry = replace(
        Prototype001Parameters(), headstock_engraving_text="Jone"
    ).build()
    plan = plan_neck_machining(geometry, NeckMachiningParameters(blank=blank))
    names = [setup.name for setup in plan.setups]

    face = "Neck_top" if blank == "solid" else "Headstock_top"
    assert names[names.index(face) + 1] == "Headstock_engraving"
    assert len(plan.preview_outlines) == len(plan.setups)
    (setup,) = [s for s in plan.setups if s.name == "Headstock_engraving"]
    (path,) = setup.toolpaths
    # 1 mm into the face, which falls away along the angled headstock.
    lettering = geometry.headstock_engraving
    assert lettering is not None
    deepest_face = min(
        geometry.headstock.top_z(p.x, p.y) for line in lettering.lines for p in line
    )
    assert path.deepest_z() == pytest.approx(deepest_face - 1.0, abs=0.01)


def test_the_editor_and_freecad_show_the_lettering() -> None:
    editor = headstock_editor_layout(
        {"prototype": {"headstock_engraving_text": "Jone"}}
    )
    assert editor["lettering"]["lines"] and editor["lettering"]["problem"] is None
    wide = headstock_editor_layout(
        {"prototype": {"headstock_engraving_text": "JONE LAPPI"}}
    )
    assert "runs off the face" in wide["lettering"]["problem"]
    assert headstock_editor_layout({"prototype": {}})["lettering"] is None

    geometry = replace(
        Prototype001Parameters(), headstock_engraving_text="Jone"
    ).build()
    script = FreeCADScriptExporter().render_prototype001(geometry)
    assert "HeadstockLettering" in script


@pytest.mark.parametrize("font", ["sans", "script", "gothic"])
def test_every_font_sets_a_name_its_capitals_the_height_asked(font: str) -> None:
    from cncguitarwizard.geometry.lettering import FONTS

    lines = text_lines("H", 10.0, Point2D(0.0, 0.0), 0.0, font)
    ys = [p.y for line in lines for p in line]
    # The capital H is exactly the height, centred on the centre.
    assert max(ys) - min(ys) == pytest.approx(10.0, abs=0.2)
    assert (max(ys) + min(ys)) / 2.0 == pytest.approx(0.0, abs=0.2)
    if font != "sans":
        # The converted fonts have the Nordic letters too.
        assert text_lines("Jöne Läppi Å", 10.0, Point2D(0.0, 0.0), 0.0, font)
        assert all(c in FONTS[font].glyphs for c in "äöåÄÖÅ")


def test_an_unknown_font_is_refused() -> None:
    with pytest.raises(GeometryException, match="Unknown lettering font"):
        text_lines("Jone", 10.0, Point2D(0.0, 0.0), 0.0, "comic")


def test_the_headstock_takes_a_script_or_gothic_name() -> None:
    for font in ("script", "gothic"):
        geometry = replace(
            Prototype001Parameters(),
            headstock_engraving_text="Jone",
            headstock_engraving_font=font,  # type: ignore[arg-type]
        ).build()
        assert geometry.headstock_engraving is not None
        assert geometry.headstock_engraving.lines
