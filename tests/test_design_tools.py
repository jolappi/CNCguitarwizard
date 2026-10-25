"""Tests for the command line's design tools: settings, new-design, set, check."""

import json
from pathlib import Path
from typing import Any

import pytest

from cncguitarwizard.__main__ import main
from cncguitarwizard.design_tools import (
    DesignFileError,
    check_design,
    describe_settings,
    new_design,
    read_design,
    set_values,
    write_design,
)


def _tele() -> dict[str, Any]:
    return new_design("electric_guitar", "telecaster", "Oma Tele")


def test_a_new_design_starts_from_an_instrument_or_its_style() -> None:
    plain = new_design("bass_guitar", name="Basso")
    tele = _tele()

    assert plain["instrument"] == "bass_guitar"
    assert plain["prototype"] == {} and plain["name"] == "Basso"
    assert tele["prototype"]["body_pickups"] == "SS"
    assert check_design(plain)["ok"]
    assert check_design(tele)["ok"]


def test_an_unknown_instrument_or_style_is_refused_with_the_choices() -> None:
    with pytest.raises(DesignFileError, match="choose one of electric_guitar"):
        new_design("banjo")
    with pytest.raises(DesignFileError, match="The styles for it: jazz_bass"):
        new_design("bass_guitar", "telecaster")


@pytest.mark.parametrize(
    ("assignment", "name", "value"),
    [
        ("scale_length=24.75in", "scale_length", 628.65),
        ('scale_length=25.5"', "scale_length", 647.7),
        ("scale_length=610mm", "scale_length", 610.0),
        ("scale_length=609,5", "scale_length", 609.5),
        ("fret_count=22", "fret_count", 22),
        ("fretboard_scalloped=yes", "fretboard_scalloped", True),
        ("handedness=left", "handedness", "left"),
        (
            "inlay_single_marker_frets=[3, 5, 7, 9]",
            "inlay_single_marker_frets",
            [3, 5, 7, 9],
        ),
    ],
)
def test_values_are_read_as_their_settings_type(
    assignment: str, name: str, value: object
) -> None:
    result = set_values(new_design("electric_guitar"), [assignment])

    assert result["rejected"] == []
    assert result["design"]["prototype"][name] == value


def test_an_optional_number_is_emptied_with_none() -> None:
    tilted = set_values(new_design("electric_guitar"), ["neck_angle=2"])["design"]

    result = set_values(tilted, ["neck_angle=none"])

    assert result["changes"] == [{"name": "neck_angle", "from": 2.0, "to": None}]
    assert result["design"]["prototype"]["neck_angle"] is None


@pytest.mark.parametrize(
    ("assignment", "reason"),
    [
        ("fret_count=22.5", "takes a whole number"),
        ("neck_angle=2in", "is no length; it takes no inches"),
        ("scale_length=long", "takes a number"),
        ("fretboard_scalloped=maybe", "is true or false"),
        ("handedness=both", "is one of right, left"),
        ("inlay_single_marker_frets=3,5", "takes JSON"),
        ("nonsense=1", "There is no setting 'nonsense'"),
        ("instrument=bass_guitar", "start a new design"),
        ("body_bridge=tremolo", "body_bridge is one of"),
        ("body_bridge.foo=1", "has no field 'foo'"),
        ("fret_count.foo=1", "has no fields of its own"),
        ("fret_count", "Write it as name=value"),
    ],
)
def test_a_value_that_does_not_read_is_refused_and_nothing_kept(
    assignment: str, reason: str
) -> None:
    result = set_values(new_design("electric_guitar"), ["handedness=left", assignment])

    assert [refusal["assignment"] for refusal in result["rejected"]] == [assignment]
    assert reason in result["rejected"][0]["reason"]
    assert result["keep"] is False and result["check"] is None


def test_a_bridge_takes_another_kind_and_its_own_fields() -> None:
    result = set_values(
        new_design("seven_string_guitar"),
        ["body_bridge=hardtail", "body_bridge.string_count=7"],
    )

    bridge = result["design"]["prototype"]["body_bridge"]
    # Written whole, with the kind's own defaults.
    assert bridge["kind"] == "hardtail" and bridge["string_count"] == 7
    assert "screw_count" in bridge
    assert result["changes"][0]["to"]["kind"] == "hardtail"
    assert result["changes"][1] == {
        "name": "body_bridge.string_count",
        "from": 6,
        "to": 7,
    }
    assert result["keep"], result["check"]


def test_set_says_what_was_so_already_and_what_does_nothing() -> None:
    result = set_values(_tele(), ["handedness=left", "body_neck_pickup=humbucker"])

    assert result["changes"] == [{"name": "handedness", "from": "right", "to": "left"}]
    assert result["unchanged"] == ["body_neck_pickup"]
    # The Tele's "SS" layout decides its pickups: a neck pickup's own kind
    # needs the custom layout.
    assert result["not_applied"] == [
        {"name": "body_neck_pickup", "applies_when": [{"body_pickups": ["custom"]}]}
    ]
    assert result["keep"]


def test_a_change_that_breaks_the_design_is_not_kept() -> None:
    result = set_values(new_design("electric_guitar"), ["heel_mounting_length=10"])

    assert result["keep"] is False
    assert result["check"]["ok"] is False
    assert "at least 40 mm" in result["check"]["error"]


def test_an_unfinished_design_is_kept_while_it_gets_no_worse() -> None:
    broken = set_values(new_design("electric_guitar"), ["heel_mounting_length=10"])[
        "design"
    ]

    aside = set_values(broken, ["handedness=left"])
    fixed = set_values(broken, ["heel_mounting_length=60"])

    assert aside["keep"] and not aside["check"]["ok"]
    assert fixed["keep"] and fixed["check"]["ok"]


def test_check_reports_what_is_wrong_and_what_was_changed() -> None:
    design = _tele()
    design["prototype"]["body_flux_capacitor"] = 1.21
    good = check_design(design)
    broken = check_design(
        {**design, "prototype": {**design["prototype"], "heel_mounting_length": 10.0}}
    )

    assert good["ok"] and good["error"] is None and good["problems"] == []
    assert good["skipped"] == ["body_flux_capacitor"]
    assert good["sheet"]["status"] == "READY FOR HUMAN REVIEW"
    assert good["changed"]["body_pickups"] == "SS"
    assert not broken["ok"] and broken["error"].startswith("NeckGeometryError")
    assert broken["sheet"] is None


def test_settings_are_found_by_words_group_and_change() -> None:
    design = _tele()

    found = describe_settings(design, search="neck pickup")
    machining = describe_settings(group="machining")
    changed = describe_settings(design, changed_only=True)
    plain = describe_settings(search="scale length")

    by_name = {entry["name"]: entry for entry in found}
    assert by_name["body_neck_pickup"]["applies"] is False
    assert by_name["body_neck_pickup"]["applies_when"] == [{"body_pickups": ["custom"]}]
    assert "humbucker" in by_name["body_neck_pickup"]["options"]
    assert {entry["group"] for entry in machining} == {"Machining"}
    assert "body_pickups" in {entry["name"] for entry in changed}
    assert "string_count" not in {entry["name"] for entry in changed}
    assert plain[0]["name"] == "scale_length" and "value" not in plain[0]
    bridge = next(
        entry
        for entry in describe_settings(search="bridge")
        if entry["name"] == "body_bridge"
    )
    assert bridge["kinds"][0] == "kahler_7300"


def test_a_file_that_is_no_design_is_refused(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{nope", encoding="utf-8")
    other = tmp_path / "other.json"
    other.write_text('{"format": "something-else"}', encoding="utf-8")

    with pytest.raises(DesignFileError, match="broken.json"):
        read_design(broken)
    with pytest.raises(DesignFileError, match="not a CNCguitarwizard design"):
        read_design(other)
    with pytest.raises(DesignFileError, match="missing.json"):
        read_design(tmp_path / "missing.json")


def test_the_command_line_makes_changes_and_checks_a_design(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "oma.json"

    main(
        [
            "new-design",
            "--instrument",
            "electric_guitar",
            "--style",
            "telecaster",
            "--name",
            "Oma Tele",
            "--output",
            str(path),
        ]
    )
    main(["set", "--design", str(path), "handedness=left", "scale_length=25.5in"])
    main(["check", "--design", str(path)])

    printed = capsys.readouterr().out
    assert f"Saved {path}" in printed
    assert 'handedness: "right" -> "left"' in printed
    assert "Already so: scale_length" in printed
    assert printed.rstrip().endswith("OK: ready for human review")
    assert read_design(path)["prototype"]["handedness"] == "left"


def test_the_command_line_keeps_the_file_when_a_change_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "oma.json"
    write_design(path, _tele())
    before = path.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as refused:
        main(["set", "--design", str(path), "--json", "fret_count=many"])

    printed = json.loads(capsys.readouterr().out)
    assert refused.value.code == 1
    assert printed["saved"] is None and printed["rejected"][0]["assignment"] == (
        "fret_count=many"
    )
    assert path.read_text(encoding="utf-8") == before


def test_check_ends_with_an_error_code_for_a_design_that_is_not_ok(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "broken.json"
    design = new_design("electric_guitar")
    design["prototype"]["heel_mounting_length"] = 10.0
    write_design(path, design)

    with pytest.raises(SystemExit) as failed:
        main(["check", "--design", str(path), "--json"])

    assert failed.value.code == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_the_command_line_refuses_to_overwrite_or_list_changes_without_a_design(
    tmp_path: Path,
) -> None:
    path = tmp_path / "oma.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit) as exists:
        main(["new-design", "--instrument", "electric_guitar", "--output", str(path)])
    with pytest.raises(SystemExit) as no_design:
        main(["settings", "--changed"])

    assert exists.value.code == 2 and no_design.value.code == 2
    assert path.read_text(encoding="utf-8") == "{}"


def test_settings_print_json_for_an_assistant(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["settings", "--search", "fret count", "--json"])

    entries = json.loads(capsys.readouterr().out)
    assert entries[0]["name"] == "fret_count"
    assert entries[0]["type"] == "int"
