"""Tests for repairing a design that would show an editor in error."""

from typing import Any

from cncguitarwizard.webapp import body_editor_layout, design_problems, repair_design

DESIGN_BY_JONE = dict(
    body_editor_layout({"prototype": {}})["templates"]["design_by_jone"]["shape"]
)
NO_ROOM = [[-40.0, -20.0], [-5.5, -20.0], [-64.6, 15.0], [-5.5, 18.0]]


def change(name: str, default: Any, kind_set: str = "prototype") -> dict[str, Any]:
    """A changed setting as the form holds it."""
    return {"set": kind_set, "name": name, "default": default}


def test_the_defaults_show_no_problems() -> None:
    assert design_problems({"prototype": {}}) == []
    result = repair_design({"prototype": {}}, [])
    assert result == {"problems": [], "reset": [], "remaining": []}


def test_a_neck_bolt_with_no_room_is_put_back() -> None:
    shape = dict(DESIGN_BY_JONE, neck_bolts=NO_ROOM)
    payload = {"prototype": {"body_shape": shape, "body_thickness": 46.0}}
    changes = [
        change("body_thickness", 44.0),
        change("neck_bolts", DESIGN_BY_JONE["neck_bolts"], "prototype.body_shape"),
    ]

    problems = design_problems(payload)
    assert any(
        "Neck bolt 3" in problem and "no room" in problem for problem in problems
    )
    assert "Neck bolt 3 hole falls outside the outline." in problems
    result = repair_design(payload, changes)
    # Only the bolts go back; the thicker body stays.
    assert result["reset"] == [1]
    assert result["remaining"] == []


def test_settings_that_cause_it_together_are_put_back_together() -> None:
    # A plate on the Design by Jone body (it has no room for one) and a
    # bolt dragged past the cutaway: neither alone clears it.
    shape = dict(DESIGN_BY_JONE, neck_bolts=NO_ROOM)
    payload = {
        "prototype": {
            "body_shape": shape,
            "body_neck_plate": "plate",
            "body_heel_relief": "contour",
            "body_heel_relief_line": "corner",
        }
    }
    changes = [
        change("body_heel_relief", "none"),
        change("body_heel_relief_line", "around"),
        change("body_neck_plate", "ferrules"),
        change("neck_bolts", DESIGN_BY_JONE["neck_bolts"], "prototype.body_shape"),
    ]

    result = repair_design(payload, changes)
    assert sorted(result["reset"]) == [2, 3]
    assert result["remaining"] == []
