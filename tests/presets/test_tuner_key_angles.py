"""Tests for the tuners' keys turned in their holes (``tuner_key_angles``)."""

import math
from dataclasses import replace
from pathlib import Path

import pytest

from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.render.preview3d import detail_parts
from cncguitarwizard.webapp import headstock_editor_layout, parameter_schema

GUITAR = Prototype001Parameters()
TURNED = (30.0, -20.0, 0.0, 0.0, 90.0, 0.0)


def test_every_key_points_straight_out_unless_turned() -> None:
    assert GUITAR.key_angles() == (0.0,) * 6
    assert replace(GUITAR, tuner_key_angles=TURNED).key_angles() == TURNED
    # A headless neck has no tuners to turn.
    headless = replace(GUITAR, headless=True, tuner_key_angles=(5.0,))
    assert headless.key_angles() == ()


@pytest.mark.parametrize(
    ("angles", "match"),
    [
        ((10.0,), "has 6 tuners; tuner_key_angles gives 1"),
        ((91.0, 0.0, 0.0, 0.0, 0.0, 0.0), "at most 90 degrees"),
        ((math.nan,) * 6, "finite"),
    ],
)
def test_angles_that_do_not_fit_the_tuners_are_refused(
    angles: tuple[float, ...], match: str
) -> None:
    with pytest.raises(NeckGeometryError, match=match):
        replace(GUITAR, tuner_key_angles=angles).build(wired=False)


def test_the_3d_preview_turns_each_key_toward_the_tip() -> None:
    # On a flat headstock the posts stand straight up, so the buttons'
    # reach shows in plan: 26 mm from the post to the button's middle,
    # 6.5 mm round it, the gear's housing 9 mm round the post.
    flat = replace(GUITAR, headstock_angle=0.0)
    centres = flat.tuner_centres()
    nearest_tip = min(x for _, x, _ in centres)
    widest = max(abs(y) for _, _, y in centres)

    def plan_extent(parameters: Prototype001Parameters) -> tuple[float, float]:
        (tuners,) = detail_parts(parameters.build(wired=False), parameters, "headstock")
        p = tuners.positions
        return min(p[0::3]), max(abs(y) for y in p[1::3])

    tip_end, across = plan_extent(flat)
    assert tip_end == pytest.approx(nearest_tip - 9.0, abs=0.5)
    assert across == pytest.approx(widest + 26.0 + 6.5, abs=0.5)
    tip_end, across = plan_extent(replace(flat, tuner_key_angles=(90.0,) * 6))
    assert tip_end == pytest.approx(nearest_tip - 26.0 - 6.5, abs=0.5)
    assert across == pytest.approx(widest + 9.0, abs=0.5)


def test_the_editor_turns_the_keys_and_writes_their_angles() -> None:
    def keys(values: dict[str, object]) -> list[float]:
        layout = headstock_editor_layout({"prototype": values})
        return [hole["key"] for hole in layout["holes"]]

    assert keys({}) == [0.0] * 6
    assert keys({"tuner_key_angles": list(TURNED)}) == list(TURNED)
    layout = headstock_editor_layout({"prototype": {"tuner_key_angles": [5.0]}})
    assert "tuner_key_angles gives 1" in layout["error"]
    script = (Path(__file__).resolve().parents[2] / "site" / "app.js").read_text(
        encoding="utf-8"
    )
    # A key dragged round its post is written back, none while all point
    # straight out; Start over puts them all straight out again.
    assert 'key.addEventListener("pointerdown", (event) => this.startKeyTurn(' in script
    assert "angles.some((angle) => angle !== 0) ? angles : []" in script
    assert "    bodyEditor.setField(keys, []);\n" in script
    # As the holes, when the style or its tuner settings change by hand.
    assert "const { holes, keys } = headstockEditor.inputs();" in script


def test_the_field_is_in_the_form_and_a_neck_template_resets_it() -> None:
    schema = parameter_schema()
    names = {
        field["name"] for group in schema["prototype"] for field in group["fields"]
    }
    assert "tuner_key_angles" in names
    for template in schema["neck_templates"].values():
        assert (
            "tuner_key_angles" in template["resets"]
            or "tuner_key_angles" in template["values"]
        )
