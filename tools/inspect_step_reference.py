"""Create a compact geometric report for a reference neck STEP model.

Usage (with the FreeCAD command-line executable)::

    freecadcmd tools/inspect_step_reference.py /path/to/reference.step

The script only imports and analyses the supplied reference.  It does not
change the STEP file or the CNCguitarwizard model.
"""

from __future__ import annotations

import sys
from pathlib import Path

import FreeCAD as App
import Import


def _bbox_text(shape: object) -> str:
    """Return a concise millimetre bounding-box description."""
    box = shape.BoundBox
    return (
        f"X {box.XMin:.3f} .. {box.XMax:.3f} ({box.XLength:.3f}) | "
        f"Y {box.YMin:.3f} .. {box.YMax:.3f} ({box.YLength:.3f}) | "
        f"Z {box.ZMin:.3f} .. {box.ZMax:.3f} ({box.ZLength:.3f})"
    )


def _face_description(index: int, face: object) -> str:
    """Describe a face independently of its unstable STEP topology number."""
    center = face.CenterOfMass
    surface_name = type(face.Surface).__name__
    return (
        f"  Face {index:>3}: {surface_name:<28} area={face.Area:10.3f} | "
        f"center=({center.x:.3f}, {center.y:.3f}, {center.z:.3f}) | "
        f"{_bbox_text(face)}"
    )


def inspect(step_path: Path) -> Path:
    """Import *step_path* and write a report beside it.

    The report lists the large faces of objects whose label begins with
    ``Neck``.  Those faces expose the planar mounting section and the curved
    heel-to-neck blend without needing to modify the reference geometry.
    """
    if not step_path.is_file():
        raise FileNotFoundError(f"Reference STEP not found: {step_path}")

    document = App.newDocument("ReferenceNeckInspection")
    Import.insert(str(step_path), document.Name)
    document.recompute()

    report_path = step_path.with_name(f"{step_path.stem}.inspection.txt")
    lines = [
        "Reference neck STEP inspection",
        f"Source: {step_path}",
        "Units: millimetres (as supplied by the STEP file)",
        "",
    ]

    shapes = [
        obj
        for obj in document.Objects
        if hasattr(obj, "Shape") and not obj.Shape.isNull()
    ]
    lines.append(f"Imported shape objects: {len(shapes)}")
    lines.append("")

    for obj in shapes:
        label = getattr(obj, "Label", obj.Name)
        if not label.lower().startswith("neck"):
            continue

        shape = obj.Shape
        lines.extend(
            [
                label,
                "-" * len(label),
                f"Solid count: {len(shape.Solids)}",
                f"Face count: {len(shape.Faces)}",
                f"Bounding box: {_bbox_text(shape)}",
                "",
                "Largest faces (flat heel and its blend are normally here):",
            ]
        )
        faces = list(enumerate(shape.Faces, start=1))
        faces.sort(key=lambda item: item[1].Area, reverse=True)
        lines.extend(_face_description(index, face) for index, face in faces[:30])
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> None:
    """Run the command-line reference inspection."""
    if len(sys.argv) != 2:
        raise SystemExit("Usage: freecadcmd tools/inspect_step_reference.py PATH.step")
    print(f"Wrote inspection report: {inspect(Path(sys.argv[1]))}")


if __name__ == "__main__":
    main()
