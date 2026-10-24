"""Tests for the FreeCAD script that measures the finished model."""

import ast
import json

from cncguitarwizard.backends.freecad import (
    MEASURE_SCRIPT_NAME,
    read_measured,
    render_model_measure,
)
from cncguitarwizard.backends.freecad.measure import MEASURED_PREFIX


def test_the_script_opens_the_model_and_reads_the_step_back() -> None:
    source = render_model_measure()

    ast.parse(source)
    assert MEASURE_SCRIPT_NAME == "Prototype001_check.py"
    assert 'App.openDocument(os.path.join(FOLDER, "Prototype001.FCStd"))' in source
    assert 'Part.read(os.path.join(FOLDER, "Prototype001.step"))' in source
    assert 'document.getObject("Parameters")' in source
    # The parts the STEP and the other 3D formats hold: solids shown.
    assert 'part.isDerivedFrom("Part::Feature")' in source
    assert "and part.Shape.Solids" in source
    assert f"{MEASURED_PREFIX!r}" in source


def test_the_last_measured_line_is_read_among_freecads_own() -> None:
    first = {"parts": {}, "step": {}, "sheet": False}
    last = {"parts": {"Body": {}}, "step": {}, "sheet": True}
    stdout = "\n".join(
        [
            "FreeCAD 1.1, Libs: 1.1",
            MEASURED_PREFIX + json.dumps(first),
            "Exiting",
            MEASURED_PREFIX + json.dumps(last),
        ]
    )

    assert read_measured(stdout) == last


def test_nothing_that_reads_is_none() -> None:
    assert read_measured("") is None
    assert read_measured("FreeCAD 1.1\nExiting") is None
    assert read_measured(MEASURED_PREFIX + "{broken") is None
    assert read_measured(MEASURED_PREFIX + "[1, 2]") is None
