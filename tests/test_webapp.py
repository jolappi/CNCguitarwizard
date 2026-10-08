"""Tests for the browser (Pyodide) glue module."""

import json
from pathlib import Path

import pytest

from cncguitarwizard.webapp import (
    advance_build,
    body_editor_layout,
    finish_build,
    headstock_editor_layout,
    import_outline,
    load_design,
    outline_template,
    parameter_schema,
    run_build,
    start_build,
    upgrade_design,
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
            "barbed_wire_2",
            "dot",
            "block",
            "trapezoid",
            "sharktooth",
            "parallelogram",
            "diamond",
            "split_block",
            "custom",
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
        "single_string",
    }
    assert bridge["variants"]["floyd_rose"]["label"].startswith("Floyd Rose")
    floyd_fields = {f["name"]: f for f in bridge["variants"]["floyd_rose"]["fields"]}
    assert "kind" not in floyd_fields
    assert floyd_fields["pivot_stud_spacing"].pop("help")
    # Empty: the string count's (73.91 mm for six).
    assert floyd_fields["pivot_stud_spacing"] == {
        "name": "pivot_stud_spacing",
        "type": "optional_float",
        "default": None,
        "advanced": False,
    }
    assert floyd_fields["string_count"]["advanced"] is True
    assert floyd_fields["cover_depth"]["advanced"] is True
    kahler_fields = bridge["variants"]["kahler_7300"]["fields"]
    assert [f["name"] for f in kahler_fields if f["advanced"]] == ["string_count"]
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
    assert bridge["variants"]["kahler_7300"]["max_strings"] == 8
    assert bridge["variants"]["kahler_7300"]["min_strings"] == 6
    assert bridge["variants"]["tune_o_matic"]["max_strings"] == 6
    assert bridge["variants"]["hardtail"]["max_strings"] is None
    assert bridge["variants"]["single_string"]["min_strings"] is None
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
    assert len(started["stages"]) == 8
    first = advance_build()
    assert first == {
        "completed": 1,
        "total": 8,
        "done": False,
        "next": "Planning the body toolpaths",
    }
    assert finish_build() == {"error": "The build has not finished."}
    step = first
    while not step["done"]:
        step = advance_build()
    assert step["completed"] == 8 and step["next"] is None
    result = finish_build()
    assert "Body_top.nc" in result["files"] and result["plan_view"].startswith("<svg")
    # The DXF outlines come with the files.
    assert result["files"]["Prototype001_plan.dxf"].endswith("EOF\n")
    assert "Prototype001_covers.dxf" in result["files"]
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
        "alexi_hexed",
        "mockingbird",
        "telecaster",
        "sg",
        "explorer",
        "flying_v",
        "jazz_bass",
    ]
    assert templates["mockingbird"]["label"] == (
        "Mockingbird style (mockup, not the original)"
    )
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


@pytest.mark.parametrize("style", ["3+3", "6_inline", "4+2"])
def test_an_older_designs_fitted_headstock_loads_as_drawn(style: str) -> None:
    from cncguitarwizard.presets import Prototype001Parameters

    old = {
        "format": "cncguitarwizard-design",
        "instrument": "electric_guitar",
        "prototype": {
            "headstock_style": style,
            "headstock_outline": "fitted",
            "headstock_bass_edge": [],
            "headstock_treble_edge": [],
        },
        "machining": {"feed_rate": 800.0},
    }
    upgraded = upgrade_design(old)
    # Loaded as drawn, so the headstock editor opens with its settings...
    assert upgraded["prototype"]["headstock_outline"] == "drawn"
    assert upgraded["machining"] == old["machining"]
    assert old["prototype"]["headstock_outline"] == "fitted"
    # ...and with no edges drawn the drawn outline is the fitted one.
    fitted = Prototype001Parameters(headstock_style=style, headstock_outline="fitted")
    drawn = Prototype001Parameters(headstock_style=style, headstock_outline="drawn")
    assert drawn.headstock_design() == fitted.headstock_design()


def test_a_headless_or_drawn_fitted_headstock_stays_fitted() -> None:
    def outline(instrument: str, **values: object) -> str:
        prototype = {"headstock_outline": "fitted", **values}
        design = {"instrument": instrument, "prototype": prototype}
        return str(upgrade_design(design)["prototype"]["headstock_outline"])

    assert outline("electric_guitar", headless=True) == "fitted"
    # A headless instrument's design without the field is headless too.
    assert outline("headless_guitar") == "fitted"
    edge = [[22.5, 20.0], [150.0, 30.0]]
    assert outline("electric_guitar", headstock_bass_edge=edge) == "fitted"
    assert outline("electric_guitar") == "drawn"
    assert upgrade_design({"instrument": "bass_guitar"})["prototype"] == {}


def test_a_design_saved_with_six_mm_index_pins_follows_a_wider_tool() -> None:
    old = {
        "format": "cncguitarwizard-design",
        "instrument": "electric_guitar",
        "machining": {"tool_diameter": 8.0, "index_pin_diameter": 6.0},
    }
    # 6 mm was the default: it loads empty, the dowels as wide as the tool.
    upgraded = upgrade_design(old)
    assert upgraded["machining"] == {"tool_diameter": 8.0, "index_pin_diameter": None}
    assert old["machining"]["index_pin_diameter"] == 6.0
    assert load_design(old).machining.pin_diameter == 8.0
    # Other dowels stay as saved, and a design without machining has none.
    kept = {**old, "machining": {"index_pin_diameter": 10.0}}
    assert upgrade_design(kept)["machining"] == kept["machining"]
    assert "machining" not in upgrade_design({"instrument": "bass_guitar"})


def test_a_saved_design_loads_as_the_web_app_loads_it() -> None:
    from cncguitarwizard.exceptions import CNCGuitarWizardError
    from cncguitarwizard.presets import Prototype001Parameters

    loaded = load_design(
        {
            "format": "cncguitarwizard-design",
            "name": "Seven",
            "instrument": "seven_string_guitar",
            "prototype": {
                "body_thickness": 41.0,
                "headstock_outline": "fitted",
                "inlay_dot_diameter": 5.0,
                "gone_setting": True,
                "body_bridge": {"kind": "hardtail", "string_count": 7, "old": 1},
                "body_shape": {"kind": "no_such_body"},
            },
            "machining": {
                "feed_rate": 750.0,
                "index_pin_positions": [[-40, 0], [440, 0]],
            },
        }
    )
    parameters = loaded.parameters
    assert loaded.name == "Seven"
    assert parameters.body_thickness == 41.0
    assert parameters.inlay_dot_diameter == 5.0
    # A value the file lacks is the instrument's default...
    assert parameters.string_count == 7
    assert parameters.scale_length == 647.7
    assert parameters.body_shape == Prototype001Parameters().body_shape
    # ...it is brought up to date, and the unknown settings are skipped.
    assert parameters.headstock_outline == "drawn"
    assert parameters.body_bridge.kind == "hardtail"
    assert loaded.skipped == ("gone_setting", "body_bridge.old", "body_shape.kind")
    assert loaded.machining.feed_rate == 750.0
    assert loaded.machining.index_pin_positions == ((-40, 0), (440, 0))
    with pytest.raises(CNCGuitarWizardError, match="not a CNCguitarwizard design"):
        load_design({"format": "other"})
    with pytest.raises(CNCGuitarWizardError, match="Unknown instrument 'ukulele'"):
        load_design({"format": "cncguitarwizard-design", "instrument": "ukulele"})


def test_the_headstock_editor_reports_rather_than_raises() -> None:
    # A locking nut wider than the neck, and offsets for a shorter row:
    # the editor says why instead of failing without a word.
    nut = headstock_editor_layout({"prototype": {"locking_nut": "r3"}})
    assert "nut_width must be at least" in nut["error"]
    row = headstock_editor_layout(
        {
            "prototype": {
                "headstock_style": "7_inline",
                "tuner_inline_offsets": [20, 12, 4, -4, -12, -20],
            }
        }
    )
    assert "needs 7 tuner_inline_offsets" in row["error"]
    long = headstock_editor_layout({"prototype": {"headstock_length": 400.0}})
    assert "shorten headstock_length" in long["error"]


def test_the_headstock_editor_opens_on_a_drawing_its_tuners_no_longer_fit() -> None:
    # A six-in-line reverse drawn for a 635 mm scale and a zero fret: on
    # 609.6 mm with a shelf nut the last post moves to 14.5 mm from the
    # drawn edge. With lettering on, the whole layout failed, so the
    # editor showed nothing and Start over had nothing to start over from.
    edges = {
        "headstock_bass_edge": [
            [21.5, 31.9], [44.8, 35.6], [64.8, 31.4], [83.5, 29.5],
            [106.8, 32.8], [126.4, 39.7], [145.4, 35.4], [168.7, 35.7],
            [181.6, 36.4], [185.6, 27.5], [198.9, 9.6],
        ],
        "headstock_treble_edge": [
            [22.5, 28.5], [45, 36], [63.8, 31.2], [82.5, 26.5],
            [101.2, 21.7], [120, 17], [138.8, 12.2], [157.5, 7.4],
            [176.2, 2.7], [198.9, -2.1],
        ],
    }  # fmt: skip
    layout = headstock_editor_layout(
        {
            "prototype": {
                "headstock_style": "6_inline_reverse",
                "headstock_outline": "drawn",
                "headstock_engraving_text": "ALEKSI",
                **edges,
            }
        }
    )
    assert "error" not in layout
    lettering = layout["lettering"]
    assert lettering["lines"]
    assert "14.5 mm from the drawn headstock edge" in lettering["problem"]


def test_a_neck_template_puts_back_what_another_left() -> None:
    templates = parameter_schema()["neck_templates"]
    # The Explorer places its own row of posts and has no tip points; a
    # Telecaster loaded after it must not keep that row under its outline.
    assert "tuner_inline_offsets" not in templates["explorer"]["resets"]
    assert "headstock_tip_points" in templates["explorer"]["resets"]
    assert {"tuner_inline_offsets", "tuner_inline_first_distance"} <= set(
        templates["telecaster"]["resets"]
    )
    for template in templates.values():
        assert not set(template["resets"]) & set(template["values"])


def test_the_headstock_editor_opens_on_any_drawing() -> None:
    bass = [[45.0, 30.8], [80.0, 34.0], [120.0, 27.0], [170.0, 30.0]]
    treble = [[45.0, 30.8], [95.0, 29.0], [140.0, 24.0], [170.0, 18.0]]
    drawn = {
        "headstock_outline": "drawn",
        "headstock_bass_edge": bass,
        "headstock_treble_edge": treble,
        "headstock_engraving_text": "JONE",
    }
    # The fitted outline it would start over from narrows to nothing:
    # the drawing still opens, its start edges its own.
    long = headstock_editor_layout({"prototype": {**drawn, "headstock_length": 400.0}})
    assert "error" not in long
    assert long["start_edges"]["bass"][-1] == [170.0, 30.0]
    # Edges dragged across each other (a figure eight): it opens, and
    # says where they cross.
    crossed = [[45.0, 30.8], [100.0, -40.0], [170.0, 30.0]]
    eight = headstock_editor_layout(
        {"prototype": {**drawn, "headstock_bass_edge": crossed}}
    )
    assert "error" not in eight
    assert "meet or cross" in eight["lettering"]["problem"]


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
        "superstrat",
        "volume_1",
        "active_4",
        "tele",
        "jazz_bass",
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
    back = fields["neck_back_cut"]
    assert back["advanced"] is False and back["default"] == "rough_and_finish"
    assert back["options"] == ["rough_and_finish", "ball"]
    assert back["labels"]["ball"].startswith("Ball nose alone")


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


def test_the_body_outline_goes_out_as_a_template_and_comes_back() -> None:
    import dataclasses

    from cncguitarwizard.presets import Prototype001Parameters
    from cncguitarwizard.webapp import _coerce, _jsonable

    seven = Prototype001Parameters.for_instrument("seven_string_guitar")
    # The form sends every value: a seven-string's own defaults.
    seven_values = {
        field.name: _jsonable(getattr(seven, field.name))
        for field in dataclasses.fields(seven)
    }
    for prototype in ({}, {"handedness": "left"}, seven_values):
        payload = {"prototype": prototype}
        svg = outline_template(payload, "body")["svg"]
        for name in ("cgwReference", "cgwOutline", "cgwMarkA", "Neck pocket"):
            assert name in svg
        back = import_outline(payload, "body", svg)
        built = Prototype001Parameters(**_coerce(prototype))
        points = built.body_shape.control_points  # type: ignore[union-attr]
        # Unchanged, it is the same drawing (mirrored and widened as shown,
        # read back as drawn).
        assert back["values"]["control_points"] == [list(p) for p in points]
        assert back["message"].startswith("Imported the outline: 64 handles")


def test_the_headstock_outline_goes_out_as_a_template_and_comes_back() -> None:
    payload = {"prototype": {"headstock_style": "6_inline"}}
    svg = outline_template(payload, "headstock")["svg"]
    assert "Tuner hole" in svg and "Keep the edge outside" in svg
    # Moved and scaled by another program, and made 10 % longer there.
    edited = svg.replace(
        '<path id="cgwOutline"', '<path id="cgwOutline" transform="scale(1.1 1)"'
    ).replace(
        '  <g id="cgwReference"', '  <g transform="scale(0.75)"><g id="cgwReference"'
    )
    edited = edited.replace("</svg>", "</g></svg>")
    values = import_outline(payload, "headstock", edited)
    start = headstock_editor_layout(payload)["start_edges"]
    assert values["values"]["headstock_outline"] == "drawn"
    assert values["values"]["headstock_bass_edge"][-1][0] == pytest.approx(
        start["bass"][-1][0] * 1.1, abs=0.02
    )
    assert "scaled it by 0.75" in values["message"]


def test_an_outline_that_cannot_be_drawn_says_why() -> None:
    drawn = {"prototype": {}}
    assert "error" in outline_template(drawn, "fretboard")
    assert (
        "Only a drawn body"
        in outline_template(
            {"prototype": {"body_shape": {"kind": "design_by_jone"}}}, "body"
        )["error"]
    )
    assert (
        "headless"
        in outline_template(
            {"prototype": {"headless": True, "headstock_outline": "drawn"}}, "headstock"
        )["error"]
    )
    assert "not an SVG file" in import_outline(drawn, "body", "{}")["error"]
    svg = outline_template(drawn, "body")["svg"]
    assert (
        "cgwMarkC is missing"
        in import_outline(drawn, "body", svg.replace("cgwMarkC", "x"))["error"]
    )


def test_the_body_template_carries_the_engraving_to_draw_on() -> None:
    payload = {"prototype": {"body_engraving": True, "body_engraving_pattern": "flame"}}
    svg = outline_template(payload, "body")["svg"]
    # Read back unchanged, the pattern is left as it is (laid out at random).
    assert set(import_outline(payload, "body", svg)["values"]) == {"control_points"}
    # A line taken out: the rest is the top's drawn engraving from now on.
    start = svg.index('<g id="cgwPatternLayer"')
    first = svg.index("<path", start)
    end = svg.index("/>", first) + 2
    result = import_outline(payload, "body", svg[:first] + svg[end:])
    values = result["values"]
    assert values["body_engraving"] is True
    assert values["body_engraving_pattern"] == "drawn"
    assert len(values["body_engraving_lines"]) == svg.count("<path", start) - 2
    assert "lines to engrave" in result["message"]
    # Every line taken out: no engraving.
    layer_end = svg.index("</g>", start)
    cleared = svg[: svg.index("\n", start) + 1] + svg[layer_end:]
    assert import_outline(payload, "body", cleared)["values"]["body_engraving"] is False
