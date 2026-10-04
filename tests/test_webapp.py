"""Tests for the browser (Pyodide) glue module."""

import json
from pathlib import Path

import pytest

from cncguitarwizard.webapp import (
    advance_build,
    body_editor_layout,
    finish_build,
    headstock_editor_layout,
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
    scale = dict(prototype_fields["scale_length"])
    # Every field explains itself (see test_every_form_field_explains_itself).
    assert scale.pop("help").startswith("The scale:")
    assert scale == {
        "name": "scale_length",
        "type": "float",
        "default": 609.6,
        "advanced": False,
    }
    assert prototype_fields["fret_count"]["type"] == "int"
    shape = prototype_fields["body_shape"]
    assert shape["type"] == "variant" and shape["advanced"] is False
    # The form's body is always drawn: the Design by Jone template.
    assert shape["default"]["kind"] == "your_design"
    assert len(shape["default"]["control_points"]) == 64
    assert set(shape["variants"]) == {"your_design"}
    assert shape["variants"]["your_design"]["label"].startswith("Your design")
    strat_fields = {f["name"]: f for f in shape["variants"]["your_design"]["fields"]}
    assert strat_fields["control_points"]["type"] == "json"
    assert len(strat_fields["control_points"]["default"]) == 42
    assert strat_fields["pot_offsets"].pop("help")
    assert strat_fields["pot_offsets"] == {
        "name": "pot_offsets",
        "type": "json",
        "default": [[180.8, 86.0], [220.8, 87.0]],
        "advanced": True,
    }
    assert prototype_fields["inlay_style"].pop("help")
    assert prototype_fields["inlay_style"] == {
        "name": "inlay_style",
        "type": "choice",
        "default": "barbed_wire",
        "advanced": False,
        "options": [
            "barbed_wire",
            "dot",
            "block",
            "trapezoid",
            "sharktooth",
            "parallelogram",
            "diamond",
            "split_block",
        ],
        "labels": prototype_fields["inlay_style"]["labels"],
    }
    assert prototype_fields["inlay_style"]["labels"]["trapezoid"] == (
        "Trapezoids (Les Paul)"
    )
    bridge = prototype_fields["body_bridge"]
    assert bridge["type"] == "variant"
    assert bridge["default"]["kind"] == "kahler_7300"
    assert bridge["default"]["baseplate_depth"] == 25.0
    assert set(bridge["variants"]) == {
        "kahler_7300",
        "floyd_rose",
        "tune_o_matic",
        "hardtail",
        "headless",
    }
    assert bridge["variants"]["floyd_rose"]["label"].startswith("Floyd Rose")
    floyd_fields = {f["name"]: f for f in bridge["variants"]["floyd_rose"]["fields"]}
    assert "kind" not in floyd_fields
    assert floyd_fields["pivot_stud_spacing"].pop("help")
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
        "3+3",
        "6_inline",
        "6_inline_reverse",
        "4+2",
        "2+4",
        "2+2",
        "4_inline",
        "4_inline_reverse",
        "4+1",
        "1+4",
        "3+2",
        "2+3",
        "5_inline",
        "5_inline_reverse",
        "4+3",
        "3+4",
        "7_inline",
        "7_inline_reverse",
        "4+4",
        "8_inline",
        "8_inline_reverse",
    ]
    assert bridge["variants"]["kahler_7300"]["max_strings"] == 6
    assert bridge["variants"]["hardtail"]["max_strings"] is None
    assert prototype_fields["body_pickups"]["options"] == [
        "HH",
        "HSH",
        "HSS",
        "H",
        "SSS",
        "SS",
        "PJ",
        "JJ",
        "P",
        "MM",
        "RR",
        "custom",
    ]
    assert prototype_fields["body_pickups"]["advanced"] is False
    assert prototype_fields["body_neck_pickup"]["advanced"] is True
    assert prototype_fields["body_middle_pickup_offset"]["type"] == "optional_float"
    assert prototype_fields["body_neck_pickup"]["options"] == [
        "humbucker",
        "single_coil",
        "jazz_bass",
        "precision_bass",
        "bass_soapbar",
        "rickenbacker",
        "none",
    ]
    assert prototype_fields["string_count"]["advanced"] is False
    # The instrument is chosen above the form, with its own defaults.
    assert "instrument" not in prototype_fields
    assert set(schema["instruments"]) == {
        "electric_guitar",
        "seven_string_guitar",
        "eight_string_guitar",
        "bass_guitar",
        "five_string_bass",
        "headless_guitar",
        "headless_bass",
    }
    assert schema["instruments"]["five_string_bass"]["label"] == "5-string bass"
    assert schema["instruments"]["headless_bass"]["label"] == "Headless bass"
    eight = schema["instruments"]["eight_string_guitar"]
    assert eight["label"] == "8-string guitar"
    assert eight["overrides"]["body_bridge"] == {
        **eight["overrides"]["body_bridge"],
        "kind": "hardtail",
        "string_count": 8,
    }
    bass = schema["instruments"]["bass_guitar"]
    assert bass["label"] == "Bass guitar"
    assert bass["overrides"]["string_count"] == 4
    assert bass["overrides"]["body_bridge"]["kind"] == "hardtail"
    assert bass["overrides"]["body_shape"]["kind"] == "your_design"
    assert schema["instruments"]["electric_guitar"]["overrides"] == {}
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
                "body_shape": {
                    "kind": "design_by_jone",
                    "pot_offsets": [[180.8, 86.0]],
                },
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

    assert "Unknown bridge or body shape kind" in result.get("error", "")


def test_stepwise_build_reports_progress_between_stages(tmp_path: Path) -> None:
    started = start_build({"prototype": {}, "machining": {}}, str(tmp_path))

    assert started["stages"][0] == "Building the geometry"
    assert len(started["stages"]) == 7
    first = advance_build()
    assert first == {
        "completed": 1,
        "total": 7,
        "done": False,
        "next": "Planning the body toolpaths",
    }
    assert finish_build() == {"error": "The build has not finished."}
    step = first
    while not step["done"]:
        step = advance_build()
    assert step["completed"] == 7 and step["next"] is None
    result = finish_build()
    assert "Body_top.nc" in result["files"] and result["plan_view"].startswith("<svg")
    assert advance_build() == {"error": "No build has been started."}


def test_stepwise_build_surfaces_stage_errors(tmp_path: Path) -> None:
    # A 440 mm rod does not fit a 22-fret neck.
    started = start_build(
        {"prototype": {"fret_count": 22, "truss_rod_length": 440.0}}, str(tmp_path)
    )

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


def test_body_editor_layout_lists_the_fixed_features_relative_to_the_heel() -> None:
    layout = body_editor_layout({"prototype": {"body_shape": {"kind": "your_design"}}})

    assert layout["samples_per_segment"] == 8
    templates = layout["templates"]
    assert list(templates) == [
        "design_by_jone",
        "les_paul",
        "stratocaster",
        "jackson_rr",
        "jazz_bass",
    ]
    assert templates["les_paul"]["label"] == "Les Paul style (mockup, not the original)"
    assert templates["stratocaster"]["label"] == (
        "Stratocaster style (mockup, not the original)"
    )
    # The Stratocaster template is traced from a reference drawing (76
    # points); a new drawing still starts from the 42-point default.
    strat_points = templates["stratocaster"]["shape"]["control_points"]
    assert len(strat_points) == 76 and strat_points != layout["start_points"]
    assert len(templates["design_by_jone"]["shape"]["control_points"]) == 64
    # The Jackson RR is a mockup too, its switch moved onto the bass wing.
    assert templates["jackson_rr"]["label"] == (
        "Jackson RR style (mockup, not the original)"
    )
    rr = templates["jackson_rr"]["shape"]
    assert len(rr["control_points"]) == 64
    assert rr["switch_cavity_y"] < 0.0 < min(y for _, y in rr["pot_offsets"])
    assert templates["jazz_bass"]["label"] == (
        "Jazz Bass style (mockup, not the original)"
    )
    assert len(templates["jazz_bass"]["shape"]["control_points"]) == 76
    assert len(layout["start_points"]) == 42
    roles = {polygon["name"]: polygon["role"] for polygon in layout["polygons"]}
    assert roles["Neck pocket"] == "pocket"
    assert roles["Neck pickup route"] == "pickup"
    assert roles["Control cavity"] == "rear"
    assert roles["Switch cavity cover recess"] == "cover"
    pocket = next(p for p in layout["polygons"] if p["name"] == "Neck pocket")
    # The pocket ends at the heel end, the editor's X = 0.
    assert max(x for x, _ in pocket["points"]) == pytest.approx(0.0, abs=0.01)
    names = {circle["name"] for circle in layout["circles"]}
    assert {"Switch shaft hole", "Pot 1 shaft hole"} <= names
    # The jack of the drawn body sits at its own placement.
    # The jack starts on the outline, where its line meets it near 284 mm.
    assert layout["jack"]["x"] == pytest.approx(284.0, abs=2.0)
    # Draggable groups: electronics and pickups move, neck and bridge do not.
    groups = {p["name"]: p["group"] for p in layout["polygons"]}
    assert groups["Control cavity"] == "control"
    assert groups["Control cavity cover recess"] == "control"
    assert groups["Switch cavity"] == "switch"
    assert groups["Neck pickup route"] == "pickup:neck"
    assert groups["Neck pocket"] is None and groups["Neck"] is None
    assert groups["Bridge baseplate cutout"] is None
    circle_groups = {c["name"]: c["group"] for c in layout["circles"]}
    assert circle_groups["Pot 2 shaft hole"] == "pot:1"
    assert circle_groups["Switch shaft hole"] == "switch"
    assert circle_groups["Bridge pickup bass screw recess"] == "pickup:bridge"
    assert layout["jack"]["group"] == "jack"
    json.dumps(layout)


def test_body_editor_layout_follows_the_bridge_and_reports_errors() -> None:
    floyd = body_editor_layout({"prototype": {"body_bridge": {"kind": "floyd_rose"}}})
    assert any(p["name"] == "Floyd Rose recess" for p in floyd["polygons"])
    assert any(c["name"] == "Pivot stud" for c in floyd["circles"])
    assert "TypeError" in body_editor_layout({"prototype": {"nope": 1}})["error"]


def test_run_build_makes_a_bass(tmp_path: Path) -> None:
    result = run_build(
        {"prototype": {"instrument": "bass_guitar", **_bass_overrides()}},
        str(tmp_path),
    )

    assert "error" not in result
    assert result["report"]["parameters"]["string_count"] == 4
    top = result["files"]["Body_top.nc"]
    assert "(-- Neck pickup route --)" in top and "(-- Bridge pickup route --)" in top
    assert "String 4 through hole" in result["files"]["Body_top_small_holes.nc"]
    assert "String 5 through hole" not in result["files"]["Body_top_small_holes.nc"]


def _bass_overrides() -> dict[str, object]:
    return parameter_schema()["instruments"]["bass_guitar"]["overrides"]


def test_headstock_editor_layout_gives_fitted_edges_and_the_holes(
    tmp_path: Path,
) -> None:
    layout = headstock_editor_layout({"prototype": {"headstock_style": "4+2"}})

    assert layout["nut_half_width"] == 21.0
    assert layout["bass_sign"] == -1.0
    assert layout["min_edge_distance"] == 15.0
    for side in ("bass", "treble"):
        edge = layout["start_edges"][side]
        assert len(edge) == 10 and edge[0][0] == 22.5 and edge[1][0] == 45.0
        assert edge[-1][0] == 150.0
    assert len(layout["holes"]) == 6
    assert {hole["side"] for hole in layout["holes"]} == {"bass", "treble"}
    # The drawn start edges build as they are.
    built = run_build(
        {
            "prototype": {
                "headstock_style": "4+2",
                "headstock_outline": "drawn",
                "headstock_bass_edge": layout["start_edges"]["bass"],
                "headstock_treble_edge": layout["start_edges"]["treble"],
            }
        },
        str(tmp_path),
    )
    assert "error" not in built
    json.dumps(layout)


def test_body_editor_layout_moves_the_middle_pickup_as_its_own_group() -> None:
    layout = body_editor_layout({"prototype": {"body_pickups": "HSH"}})
    groups = {p["name"]: p["group"] for p in layout["polygons"]}

    assert groups["Middle pickup route"] == "pickup:middle"
    assert {c["group"] for c in layout["circles"]} >= {"pickup:middle"}


def test_the_control_layout_is_a_basic_choice_and_shows_in_the_editor() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    assert fields["body_controls"]["advanced"] is False
    assert fields["body_controls"]["labels"]["gibson_4"].startswith("Gibson")
    assert fields["body_controls"]["options"] == [
        "almond_2",
        "gibson_4",
        "rear_3",
        "tele",
        "pickguard",
        "none",
    ]

    tele = body_editor_layout({"prototype": {"body_controls": "tele"}})
    roles = {p["name"]: (p["role"], p["group"]) for p in tele["polygons"]}
    assert roles["Control plate recess"] == ("top_control", "control")
    assert roles["Control cavity"] == ("top_control", "control")
    screws = [c for c in tele["circles"] if c["name"].startswith("Control plate")]
    assert len(screws) == 2 and all(c["group"] == "control" for c in screws)

    gibson = body_editor_layout({"prototype": {"body_controls": "gibson_4"}})
    marks = [c for c in gibson["circles"] if "cover screw" in c["name"]]
    assert len(marks) == 7 and all(c.get("rear") for c in marks)


def test_edge_finishes_are_basic_fields_and_contours_show_in_the_editor() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    for name in (
        "body_top_edge_radius",
        "body_back_edge_radius",
        "body_top_binding_width",
        "body_arm_contour_depth",
        "body_belly_cut_depth",
    ):
        assert fields[name]["advanced"] is False
        assert fields[name]["default"] == 0.0
    assert fields["body_arm_contour_width"]["advanced"] is True

    layout = body_editor_layout(
        {
            "prototype": {
                "body_shape": {"kind": "your_design"},
                "body_arm_contour_depth": 12.0,
                "body_belly_cut_depth": 10.0,
            }
        }
    )
    roles = {p["name"]: p["role"] for p in layout["polygons"]}
    assert roles["Arm contour"] == "contour_top"
    assert roles["Belly cut"] == "contour_back"
    assert layout["widening"] == 0.0


def test_the_multiscale_fields_sit_with_the_scale() -> None:
    groups = {
        field["name"]: group["title"]
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    for name in ("bass_scale_length", "perpendicular_fret", "fret_slant_angle"):
        assert groups[name] == "Scale and fretboard"


def test_the_post_processor_is_a_basic_choice_with_readable_names() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["machining"]
        for field in group["fields"]
    }
    choice = fields["post_processor"]
    assert choice["advanced"] is False and choice["default"] == "grbl"
    assert choice["options"] == [
        "grbl",
        "linuxcnc",
        "mach3",
        "marlin",
        "fanuc",
        "kosy",
    ]
    assert choice["labels"]["mach3"] == "Mach3 / Mach4 / UCCNC"
    assert fields["spindle_dwell"]["default"] == 0.0


def test_the_pickup_selector_is_a_basic_choice() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    choice = fields["body_switch"]
    assert choice["advanced"] is False and choice["default"] == "toggle"
    assert choice["options"] == ["toggle", "micro"]
    assert choice["labels"]["micro"].startswith("Micro")


def test_the_neck_blank_is_a_basic_machining_choice() -> None:
    fields = {
        field["name"]: field
        for group in parameter_schema()["machining"]
        for field in group["fields"]
    }
    choice = fields["neck_blank"]
    assert choice["advanced"] is False and choice["default"] == "solid"
    assert choice["options"] == ["solid", "laminated"]
    assert choice["labels"]["laminated"].startswith("Neck plank first")


def test_body_editor_layout_gives_the_control_cavity_stretch_handles() -> None:
    def control(**shape: object) -> dict[str, object]:
        layout = body_editor_layout(
            {
                "prototype": {
                    "body_controls": "gibson_4",
                    "body_shape": {"kind": "your_design", **shape},
                }
            }
        )
        return layout["control"]

    plain = control()
    assert plain["axis"] == [1.0, 0.0]
    (x0, y0), (x1, y1) = plain["ends"]
    # The ends of the 90 mm cover, either side of the centre.
    assert x1 - x0 == pytest.approx(90.0)
    assert (x0 + x1) / 2 == pytest.approx(plain["centre"][0])
    stretched = control(control_stretch=20.0)
    (sx0, _), (sx1, _) = stretched["ends"]
    assert (sx0, sx1) == pytest.approx((x0 - 10.0, x1 + 10.0))
    # The sides of the 82 mm wide cover, square to the axis.
    (_, side0), (_, side1) = plain["sides"]
    assert side1 - side0 == pytest.approx(82.0)
    (_, wide0), (_, wide1) = control(control_stretch_across=8.0)["sides"]
    assert wide1 - wide0 == pytest.approx(90.0)
    no_controls = body_editor_layout({"prototype": {"body_controls": "none"}})
    assert no_controls["control"] is None


def test_schema_lists_each_pickup_layouts_types() -> None:
    layouts = parameter_schema()["pickup_configurations"]

    # The body editor turns a layout into "custom" to drop one pickup.
    assert layouts["HH"] == ["humbucker", "none", "humbucker"]
    assert layouts["RR"] == ["rickenbacker", "none", "rickenbacker"]
    assert "custom" not in layouts


def test_the_nc_programs_download_as_one_zip_named_for_the_guitar(
    tmp_path: Path,
) -> None:
    import base64
    import io
    import zipfile

    from cncguitarwizard.webapp import archive_name, nc_archive, run_build

    assert archive_name("Jone / #1") == "Jone-1"
    assert archive_name("Läpikaula 2026") == "Läpikaula 2026"
    assert archive_name("  ") == "cncguitarwizard"
    result = run_build({"prototype": {}}, str(tmp_path))
    archive = nc_archive("Jonen Strat")
    assert archive["name"] == "Jonen Strat.zip"
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(archive["data"]))) as zipped:
        names = zipped.namelist()
        programs = [name for name in result["files"] if name.endswith(".nc")]
        # Every program, in a folder a part, numbered in running order.
        assert len(names) == len(programs) + 1
        assert "Jonen Strat/README.txt" in names
        assert "Jonen Strat/Body/01_Body_index_pins.nc" in names
        assert "Jonen Strat/Neck/01_Neck_index_pins.nc" in names
        assert (
            zipped.read("Jonen Strat/Body/01_Body_index_pins.nc").decode()
            == (result["files"]["Body_index_pins.nc"])
        )
        readme = zipped.read("Jonen Strat/README.txt").decode()
        assert readme.index("Body:") < readme.index("Neck:")


def test_every_form_field_explains_itself() -> None:
    from cncguitarwizard.webapp import _focus, _mentions

    schema = parameter_schema()
    seen: dict[str, str] = {}

    def walk(fields: list[dict[str, object]], prefix: str = "") -> None:
        for field in fields:
            seen[prefix + str(field["name"])] = str(field.get("help", ""))
            for kind, variant in dict(field.get("variants", {})).items():  # type: ignore[call-overload]
                walk(variant["fields"], f"{prefix}{field['name']}.{kind}.")

    for key in ("prototype", "machining"):
        for group in schema[key]:
            walk(group["fields"])
    assert all(seen.values()), [name for name, text in seen.items() if not text]
    # Plain words up front; the code's own documentation for the rest.
    assert "from the nut to the bridge saddles" in seen["scale_length"]
    assert seen["tool_diameter"] == "Cutting diameter of the end mill."
    assert "pocket" in seen["truss_rod_pocket_depth"]
    assert "Jack bore start Y" in seen["body_shape.your_design.jack_y"]
    assert all(len(text) <= 900 for text in seen.values())
    # A wildcard names its group, but body_* alone is too wide to.
    assert _mentions("a step (truss_rod_step_*)", "truss_rod_step_depth")
    assert _mentions("body_*_binding_width wide", "body_back_binding_width")
    assert not _mentions("see the body_* comments", "body_thickness")
    # Another field's block gives only the sentences naming the field.
    block = "Edge finishes are optional. The rim is flat. body_x is round."
    assert _focus(block, "body_x") == "body_x is round."
