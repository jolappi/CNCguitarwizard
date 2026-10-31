"""Tests for the quick 3D model: closed meshes of the design's own surfaces,
made in a second or two, to turn and look at."""

import base64
import math
from collections import Counter
from dataclasses import replace

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.geometry.body import HardtailSpec
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.styles import STYLES
from cncguitarwizard.render.preview3d import (
    DETAILS,
    PreviewPart,
    detail_parts,
    preview_parts,
    stl_bytes,
)
from cncguitarwizard.webapp import quick_model

STYLE = STYLES["stratocaster"]
STRAT = Prototype001Parameters(**STYLE.prototype_values(STYLE.instruments[0]))
LP_STYLE = STYLES["les_paul"]
LES_PAUL = Prototype001Parameters(**LP_STYLE.prototype_values(LP_STYLE.instruments[0]))


def parts_of(parameters: Prototype001Parameters) -> tuple[PreviewPart, ...]:
    geometry = parameters.build(wired=False)
    rows = FreeCADScriptExporter.neck_loft_rows(
        geometry.neck_surface,
        geometry.headstock,
        geometry.joint_fillet_radius,
        geometry.volute,
    )
    return preview_parts(geometry, rows)


def points(part: PreviewPart) -> list[tuple[float, float, float]]:
    p = part.positions
    return [(p[i], p[i + 1], p[i + 2]) for i in range(0, len(p), 3)]


def volume(part: PreviewPart) -> float:
    corners = points(part)
    total = 0.0
    for i in range(0, len(part.triangles), 3):
        a, b, c = (corners[v] for v in part.triangles[i : i + 3])
        total += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        )
    return total / 6.0


@pytest.mark.parametrize(
    "parameters", [Prototype001Parameters(), STRAT], ids=["default", "strat"]
)
def test_each_part_is_a_closed_mesh_turned_outward(parameters) -> None:  # type: ignore[no-untyped-def]
    parts = parts_of(parameters)
    assert [part.name for part in parts] == ["Body", "Neck", "Fretboard"]
    for part in parts:
        edges: Counter[tuple[int, int]] = Counter()
        tri = part.triangles
        for i in range(0, len(tri), 3):
            a, b, c = tri[i : i + 3]
            edges.update(((a, b), (b, c), (c, a)))
        # Every edge met once each way: no hole, no fold.
        assert all(count == 1 and (v, u) in edges for (u, v), count in edges.items())
        assert volume(part) > 0.0
    body = parts[0]
    # About the slab's volume less its routes and contours.
    outline = parameters.build(wired=False).body.outline.points
    area = 0.5 * abs(
        sum(
            a.x * b.y - b.x * a.y
            for a, b in zip(outline, (*outline[1:], outline[0]), strict=True)
        )
    )
    assert 0.75 < volume(body) / (area * parameters.body_thickness) < 1.0


def test_the_body_shows_its_roundover_contours_and_routes() -> None:
    geometry = STRAT.build(wired=False)
    body_solid = geometry.body
    body = parts_of(STRAT)[0]
    top = [p for p in points(body) if p[2] > -body_solid.thickness / 2.0]
    back = [p for p in points(body) if p[2] <= -body_solid.thickness / 2.0]
    # The top's edge lowered by its 7/16 in roundover where no contour
    # reaches (the treble side's widest; the arm contour runs on to the
    # tail).
    widest = max(p[1] for p in top)
    assert min(p[2] for p in top if p[1] > widest - 0.5) == pytest.approx(
        -11.1, abs=0.2
    )
    tail = max(p[0] for p in top)
    # The arm contour and the pickups' routes down into the top.
    assert min(p[2] for p in top) < -10.0
    # The back square beside the neck plate (the roundover stopped short of
    # it), rounded at the tail.
    front = min(p[0] for p in back if abs(p[1]) < 5.0)
    beside = [p for p in back if p[0] < front + 1.0 and abs(p[1]) < 20.0]
    assert beside and all(p[2] == pytest.approx(-body_solid.thickness) for p in beside)
    assert max(p[2] for p in back if p[0] > tail - 0.5) > -body_solid.thickness + 10.0


def closed_and_outward(part: PreviewPart) -> bool:
    edges: Counter[tuple[int, int]] = Counter()
    tri = part.triangles
    for i in range(0, len(tri), 3):
        a, b, c = tri[i : i + 3]
        edges.update(((a, b), (b, c), (c, a)))
    each_way = all(count == 1 and (v, u) in edges for (u, v), count in edges.items())
    return each_way and volume(part) > 0.0


@pytest.mark.parametrize("detail", list(DETAILS))
@pytest.mark.parametrize(
    "parameters",
    [Prototype001Parameters(), STRAT, LES_PAUL],
    ids=["default", "strat", "les_paul"],
)
def test_each_detail_set_is_closed_meshes_turned_outward(  # type: ignore[no-untyped-def]
    parameters, detail
) -> None:
    parts = detail_parts(parameters.build(wired=False), parameters, detail)
    assert parts
    assert all(closed_and_outward(part) for part in parts)


def test_the_details_sit_where_the_design_puts_them() -> None:
    geometry = STRAT.build(wired=False)
    surface = geometry.fretboard_surface
    frets, markers, nut = detail_parts(geometry, STRAT, "neck")
    assert (frets.name, markers.name, nut.name) == ("Frets", "Markers", "Nut")
    # The crowns on the board's top, as high as the frets are.
    top = surface.center_thickness + STRAT.fret_height
    assert max(p[2] for p in points(frets)) == pytest.approx(top)
    # One crown at each fret, along its slot (the first's).
    first = geometry.fret_layout.slots[0].start.x
    assert any(abs(p[0] - first) < 1e-9 for p in points(frets))
    # The nut up to the strings, behind the board's end.
    assert max(p[0] for p in points(nut)) == pytest.approx(0.0, abs=1e-9)
    assert max(p[2] for p in points(nut)) == pytest.approx(top + 0.5)

    (tuners,) = detail_parts(geometry, STRAT, "headstock")
    tuner_points = points(tuners)
    for hole in geometry.tuner_layout.holes:
        face = geometry.headstock.face_z(hole.center.x)
        # Its post standing on the face, over its hole.
        assert any(
            math.hypot(p[0] - hole.center.x, p[1] - hole.center.y) < hole.diameter
            and p[2] == pytest.approx(face + 17.0, abs=0.01)
            for p in tuner_points
        )

    guard, pickups, knobs = detail_parts(geometry, STRAT, "body")
    assert (guard.name, pickups.name, knobs.name) == ("Pickguard", "Pickups", "Knobs")
    # The pickguard on the top, the pickups up through it, a knob on each pot.
    assert min(p[2] for p in points(guard)) == pytest.approx(0.0)
    assert max(p[2] for p in points(guard)) == pytest.approx(2.5)
    assert max(p[2] for p in points(pickups)) == pytest.approx(2.5 + 6.0)
    pots = [h for h in geometry.covers[0].holes if h.name.startswith("Control pot")]
    for pot in pots:
        assert any(
            math.hypot(p[0] - pot.center_x, p[1] - pot.center_y) < 13.0
            and p[2] == pytest.approx(2.5 + 17.0)
            for p in points(knobs)
        )

    bridge, strings = detail_parts(geometry, STRAT, "bridge")
    assert (bridge.name, strings.name) == ("Bridge", "Strings")
    # The strings over the saddles at the scale line, where its tremolo's
    # block holds them.
    reach = max(p[0] for p in points(strings))
    assert reach == pytest.approx(STRAT.scale_length, abs=0.7)
    assert max(p[2] for p in points(bridge)) < max(p[2] for p in points(strings))
    # A hardtail's run on into the string-through holes behind them.
    hardtail = replace(STRAT, body_bridge=HardtailSpec())
    through = hardtail.build(wired=False)
    holes = [h.center_x for h in through.body.holes if h.name.startswith("String ")]
    _, strings = detail_parts(through, hardtail, "bridge")
    reach = max(p[0] for p in points(strings))
    assert reach == pytest.approx(max(holes), abs=0.7)
    # The body's own details: none for a design without a pickguard.
    default = Prototype001Parameters()
    names = [
        part.name for part in detail_parts(default.build(wired=False), default, "body")
    ]
    assert names == ["Pickups", "Knobs"]


def test_each_bridge_is_drawn_where_its_own_parts_are() -> None:
    from dataclasses import replace

    from cncguitarwizard.geometry.body import BodySolid, HardtailSpec, TuneOMaticSpec

    def bridge_and_strings(
        parameters: Prototype001Parameters,
    ) -> tuple[
        BodySolid, list[tuple[float, float, float]], list[tuple[float, float, float]]
    ]:
        geometry = parameters.build(wired=False)
        bridge, strings = detail_parts(geometry, parameters, "bridge")
        return geometry.body, points(bridge), points(strings)

    # A Kahler 7300 down in its baseplate's cutout, its plate over it and on
    # forward under the saddles at the scale line (not on the bare top).
    kahler = Prototype001Parameters()
    body, bridge, strings = bridge_and_strings(kahler)
    plate = body.bridge_footprint
    (cutout,) = (
        c for c in body.extra_cavities if c.name.startswith("Bridge baseplate")
    )
    assert plate
    assert min(p[0] for p in bridge) < kahler.centre_scale - 1.5
    assert max(p[0] for p in bridge) >= max(q.x for q in plate) - 1.0
    assert min(p[2] for p in bridge) == pytest.approx(-cutout.depth + 1.0, abs=0.01)
    assert max(p[0] for p in strings) == pytest.approx(kahler.centre_scale, abs=1.0)
    # A Tune-o-matic's strings on to its stop tailpiece, a hardtail's into
    # their holes through the body.
    tom = replace(kahler, body_bridge=TuneOMaticSpec())
    body, bridge, strings = bridge_and_strings(tom)
    studs = [h.center_x for h in body.holes if h.name.startswith("Tailpiece stud")]
    assert max(p[0] for p in strings) == pytest.approx(sum(studs) / len(studs), abs=1.0)
    hardtail = replace(kahler, body_bridge=HardtailSpec())
    body, bridge, strings = bridge_and_strings(hardtail)
    holes = [h.center_x for h in body.holes if h.name.startswith("String ")]
    assert max(p[0] for p in strings) == pytest.approx(max(holes), abs=1.0)


def test_a_tilted_neck_is_drawn_tilted_onto_the_body() -> None:
    geometry = LES_PAUL.build(wired=False)
    angle, pivot_x, pivot_z = geometry.neck_tilt
    assert angle > 0.0
    board = parts_of(LES_PAUL)[2]
    # The board's top at the nut, turned down about the pivot as the build
    # turns it.
    thickness = geometry.fretboard_surface.center_thickness
    turn = math.radians(angle)
    x = pivot_x - pivot_x * math.cos(turn) - (thickness - pivot_z) * math.sin(turn)
    z = pivot_z - pivot_x * math.sin(turn) + (thickness - pivot_z) * math.cos(turn)
    assert any(
        p[0] == pytest.approx(x)
        and p[1] == pytest.approx(0.0, abs=1e-9)
        and p[2] == pytest.approx(z)
        for p in points(board)
    )


def test_the_web_app_sends_the_parts_and_an_stl_holds_them() -> None:
    result = quick_model({"prototype": {}})
    assert [part["name"] for part in result["parts"]] == ["Body", "Neck", "Fretboard"]
    for part in result["parts"]:
        positions = base64.b64decode(part["positions"])
        triangles = base64.b64decode(part["triangles"])
        assert len(positions) % 12 == 0 and len(triangles) % 12 == 0
        assert max(memoryview(triangles).cast("I")) < len(positions) // 12
        assert part["colour"].startswith("#")
    assert "error" in quick_model({"prototype": {"body_thickness": -1.0}})
    # The detail sets ticked after the parts; one not known is told.
    detailed = quick_model({"prototype": {}}, ["headstock", "bridge"])
    names = [part["name"] for part in detailed["parts"]]
    assert names == ["Body", "Neck", "Fretboard", "Tuners", "Bridge", "Strings"]
    assert "ValidationError" in quick_model({"prototype": {}}, ["pickups"])["error"]
    parts = parts_of(Prototype001Parameters())
    data = stl_bytes(parts)
    count = sum(len(part.triangles) // 3 for part in parts)
    assert len(data) == 84 + 50 * count
    assert int.from_bytes(data[80:84], "little") == count
    assert math.isfinite(volume(parts[1]))


def test_a_headstock_turned_round_takes_the_strings_the_other_way_round() -> None:
    # Turned round, a six in line is a reverse one: the high E wound on the
    # post nearest the nut, the low E on the one at the tip.
    from cncguitarwizard.render.preview3d import _posts_of_strings

    inline = replace(Prototype001Parameters(), headstock_style="6_inline")
    turned = replace(inline, headstock_bass_side="+y")
    for parameters, nearest in ((inline, 0), (turned, -1)):
        posts = _posts_of_strings(parameters.build(wired=False), parameters)
        along = [post[0] for post in posts if post is not None]
        assert len(along) == 6
        assert along[nearest] == max(along)
        assert along[-1 - nearest] == min(along)
