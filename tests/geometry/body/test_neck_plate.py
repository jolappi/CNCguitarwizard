"""Tests for the neck plate: a bolt-on neck's bolts through a plate on the back."""

import ast
import math
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters, plan_body_machining
from cncguitarwizard.geometry.body import HeelRelief
from cncguitarwizard.geometry.body.body_solid import outlines_overlap
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.presets.prototype001 import NECK_PLATE_RELIEF_GAP
from cncguitarwizard.render.dxf import render_plan_dxf
from cncguitarwizard.render.svg.plan_view import render_plan_view_svg
from cncguitarwizard.webapp import body_editor_layout

STRATOCASTER = YOUR_DESIGN_TEMPLATES["stratocaster"][1]


def strat(**overrides: object) -> Prototype001Parameters:
    """The Stratocaster style body, whose back has room for a Fender plate."""
    return replace(  # type: ignore[arg-type]
        Prototype001Parameters(), **{"body_shape": STRATOCASTER, **overrides}
    )


def bolts(parameters: Prototype001Parameters) -> dict[str, tuple[float, float]]:
    """The neck bolts' holes by name: (X from the heel end, Y)."""
    heel_end = parameters.body_layout().heel_end
    return {
        hole.name: (hole.center_x - heel_end, hole.center_y)
        for hole in parameters.build().body.rear_holes
        if hole.name.startswith("Neck bolt")
    }


def test_a_fender_plate_holds_the_bolts_at_its_holes() -> None:
    parameters = strat(body_neck_plate="plate")
    body = parameters.build().body
    heel_end = parameters.body_layout().heel_end

    # No ferrules: four bolt holes 50.8 x 38.1 apart, the tail pair 3 mm
    # of wood (the end wall) from the heel end.
    expected = {
        "Neck bolt 1 hole": (-56.3, -19.05),
        "Neck bolt 2 hole": (-5.5, -19.05),
        "Neck bolt 3 hole": (-56.3, 19.05),
        "Neck bolt 4 hole": (-5.5, 19.05),
    }
    found = bolts(parameters)
    assert found.keys() == expected.keys()
    for name, place in expected.items():
        assert found[name] == pytest.approx(place)
    xs = [point.x - heel_end for point in body.neck_plate]
    ys = [point.y for point in body.neck_plate]
    assert max(xs) - min(xs) == pytest.approx(63.5)
    assert max(ys) - min(ys) == pytest.approx(50.8)
    # Its corners are rounded about the holes, 6.35 mm out all round.
    for x, y in bolts(parameters).values():
        nearest = min(
            math.hypot(point.x - heel_end - x, point.y - y) for point in body.neck_plate
        )
        assert nearest == pytest.approx(6.35, abs=0.05)


def test_an_asymmetric_plate_clips_its_treble_corner_toward_the_nut() -> None:
    parameters = strat(body_neck_plate="asymmetric")
    plate = parameters.build().body.neck_plate
    heel_end = parameters.body_layout().heel_end
    treble = -parameters.bass_sign
    nut_end = heel_end - 62.65

    assert not point_in_polygon(Point2D(nut_end + 3.0, treble * 22.4), plate)
    assert point_in_polygon(Point2D(nut_end + 3.0, -treble * 22.4), plate)
    # That corner's bolt moves in along the diagonal, the others stay.
    shift = (19.0 / math.sqrt(2.0) + 6.35 - 6.35 * math.sqrt(2.0)) / math.sqrt(2.0)
    treble_side = sorted(xy for xy in bolts(parameters).values() if xy[1] * treble > 0)
    assert treble_side[0] == pytest.approx((-56.3 + shift, treble * (19.05 - shift)))
    assert treble_side[1] == pytest.approx((-5.5, treble * 19.05))


def test_the_plate_needs_the_flat_back() -> None:
    # The Design by Jone body's deep treble cutaway leaves it no room.
    with pytest.raises(BodyGeometryError, match="keep 1 mm of flat back"):
        replace(Prototype001Parameters(), body_neck_plate="plate").build()
    # Nor does it sit on a roundover.
    with pytest.raises(BodyGeometryError, match="keep 7 mm of flat back"):
        strat(body_neck_plate="plate", body_back_edge_radius=6.0).build()


def test_the_plate_keeps_clear_of_the_rear_covers() -> None:
    body = strat(body_neck_plate="plate").build().body
    assert body.control_cavity is not None
    cover = body.control_cavity.cover_recess

    with pytest.raises(BodyGeometryError, match=f"overlaps {cover.name}"):
        replace(body, neck_plate=cover.outline)


@pytest.mark.parametrize("kind", ["plate", "asymmetric"])
@pytest.mark.parametrize("relief", ["contour", "notch"])
def test_a_corner_heel_relief_slants_past_the_plate(kind: str, relief: str) -> None:
    parameters = strat(
        body_neck_plate=kind, body_heel_relief=relief, body_heel_relief_line="corner"
    )
    body = parameters.build().body
    (heel_relief,) = body.contours
    treble = -parameters.bass_sign

    assert not outlines_overlap(body.neck_plate, heel_relief.region())
    # Its line runs at 45 degrees, the gap out from the plate's corner.
    out = (-math.sqrt(0.5), treble * math.sqrt(0.5))
    corner = max(body.neck_plate, key=lambda p: p.x * out[0] + p.y * out[1])
    reach = corner.x * out[0] + corner.y * out[1]
    for point in heel_relief.inner_edge():
        assert point.x * out[0] + point.y * out[1] == pytest.approx(
            reach + NECK_PLATE_RELIEF_GAP
        )
    # The back is cut away beyond it.
    beyond = NECK_PLATE_RELIEF_GAP + 2.0
    assert (
        heel_relief.depth_at(
            Point2D(corner.x + out[0] * beyond, corner.y + out[1] * beyond)
        )
        > 0.0
    )


def test_a_plate_leaves_the_heel_relief_round_the_heel() -> None:
    # Choosing a plate does not change the relief's line: still the U
    # round the heel, across the neck pocket, as without one (the plate on
    # it then refused at the build, not in the editor's drawing).
    around = strat(body_heel_relief="contour")
    with_plate = replace(around, body_neck_plate="plate")
    heel_end = around.body_layout().heel_end

    lines = [
        next(c for c in p.body_layout().contours if c.name == "Heel relief").line
        for p in (around, with_plate)
    ]
    assert lines[0] == lines[1]
    assert max(point.x for point in lines[1]) == pytest.approx(heel_end + 15.0, abs=0.1)
    with pytest.raises(BodyGeometryError, match="sits on the Heel relief"):
        with_plate.build()
    layout = body_editor_layout(
        {"prototype": {"body_heel_relief": "contour", "body_neck_plate": "plate"}}
    )
    assert "error" not in layout
    assert layout["heel_relief"]["automatic"] is True


@pytest.mark.parametrize("relief", ["contour", "notch", "bevel"])
def test_a_corner_heel_relief_cuts_the_treble_corner_without_a_plate(
    relief: str,
) -> None:
    # The Design by Jone body, with ferrules: its line slants at 45 degrees
    # across the treble corner, crossing the centreline the reach (15 mm)
    # behind the body's edge at the neck end.
    parameters = replace(
        Prototype001Parameters(),
        body_heel_relief=relief,
        body_heel_relief_line="corner",
    )
    body = parameters.build().body
    (heel_relief,) = [c for c in body.contours if c.name == "Heel relief"]
    assert isinstance(heel_relief, HeelRelief)
    treble = -parameters.bass_sign
    out = (-math.sqrt(0.5), treble * math.sqrt(0.5))
    across = [p.x * out[0] + p.y * out[1] for p in heel_relief.inner_edge()]
    assert max(across) - min(across) == pytest.approx(0.0, abs=1e-6)
    # Where the centreline leaves the body ahead of the heel end.
    edge = parameters.body_layout().heel_end
    while point_in_polygon(Point2D(edge, 0.0), body.outline.points):
        edge -= 0.5
    crossing = across[0] / out[0]  # the line's X on the centreline
    assert crossing - edge == pytest.approx(15.0)
    # The relief is the treble corner: deep near it, nothing on the bass side.
    deepest = max(heel_relief.edge, key=lambda p: p.x * out[0] + p.y * out[1])
    assert deepest.y * treble > 0.0
    assert heel_relief.depth_at(Point2D(edge + 20.0, -treble * 20.0)) == 0.0
    if relief == "bevel":
        # A flat slope across the corner, at the face along its line.
        assert heel_relief.plane_axis == pytest.approx(out)
        assert heel_relief.plane[1] == pytest.approx(min(across))


def test_a_plate_beside_a_corner_bevel_stays_flat() -> None:
    parameters = strat(
        body_neck_plate="asymmetric",
        body_heel_relief="bevel",
        body_heel_relief_line="corner",
    )
    body = parameters.build().body

    assert not any(hole.name.startswith("Neck bolt") for hole in body.side_holes)
    assert {
        hole.name for hole in body.rear_holes if hole.name.startswith("Neck bolt")
    } == {f"Neck bolt {n} hole" for n in range(1, 5)}


def test_a_drawn_heel_relief_over_the_plate_is_refused() -> None:
    line = ((-80.0, 40.0), (-20.0, 40.0), (15.0, 0.0), (-20.0, -40.0), (-80.0, -40.0))
    parameters = strat(
        body_neck_plate="plate",
        body_heel_relief="contour",
        body_shape=replace(STRATOCASTER, heel_relief_points=line),
    )
    with pytest.raises(BodyGeometryError, match="sits on the Heel relief"):
        parameters.build()


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"body_neck_plate_length": -1.0}, "finite and positive"),
        ({"body_neck_plate_hole_inset": 2.0}, "must fit in it"),
        ({"body_neck_plate_hole_inset": 24.0}, "must fit in it"),
        (
            {"body_neck_plate": "asymmetric", "body_neck_plate_clip": 30.0},
            "under half",
        ),
        ({"neck_joint": "set"}, "bolt-on neck's bolts"),
    ],
)
def test_plate_sizes_that_do_not_fit_are_refused(
    overrides: dict[str, object], match: str
) -> None:
    parameters = strat(**{"body_neck_plate": "plate", **overrides})
    with pytest.raises(BodyGeometryError, match=match):
        parameters.build()


def test_the_plate_has_no_ferrules_to_machine_and_is_drawn() -> None:
    geometry = strat(body_neck_plate="asymmetric").build()
    plan = plan_body_machining(geometry.body, MachiningParameters())

    assert not any("ferrule" in path.name for path in plan.back.toolpaths)
    assert plan.back_small_holes is not None
    assert {f"Neck bolt {n} hole" for n in range(1, 5)} <= {
        path.name for path in plan.back_small_holes.toolpaths
    }
    assert "Neck plate (back)" in render_plan_view_svg(geometry)
    assert "NECK_PLATE" in render_plan_dxf(geometry)
    ast.parse(FreeCADScriptExporter().render_prototype001(geometry))


def test_the_body_editor_draws_the_plate_and_keeps_its_bolts() -> None:
    layout = body_editor_layout({"prototype": {"body_neck_plate": "plate"}})

    (plate,) = [p for p in layout["polygons"] if p["role"] == "neck_plate"]
    assert len(plate["points"]) > 4
    groups = {c["name"]: c["group"] for c in layout["circles"]}
    assert all(
        group is None for name, group in groups.items() if name.startswith("Neck bolt")
    )
    # Its other features still move.
    assert any(group for name, group in groups.items() if "cover screw" in name)
    plain = body_editor_layout({"prototype": {}})
    assert not any(p["role"] == "neck_plate" for p in plain["polygons"])
    assert {
        c["group"] for c in plain["circles"] if c["name"].startswith("Neck bolt")
    } == {"bolt:0", "bolt:1", "bolt:2", "bolt:3"}


def test_a_corner_heel_relief_needs_body_beyond_the_plates_corner() -> None:
    # The Design by Jone body's treble cutaway runs right by the plate.
    parameters = replace(
        Prototype001Parameters(),
        body_neck_plate="plate",
        body_heel_relief="contour",
        body_heel_relief_line="corner",
    )
    with pytest.raises(BodyGeometryError, match="set body_heel_relief_line to around"):
        parameters.build()


def test_the_body_editor_draws_the_u_for_a_corner_line_that_does_not_fit() -> None:
    # The Design by Jone body leaves no corner beyond a plate's: the editor
    # still draws (its layout is not validated), the U round the heel, and
    # says why the chosen line could not be laid out.
    layout = body_editor_layout(
        {
            "prototype": {
                "body_heel_relief": "notch",
                "body_heel_relief_line": "corner",
                "body_neck_plate": "plate",
            }
        }
    )

    assert "error" not in layout
    line = layout["heel_relief"]
    assert line["automatic"] is True and len(line["points"]) == 7
    (problem,) = layout["problems"]
    assert "no corner of the body to cut" in problem
    for relief in ("contour", "bevel"):
        corner = body_editor_layout(
            {
                "prototype": {
                    "body_heel_relief": relief,
                    "body_heel_relief_line": "corner",
                }
            }
        )
        assert corner["problems"] == []


def test_the_body_editor_draws_neck_bolts_with_no_room_where_they_are_asked() -> None:
    # A bolt dragged out past the treble cutaway: the build refuses it, but
    # the editor still draws every bolt (where asked, not moved out) to be
    # dragged back, and says why.
    drawn = Prototype001Parameters().built_body_shape
    bolts = ((-40.0, -20.0), (-5.5, -20.0), (-64.6, 15.0), (-5.5, 18.0))
    prototype = {
        "body_shape": {
            "kind": "your_design",
            **{
                name: value
                for name, value in body_editor_layout({"prototype": {}})["templates"][
                    "design_by_jone"
                ]["shape"].items()
                if name != "kind"
            },
            "neck_bolts": [list(bolt) for bolt in bolts],
        }
    }
    with pytest.raises(BodyGeometryError, match="Neck bolt 3 .* has no room"):
        replace(
            Prototype001Parameters(), body_shape=replace(drawn, neck_bolts=bolts)
        ).build()
    layout = body_editor_layout({"prototype": prototype})

    assert "error" not in layout
    (problem,) = layout["problems"]
    assert "Neck bolt 3" in problem and "has no room" in problem
    circles = {c["name"]: c for c in layout["circles"]}
    assert circles["Neck bolt 3 hole"]["x"] == pytest.approx(-64.6)
    assert circles["Neck bolt 3 hole"]["group"] == "bolt:2"
