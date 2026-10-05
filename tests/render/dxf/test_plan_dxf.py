"""Tests for the DXF plan outlines and the sheet plates' layout."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from cncguitarwizard.geometry.primitives import Point2D
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.render.dxf import DxfDocument, render_covers_dxf, render_plan_dxf
from cncguitarwizard.workflows.prototype001 import Prototype001Build

GEOMETRY = Prototype001Parameters().build()


def _pairs(text: str) -> list[tuple[int, str]]:
    lines = text.splitlines()
    assert len(lines) % 2 == 0
    return [(int(lines[i]), lines[i + 1]) for i in range(0, len(lines), 2)]


def _entities(text: str) -> list[dict[str, Any]]:
    """Return the ENTITIES section's entities, a polyline with its vertices."""
    pairs = _pairs(text)
    start = pairs.index((2, "ENTITIES"))
    entities: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for code, value in pairs[start + 1 :]:
        if code == 0:
            if value in ("ENDSEC", "EOF"):
                break
            if value == "VERTEX":
                assert current is not None and current["type"] == "POLYLINE"
                current["vertices"].append({})
                continue
            if value == "SEQEND":
                continue
            current = {"type": value, "vertices": []}
            entities.append(current)
            continue
        assert current is not None
        vertices = current["vertices"]
        if current["type"] == "POLYLINE" and vertices and code in (10, 20, 8):
            vertices[-1][str(code)] = value
        else:
            current[str(code)] = value
    return entities


def _layers(text: str) -> dict[str, int]:
    pairs = _pairs(text)
    layers: dict[str, int] = {}
    for index, (code, value) in enumerate(pairs):
        if (code, value) == (0, "LAYER"):
            name = pairs[index + 1][1]
            colour = next(int(v) for c, v in pairs[index:] if c == 62)
            layers[name] = colour
    return layers


def test_the_plan_is_an_r12_dxf_a_layer_a_kind() -> None:
    text = render_plan_dxf(GEOMETRY)
    pairs = _pairs(text)
    assert pairs[:4] == [(0, "SECTION"), (2, "HEADER"), (9, "$ACADVER"), (1, "AC1009")]
    assert (9, "$INSUNITS") in pairs and pairs[-1] == (0, "EOF")
    layers = _layers(text)
    for name in (
        "BODY_OUTLINE",
        "NECK_OUTLINE",
        "HEADSTOCK_OUTLINE",
        "FRETBOARD_OUTLINE",
        "FRET_SLOTS",
        "INLAYS",
        "TUNER_HOLES",
        "BODY_TOP_CAVITIES",
        "BODY_REAR_CAVITIES",
        "BODY_HOLES_TOP",
        "BODY_HOLES_BACK",
        "WIRE_HOLES",
        "COVERS",
        "CENTERLINE",
    ):
        assert name in layers
    entities = _entities(text)
    # Every entity on a declared layer.
    assert all(entity["8"] in layers for entity in entities)

    def on(layer: str, kind: str) -> list[dict[str, Any]]:
        return [e for e in entities if e["8"] == layer and e["type"] == kind]

    (body,) = on("BODY_OUTLINE", "POLYLINE")
    assert body["70"] == "1"
    vertices = body["vertices"]
    assert isinstance(vertices, list)
    assert len(vertices) == len(GEOMETRY.body.outline.points)
    first = GEOMETRY.body.outline.points[0]
    assert float(vertices[0]["10"]) == pytest.approx(first.x, abs=1e-4)
    assert float(vertices[0]["20"]) == pytest.approx(first.y, abs=1e-4)
    assert len(on("FRET_SLOTS", "LINE")) == len(GEOMETRY.fret_layout.slots)
    assert len(on("INLAYS", "POLYLINE")) == len(GEOMETRY.inlay_layout.markers)
    assert len(on("TUNER_HOLES", "CIRCLE")) == len(GEOMETRY.tuner_layout.holes)
    assert len(on("BODY_TOP_CAVITIES", "POLYLINE")) == len(GEOMETRY.body.top_cavities)
    assert len(on("WIRE_HOLES", "LINE")) == len(GEOMETRY.body.wire_holes)
    hole = GEOMETRY.tuner_layout.holes[0]
    circle = on("TUNER_HOLES", "CIRCLE")[0]
    assert float(circle["40"]) == pytest.approx(hole.diameter / 2.0)


def test_a_zero_fret_and_a_relief_are_drawn_too() -> None:
    geometry = replace(
        Prototype001Parameters(),
        nut_style="zero_fret",
        body_engraving=True,
        body_engraving_pattern="camo",
    ).build()
    entities = _entities(render_plan_dxf(geometry))
    slots = [e for e in entities if e["8"] == "FRET_SLOTS"]
    assert len(slots) == len(geometry.fret_layout.slots) + 1
    engraving = geometry.body.engraving
    assert engraving is not None
    shapes = [e for e in entities if e["8"] == "ENGRAVING"]
    assert len(shapes) == len(engraving.pockets)
    assert all(shape["70"] == "1" for shape in shapes)


def test_the_plates_are_laid_out_apart_for_cutting() -> None:
    covers = GEOMETRY.covers
    text = render_covers_dxf(covers)
    assert text is not None
    entities = _entities(text)
    outlines = [e for e in entities if e["8"] == "COVER_OUTLINES"]
    assert len(outlines) == len(covers)
    boxes = []
    for outline in outlines:
        vertices = outline["vertices"]
        assert isinstance(vertices, list)
        xs = [float(v["10"]) for v in vertices]
        ys = [float(v["20"]) for v in vertices]
        boxes.append((min(xs), max(xs), min(ys), max(ys)))
    # Side by side, from the origin, none over another.
    assert min(box[0] for box in boxes) == pytest.approx(0.0, abs=1e-6)
    for (_, right, _, _), (left, _, _, _) in zip(boxes, boxes[1:], strict=False):
        assert left >= right + 9.99
    holes = [e for e in entities if e["8"] == "COVER_HOLES"]
    assert len(holes) == sum(len(c.holes) + len(c.slots) for c in covers)
    labels = [e for e in entities if e["type"] == "TEXT"]
    assert [label["1"] for label in labels] == [
        f"{cover.name} ({cover.thickness:g} mm)" for cover in covers
    ]
    assert render_covers_dxf(()) is None


def test_open_polylines_and_degenerate_ones() -> None:
    dxf = DxfDocument()
    layer = dxf.layer("A", 1)
    dxf.polyline([Point2D(0, 0), Point2D(1, 0)], layer, closed=False)
    dxf.polyline([Point2D(0, 0)], layer)  # too short: left out
    # A closing point equal to the first is dropped (the flag closes it).
    dxf.polyline([Point2D(0, 0), Point2D(1, 0), Point2D(1, 1), Point2D(0, 0)], layer)
    entities = _entities(dxf.render())
    assert [e["70"] for e in entities] == ["0", "1"]
    assert [len(e["vertices"]) for e in entities] == [2, 3]


def test_the_build_writes_both_dxf_files(tmp_path: Path) -> None:
    build = Prototype001Build(tmp_path, Prototype001Parameters(), run_freecad=False)
    assert "Writing the DXF outlines" in build.labels
    while build.advance():
        pass
    names = [path.name for path in build.result.dxf_paths]
    assert names == ["Prototype001_plan.dxf", "Prototype001_covers.dxf"]
    assert all((tmp_path / name).read_text().endswith("EOF\n") for name in names)
