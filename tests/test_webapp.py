"""Tests for the browser (Pyodide) glue module."""

import json
from pathlib import Path

from cncguitarwizard.webapp import parameter_schema, run_build


def test_schema_lists_every_parameter_with_a_form_type() -> None:
    schema = parameter_schema()

    prototype_fields = {
        field["name"]: field
        for group in schema["prototype"]
        for field in group["fields"]
    }
    assert prototype_fields["scale_length"] == {
        "name": "scale_length",
        "type": "float",
        "default": 609.6,
    }
    assert prototype_fields["fret_count"]["type"] == "int"
    stud_spacing = prototype_fields["body_bridge_pivot_stud_spacing"]
    assert stud_spacing["type"] == "optional_float"
    assert prototype_fields["body_pot_positions"] == {
        "name": "body_pot_positions",
        "type": "json",
        "default": [[642.0, 86.0], [682.0, 87.0]],
    }
    titles = [group["title"] for group in schema["prototype"]]
    assert "Body" in titles and "Headstock and tuners" in titles
    machining = {field["name"] for field in schema["machining"][0]["fields"]}
    assert {"tool_diameter", "index_pin_positions", "tab_count"} <= machining
    json.dumps(schema)


def test_run_build_returns_files_report_and_plan_view(tmp_path: Path) -> None:
    result = run_build(
        {
            "prototype": {
                "body_thickness": 42.0,
                "body_pot_positions": [[642.0, 86.0]],
            },
            "machining": {"feed_rate": 800.0},
        },
        str(tmp_path),
    )

    assert "error" not in result
    expected = {"Prototype001_freecad.py", "Body_top.nc", "Body_back.svg", "build.json"}
    assert expected <= set(result["files"])
    assert result["report"]["parameters"]["body_thickness"] == 42.0
    assert result["report"]["machining"]["feed_rate"] == 800.0
    assert result["report"]["status"] == "scripts_only"
    assert result["plan_view"].startswith("<svg")
    assert "Pot 2 shaft hole" not in result["files"]["Body_top.nc"]
    json.dumps(result)


def test_run_build_reports_rejected_parameters(tmp_path: Path) -> None:
    result = run_build({"prototype": {"headstock_thickness": 5.0}}, str(tmp_path))

    assert set(result) == {"error"}
    assert "GeometryError" in result["error"]


def test_run_build_reports_unknown_fields(tmp_path: Path) -> None:
    result = run_build({"prototype": {"no_such_field": 1.0}}, str(tmp_path))

    assert "TypeError" in result["error"]
