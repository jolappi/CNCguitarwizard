"""Tests for a body glued up from a core and a separate top (a Les Paul's
maple cap): its wire channels and chambers routed into the core under the
top, the core's own programs run first, and the model's two solids."""

import math
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.cam import MachiningParameters, plan_body_machining
from cncguitarwizard.geometry.body import TracedCavity
from cncguitarwizard.geometry.body.chambers import (
    CHAMBER_EDGE_WALL,
    CHAMBER_FLOOR,
    CHAMBER_WALL,
)
from cncguitarwizard.geometry.body.wiring import WIRE_CORE_CHANNEL_DEPTH
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import Point2D, point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.styles import STYLES
from cncguitarwizard.render.preview3d import preview_parts
from cncguitarwizard.webapp import _quick_base

STYLE = STYLES["les_paul"]
LES_PAUL = Prototype001Parameters(**STYLE.prototype_values(STYLE.instruments[0]))
CHAMBERED = replace(LES_PAUL, body_chambers=True)


def _distance_to(point: Point2D, polygon: tuple[Point2D, ...]) -> float:
    best = math.inf
    for a, b in zip(polygon, (*polygon[1:], polygon[0]), strict=True):
        dx, dy = b.x - a.x, b.y - a.y
        length = dx * dx + dy * dy
        t = ((point.x - a.x) * dx + (point.y - a.y) * dy) / length if length else 0.0
        t = max(0.0, min(1.0, t))
        best = min(best, math.hypot(a.x + t * dx - point.x, a.y + t * dy - point.y))
    return best


def _circle(x: float, y: float, radius: float) -> tuple[Point2D, ...]:
    return tuple(
        Point2D(
            x + radius * math.cos(k * math.pi / 12),
            y + radius * math.sin(k * math.pi / 12),
        )
        for k in range(24)
    )


def test_a_les_paul_s_wiring_runs_under_its_maple_cap() -> None:
    body = LES_PAUL.build().body
    # A 5/8 in cap, leaving the 1/4 in of maple at the carve's rim.
    assert body.cap_thickness == pytest.approx(15.875)
    assert body.core_thickness == pytest.approx(body.thickness - 15.875)
    # Every lead's way a channel under it, none left to the builder (no
    # straight hole reaches a Les Paul's pickups from its controls).
    assert not body.wire_notes
    channels = {cavity.name for cavity in body.core_cavities}
    assert channels == {
        "Neck pickup wire channel",
        "Bridge pickup wire channel",
        "Switch wire channel",
    }
    # One piece without it, the leads left to the builder as before.
    plain = replace(LES_PAUL, body_cap_thickness=0.0).build().body
    assert not plain.core_cavities and plain.wire_notes


def test_chambers_lighten_the_core_clear_of_everything() -> None:
    body = CHAMBERED.build().body
    chambers = [c for c in body.core_cavities if c.name.startswith("Chamber")]
    assert len(chambers) >= 2
    keep_clear = [
        *(c.outline for c in body.top_cavities if c.depth > body.cap_thickness),
        *(p.outline for rear in body.rear_cavities for p in rear.pockets),
        *(_circle(h.center_x, h.center_y, h.diameter / 2.0) for h in body.holes),
    ]
    middle = max(
        abs(p.y) for c in (body.neck_pickup, body.bridge_pickup) if c for p in c.outline
    )
    for chamber in chambers:
        assert chamber.depth == pytest.approx(body.core_thickness - CHAMBER_FLOOR)
        for point in chamber.outline:
            assert _distance_to(point, body.outline.points) >= CHAMBER_EDGE_WALL - 0.5
            assert all(
                not point_in_polygon(point, polygon)
                and _distance_to(point, polygon) >= CHAMBER_WALL - 0.5
                for polygon in keep_clear
            )
            # The middle under the pickups and the bridge left solid.
            assert abs(point.y) > middle
    # The same chambers drawn as built (the wiring is not planned for a
    # drawing).
    drawn = CHAMBERED.build(wired=False).body.core_cavities
    assert [c.outline for c in drawn] == [c.outline for c in chambers]


def test_a_separate_top_is_refused_where_it_cannot_be_made() -> None:
    # Chambers without a top: left alone, as the web app hides them.
    plain = replace(CHAMBERED, body_cap_thickness=0.0).build(wired=False)
    assert not plain.body.core_cavities
    with pytest.raises(BodyGeometryError, match="body_cap_thickness must lie"):
        replace(LES_PAUL, body_cap_thickness=LES_PAUL.body_thickness).build(wired=False)
    # A neck-through body takes none: both left alone there (as the web
    # app hides them).
    through = replace(CHAMBERED, neck_joint="neck_through").build(wired=False)
    assert through.body.cap_thickness == 0.0 and not through.body.core_cavities
    body = LES_PAUL.build(wired=False).body
    assert body.neck_pickup is not None
    route = TracedCavity("Route", body.neck_pickup.outline, 5.0)
    with pytest.raises(BodyGeometryError, match="need a separate top"):
        replace(body, cap_thickness=0.0, core_cavities=(route,))
    with pytest.raises(BodyGeometryError, match="wood of the core over the back"):
        replace(body, core_cavities=(replace(route, depth=body.core_thickness),))


def test_the_core_is_routed_before_its_top_is_glued_on() -> None:
    body = CHAMBERED.build().body
    plan = plan_body_machining(body, MachiningParameters())
    names = [setup.name for setup in plan.setups]
    assert names[:3] == ["Body_core_index_pins", "Body_core_top", "Body_index_pins"]
    assert len(plan.preview_outlines) == len(plan.setups)
    core = plan.core_top
    assert core is not None
    assert [path.name for path in core.toolpaths] == [
        c.name for c in body.core_cavities
    ]
    # Each to its depth below the core's own top (its work zero).
    for path, cavity in zip(core.toolpaths, body.core_cavities, strict=True):
        assert path.deepest_z() == pytest.approx(-cavity.depth)
    assert any("glue the 15.875 mm top on" in note for note in core.notes)
    assert any("through the top" in note for note in plan.index_pins.notes)
    # One piece: no core programs.
    plain = plan_body_machining(
        replace(LES_PAUL, body_cap_thickness=0.0).build().body, MachiningParameters()
    )
    assert plain.setups[0].name == "Body_index_pins"


def test_the_model_is_the_core_and_its_top() -> None:
    geometry = CHAMBERED.build()
    source = FreeCADScriptExporter().render_prototype001(
        geometry, step_path=Path("Prototype001.step")
    )
    assert "cap_feature = document.addObject('Part::Feature', 'Top')" in source
    assert "body_shape.cut(CORE_CUTTERS)" in source
    for cavity in geometry.body.core_cavities:
        assert f"# {cavity.name.lower()}\n" in source
    # Both in the STEP.
    assert "body_feature, cap_feature]," in source
    # The quick model draws them apart: the core up to the top's underside,
    # the top over it.
    rows = FreeCADScriptExporter.neck_loft_rows(
        geometry.neck_surface,
        geometry.headstock,
        geometry.joint_fillet_radius,
        geometry.volute,
    )
    parts = {part.name: part for part in preview_parts(geometry, rows)}
    assert set(parts) == {"Body", "Neck", "Fretboard", "Top"}
    split = -geometry.body.cap_thickness
    assert max(parts["Body"].positions[2::3]) == pytest.approx(split)
    assert min(parts["Top"].positions[2::3]) == pytest.approx(split)
    # The web app's quick model draws the wire channels too (built wired
    # under a top): their floors WIRE_CORE_CHANNEL_DEPTH under it.
    body = {part.name: part for part in _quick_base(CHAMBERED)}["Body"]
    floor = split - WIRE_CORE_CHANNEL_DEPTH
    assert any(z == pytest.approx(floor) for z in body.positions[2::3])
    for part in (parts["Body"], parts["Top"]):
        edges: Counter[tuple[int, int]] = Counter()
        tri = part.triangles
        for i in range(0, len(tri), 3):
            a, b, c = tri[i : i + 3]
            edges.update(((a, b), (b, c), (c, a)))
        assert all(n == 1 and (v, u) in edges for (u, v), n in edges.items())
