"""Tests for FreeCAD's modules over the browser's OpenCascade
(``backends.occt.freecad_api``): its own arithmetic, and that every name
the build's FreeCAD scripts use is there."""

import ast
import json
import math
import os
from dataclasses import replace
from pathlib import Path

import pytest

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.backends.occt import freecad_api
from cncguitarwizard.backends.occt.freecad_api import (
    Placement,
    Rotation,
    Shape,
    Vector,
)
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES
from cncguitarwizard.presets.prototype001 import BODY_TEMPLATE_VALUES


def moved(placement: Placement, point: tuple[float, float, float]) -> tuple[float, ...]:
    return tuple(
        sum(row[k] * point[k] for k in range(3)) + row[3] for row in placement.matrix
    )


def test_vectors_add_scale_and_dot_as_freecads() -> None:
    a, b = Vector(1.0, 2.0, 2.0), Vector(0.0, 1.0, 0.0)

    assert a.Length == 3.0
    assert a * b == 2.0  # a vector times a vector: their dot product
    assert tuple(a * 2.0) == (2.0, 4.0, 4.0)
    assert tuple(a - b) == (1.0, 1.0, 2.0)
    assert tuple(Vector(3.0, 0.0, 4.0).normalize()) == (0.6, 0.0, 0.8)
    assert tuple(a.cross(b)) == (-2.0, 0.0, 1.0)


def test_a_placement_turns_about_its_centre_then_moves() -> None:
    tilt = Placement(
        Vector(0.0, 0.0, 5.0), Rotation(Vector(0, 1, 0), 90.0), Vector(10, 0, 0)
    )

    x, y, z = moved(tilt, (20.0, 0.0, 0.0))
    # Turned a quarter about Y round (10, 0, 0), then 5 up.
    assert (x, y, z) == pytest.approx((10.0, 0.0, -5.0))
    # FreeCAD's order: a.multiply(b) puts b first.
    shift = Placement(Vector(1.0, 0.0, 0.0))
    both = tilt.multiply(shift)
    assert moved(both, (19.0, 0.0, 0.0)) == pytest.approx((x, y, z))
    assert Placement().is_identity and not both.is_identity


def test_a_compound_cuts_with_each_of_its_members() -> None:
    # Regression: an epoxy tray's walls, one compound with two of them
    # alike, cut the tray's face into an invalid one in the browser (its
    # OpenCascade takes a tool's parts as never overlapping); FreeCAD's
    # was right.
    a, b, c = Shape("a"), Shape("b"), Shape("c")
    walls = Shape("walls", (a, Shape("inner", (b, c))))

    assert walls._tools() == [a, b, c]
    assert a._tools() == [a]


def scripts() -> dict[str, str]:
    d = Prototype001Parameters()
    designs = {
        "bolt-on": d,
        "engraved": replace(
            d,
            body_engraving=True,
            headstock_engraving_text="Jone",
            fretboard_binding_width=1.5,
            body_top_binding_width=3.0,
        ),
        "stepped": replace(
            d,
            body_shape=YOUR_DESIGN_TEMPLATES["alexi_hexed"][1],
            **BODY_TEMPLATE_VALUES["alexi_hexed"],
        ),
        "neck-through": replace(
            d,
            neck_joint="neck_through",
            body_top_bevel_width=12.0,
            body_back_bevel_width=12.0,
            inlay_style="runes",
            neck_carbon_rods=True,
        ),
        "epoxy": replace(
            d,
            body_epoxy_tray_depth=3.0,
            heel_width=58.0,
            truss_rod_install="back",
            headstock_angle=0.0,
            nut_jig=True,
            body_battery_box=True,
            neck_heel_end="round",
        ),
        "set": replace(
            d,
            neck_joint="set",
            headstock_pointed_volute=True,
            locking_nut="r2",
            truss_rod_adjustment="headstock",
            fretboard_scalloped=True,
        ),
        "carved": replace(d, body_carved_top=True, body_belly_cut_depth=10.0),
    }
    exporter = FreeCADScriptExporter()
    return {
        name: exporter.render_prototype001(
            parameters.build(),
            fcstd_path=Path("/m/P.FCStd"),
            step_path=Path("/m/P.step"),
        )
        for name, parameters in designs.items()
    }


# Python's own: what the scripts call on lists, numbers, text and modules.
PYTHON = (
    {name for kind in (list, dict, str, float, tuple, set) for name in dir(kind)}
    | set(dir(math))
    | set(dir(os))
    | set(dir(os.path))
    | set(dir(json))
)
# Only read with FreeCAD's window up, which there is not here.
WINDOW_ONLY = {"ViewObject"}


SCRIPTS = scripts()


@pytest.mark.parametrize(("design", "source"), list(SCRIPTS.items()), ids=list(SCRIPTS))
def test_every_name_the_script_uses_is_here(design: str, source: str) -> None:
    freecad_api.connect(object())  # names only: nothing is built
    import FreeCAD
    import Part

    modules = {"App": FreeCAD, "FreeCAD": FreeCAD, "Part": Part}
    provided = {
        name
        for kind in (
            freecad_api.Shape,
            Vector,
            freecad_api.BoundBox,
            freecad_api.Document,
            freecad_api.Feature,
            Placement,
            Rotation,
            freecad_api.BSplineSurface,
            freecad_api.LineSegment,
            freecad_api.Arc,
        )
        for name in dir(kind)
    } | {
        name
        for made in (
            freecad_api.Feature("x"),
            freecad_api.BoundBox((0, 0, 0), (1, 1, 1)),
            Vector(),
        )
        for name in vars(made)
    }
    missing = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Attribute):
            continue
        if isinstance(node.value, ast.Name) and node.value.id in modules:
            if not hasattr(modules[node.value.id], node.attr):
                missing.add(f"{node.value.id}.{node.attr}")
        elif node.attr not in provided | PYTHON | WINDOW_ONLY:
            missing.add(node.attr)

    assert not missing, f"{design}: {sorted(missing)}"


def test_the_page_is_offered_every_format_but_iges() -> None:
    from cncguitarwizard.backends.occt import FORMATS
    from cncguitarwizard.webapp import parameter_schema

    assert list(FORMATS) == ["step", "stl", "3mf", "obj", "glb", "brep"]
    assert parameter_schema()["model_formats"] == FORMATS


def test_the_builds_own_script_makes_its_spreadsheet_here(tmp_path: Path) -> None:
    # The build's script ends with the parameter sheet, a Spreadsheet::Sheet
    # FreeCAD keeps in the model: made here too, but no part of it.
    import re

    from cncguitarwizard.workflows import build_prototype001

    result = build_prototype001(tmp_path, run_freecad=False)
    script = result.python_path.read_text(encoding="utf-8")

    kinds = set(re.findall(r'addObject\(\s*"([^"]+)"', script))
    assert "Spreadsheet::Sheet" in kinds
    for kind in sorted(kinds):
        freecad_api.Document("kinds").addObject(kind, "x")  # each is made here

    document = freecad_api.Document("Prototype001")
    start = script.index("# The design's parameter sheet")
    end = script.index("document.recompute()", start)
    namespace: dict[str, object] = {"document": document}
    exec(compile(script[start:end], "sheet", "exec"), namespace)  # noqa: S102

    sheet = namespace["parameter_sheet"]
    assert isinstance(sheet, freecad_api.Sheet)
    named = {alias: cell for cell, alias in sheet.aliases.items()}
    assert sheet.cells["A1"] == "'group"
    assert sheet.cells[named["scale_length"]] == "609.6"
    assert sheet.cells[named["status"]] == "'READY FOR HUMAN REVIEW"
    assert document.Objects == []  # no part: the model takes none of it
