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


def test_a_strap_guide_in_the_way_is_moved_before_it_is_turned_off() -> None:
    # Dropped on the control cavity's cover: putting its place back to
    # automatic clears it, so the guide stays.
    layout = body_editor_layout({"prototype": {}})
    (recess,) = [
        p for p in layout["polygons"] if p["name"].startswith("Control cavity cover")
    ]
    x = sum(point[0] for point in recess["points"]) / len(recess["points"])
    y = sum(point[1] for point in recess["points"]) / len(recess["points"])
    shape = dict(
        DESIGN_BY_JONE,
        strap_guide_offset=round(x, 1),
        strap_guide_y=round(y, 1),
        strap_guide_angle_degrees=0.0,
    )
    payload = {"prototype": {"body_shape": shape, "body_strap_guide": True}}
    changes = [
        change("body_strap_guide", False),
        change("strap_guide_offset", None, "prototype.body_shape"),
        change("strap_guide_y", None, "prototype.body_shape"),
        change("strap_guide_angle_degrees", None, "prototype.body_shape"),
    ]

    assert any("strap guide" in problem for problem in design_problems(payload))
    result = repair_design(payload, changes)
    assert 0 not in result["reset"] and result["reset"]
    assert result["remaining"] == []
