"""Generate deterministic Python scripts for execution inside FreeCAD."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

from ...geometry.fretboard import FretboardSurface, FretLayout
from ...geometry.neck import (
    HeadstockSolid,
    NeckBackSurface,
    TrussRodChannel,
    TunerLayout,
)
from ...geometry.primitives import Point3D
from ...presets import Prototype001Geometry
from .exceptions import FreeCADBackendError

_VALID_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class FreeCADScriptExporter:
    """Render loft-ready geometry as a standalone FreeCAD Python script.

    The exporter itself has no FreeCAD dependency. Generated scripts import
    ``FreeCAD`` and ``Part`` only when executed inside FreeCAD.
    """

    def render_neck_back(
        self,
        surface: NeckBackSurface,
        document_name: str = "CNCguitarwizard",
        object_name: str = "NeckBack",
        fcstd_path: Path | None = None,
        step_path: Path | None = None,
    ) -> str:
        """Return a FreeCAD script that lofts the neck-back solid.

        Args:
            surface: Backend-independent neck-back surface.
            document_name: FreeCAD document identifier.
            object_name: FreeCAD object identifier.
            fcstd_path: Optional destination for the FreeCAD document.
            step_path: Optional destination for the STEP model.

        Returns:
            Standalone Python source for execution inside FreeCAD.
        """
        rows = tuple(self._close_neck_row(row) for row in surface.mesh.rows)
        return self._render_loft_script(
            rows,
            document_name,
            object_name,
            fcstd_path,
            step_path,
        )

    def render_prototype001(
        self,
        geometry: Prototype001Geometry,
        join_headstock_to_neck: bool = True,
        fcstd_path: Path | None = None,
        step_path: Path | None = None,
    ) -> str:
        """Return a complete FreeCAD script from one Prototype001 model.

        Args:
            geometry: Fully built Prototype001 geometry bundle.
            join_headstock_to_neck: Fuse headstock and neck for manufacturing.
            fcstd_path: Optional destination for the FreeCAD document.
            step_path: Optional destination for the combined STEP export.

        Returns:
            Standalone Python source for execution inside FreeCAD.
        """
        return self.render_neck_assembly(
            geometry.neck_surface,
            geometry.fretboard_surface,
            truss_rod_channel=geometry.truss_rod_channel,
            headstock=geometry.headstock,
            tuner_layout=geometry.tuner_layout,
            tuner_chamfer_depth=geometry.tuner_chamfer_depth,
            joint_fillet_radius=geometry.joint_fillet_radius,
            join_headstock_to_neck=join_headstock_to_neck,
            fret_layout=geometry.fret_layout,
            fret_slot_width=geometry.fret_slot_width,
            fret_slot_depth=geometry.fret_slot_depth,
            fcstd_path=fcstd_path,
            step_path=step_path,
        )

    def render_fretboard(
        self,
        surface: FretboardSurface,
        document_name: str = "CNCguitarwizard",
        object_name: str = "Fretboard",
        fcstd_path: Path | None = None,
        step_path: Path | None = None,
    ) -> str:
        """Return a FreeCAD script that lofts the fretboard solid.

        Args:
            surface: Backend-independent fretboard playing surface.
            document_name: FreeCAD document identifier.
            object_name: FreeCAD object identifier.
            fcstd_path: Optional destination for the FreeCAD document.
            step_path: Optional destination for the STEP model.

        Returns:
            Standalone Python source for execution inside FreeCAD.
        """
        rows = tuple(self._close_fretboard_row(row) for row in surface.mesh.rows)
        return self._render_loft_script(
            rows,
            document_name,
            object_name,
            fcstd_path,
            step_path,
        )

    def render_neck_assembly(
        self,
        neck_surface: NeckBackSurface,
        fretboard_surface: FretboardSurface,
        document_name: str = "CNCguitarwizard",
        neck_object_name: str = "NeckBack",
        fretboard_object_name: str = "Fretboard",
        headstock_object_name: str = "Headstock",
        truss_rod_channel: TrussRodChannel | None = None,
        headstock: HeadstockSolid | None = None,
        tuner_layout: TunerLayout | None = None,
        tuner_chamfer_depth: float = 0.2,
        joint_fillet_radius: float = 0.0,
        join_headstock_to_neck: bool = False,
        fret_layout: FretLayout | None = None,
        fret_slot_width: float = 0.6,
        fret_slot_depth: float = 2.7,
        fcstd_path: Path | None = None,
        step_path: Path | None = None,
    ) -> str:
        """Return a FreeCAD script containing neck and fretboard solids.

        The two solids remain separate document objects so their fit and
        manufacturing geometry can be inspected independently.

        Args:
            neck_surface: Backend-independent neck-back surface.
            fretboard_surface: Backend-independent fretboard surface.
            document_name: FreeCAD document identifier.
            neck_object_name: FreeCAD identifier for the neck object.
            fretboard_object_name: FreeCAD identifier for the fretboard.
            headstock_object_name: FreeCAD identifier for the headstock.
            truss_rod_channel: Optional rectangular channel cut from the neck.
            headstock: Optional angled headstock solid.
            tuner_layout: Optional six-hole layout cut through the headstock.
            tuner_chamfer_depth: Depth of the 45-degree top-edge chamfer.
            joint_fillet_radius: Radius for lateral heel and headstock joints.
            join_headstock_to_neck: Fuse headstock and neck into one wood solid.
            fret_layout: Optional bounded fret slots cut into the fretboard.
            fret_slot_width: Width of each fret slot in millimetres.
            fret_slot_depth: Vertical slot depth below the playing surface.
            fcstd_path: Optional destination for the FreeCAD document.
            step_path: Optional destination for the combined STEP export.

        Returns:
            Standalone Python source for execution inside FreeCAD.
        """
        self._validate_identifier(document_name, "document")
        self._validate_identifier(neck_object_name, "neck object")
        self._validate_identifier(fretboard_object_name, "fretboard object")
        self._validate_identifier(headstock_object_name, "headstock object")
        if neck_object_name == fretboard_object_name:
            raise FreeCADBackendError(
                "Neck and fretboard object names must be different."
            )
        object_names = (neck_object_name, fretboard_object_name)
        if headstock is not None and headstock_object_name in object_names:
            raise FreeCADBackendError(
                "Headstock object name must differ from other assembly objects."
            )
        self._validate_output_path(fcstd_path, {".fcstd"}, "FreeCAD")
        self._validate_output_path(step_path, {".step", ".stp"}, "STEP")
        self._validate_truss_rod_channel(neck_surface, truss_rod_channel)
        self._validate_tuner_layout(
            headstock,
            tuner_layout,
            tuner_chamfer_depth,
        )
        if (
            not math.isfinite(joint_fillet_radius)
            or joint_fillet_radius < 0.0
            or joint_fillet_radius > neck_surface.final_fret_thickness / 2.0
        ):
            raise FreeCADBackendError(
                "Joint fillet radius must be finite, non-negative, and no "
                "greater than half the heel thickness."
            )
        self._validate_headstock_join(
            neck_surface,
            headstock,
            join_headstock_to_neck,
        )
        self._validate_fret_slots(
            fretboard_surface,
            fret_layout,
            fret_slot_width,
            fret_slot_depth,
        )

        heel_start = (
            neck_surface.neck_outline.last_fret_position
            - neck_surface.heel_flat_start_offset
        )
        heel_start_index = neck_surface.station_positions.index(heel_start)
        neck_rows = tuple(
            self._close_neck_row(row)
            for row in neck_surface.mesh.rows[: heel_start_index + 1]
        )
        heel_length = (
            neck_surface.heel_flat_start_offset
            + neck_surface.neck_outline.heel_length
        )
        heel_start_fraction = (
            heel_start / neck_surface.neck_outline.last_fret_position
        )
        heel_start_width = (
            neck_surface.neck_outline.nut_width
            + (
                neck_surface.neck_outline.last_fret_width
                - neck_surface.neck_outline.nut_width
            )
            * heel_start_fraction
        )
        heel_end_width = neck_surface.neck_outline.heel_width
        heel_thickness = neck_surface.final_fret_thickness
        fretboard_rows = tuple(
            self._close_fretboard_row(row)
            for row in fretboard_surface.mesh.rows
        )
        fret_surface_rows = fretboard_surface.mesh.rows[
            1 : fretboard_surface.fret_count + 1
        ]
        export_features = "[neck_feature, fretboard_feature]"
        if headstock is not None and not join_headstock_to_neck:
            export_features = (
                "[neck_feature, fretboard_feature, headstock_feature]"
            )
        output_commands = self._render_output_commands(
            fcstd_path,
            step_path,
            export_features,
        )
        truss_rod_source = self._render_truss_rod_cut(truss_rod_channel)
        fret_slot_source = self._render_fret_slot_cut(
            fret_layout,
            fret_slot_width,
            fret_slot_depth,
        )
        serialized_fret_rows = (
            f"FRET_SURFACE_ROWS = {self._serialize_rows(fret_surface_rows)}\n"
            if fret_layout is not None
            else ""
        )
        headstock_source = self._render_headstock(
            headstock,
            headstock_object_name,
            tuner_layout,
            tuner_chamfer_depth,
            joint_fillet_radius,
            join_headstock_to_neck,
        )

        return (
            '"""Generated by CNCguitarwizard. Do not edit manually."""\n\n'
            "import FreeCAD as App\n"
            "import Part\n\n"
            f"NECK_SECTION_POINTS = {self._serialize_rows(neck_rows)}\n"
            "HEEL_BLOCK = "
            f"[{heel_start},{heel_length},{heel_start_width},"
            f"{heel_end_width},{heel_thickness}]\n"
            "FRETBOARD_SECTION_POINTS = "
            f"{self._serialize_rows(fretboard_rows)}\n"
            f"{serialized_fret_rows}\n"
            "def make_loft(section_points):\n"
            '    """Create a solid loft from closed XYZ sections."""\n'
            "    sections = []\n"
            "    for points in section_points:\n"
            "        vectors = [App.Vector(x, y, z) for x, y, z in points]\n"
            "        vectors.append(vectors[0])\n"
            "        sections.append(Part.makePolygon(vectors))\n"
            "    shape = Part.makeLoft(sections, True, False, False)\n"
            "    return require_shape(shape, \"loft\")\n\n"
            "def require_shape(shape, operation):\n"
            '    """Reject null or invalid FreeCAD operation results."""\n'
            "    if shape.isNull():\n"
            "        raise RuntimeError(f\"{operation} produced a null shape\")\n"
            "    if not shape.isValid():\n"
            "        raise RuntimeError(f\"{operation} produced an invalid shape\")\n"
            "    return shape\n\n"
            "def side_joint_edges(shape, joint_x, minimum_abs_y, x_tolerance):\n"
            '    """Return lateral edges local to one solid joint."""\n'
            "    return [\n"
            "        edge\n"
            "        for edge in shape.Edges\n"
            "        if any(\n"
            "            abs(vertex.Point.y) >= minimum_abs_y\n"
            "            for vertex in edge.Vertexes\n"
            "        )\n"
            "        and edge.BoundBox.XMin >= joint_x - x_tolerance\n"
            "        and edge.BoundBox.XMax <= joint_x + x_tolerance\n"
            "    ]\n\n"
            "def safe_fillet(shape, radius, edges, operation):\n"
            '    """Apply the largest valid radius without aborting the build."""\n'
            "    if radius <= 0.0 or not edges:\n"
            "        return shape\n"
            "    for factor in (1.0, 0.75, 0.5, 0.25):\n"
            "        attempted_radius = radius * factor\n"
            "        try:\n"
            "            candidate = shape.makeFillet(attempted_radius, edges)\n"
            "        except Exception as error:\n"
            "            print(\n"
            "                f\"WARNING: {operation} radius \"\n"
            "                f\"{attempted_radius:.3f} mm failed: {error}\"\n"
            "            )\n"
            "            continue\n"
            "        if not candidate.isNull() and candidate.isValid():\n"
            "            print(\n"
            "                f\"{operation}: applied {attempted_radius:.3f} mm\"\n"
            "            )\n"
            "            return candidate\n"
            "    print(f\"WARNING: {operation} skipped; base transition retained\")\n"
            "    return shape\n\n"
            f'document = App.newDocument("{document_name}")\n'
            "neck_shape = make_loft(NECK_SECTION_POINTS)\n"
            "heel_start, heel_length, heel_start_width, "
            "heel_end_width, heel_thickness = HEEL_BLOCK\n"
            "heel_end = heel_start + heel_length\n"
            "heel_bottom = [\n"
            "    App.Vector(heel_start, -heel_start_width / 2.0, "
            "-heel_thickness),\n"
            "    App.Vector(heel_end, -heel_end_width / 2.0, "
            "-heel_thickness),\n"
            "    App.Vector(heel_end, heel_end_width / 2.0, "
            "-heel_thickness),\n"
            "    App.Vector(heel_start, heel_start_width / 2.0, "
            "-heel_thickness),\n"
            "]\n"
            "heel_bottom.append(heel_bottom[0])\n"
            "heel_face = Part.Face(Part.makePolygon(heel_bottom))\n"
            "heel_shape = heel_face.extrude("
            "App.Vector(0.0, 0.0, heel_thickness))\n"
            f"joint_fillet_radius = {joint_fillet_radius}\n"
            "neck_shape = require_shape(\n"
            "    neck_shape.fuse(heel_shape).removeSplitter(),\n"
            '    "heel-block fusion",\n'
            ")\n"
            "if joint_fillet_radius > 0.0:\n"
            "    heel_joint_edges = side_joint_edges(\n"
            "        neck_shape,\n"
            "        heel_start,\n"
            "        heel_start_width / 2.0 - 0.1,\n"
            "        0.25,\n"
            "    )\n"
            "    neck_shape = safe_fillet(\n"
            "        neck_shape,\n"
            "        joint_fillet_radius,\n"
            "        heel_joint_edges,\n"
            '        "heel side-joint fillet",\n'
            "    )\n"
            f"{truss_rod_source}"
            "neck_feature = document.addObject("
            f'"Part::Feature", "{neck_object_name}")\n'
            "neck_feature.Shape = neck_shape\n"
            "fretboard_feature = document.addObject("
            f'"Part::Feature", "{fretboard_object_name}")\n'
            "fretboard_shape = make_loft(FRETBOARD_SECTION_POINTS)\n"
            f"{fret_slot_source}"
            "fretboard_feature.Shape = fretboard_shape\n"
            f"{headstock_source}"
            "document.recompute()\n"
            f"{output_commands}"
        )

    def _render_headstock(
        self,
        headstock: HeadstockSolid | None,
        object_name: str,
        tuner_layout: TunerLayout | None,
        tuner_chamfer_depth: float,
        joint_fillet_radius: float,
        join_to_neck: bool,
    ) -> str:
        """Return FreeCAD commands that create an angled headstock solid."""
        if headstock is None:
            return ""

        boundary = self._serialize_points(headstock.top_boundary)
        vector = headstock.extrusion_vector
        tuner_source = self._render_tuner_hole_cuts(
            headstock,
            tuner_layout,
            tuner_chamfer_depth,
        )
        feature_source = (
            "neck_shape = require_shape(\n"
            "    neck_shape.fuse(headstock_shape),\n"
            '    "headstock-to-neck fusion",\n'
            ")\n"
            "neck_feature.Shape = neck_shape\n"
            if join_to_neck
            else (
                "headstock_feature = document.addObject("
                f'"Part::Feature", "{object_name}")\n'
                "headstock_feature.Shape = headstock_shape\n"
            )
        )
        return (
            f"HEADSTOCK_BOUNDARY = {boundary}\n"
            "headstock_vectors = "
            "[App.Vector(x, y, z) for x, y, z in HEADSTOCK_BOUNDARY]\n"
            "headstock_vectors.append(headstock_vectors[0])\n"
            "headstock_face = Part.Face(Part.makePolygon(headstock_vectors))\n"
            "headstock_shape = headstock_face.extrude("
            f"App.Vector({vector.x}, {vector.y}, {vector.z}))\n"
            f"{tuner_source}"
            "if joint_fillet_radius > 0.0:\n"
            "    headstock_joint_edges = side_joint_edges(\n"
            "        headstock_shape,\n"
            "        0.0,\n"
            f"        {headstock.plan.nut_width / 2.0 - 0.1},\n"
            f"        {abs(vector.x) + 0.1},\n"
            "    )\n"
            "    headstock_shape = safe_fillet(\n"
            "        headstock_shape,\n"
            "        joint_fillet_radius,\n"
            "        headstock_joint_edges,\n"
            '        "headstock side-joint fillet",\n'
            "    )\n"
            f"{feature_source}"
        )

    @staticmethod
    def _render_tuner_hole_cuts(
        headstock: HeadstockSolid,
        layout: TunerLayout | None,
        chamfer_depth: float,
    ) -> str:
        """Return FreeCAD commands for six normal-through tuner holes."""
        if layout is None:
            return ""

        radians = math.radians(headstock.angle.angle_degrees)
        tangent = math.tan(radians)
        holes = [
            [
                hole.center.x,
                hole.center.y,
                hole.center.x * tangent,
                hole.diameter,
            ]
            for hole in layout.holes
        ]
        axis = headstock.extrusion_vector
        axis_x = axis.x / headstock.thickness
        axis_y = axis.y / headstock.thickness
        axis_z = axis.z / headstock.thickness
        return (
            f"TUNER_HOLES = {json.dumps(holes, separators=(',', ':'))}\n"
            f"tuner_axis = App.Vector({axis_x}, {axis_y}, {axis_z})\n"
            "tuner_overcut = 1.0\n"
            f"tuner_chamfer_depth = {chamfer_depth}\n"
            "for x, y, z, diameter in TUNER_HOLES:\n"
            "    top_center = App.Vector(x, y, z)\n"
            "    cutter_start = top_center - tuner_axis * tuner_overcut\n"
            "    cutter = Part.makeCylinder(\n"
            "        diameter / 2.0,\n"
            f"        {headstock.thickness} + 2.0 * tuner_overcut,\n"
            "        cutter_start,\n"
            "        tuner_axis,\n"
            "    )\n"
            "    headstock_shape = require_shape(\n"
            "        headstock_shape.cut(cutter),\n"
            '        "tuner-hole cut",\n'
            "    )\n"
            "    if tuner_chamfer_depth > 0.0:\n"
            "        chamfer = Part.makeCone(\n"
            "            diameter / 2.0 + tuner_chamfer_depth,\n"
            "            diameter / 2.0,\n"
            "            tuner_chamfer_depth,\n"
            "            top_center,\n"
            "            tuner_axis,\n"
            "        )\n"
            "        headstock_shape = require_shape(\n"
            "            headstock_shape.cut(chamfer),\n"
            '            "tuner chamfer cut",\n'
            "        )\n"
        )

    @staticmethod
    def _render_fret_slot_cut(
        layout: FretLayout | None,
        slot_width: float,
        slot_depth: float,
    ) -> str:
        """Return FreeCAD commands for radius-following fret-slot cuts."""
        if layout is None:
            return ""

        return (
            f"fret_slot_width = {slot_width}\n"
            f"fret_slot_depth = {slot_depth}\n"
            "fret_slot_surface_overcut = 0.2\n"
            "fret_slot_side_overcut = 1.0\n"
            "for fret_index, surface_row in enumerate(\n"
            "    FRET_SURFACE_ROWS,\n"
            "    start=1,\n"
            "):\n"
            "    position = surface_row[0][0]\n"
            "    profile_x = position - fret_slot_width / 2.0\n"
            "    first = surface_row[0]\n"
            "    last = surface_row[-1]\n"
            "    extended_row = [\n"
            "        (first[0], first[1] - fret_slot_side_overcut, first[2]),\n"
            "        *surface_row,\n"
            "        (last[0], last[1] + fret_slot_side_overcut, last[2]),\n"
            "    ]\n"
            "    profile = [\n"
            "        App.Vector(\n"
            "            profile_x,\n"
            "            y,\n"
            "            z + fret_slot_surface_overcut,\n"
            "        )\n"
            "        for _, y, z in extended_row\n"
            "    ]\n"
            "    profile.extend(\n"
            "        App.Vector(profile_x, y, z - fret_slot_depth)\n"
            "        for _, y, z in reversed(extended_row)\n"
            "    )\n"
            "    profile.append(profile[0])\n"
            "    slot_face = Part.Face(Part.makePolygon(profile))\n"
            "    slot_shape = slot_face.extrude(\n"
            "        App.Vector(fret_slot_width, 0.0, 0.0)\n"
            "    )\n"
            "    fretboard_shape = require_shape(\n"
            "        fretboard_shape.cut(slot_shape).removeSplitter(),\n"
            '        f"fret-slot cut {fret_index}",\n'
            "    )\n"
        )

    @staticmethod
    def _render_truss_rod_cut(
        channel: TrussRodChannel | None,
    ) -> str:
        """Return FreeCAD commands that subtract a rectangular rod channel."""
        if channel is None:
            return ""

        start = channel.start_position
        lateral_start = -channel.width / 2.0
        vertical_start = -channel.depth
        return (
            "truss_rod_shape = Part.makeBox("
            f"{channel.length}, {channel.width}, {channel.depth}, "
            f"App.Vector({start}, {lateral_start}, {vertical_start}))\n"
            "neck_shape = require_shape(\n"
            "    neck_shape.cut(truss_rod_shape),\n"
            '    "truss-rod cut",\n'
            ")\n"
        )

    def write_script(self, path: Path, source: str) -> None:
        """Write generated FreeCAD source using UTF-8 encoding.

        Args:
            path: Destination ``.py`` or ``.FCMacro`` path.
            source: Script returned by a render method.
        """
        if path.suffix not in {".py", ".FCMacro"}:
            raise FreeCADBackendError(
                "FreeCAD scripts must use a .py or .FCMacro suffix."
            )
        path.write_text(source, encoding="utf-8")

    @staticmethod
    def _close_neck_row(row: tuple[Point3D, ...]) -> tuple[Point3D, ...]:
        """Close one neck-back section across the fretboard underside."""
        return row

    @staticmethod
    def _close_fretboard_row(row: tuple[Point3D, ...]) -> tuple[Point3D, ...]:
        """Close one radiused fretboard section across its flat underside."""
        first = row[0]
        last = row[-1]
        return (*row, Point3D(last.x, last.y, 0.0), Point3D(first.x, first.y, 0.0))

    def _render_loft_script(
        self,
        rows: tuple[tuple[Point3D, ...], ...],
        document_name: str,
        object_name: str,
        fcstd_path: Path | None,
        step_path: Path | None,
    ) -> str:
        """Return common FreeCAD loft source for closed section rows."""
        self._validate_identifier(document_name, "document")
        self._validate_identifier(object_name, "object")
        self._validate_output_path(fcstd_path, {".fcstd"}, "FreeCAD")
        self._validate_output_path(step_path, {".step", ".stp"}, "STEP")
        serialized_rows = self._serialize_rows(rows)
        output_commands = self._render_output_commands(
            fcstd_path,
            step_path,
            "[feature]",
        )

        return (
            '"""Generated by CNCguitarwizard. Do not edit manually."""\n\n'
            "import FreeCAD as App\n"
            "import Part\n\n"
            f"SECTION_POINTS = {serialized_rows}\n\n"
            "def closed_wire(points):\n"
            '    """Create one closed polygon wire from XYZ triples."""\n'
            "    vectors = [App.Vector(x, y, z) for x, y, z in points]\n"
            "    vectors.append(vectors[0])\n"
            "    return Part.makePolygon(vectors)\n\n"
            "def require_shape(shape, operation):\n"
            '    """Reject null or invalid FreeCAD operation results."""\n'
            "    if shape.isNull():\n"
            "        raise RuntimeError(f\"{operation} produced a null shape\")\n"
            "    if not shape.isValid():\n"
            "        raise RuntimeError(f\"{operation} produced an invalid shape\")\n"
            "    return shape\n\n"
            f'document = App.newDocument("{document_name}")\n'
            "sections = [closed_wire(points) for points in SECTION_POINTS]\n"
            "shape = require_shape(\n"
            "    Part.makeLoft(sections, True, False, False),\n"
            '    "loft",\n'
            ")\n"
            f'feature = document.addObject("Part::Feature", "{object_name}")\n'
            "feature.Shape = shape\n"
            "document.recompute()\n"
            f"{output_commands}"
        )

    @staticmethod
    def _render_output_commands(
        fcstd_path: Path | None,
        step_path: Path | None,
        step_objects: str,
    ) -> str:
        """Return optional FreeCAD document and STEP export commands."""
        commands: list[str] = []
        if fcstd_path is not None:
            path_literal = json.dumps(str(fcstd_path))
            commands.append(f"document.saveAs({path_literal})")
        if step_path is not None:
            path_literal = json.dumps(str(step_path))
            commands.append(f"Part.export({step_objects}, {path_literal})")
        if not commands:
            return ""
        return "\n".join(commands) + "\n"

    @staticmethod
    def _serialize_rows(rows: tuple[tuple[Point3D, ...], ...]) -> str:
        """Return compact deterministic JSON for section coordinates."""
        return json.dumps(
            [
                [[point.x, point.y, point.z] for point in row]
                for row in rows
            ],
            separators=(",", ":"),
        )

    @staticmethod
    def _serialize_points(points: tuple[Point3D, ...]) -> str:
        """Return compact deterministic JSON for three-dimensional points."""
        return json.dumps(
            [[point.x, point.y, point.z] for point in points],
            separators=(",", ":"),
        )

    @staticmethod
    def _validate_identifier(value: str, label: str) -> None:
        """Reject names that are unsafe in generated source and FreeCAD."""
        if not _VALID_IDENTIFIER.fullmatch(value):
            raise FreeCADBackendError(
                f"FreeCAD {label} name must be a valid identifier."
            )

    @staticmethod
    def _validate_output_path(
        path: Path | None,
        allowed_suffixes: set[str],
        label: str,
    ) -> None:
        """Reject output paths with a format-specific invalid suffix."""
        if path is not None and path.suffix.lower() not in allowed_suffixes:
            suffixes = " or ".join(sorted(allowed_suffixes))
            raise FreeCADBackendError(
                f"{label} output path must use a {suffixes} suffix."
            )

    @staticmethod
    def _validate_truss_rod_channel(
        surface: NeckBackSurface,
        channel: TrussRodChannel | None,
    ) -> None:
        """Ensure an optional channel belongs to and remains within the neck."""
        if channel is None:
            return
        if channel.neck_outline != surface.neck_outline:
            raise FreeCADBackendError(
                "Truss-rod channel and neck surface must share an outline."
            )
        if channel.depth >= surface.first_fret_thickness:
            raise FreeCADBackendError(
                "Truss-rod channel must leave wood beneath its floor."
            )

    @staticmethod
    def _validate_tuner_layout(
        headstock: HeadstockSolid | None,
        layout: TunerLayout | None,
        chamfer_depth: float,
    ) -> None:
        """Ensure optional tuner holes belong to the exported headstock."""
        if layout is None:
            return
        if headstock is None:
            raise FreeCADBackendError(
                "Tuner-hole export requires a headstock solid."
            )
        if layout.headstock != headstock.plan:
            raise FreeCADBackendError(
                "Tuner layout and headstock solid must share a plan."
            )
        if (
            not math.isfinite(chamfer_depth)
            or chamfer_depth < 0.0
            or chamfer_depth >= headstock.thickness
        ):
            raise FreeCADBackendError(
                "Tuner chamfer depth must be non-negative and less than "
                "the headstock thickness."
            )

    @staticmethod
    def _validate_headstock_join(
        neck_surface: NeckBackSurface,
        headstock: HeadstockSolid | None,
        join_to_neck: bool,
    ) -> None:
        """Ensure an optional headstock fusion has compatible geometry."""
        if not join_to_neck:
            return
        if headstock is None:
            raise FreeCADBackendError(
                "Joining the headstock requires a headstock solid."
            )
        if not math.isclose(
            headstock.plan.nut_width,
            neck_surface.neck_outline.nut_width,
        ):
            raise FreeCADBackendError(
                "Joined headstock and neck must share a nut width."
            )

    @staticmethod
    def _validate_fret_slots(
        surface: FretboardSurface,
        layout: FretLayout | None,
        slot_width: float,
        slot_depth: float,
    ) -> None:
        """Ensure optional fret slots match and remain within the fretboard."""
        if layout is None:
            return
        dimensions = (slot_width, slot_depth)
        if not all(
            math.isfinite(value) and value > 0.0 for value in dimensions
        ):
            raise FreeCADBackendError(
                "Fret-slot width and depth must be finite and positive."
            )
        if not math.isclose(
            layout.fretboard.scale_length,
            surface.scale_length,
        ):
            raise FreeCADBackendError(
                "Fret layout and fretboard surface must share a scale length."
            )
        if layout.fret_count != surface.fret_count:
            raise FreeCADBackendError(
                "Fret layout and fretboard surface must share a fret count."
            )
        surface_positions = surface.station_positions[
            1 : surface.fret_count + 1
        ]
        layout_positions = tuple(
            (slot.start.x + slot.end.x) / 2.0 for slot in layout.slots
        )
        if any(
            not math.isclose(surface_position, layout_position)
            for surface_position, layout_position in zip(
                surface_positions,
                layout_positions,
                strict=True,
            )
        ):
            raise FreeCADBackendError(
                "Fret layout positions do not match the fretboard surface."
            )
        minimum_thickness = min(
            point.z for row in surface.mesh.rows for point in row
        )
        if slot_depth >= minimum_thickness:
            raise FreeCADBackendError(
                "Fret slots must leave material beneath their floors."
            )
