"""Tests for when a setting does anything (``setting_conditions``): a
setting the web app hides must never change the instrument."""

import hashlib
import itertools
import json
import tempfile
import typing
from dataclasses import fields, replace
from functools import cache
from pathlib import Path

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam.parameters import MachiningParameters
from cncguitarwizard.exceptions import CNCGuitarWizardError
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.setting_conditions import (
    APPLIES_WHEN,
    NOT_EMPTY,
    Condition,
    applies,
)
from cncguitarwizard.webapp import _variations, parameter_schema, run_build

DEFAULTS = Prototype001Parameters()
HINTS = typing.get_type_hints(Prototype001Parameters)
STRATOCASTER = YOUR_DESIGN_TEMPLATES["stratocaster"][1]
BASES: tuple[dict[str, object], ...] = ({}, {"body_shape": STRATOCASTER})
"""The instruments a case is built on, the next where the last does not
build it (a neck plate fits the Stratocaster's back, not the default's)."""
ROOT = Path(__file__).resolve().parent.parent


def choices(name: str) -> tuple[str | bool, ...]:
    """Return every value a choice or a switch can have."""
    if HINTS[name] is bool:
        return (True, False)
    return tuple(a for a in typing.get_args(HINTS[name]) if isinstance(a, str))


def meeting(allowed: tuple[str | bool, ...]) -> str | bool:
    """Return a value one of a condition's ``allowed`` values stands for."""
    return "AB" if allowed[0] == NOT_EMPTY else allowed[0]


def breaking(name: str, allowed: tuple[str | bool, ...]) -> list[str | bool]:
    """Return the values of setting ``name`` a condition does not allow."""
    if NOT_EMPTY in allowed:
        return [""]
    return [value for value in choices(name) if value not in allowed]


def failing(conditions: tuple[Condition, ...]) -> list[dict[str, object]]:
    """Return the ways to meet none of ``conditions``: one alone breaks
    each setting it names in turn, the others met; several are each
    broken by one of their settings, every consistent way."""
    if len(conditions) == 1:
        (condition,) = conditions
        met = {other: meeting(allowed) for other, allowed in condition.items()}
        return [
            {**met, other: value}
            for other, allowed in condition.items()
            for value in breaking(other, allowed)
        ]
    ways = []
    for picks in itertools.product(
        *(
            [(o, v) for o, allowed in c.items() for v in breaking(o, allowed)]
            for c in conditions
        )
    ):
        values: dict[str, object] = {}
        if all(values.setdefault(other, value) == value for other, value in picks):
            ways.append(values)
    return ways


@cache
def model(values: tuple[tuple[str, object], ...]) -> str:
    """Return a fingerprint of the FreeCAD model ``values`` build."""
    geometry = replace(DEFAULTS, **dict(values)).build()
    source = FreeCADScriptExporter().render_prototype001(
        geometry, fcstd_path=Path("/m/P.FCStd"), step_path=Path("/m/P.step")
    )
    return hashlib.sha256(source.encode()).hexdigest()


def frozen(values: dict[str, object]) -> tuple[tuple[str, object], ...]:
    return tuple(sorted(values.items()))


DESIGN = {f.name for f in fields(Prototype001Parameters) if f.init}
MACHINING = {f.name for f in fields(MachiningParameters) if f.init}


def test_every_condition_names_settings_and_their_values() -> None:
    names = DESIGN

    for name, conditions in APPLIES_WHEN.items():
        assert name in DESIGN | MACHINING and conditions
        for condition in conditions:
            for other, values in condition.items():
                assert other in names and other != name
                if NOT_EMPTY in values:
                    assert HINTS[other] is str and values == (NOT_EMPTY,)
                else:
                    assert set(values) <= set(choices(other))


CASES = [
    (name, values)
    for name, conditions in APPLIES_WHEN.items()
    if name in DESIGN
    for values in failing(conditions)
]


@pytest.mark.parametrize(
    ("name", "values"),
    CASES,
    ids=[f"{name}-{'-'.join(map(str, v.values()))}" for name, v in CASES],
)
def test_a_hidden_setting_changes_nothing(name: str, values: dict[str, object]) -> None:
    # None of its conditions met: the page hides the setting, so changing
    # it must leave the model as it was. Refused only for its value, as it
    # would be where it applies, never for being set at all where it does
    # not (a hidden setting no one can see to mend).
    assert not applies(name, {**{f: getattr(DEFAULTS, f) for f in HINTS}, **values})
    for base in BASES:
        try:
            before = model(frozen({**base, **values}))
            break
        except CNCGuitarWizardError:
            continue
    else:
        pytest.skip("this combination does not build at all")
    values = {**base, **values}
    first = APPLIES_WHEN[name][0]
    met = {**base, **{other: meeting(allowed) for other, allowed in first.items()}}
    current = getattr(DEFAULTS, name)
    tried = _variations(name, current)[:2]
    if not tried and current is None and "float" in str(HINTS[name]):
        tried = [2.0]
    for changed in tried:
        try:
            after = model(frozen({**values, name: changed}))
        except CNCGuitarWizardError:
            with pytest.raises(CNCGuitarWizardError):
                model(frozen({**met, name: changed}))
            continue
        assert after == before


@cache
def programs(machining: tuple[tuple[str, object], ...]) -> str:
    """Return a fingerprint of every file a default design's build writes
    (but its report, which is dated) with ``machining``."""
    with tempfile.TemporaryDirectory() as folder:
        result = run_build({"prototype": {}, "machining": dict(machining)}, folder)
    files = {k: v for k, v in result["files"].items() if not k.endswith(".json")}
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def test_a_hidden_machining_setting_changes_no_program() -> None:
    # A feature's own cutter, the default design without the feature.
    defaults = {f: getattr(DEFAULTS, f) for f in HINTS}
    names = [name for name in APPLIES_WHEN if name in MACHINING]
    assert names
    for name in names:
        assert not applies(name, defaults)
        current = getattr(MachiningParameters(), name)
        changed = not current if isinstance(current, bool) else current * 1.5
        assert programs(((name, changed),)) == programs(())


def test_a_heel_setting_does_something_on_a_bolt_on_neck_only() -> None:
    bolted = (("neck_joint", "bolt_on"),)
    through = (("neck_joint", "neck_through"),)

    assert model(bolted) != model((*bolted, ("heel_thickness", 24.0)))
    assert model(through) == model((*through, ("heel_thickness", 24.0)))


def test_lettering_settings_wait_for_lettering() -> None:
    values = {f: getattr(DEFAULTS, f) for f in HINTS}

    assert not applies("headstock_engraving_font", values)
    assert applies(
        "headstock_engraving_font", {**values, "headstock_engraving_text": "Jone"}
    )


def test_the_page_hides_what_does_not_apply() -> None:
    schema = parameter_schema()
    script = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    page = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    layout = (ROOT / "site" / "desktop.js").read_text(encoding="utf-8")

    assert schema["applies_when"]["heel_thickness"] == [
        {"neck_joint": ["bolt_on", "set"]}
    ]
    assert schema["applies_when"]["fret_height"] == [
        {"locking_nut": ["auto", "r2", "r3", "r7", "r8"]},
        {"nut_jig": [True]},
    ]
    assert schema["any_text"] == NOT_EMPTY
    assert "function showApplicableSettings()" in script
    assert "conditions.some((condition) => Object.entries(condition)" in script
    assert 'form.addEventListener("change", showApplicableSettings);' in script
    assert ".field.not-applicable, .editor-options .not-applicable" in page
    # The neck's type heads its page, shared with the body's.
    neck = layout[layout.index("    neck: [") : layout.index("    fretboard: [")]
    assert neck.index('"neck_joint"') < neck.index('"nut_width"')
    assert '"neck_joint", "truss_rod_adjustment"' in layout
