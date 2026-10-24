"""The build's FreeCAD script run on OpenCascade in the browser, and its
model written in the other 3D formats as files: no FreeCAD needed.

``connect`` takes OpenCascade's bindings once; ``export_zip`` builds the
model from the script (once a script: the next format reuses it) and
returns one format's files in a ZIP: each solid part shown in the model on
its own and the whole guitar, named as FreeCAD's export script names them
(``Prototype001_Body.stl``, ``Prototype001.stl``).
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from collections.abc import Callable, Sequence
from typing import Any

from ..freecad.formats import (
    EXPORT_FORMATS,
    MESH_ANGULAR_DEFLECTION,
    MESH_LINEAR_DEFLECTION,
)
from . import freecad_api
from .freecad_api import OCCError, Shape, engine
from .meshes import WRITERS, Mesh

FORMATS: dict[str, str] = {
    name: meaning for name, meaning in EXPORT_FORMATS.items() if name != "iges"
}
"""The formats written in the browser, by extension (IGES needs a writer the
browser's OpenCascade leaves out: FreeCAD's export script still writes it)."""

STEM = "Prototype001"
"""The files' names start with it, as the build's own."""

COLOURS: dict[str, tuple[float, float, float]] = {
    "NeckBack": (0.86, 0.73, 0.52),
    "Fretboard": (0.24, 0.15, 0.09),
}
"""A part's colour in the formats that keep one; any other part's
``BODY_COLOUR``."""

BODY_COLOUR = (0.72, 0.52, 0.32)

_MODEL: tuple[str, list[tuple[str, Shape]]] | None = None
"""The last script's digest and the parts it made."""


def connect(oc: Any) -> None:
    """Use ``oc`` (replicad-opencascadejs, initialised) from now on."""
    global _MODEL
    freecad_api.connect(oc)
    _MODEL = None


def build(
    script: str, report: Callable[[str], None] = print
) -> list[tuple[str, Shape]]:
    """Return the solid parts ``script`` makes, each placed as it is shown.

    Run as FreeCAD runs it (``__file__`` beside it); the same script again
    gives the same parts without building them again.

    Raises:
        OCCError: When the script makes no document or no solid part.
    """
    global _MODEL
    digest = hashlib.sha256(script.encode("utf-8")).hexdigest()
    if _MODEL is not None and _MODEL[0] == digest:
        return _MODEL[1]
    report("Building the 3D model…")
    freecad_api.DOCUMENTS.clear()
    namespace = {"__name__": "__main__", "__file__": f"/model/{STEM}_freecad.py"}
    exec(compile(script, f"{STEM}_freecad.py", "exec"), namespace)  # noqa: S102
    if not freecad_api.DOCUMENTS:
        raise OCCError("The script made no model.")
    parts = [
        (feature.Label, feature.Placement.apply(feature.Shape))
        for feature in freecad_api.DOCUMENTS[-1].Objects
        if feature.Visibility and not feature.Shape.isNull() and feature.Shape.Solids
    ]
    if not parts:
        raise OCCError("The model has no solid part.")
    _MODEL = (digest, parts)
    return parts


def mesh(label: str, shape: Shape) -> Mesh:
    """Return ``shape``'s triangles, within ``MESH_LINEAR_DEFLECTION`` of
    its surface, each face's turned to face outward."""
    e = engine()
    e.new(
        "BRepMesh_IncrementalMesh",
        shape.shape,
        MESH_LINEAR_DEFLECTION,
        False,
        MESH_ANGULAR_DEFLECTION,
        False,
    )
    reversed_face = e.enum("TopAbs_Orientation", "TopAbs_REVERSED")
    points: list[tuple[float, float, float]] = []
    triangles: list[tuple[int, int, int]] = []
    for face in shape.Faces:
        location = e.new("TopLoc_Location")
        triangulation = e.call("BRep_Tool", "Triangulation", face.shape, location, 0)
        # A face meshing left bare comes back as nothing (no null handle).
        if triangulation is None:
            continue
        trsf = location.Transformation()
        first = len(points)
        for index in range(1, triangulation.NbNodes() + 1):
            point = triangulation.Node(index).Transformed(trsf)
            points.append((point.X(), point.Y(), point.Z()))
        flip = face.shape.Orientation() == reversed_face
        for index in range(1, triangulation.NbTriangles() + 1):
            corner = triangulation.Triangle(index)
            a, b, c = (first + corner.Value(n) - 1 for n in (1, 2, 3))
            triangles.append((a, c, b) if flip else (a, b, c))
    return Mesh(label, tuple(points), tuple(triangles), COLOURS.get(label, BODY_COLOUR))


def _read(path: str) -> bytes:
    """Return a file OpenCascade wrote into its own file system, removing it."""
    fs = engine().oc.FS
    data = fs.readFile(path)
    if hasattr(data, "to_py"):  # Pyodide: a JavaScript Uint8Array
        data = data.to_py()
    fs.unlink(path)
    return bytes(data)


def step(shapes: Sequence[Shape]) -> bytes:
    """Return a STEP of ``shapes``, its surfaces exact."""
    e = engine()
    writer = e.new("STEPControl_Writer")
    mode = e.enum("STEPControl_StepModelType", "STEPControl_AsIs")
    for shape in shapes:
        writer.Transfer(shape.shape, mode, True, e.new("Message_ProgressRange"))
    path = "/model.step"
    if str(writer.Write(path)) != str(
        e.enum("IFSelect_ReturnStatus", "IFSelect_RetDone")
    ):
        raise OCCError("The STEP could not be written.")
    return _read(path)


def brep(shapes: Sequence[Shape]) -> bytes:
    """Return an OpenCascade BREP of ``shapes`` (one compound), exact."""
    path = "/model.brep"
    whole = freecad_api.makeCompound(shapes)
    if not engine().call(
        "BRepTools", "Write", whole.shape, path, engine().new("Message_ProgressRange")
    ):
        raise OCCError("The BREP could not be written.")
    return _read(path)


def files(format_name: str, parts: Sequence[tuple[str, Shape]]) -> dict[str, bytes]:
    """Return one format's files: each part's and the whole's.

    Raises:
        OCCError: For a format not written here.
    """
    if format_name not in FORMATS:
        raise OCCError(
            f"Unknown 3D format {format_name!r}: choose from {', '.join(FORMATS)}."
        )
    result: dict[str, bytes] = {}
    if format_name in WRITERS:
        write = WRITERS[format_name]
        meshes = [mesh(label, shape) for label, shape in parts]
        for part_mesh in meshes:
            result[f"{STEM}_{part_mesh.name}.{format_name}"] = write([part_mesh])
        result[f"{STEM}.{format_name}"] = write(meshes)
        return result
    write_exact = step if format_name == "step" else brep
    for label, shape in parts:
        result[f"{STEM}_{label}.{format_name}"] = write_exact([shape])
    result[f"{STEM}.{format_name}"] = write_exact([shape for _, shape in parts])
    return result


def export_zip(
    script: str, format_name: str, name: str = "", report: Callable[[str], None] = print
) -> tuple[str, bytes]:
    """Return a ZIP of the model ``script`` makes in ``format_name``, and
    its name (``<name>_stl.zip``, the guitar's name or ``Prototype001``).

    Raises:
        OCCError: When the model cannot be built or written.
    """
    parts = build(script, report)
    report(f"Writing {format_name.upper()}…")
    written = files(format_name, parts)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_name, data in written.items():
            archive.writestr(file_name, data)
    return f"{name or STEM}_{format_name}.zip", out.getvalue()
