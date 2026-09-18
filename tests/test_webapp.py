"""Tests for the browser (Pyodide) glue module."""

import json
from pathlib import Path

from cncguitarwizard.webapp import (
    advance_build,
    finish_build,
    parameter_schema,
    run_build,
    start_build,
)


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
        "advanced": False,
    }
    assert prototype_fields["fret_count"]["type"] == "int"
    assert prototype_fields["body_pot_offsets"] == {
        "name": "body_pot_offsets",
        "type": "json",
        "default": [[180.8, 86.0], [220.8, 87.0]],
        "advanced": True,
    }
    assert prototype_fields["inlay_style"] == {
        "name": "inlay_style",
        "type": "choice",
        "default": "barbed_wire",
        "advanced": False,
        "options": ["barbed_wire", "dot", "block"],
    }
    bridge = prototype_fields["body_bridge"]
    assert bridge["type"] == "variant"
    assert bridge["default"]["kind"] == "kahler_7300"
    assert bridge["default"]["baseplate_depth"] == 25.0
    assert set(bridge["variants"]) == {
        "kahler_7300", "floyd_rose", "tune_o_matic", "hardtail"
    }
    assert bridge["variants"]["floyd_rose"]["label"].startswith("Floyd Rose")
    floyd_fields = {f["name"]: f for f in bridge["variants"]["floyd_rose"]["fields"]}
    assert "kind" not in floyd_fields
    assert floyd_fields["pivot_stud_spacing"] == {
        "name": "pivot_stud_spacing",
        "type": "float",
        "default": 73.91,
        "advanced": False,
    }
    assert floyd_fields["cover_depth"]["advanced"] is True
    kahler_fields = bridge["variants"]["kahler_7300"]["fields"]
    assert all(f["advanced"] is False for f in kahler_fields)
    assert prototype_fields["scale_length"]["advanced"] is False
    assert prototype_fields["fretboard_nut_corner_radius"]["advanced"] is True
    assert bridge["advanced"] is False
    assert prototype_fields["headstock_style"]["type"] == "choice"
    assert prototype_fields["headstock_style"]["options"] == [
        "3+3", "6_inline", "6_inline_reverse", "4+2", "2+4"
    ]
    assert prototype_fields["headstock_style"]["advanced"] is False
    assert prototype_fields["headstock_tip_width"]["type"] == "optional_float"
    assert floyd_fields["treble_side"]["type"] == "choice"
    assert floyd_fields["treble_side"]["options"] == ["+y", "-y"]
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
                "body_pot_offsets": [[180.8, 86.0]],
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
    assert "Neck_back_finish.nc" in result["files"]
    assert result["plan_view"].startswith("<svg")
    assert "Pot 2 shaft hole" not in result["files"]["Body_top.nc"]
    json.dumps(result)


def test_run_build_accepts_a_bridge_spec_as_json(tmp_path: Path) -> None:
    result = run_build(
        {
            "prototype": {
                "body_bridge": {"kind": "tune_o_matic", "compensation": 2.0},
            }
        },
        str(tmp_path),
    )

    assert "error" not in result
    assert result["report"]["parameters"]["body_bridge"]["kind"] == "tune_o_matic"
    assert result["report"]["parameters"]["body_bridge"]["compensation"] == 2.0
    assert "(-- Bridge post bass --)" in result["files"]["Body_top.nc"]


def test_run_build_rejects_an_unknown_bridge_kind(tmp_path: Path) -> None:
    result = run_build({"prototype": {"body_bridge": {"kind": "banjo"}}}, str(tmp_path))

    assert "Unknown bridge kind" in result.get("error", "")


def test_stepwise_build_reports_progress_between_stages(tmp_path: Path) -> None:
    started = start_build({"prototype": {}, "machining": {}}, str(tmp_path))

    assert started["stages"][0] == "Building the geometry"
    assert len(started["stages"]) == 6
    first = advance_build()
    assert first == {
        "completed": 1,
        "total": 6,
        "done": False,
        "next": "Planning the body toolpaths",
    }
    assert finish_build() == {"error": "The build has not finished."}
    step = first
    while not step["done"]:
        step = advance_build()
    assert step["completed"] == 6 and step["next"] is None
    result = finish_build()
    assert "Body_top.nc" in result["files"] and result["plan_view"].startswith("<svg")
    assert advance_build() == {"error": "No build has been started."}


def test_stepwise_build_surfaces_stage_errors(tmp_path: Path) -> None:
    started = start_build({"prototype": {"fret_count": 22}}, str(tmp_path))

    assert "stages" in started
    step = advance_build()
    assert "TrussRodGeometryError" in step["error"]
    assert advance_build() == {"error": "No build has been started."}


def test_start_build_rejects_bad_parameters_immediately(tmp_path: Path) -> None:
    started = start_build({"prototype": {"nope": 1}}, str(tmp_path))
    assert "TypeError" in started["error"]


def test_run_build_reports_rejected_parameters(tmp_path: Path) -> None:
    result = run_build({"prototype": {"headstock_thickness": 5.0}}, str(tmp_path))

    assert set(result) == {"error"}
    assert "GeometryError" in result["error"]


def test_run_build_reports_unknown_fields(tmp_path: Path) -> None:
    result = run_build({"prototype": {"no_such_field": 1.0}}, str(tmp_path))

    assert "TypeError" in result["error"]
