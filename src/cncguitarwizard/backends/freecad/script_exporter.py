"""Generate deterministic Python scripts for execution inside FreeCAD."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ...geometry.body import BodySolid
from ...geometry.fretboard import FretboardSurface, FretLayout, InlayLayout
from ...geometry.neck import (
    HeadstockSolid,
    NeckBackSurface,
    TrussRodChannel,
    TunerLayout,
)
from ...geometry.primitives import Point2D, Point3D
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
        hide_headstock: bool = False,
        fcstd_path: Path | None = None,
        step_path: Path | None = None,
    ) -> str:
        """Return a complete FreeCAD script from one Prototype001 model.

        Args:
            geometry: Fully built Prototype001 geometry bundle.
            join_headstock_to_neck: Fuse headstock and neck for manufacturing.
            hide_headstock: Keep the headstock as a separate, hidden document
                object out of the inspection build while retaining the outer
                D-profile construction guides.
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
            # Prototype001 bakes the volute into NeckBackSurface.  Passing a
            # swell here would create a second, overlapping root loft and may
            # force FreeCAD to fall back to a compound rather than one solid.
            headstock_root_swell=0.0,
            nut_end_u_trim_depth=geometry.nut_end_u_trim_depth,
            nut_end_u_side_fillet_radius=(
                geometry.nut_end_u_side_fillet_radius
            ),
            headstock_outer_d_profile_guide_extension=(
                geometry.headstock_outer_d_profile_guide_extension
            ),
            heel_nose_radius=geometry.heel_nose_radius,
            heel_block_start_offset=geometry.heel_block_start_offset,
            join_headstock_to_neck=(
                join_headstock_to_neck and not hide_headstock
            ),
            hide_headstock=hide_headstock,
            fret_layout=geometry.fret_layout,
            fret_slot_width=geometry.fret_slot_width,
            fret_slot_depth=geometry.fret_slot_depth,
            inlay_layout=geometry.inlay_layout,
            nut_corner_radius=geometry.fret_layout.fretboard.nut_corner_radius,
            body=geometry.body,
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
        headstock_root_swell: float = 0.0,
        nut_end_u_trim_depth: float = 0.0,
        nut_end_u_side_fillet_radius: float = 0.0,
        headstock_outer_d_profile_guide_extension: float = 0.0,
        heel_nose_radius: float = 0.0,
        heel_block_start_offset: float | None = None,
        join_headstock_to_neck: bool = False,
        hide_headstock: bool = False,
        fret_layout: FretLayout | None = None,
        fret_slot_width: float = 0.6,
        fret_slot_depth: float = 2.7,
        inlay_layout: InlayLayout | None = None,
        nut_corner_radius: float = 8.0,
        body: BodySolid | None = None,
        body_object_name: str = "Body",
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
            headstock_root_swell: Extra depth of the long, continuous
                headstock-to-neck root surface. Zero retains a plain join.
            nut_end_u_trim_depth: Maximum heelward depth of the U-shaped
                neck-end boundary. The outer corners remain at the nut line.
            nut_end_u_side_fillet_radius: Radius of the two vertical
                cylinder-side fillets at the nut-end U trim. The central U
                arc remains unchanged.
            headstock_outer_d_profile_guide_extension: Construction-only
                extension of the two outer D-profile guide lines onto the
                headstock back. It does not alter the solid or the nut seat.
            heel_nose_radius: Radius of the convex heel-block front.
            heel_block_start_offset: Distance from the final fret to the
                straight mounting block. A value greater than the surface
                flat-start offset creates a positive fusion overlap.
            join_headstock_to_neck: Fuse headstock and neck into one wood solid.
            hide_headstock: Omit the headstock solid from an inspection build
                while retaining its construction-guide references. Requires a
                non-joined headstock.
            fret_layout: Optional bounded fret slots cut into the fretboard.
            fret_slot_width: Width of each fret slot in millimetres.
            fret_slot_depth: Vertical slot depth below the playing surface.
            inlay_layout: Optional barbed-wire position markers cut into
                the fretboard surface.
            nut_corner_radius: Radius of the two nut-end corner fillets.
            body: Optional solid-body slab with its own routed cavities.
            body_object_name: FreeCAD identifier for the body object.
            fcstd_path: Optional destination for the FreeCAD document.
            step_path: Optional destination for the combined STEP export.

        Returns:
            Standalone Python source for execution inside FreeCAD.
        """
        self._validate_identifier(document_name, "document")
        self._validate_identifier(neck_object_name, "neck object")
        self._validate_identifier(fretboard_object_name, "fretboard object")
        self._validate_identifier(headstock_object_name, "headstock object")
        self._validate_identifier(body_object_name, "body object")
        if neck_object_name == fretboard_object_name:
            raise FreeCADBackendError(
                "Neck and fretboard object names must be different."
            )
        object_names = (neck_object_name, fretboard_object_name)
        if body is not None and body_object_name in object_names:
            raise FreeCADBackendError(
                "Body object name must differ from other assembly objects."
            )
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
        if (
            not math.isfinite(headstock_root_swell)
            or headstock_root_swell < 0.0
            or headstock_root_swell > 3.0
        ):
            raise FreeCADBackendError(
                "Headstock root swell must be finite and between 0 and 3 mm."
            )
        if (
            not math.isfinite(nut_end_u_trim_depth)
            or not 0.0 <= nut_end_u_trim_depth <= 30.0
        ):
            raise FreeCADBackendError(
                "Nut-end U trim depth must be finite and between 0 and 30 mm."
            )
        if (
            not math.isfinite(nut_end_u_side_fillet_radius)
            or not 0.0 <= nut_end_u_side_fillet_radius <= 2.0
        ):
            raise FreeCADBackendError(
                "Nut-end U side fillet radius must be finite and between "
                "0 and 2 mm."
            )
        if (
            not math.isfinite(heel_nose_radius)
            or heel_nose_radius < 0.0
            or heel_nose_radius > neck_surface.final_fret_thickness / 2.0
        ):
            raise FreeCADBackendError(
                "Heel nose radius must be finite, non-negative, and no "
                "greater than half the heel thickness."
            )
        if (
            not math.isfinite(headstock_outer_d_profile_guide_extension)
            or headstock_outer_d_profile_guide_extension < 0.0
        ):
            raise FreeCADBackendError(
                "Outer D-profile guide extension must be finite and "
                "non-negative."
            )
        block_start_offset = (
            neck_surface.heel_flat_start_offset
            if heel_block_start_offset is None
            else heel_block_start_offset
        )
        if (
            not math.isfinite(block_start_offset)
            or block_start_offset < 0.0
            or block_start_offset
            > (
                neck_surface.heel_flat_start_offset
                + neck_surface.heel_transition_length
            )
        ):
            raise FreeCADBackendError(
                "Heel block start offset must be finite, non-negative, and "
                "must not extend beyond the heel transition."
            )
        if heel_nose_radius > 0.0 and not math.isclose(
            block_start_offset - neck_surface.heel_flat_start_offset,
            heel_nose_radius,
        ):
            raise FreeCADBackendError(
                "The heel-block overlap must equal the heel nose radius when "
                "the legacy heel nose is enabled."
            )
        self._validate_headstock_join(
            neck_surface,
            headstock,
            join_headstock_to_neck,
        )
        if hide_headstock and join_headstock_to_neck:
            raise FreeCADBackendError(
                "A headstock can be hidden only when it is not joined to the neck."
            )
        self._validate_fret_slots(
            fretboard_surface,
            fret_layout,
            fret_slot_width,
            fret_slot_depth,
        )
        self._validate_inlay_layout(fretboard_surface, inlay_layout)
        if (
            not math.isfinite(nut_corner_radius)
            or nut_corner_radius < 0.0
            or nut_corner_radius > fretboard_surface.nut_width / 2.0
        ):
            raise FreeCADBackendError(
                "Nut corner radius must be finite, non-negative, and no "
                "greater than half the nut width."
            )

        neck_rows = tuple(
            self._close_neck_row(row)
            for row in neck_surface.mesh.rows
        )
        headstock_join_extension = neck_surface.nut_root_side_extension
        headstock_joins_neck_loft = (
            join_headstock_to_neck
            and headstock is not None
            and headstock_join_extension > 0.0
        )
        if headstock_joins_neck_loft:
            assert headstock is not None  # narrowed by headstock_joins_neck_loft
            # Splice the headstock-root transition directly into the neck's
            # own loft, in place of its stations for x <= 0, rather than
            # building it as a separate shape boolean-fused in afterwards.
            # A separate transition shape — however well its boundaries are
            # matched — is still a second, differently-built surface meeting
            # neck_shape at a real seam; graft the transition rows into the
            # same ordered station list as the rest of the neck and there is
            # only one loft, so nothing reads as an inserted third piece
            # between the neck and the headstock.
            transition_sections = self._headstock_transition_sections(
                headstock,
                neck_surface,
                joint_fillet_radius,
            )
            # The transition's own last row is built 2 mm past
            # nut_transition_length (see _headstock_transition_sections's
            # blend_end — the small margin keeps this loft's internal seam
            # clear of the truss-rod channel, which starts its cut exactly
            # at nut_transition_length), not at the nut — it now carries
            # the neck's usual rise from the nut to full thickness too, so
            # the splice picks the neck's own stations back up only past
            # that point, not past x = 0.
            first_unblended_index = next(
                index
                for index, position in enumerate(
                    neck_surface.station_positions
                )
                if position > neck_surface.nut_transition_length + 2.0
            )
            neck_rows = transition_sections + tuple(
                self._close_neck_row(row)
                for row in neck_surface.mesh.rows[first_unblended_index:]
            )
        heel_transition_x = (
            neck_surface.neck_outline.last_fret_position
            - neck_surface.heel_flat_start_offset
        )
        fretboard_rows = tuple(
            self._close_fretboard_row(row)
            for row in fretboard_surface.mesh.rows
        )
        fret_surface_rows = fretboard_surface.mesh.rows[
            1 : fretboard_surface.fret_count + 1
        ]
        export_feature_names = ["neck_feature", "fretboard_feature"]
        if (
            headstock is not None
            and not join_headstock_to_neck
            and not hide_headstock
        ):
            export_feature_names.append("headstock_feature")
        if body is not None:
            export_feature_names.append("body_feature")
        export_features = "[" + ", ".join(export_feature_names) + "]"
        output_commands = self._render_output_commands(
            fcstd_path,
            step_path,
            export_features,
        )
        truss_rod_source = self._render_truss_rod_cut(truss_rod_channel)
        # The U trim reshapes the boundary at headstock_root_start_position
        # under the assumption that it is a genuine edge of neck_shape's own
        # material — true when there is no headstock-root transition, but
        # not any more once that transition's rows are spliced directly
        # into this same loft (see above): "the boundary" is now just an
        # arbitrary interior point of one continuous surface that already
        # continues smoothly into the headstock, and cutting a U-shaped
        # scoop through it there tears a real hole through the transition.
        nut_end_u_trim_source = (
            ""
            if headstock_joins_neck_loft
            else self._render_nut_end_u_trim(
                neck_surface,
                nut_end_u_trim_depth,
                nut_end_u_side_fillet_radius,
            )
        )
        fret_slot_source = self._render_fret_slot_cut(
            fret_layout,
            fret_slot_width,
            fret_slot_depth,
        )
        inlay_source = self._render_inlay_cuts(inlay_layout)
        body_source = self._render_body(body, body_object_name)
        serialized_fret_rows = (
            f"FRET_SURFACE_ROWS = {self._serialize_rows(fret_surface_rows)}\n"
            if fret_layout is not None
            else ""
        )
        headstock_source = self._render_headstock(
            headstock,
            neck_surface,
            headstock_object_name,
            tuner_layout,
            tuner_chamfer_depth,
            joint_fillet_radius,
            headstock_root_swell,
            join_headstock_to_neck,
            headstock_outer_d_profile_guide_extension,
            include_headstock=not hide_headstock,
        )

        return (
            '"""Generated by CNCguitarwizard. Do not edit manually."""\n\n'
            "import math\n\n"
            "import FreeCAD as App\n"
            "import Part\n\n"
            f"NECK_SECTION_POINTS = {self._serialize_rows(neck_rows)}\n"
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
            "def extrusion_side_edges(\n"
            "    shape, vx, vy, vz, angle_tolerance_deg, max_x=None\n"
            "):\n"
            '    """Return edges running parallel to an extrusion vector.\n\n'
            "    ``max_x``, when given, excludes any edge that reaches\n"
            "    above it — used to keep a joint boundary sharp (unfilleted)\n"
            "    while still rounding the rest of the same run of edges.\n"
            '    """\n'
            "    length = math.sqrt(vx * vx + vy * vy + vz * vz)\n"
            "    ux, uy, uz = vx / length, vy / length, vz / length\n"
            "    cos_tolerance = math.cos(math.radians(angle_tolerance_deg))\n"
            "    edges = []\n"
            "    for edge in shape.Edges:\n"
            "        if max_x is not None and edge.BoundBox.XMax > max_x:\n"
            "            continue\n"
            "        p0 = edge.Vertexes[0].Point\n"
            "        p1 = edge.Vertexes[-1].Point\n"
            "        dx, dy, dz = p1.x - p0.x, p1.y - p0.y, p1.z - p0.z\n"
            "        edge_length = math.sqrt(dx * dx + dy * dy + dz * dz)\n"
            "        if edge_length < 1e-6:\n"
            "            continue\n"
            "        cos_angle = abs(\n"
            "            (dx * ux + dy * uy + dz * uz) / edge_length\n"
            "        )\n"
            "        if cos_angle >= cos_tolerance:\n"
            "            edges.append(edge)\n"
            "    return edges\n\n"
            "def nut_corner_edges(shape, nut_x, nut_half_width, x_tolerance):\n"
            '    """Return the two vertical edges at the nut corners."""\n'
            "    return [\n"
            "        edge\n"
            "        for edge in shape.Edges\n"
            "        if edge.BoundBox.XMin >= nut_x - x_tolerance\n"
            "        and edge.BoundBox.XMax <= nut_x + x_tolerance\n"
            "        and edge.BoundBox.ZLength > x_tolerance\n"
            "        and max(\n"
            "            abs(edge.BoundBox.YMin),\n"
            "            abs(edge.BoundBox.YMax),\n"
            "        ) >= nut_half_width - x_tolerance\n"
            "    ]\n\n"
            "def fillet_stayed_within_bounds(shape, candidate, radius):\n"
            '    """Reject a fillet that grew the bounding box.\n\n'
            "    Rounding off a corner only ever removes material — the\n"
            "    result should always fit inside the original shape's own\n"
            "    bounding box, widened by a small margin for numerical\n"
            "    noise. FreeCAD's own fillet has been observed to instead\n"
            "    bulge its blend surface out past the original envelope on\n"
            "    a tight corner, leaving a real, disconnected sliver of\n"
            "    stray geometry that isValid() does not catch (it is still\n"
            "    a technically well-formed face, just one that should not\n"
            "    be there). A fillet radius has no business explaining a\n"
            "    multi-millimetre bbox change in a dimension it is not\n"
            "    even rounding along, so the margin only needs to absorb\n"
            "    genuine floating-point slack, not the radius itself.\n"
            '    """\n'
            "    margin = 0.05\n"
            "    base = shape.BoundBox\n"
            "    box = candidate.BoundBox\n"
            "    return (\n"
            "        box.XMin >= base.XMin - margin\n"
            "        and box.XMax <= base.XMax + margin\n"
            "        and box.YMin >= base.YMin - margin\n"
            "        and box.YMax <= base.YMax + margin\n"
            "        and box.ZMin >= base.ZMin - margin\n"
            "        and box.ZMax <= base.ZMax + margin\n"
            "    )\n\n"
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
            "        if (\n"
            "            not candidate.isNull()\n"
            "            and candidate.isValid()\n"
            "            and fillet_stayed_within_bounds(\n"
            "                shape, candidate, attempted_radius\n"
            "            )\n"
            "        ):\n"
            "            print(\n"
            "                f\"{operation}: applied {attempted_radius:.3f} mm\"\n"
            "            )\n"
            "            return candidate\n"
            "        print(\n"
            "            f\"WARNING: {operation} radius \"\n"
            "            f\"{attempted_radius:.3f} mm grew the bounding box; \"\n"
            "            \"discarded\"\n"
            "        )\n"
            "    print(f\"WARNING: {operation} skipped; base transition retained\")\n"
            "    return shape\n\n"
            "def preserves_base_shape(candidate, shapes):\n"
            '    """Reject a boolean result that has lost any input solid."""\n'
            "    expected_volume = max(shape.Volume for shape in shapes)\n"
            "    if candidate.Volume < expected_volume * 0.995:\n"
            "        return False\n"
            "    candidate_box = candidate.BoundBox\n"
            "    tolerance = 0.5\n"
            "    for shape in shapes:\n"
            "        shape_box = shape.BoundBox\n"
            "        if (\n"
            "            candidate_box.XMin > shape_box.XMin + tolerance\n"
            "            or candidate_box.XMax < shape_box.XMax - tolerance\n"
            "            or candidate_box.YMin > shape_box.YMin + tolerance\n"
            "            or candidate_box.YMax < shape_box.YMax - tolerance\n"
            "            or candidate_box.ZMin > shape_box.ZMin + tolerance\n"
            "            or candidate_box.ZMax < shape_box.ZMax - tolerance\n"
            "        ):\n"
            "            return False\n"
            "    return True\n\n"
            "def drop_negligible_solids(candidate, operation):\n"
            '    """Discard near-zero-volume sliver solids from a fuse.\n\n'
            "    A boolean fuse between two surfaces that meet only at a\n"
            "    tangent boundary can leave behind extra solids with volume\n"
            "    on the order of floating-point noise (fractions of a\n"
            "    cubic micrometre) — real topology, but no real material.\n"
            "    removeSplitter() does not clean these up because they are\n"
            "    not coincident with the main solid, only vanishingly\n"
            "    small. Keeping just the dominant solid turns that into\n"
            "    the single connected result it geometrically is; a\n"
            "    genuine missing pocket would instead show up as a large\n"
            "    volume shortfall, already caught by preserves_base_shape.\n"
            '    """\n'
            "    solids = candidate.Solids\n"
            "    if len(solids) <= 1:\n"
            "        return candidate\n"
            "    solids.sort(key=lambda solid: solid.Volume, reverse=True)\n"
            "    largest = solids[0]\n"
            "    negligible = 0.01\n"
            "    if all(solid.Volume < negligible for solid in solids[1:]):\n"
            "        print(\n"
            "            f\"{operation}: dropped {len(solids) - 1} \"\n"
            "            \"negligible sliver solid(s) from the fuse\"\n"
            "        )\n"
            "        return largest\n"
            "    print(\n"
            "        f\"WARNING: {operation} produced {len(solids)} solids \"\n"
            "        \"and more than one is non-negligible; inspect the \"\n"
            "        \"root before CAM.\"\n"
            "    )\n"
            "    return candidate\n\n"
            "def fuse_or_compound(shapes, operation):\n"
            '    """Fuse solids, retaining the complete neck on failure."""\n'
            "    # Pairwise sequential fuse is preferred over multiFuse: on\n"
            "    # overlapping, nearly-tangent lofted surfaces multiFuse has\n"
            "    # been observed to return a shape that reports isValid()\n"
            "    # True yet is missing a local pocket of material at a seam,\n"
            "    # which a bounding-box/volume safety net cannot reliably\n"
            "    # detect.\n"
            "    sequential = shapes[0]\n"
            "    sequential_failed = False\n"
            "    for shape in shapes[1:]:\n"
            "        try:\n"
            "            sequential = sequential.fuse(shape).removeSplitter()\n"
            "        except Exception as error:\n"
            "            print(\n"
            '                "WARNING: "\n'
            '                f"{operation} sequential fuse failed: "\n'
            '                f"{error}"\n'
            "            )\n"
            "            sequential_failed = True\n"
            "            break\n"
            "        if sequential.isNull() or not sequential.isValid():\n"
            "            print(\n"
            '                "WARNING: "\n'
            '                f"{operation} sequential fuse produced an "\n'
            '                "invalid shape"\n'
            "            )\n"
            "            sequential_failed = True\n"
            "            break\n"
            "    candidate = None if sequential_failed else sequential\n"
            "    if (\n"
            "        candidate is not None\n"
            "        and not candidate.isNull()\n"
            "        and candidate.isValid()\n"
            "        and preserves_base_shape(candidate, shapes)\n"
            "    ):\n"
            "        return drop_negligible_solids(candidate, operation)\n"
            "    print(\n"
            "        f\"WARNING: {operation} used a compound fallback; \"\n"
            "        \"inspect the root before CAM.\"\n"
            "    )\n"
            "    compound = Part.makeCompound(shapes)\n"
            "    return require_shape(compound, operation + \" fallback\")\n\n"
            f'document = App.newDocument("{document_name}")\n'
            "neck_shape = make_loft(NECK_SECTION_POINTS)\n"
            f"{nut_end_u_trim_source}"
            f"joint_fillet_radius = {joint_fillet_radius}\n"
            "if joint_fillet_radius > 0.0:\n"
            "    heel_transition_edges = side_joint_edges(\n"
            "        neck_shape,\n"
            f"        {heel_transition_x},\n"
            f"        {neck_surface.neck_outline.heel_width / 2.0 - 1.0},\n"
            "        2.0,\n"
            "    )\n"
            "    neck_shape = safe_fillet(\n"
            "        neck_shape,\n"
            "        joint_fillet_radius,\n"
            "        heel_transition_edges,\n"
            '        "heel-transition fillet",\n'
            "    )\n"
            f"{truss_rod_source}"
            "neck_feature = document.addObject("
            f'"Part::Feature", "{neck_object_name}")\n'
            "neck_feature.Shape = neck_shape\n"
            "fretboard_feature = document.addObject("
            f'"Part::Feature", "{fretboard_object_name}")\n'
            "fretboard_shape = make_loft(FRETBOARD_SECTION_POINTS)\n"
            f"nut_corner_radius = {nut_corner_radius}\n"
            "if nut_corner_radius > 0.0:\n"
            "    fretboard_nut_edges = nut_corner_edges(\n"
            "        fretboard_shape,\n"
            "        0.0,\n"
            f"        {fretboard_surface.nut_width / 2.0},\n"
            "        0.01,\n"
            "    )\n"
            "    fretboard_shape = safe_fillet(\n"
            "        fretboard_shape,\n"
            "        nut_corner_radius,\n"
            "        fretboard_nut_edges,\n"
            '        "fretboard nut-corner fillet",\n'
            "    )\n"
            f"{fret_slot_source}"
            f"{inlay_source}"
            "fretboard_feature.Shape = fretboard_shape\n"
            f"{headstock_source}"
            f"{body_source}"
            "document.recompute()\n"
            f"{output_commands}"
        )

    def _render_headstock(
        self,
        headstock: HeadstockSolid | None,
        neck_surface: NeckBackSurface,
        object_name: str,
        tuner_layout: TunerLayout | None,
        tuner_chamfer_depth: float,
        joint_fillet_radius: float,
        root_swell: float,
        join_to_neck: bool,
        outer_d_profile_guide_extension: float,
        include_headstock: bool,
    ) -> str:
        """Return FreeCAD commands that create an angled headstock solid."""
        if headstock is None:
            return ""

        boundary = self._serialize_points(headstock.top_boundary)
        vector = headstock.extrusion_vector
        guide_source = self._render_headstock_outer_d_profile_guides(
            headstock,
            neck_surface,
            outer_d_profile_guide_extension,
        )
        if not include_headstock:
            return guide_source
        root_extension = neck_surface.nut_root_side_extension
        headstock_joins_via_loft = (
            join_to_neck and root_extension > 0.0
        )
        lateral_edge_fillet_source = ""
        if joint_fillet_radius > 0.0 and not headstock_joins_via_loft:
            # Every edge of the top/bottom boundary polygon is, by
            # construction, exactly perpendicular to the extrusion vector
            # (the vector is that tilted plane's own normal), so selecting
            # edges parallel to it picks out only the genuine lateral "side"
            # edges running the length of the headstock, wherever the plan
            # has a vertex — a flat plate's true 90-degree corner. When the
            # headstock instead joins the neck via the loft-based tip below,
            # this real circular fillet is skipped entirely: applying it
            # only away from the joint (to avoid the tip's hand-built
            # rounding disagreeing with it there) left a visible bump right
            # where the real fillet started, since a fillet selected by
            # edge range has a hard on/off boundary, not a fade. The loft
            # below rounds the whole tip with one consistent formula
            # instead, so there is nothing left for this fillet to do.
            lateral_edge_fillet_source = (
                "headstock_lateral_edges = extrusion_side_edges(\n"
                "    headstock_shape,\n"
                f"    {vector.x}, {vector.y}, {vector.z},\n"
                "    5.0,\n"
                "    None,\n"
                ")\n"
                "headstock_shape = safe_fillet(\n"
                "    headstock_shape,\n"
                "    joint_fillet_radius,\n"
                "    headstock_lateral_edges,\n"
                '    "headstock lateral edge fillet",\n'
                ")\n"
            )
        root_source = ""
        # When headstock_joins_via_loft, neck_shape's own loft already
        # carries the entire headstock — tip included — as unblended
        # stations in place of its usual x <= 0 stations (see
        # render_neck_assembly and _headstock_transition_sections). There
        # is no separate headstock solid to build or fuse here any more;
        # neck_shape already is the complete result, unless root_swell
        # (a different, older, and much smaller feature) adds one more
        # piece on top.
        joined_shapes = (
            "[neck_shape]"
            if headstock_joins_via_loft
            else "[neck_shape, headstock_shape]"
        )
        if join_to_neck and root_swell > 0.0:
            root_sections = self._headstock_root_sections(
                neck_surface,
                root_swell,
            )
            root_source += (
                "HEADSTOCK_ROOT_SECTION_POINTS = "
                f"{self._serialize_rows(root_sections)}\n"
                "headstock_root_shape = make_loft(HEADSTOCK_ROOT_SECTION_POINTS)\n"
            )
            joined_shapes = joined_shapes.removesuffix("]") + (
                ", headstock_root_shape]"
            )
        tuner_source = self._render_tuner_hole_cuts(
            headstock,
            tuner_layout,
            tuner_chamfer_depth,
            "neck_shape" if headstock_joins_via_loft else "headstock_shape",
        )
        root_edge_fillet_source = ""
        if (
            join_to_neck
            and joint_fillet_radius > 0.0
            and root_extension <= 0.0
        ):
            root_edge_x_tolerance = abs(headstock.extrusion_vector.x) + 0.01
            root_edge_fillet_source = (
                "headstock_root_edges = nut_corner_edges(\n"
                "    headstock_shape,\n"
                "    0.0,\n"
                f"    {headstock.plan.nut_width / 2.0},\n"
                f"    {root_edge_x_tolerance},\n"
                ")\n"
                "headstock_shape = safe_fillet(\n"
                "    headstock_shape,\n"
                "    joint_fillet_radius,\n"
                "    headstock_root_edges,\n"
                '    "headstock-root edge fillet",\n'
                ")\n"
            )
        feature_source = (
            "neck_shape = fuse_or_compound(\n"
            f"    {joined_shapes},\n"
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
        if headstock_joins_via_loft:
            # The flat extrusion (and any fillet on it) is only needed to
            # build headstock_shape for the non-joined/root-swell paths
            # below. Here the entire headstock, tip included, is already
            # part of neck_shape's own loft (see render_neck_assembly and
            # _headstock_transition_sections) — skip building that unused
            # extrusion entirely, and cut tuner holes directly into
            # neck_shape rather than into a separate piece to fuse in.
            return (
                f"{root_source}"
                f"{tuner_source}"
                f"{feature_source}"
                f"{guide_source}"
            )
        return (
            f"HEADSTOCK_BOUNDARY = {boundary}\n"
            "headstock_vectors = "
            "[App.Vector(x, y, z) for x, y, z in HEADSTOCK_BOUNDARY]\n"
            "headstock_vectors.append(headstock_vectors[0])\n"
            "headstock_face = Part.Face(Part.makePolygon(headstock_vectors))\n"
            "headstock_shape = headstock_face.extrude("
            f"App.Vector({vector.x}, {vector.y}, {vector.z}))\n"
            f"{lateral_edge_fillet_source}"
            f"{tuner_source}"
            f"{root_edge_fillet_source}"
            f"{root_source}"
            f"{feature_source}"
            f"{guide_source}"
        )

    @staticmethod
    def _render_nut_end_u_trim(
        neck_surface: NeckBackSurface,
        depth: float,
        side_fillet_radius: float,
    ) -> str:
        """Return source that cuts the requested U-shaped neck-end boundary.

        The original neck-end line stays in place at both outer edges. Only
        the centre moves heelward by ``depth`` on a circular U curve, so this
        changes the end boundary without altering any D-profile section or
        the fixed 5 mm nut shelf on the headstock side. Only the two vertical
        cylinder side walls at the outer nut corners are then rounded into
        the surrounding side cheeks. The central U arc remains unchanged, and
        the fixed 5 mm nut shelf is unchanged.
        """
        if depth <= 0.0:
            return ""

        half_width = neck_surface.neck_outline.nut_width / 2.0
        end_x = neck_surface.headstock_root_start_position
        # The circular arc passes through both end corners and is exactly
        # ``depth`` heelward at the centreline. It is a robust replacement
        # for a tangent U-prism boolean, which OpenCASCADE can invalidate.
        center_offset = (depth**2 - half_width**2) / (2.0 * depth)
        radius = depth - center_offset
        center_x = end_x + center_offset
        return (
            f"NUT_END_U_TRIM_DEPTH = {depth}\n"
            f"NUT_END_U_TRIM_END_X = {end_x}\n"
            f"NUT_END_U_TRIM_CENTER_X = {center_x}\n"
            f"NUT_END_U_TRIM_RADIUS = {radius}\n"
            "nut_end_u_trim_shape = Part.makeCylinder(\n"
            "    NUT_END_U_TRIM_RADIUS,\n"
            "    2000.0,\n"
            "    App.Vector(NUT_END_U_TRIM_CENTER_X, 0.0, -1000.0),\n"
            "    App.Vector(0.0, 0.0, 1.0),\n"
            ")\n"
            # The circle solved above passes through both outer corners and
            # the centreline depth point, but at this width-to-depth ratio
            # its own radius is large enough that the cylinder built from it
            # reaches well past NUT_END_U_TRIM_END_X in the headstock
            # direction too — into territory this trim was never meant to
            # touch. That used to be harmless because no neck material
            # existed there; it stopped being harmless once the headstock
            # root transition began supplying material past that point as
            # part of this same loft. Clipping the cutter to x >= end_x
            # keeps its effect exactly where the U shape is meant to be.
            "nut_end_u_trim_shape = require_shape(\n"
            "    nut_end_u_trim_shape.common(\n"
            "        Part.makeBox(\n"
            "            2000.0, 2000.0, 2000.0,\n"
            "            App.Vector(\n"
            "                NUT_END_U_TRIM_END_X, -1000.0, -1000.0\n"
            "            ),\n"
            "        )\n"
            "    ),\n"
            '    "nut-end U trim cutter clip",\n'
            ")\n"
            "neck_shape = require_shape(\n"
            "    neck_shape.cut(nut_end_u_trim_shape).removeSplitter(),\n"
            '    "nut-end U trim",\n'
            ")\n"
            f"NUT_END_U_SIDE_FILLET_RADIUS = {side_fillet_radius}\n"
            "nut_end_u_side_edges = nut_corner_edges(\n"
            "    neck_shape,\n"
            "    NUT_END_U_TRIM_END_X,\n"
            f"    {half_width},\n"
            "    0.01,\n"
            ")\n"
            "neck_shape = safe_fillet(\n"
            "    neck_shape,\n"
            "    NUT_END_U_SIDE_FILLET_RADIUS,\n"
            "    nut_end_u_side_edges,\n"
            '    "nut-end U cylinder-side fillet",\n'
            ")\n\n"
        )

    @staticmethod
    def _render_headstock_outer_d_profile_guides(
        headstock: HeadstockSolid,
        neck_surface: NeckBackSurface,
        extension: float,
    ) -> str:
        """Return construction lines for the first outer D-profile runout.

        These lines deliberately do not participate in a loft or boolean.
        They let the outermost two D-profile curves be inspected before the
        neighbouring, shorter curves are introduced. Therefore neither the
        fixed 5 mm nut shelf nor any manufacturing solid can move.
        """
        if extension <= 0.0:
            return ""

        nut_row = neck_surface._build_profile_row(0.0)
        outside_points = (nut_row[1], nut_row[-2])
        radians = math.radians(headstock.angle.angle_degrees)
        headstock_back_z = (
            -extension * math.tan(radians)
            - headstock.thickness / math.cos(radians)
        )
        guide_lines = tuple(
            (
                point,
                Point3D(-extension, point.y, headstock_back_z),
            )
            for point in outside_points
        )
        return (
            "HEADSTOCK_OUTER_D_PROFILE_GUIDES = "
            f"{FreeCADScriptExporter._serialize_rows(guide_lines)}\n"
            "outer_d_profile_guide_edges = [\n"
            "    Part.makePolygon([App.Vector(*start), App.Vector(*end)])\n"
            "    for start, end in HEADSTOCK_OUTER_D_PROFILE_GUIDES\n"
            "]\n"
            "outer_d_profile_guide_feature = document.addObject(\n"
            '    "Part::Feature", "HeadstockOuterDProfileGuides"\n'
            ")\n"
            "outer_d_profile_guide_feature.Label = (\n"
            '    "Construction: outer D-profile guide lines"\n'
            ")\n"
            "outer_d_profile_guide_feature.Shape = Part.makeCompound(\n"
            "    outer_d_profile_guide_edges\n"
            ")\n"
        )

    @staticmethod
    def _headstock_transition_sections(
        headstock: HeadstockSolid,
        neck_surface: NeckBackSurface,
        lateral_edge_fillet_radius: float,
    ) -> tuple[tuple[Point3D, ...], ...]:
        """Return the headstock-root loft: a genuinely rounded transition.

        Two things were tried and rejected here. A tight, "raced" depth
        blend inside one loft (approximating a real reference Stratocaster
        neck's near-instant thickness step) left a visible sharp facet on
        our own angled headstock, even though the same shape reads as a
        clean corner on the reference's flat, unangled peghead. Replacing
        that with a genuine boolean corner (constant depth on this piece,
        fused against the headstock's own naturally tilted ramp) is
        exactly how the reference is built, but it is still, geometrically,
        a real corner — and a real corner is a right angle by another
        name, which is the opposite of what a rounded joint needs.

        This version blends both depth (Z) and width (Y) smoothly across
        the full bridge, from ``headstock_root_start_position`` to the nut
        (x = 0.0), with a single plain smootherstep (zero slope *and* zero
        curvature at both ends, so it matches the flat ramp's constant
        slope tangentially at the root and arrives at the nut just as
        gently). Earlier attempts at a
        smooth full-bridge depth blend broke the boolean fuse when the
        bridge was only a few mm long — the curvature per millimetre was
        too high. Now that the bridge has room (headstock_root_side_extension
        is 15 mm, sized for the width taper, not squeezed to fit an
        aggressive depth blend), the same smooth blend has enough length to
        stay low-curvature and should fuse cleanly.

        The loft also carries the entire headstock blank itself — an
        unblended run of stations (pure headstock rows, fraction pinned at
        0) from the headstock's own far tip through to ``root_start`` —
        rather than fusing a separately built headstock solid on
        afterwards. Two independently constructed lofts sharing the exact
        same row formula still turned out not to be robustly fusible:
        their surfaces agreed at the shared stations but each loft fits
        its own spline through its own surrounding stations, so the
        curved, rounded lateral edge in particular could disagree by a
        hair between the two fits — enough that FreeCAD's boolean fuse
        treated it as either a degenerate near-zero-volume overlap (extra
        sliver solids) or, more often, an outright null result. Carrying
        the whole headstock as more stations in this same loft removes
        the seam (and the fuse) entirely: there is only ever one spline
        being fit, so there is nothing left to disagree with itself.
        """
        root_start = neck_surface.headstock_root_start_position
        # The rise from the headstock to the nut, and the neck's own
        # separate rise from the nut to full thickness, are each built as
        # a smootherstep-style ease — zero slope at both of *their* own
        # endpoints. Joining them right at the nut therefore meant two
        # curves that both went quiet at exactly the same point: no
        # literal flat plateau, but the eye reads the shared zero-slope
        # point as one anyway ("rise, pause, rise" rather than one hill).
        # A brief genuinely-flat run was tried right at the nut, sized for
        # physical nut clearance — but that reads exactly the same way,
        # for the same reason: a flat run bounded by two curves *is* two
        # facets meeting a flat plane, however the flat run got there. So
        # this stays one single Hermite curve, x = 0 an ordinary point
        # partway along it with whatever nonzero slope the curve is moving
        # at there — nut clearance has to be solved some other way (the
        # nut's own seat, not this surface's shape).
        #
        # It does not start at root_start: it starts a fixed ``blend_length``
        # back from the nut itself, so the rounded portion is a fixed, known
        # span measured from x = 0.
        blend_length = 20.0
        blend_start = max(-blend_length, -headstock.plan.length + 10.0)
        # A couple of millimetres past nut_transition_length, not exactly
        # at it: the surface is flat there either way (see below), but
        # the truss-rod channel happens to start its cut at exactly
        # x = nut_transition_length too, and that cut turned out to land
        # squarely on this loft's own internal seam between its Hermite
        # stations and the neck's plain ones — enough of a coincidence for
        # FreeCAD's boolean cut to return an invalid result. Moving the
        # seam a little further out costs nothing (the target value and
        # tangent are unchanged, since the neck's own taper is already
        # flat by nut_transition_length) and keeps the cut's boundary
        # clear of it.
        blend_end = neck_surface.nut_transition_length + 2.0
        end_row = neck_surface._build_profile_row(blend_end)
        sections: list[tuple[Point3D, ...]] = []
        if root_start < 0.0:
            sections.extend(
                FreeCADScriptExporter._headstock_tip_sections(
                    headstock,
                    neck_surface,
                    lateral_edge_fillet_radius,
                    blend_start,
                )
            )
            epsilon = 0.05
            headstock_before = FreeCADScriptExporter._angled_headstock_root_section(
                headstock,
                neck_surface,
                blend_start - epsilon,
                lateral_edge_fillet_radius,
            )
            headstock_after = FreeCADScriptExporter._angled_headstock_root_section(
                headstock,
                neck_surface,
                blend_start + epsilon,
                lateral_edge_fillet_radius,
            )
            start_row = FreeCADScriptExporter._angled_headstock_root_section(
                headstock,
                neck_surface,
                blend_start,
                lateral_edge_fillet_radius,
            )
            # Plain per-mm slope (not pre-scaled by any span):
            # _hermite_stations applies the start_x/end_x span itself.
            start_tangent = tuple(
                Point3D(
                    0.0,
                    (after.y - before.y) / (2.0 * epsilon),
                    (after.z - before.z) / (2.0 * epsilon),
                )
                for before, after in zip(
                    headstock_before, headstock_after, strict=True
                )
            )
            # The neck's own taper is flat on both sides of
            # nut_transition_length: zero slope there too, so the target
            # tangent at this end is genuinely zero — a real boundary
            # condition, not an approximation.
            end_tangent = tuple(Point3D(0.0, 0.0, 0.0) for _ in end_row)
            # step starts at 1, not 0: step 0 would recompute start_row,
            # already placed last by _headstock_tip_sections, as a
            # redundant, coincident duplicate station.
            hermite_rows = FreeCADScriptExporter._hermite_stations(
                start_row,
                start_tangent,
                end_row,
                end_tangent,
                blend_start,
                blend_end,
                segments=40,
                first_step=1,
            )
            # The lateral edge follows this same Hermite curve, at the
            # same pace, as the centreline — so it only reaches flat (its
            # own zero-slope target) at blend_end, not at the nut where
            # the fretboard's own flat underside actually starts. Between
            # x = 0 and blend_end the top edge is still partway through
            # the headstock's own tilt, which is exactly where the
            # fretboard needs a flat surface to glue against. The
            # centreline (bottom_z) is left exactly as this curve already
            # gives it — only the edge, and the rounded run-in between it
            # and the centre (unavoidably, since that run-in is a blend
            # between the two), is recomputed so the top edge is flat
            # from x = 0 on, easing smoothly back to the headstock's real
            # tilt a little further into the headstock instead.
            sections.extend(
                FreeCADScriptExporter._offset_edge_pivot(
                    headstock,
                    neck_surface,
                    hermite_rows,
                    lateral_edge_fillet_radius,
                    flat_end=0.0,
                    tilt_resume=-8.0,
                )
            )
        elif not sections:
            sections.append(end_row)
        return tuple(sections)

    @staticmethod
    def _offset_edge_pivot(
        headstock: HeadstockSolid,
        neck_surface: NeckBackSurface,
        rows: tuple[tuple[Point3D, ...], ...],
        lateral_edge_fillet_radius: float,
        flat_end: float,
        tilt_resume: float,
    ) -> tuple[tuple[Point3D, ...], ...]:
        """Replace each row's two true edge points with a delayed pivot.

        Every other point in the row — the flat centre run and the
        rounded run-in leading up to the edge — is left exactly as the
        Hermite curve already gives it; only index 0 and the last index
        (the two true corner points, at the top face's own Y and Z) are
        recomputed, using the headstock's own tilt formula
        (``position * tan(angle)``) scaled by a smootherstep weight that
        is 0 at ``flat_end`` (x > flat_end reads as flat, matching the
        neck's own flat_z = 0 at its edges) and 1 at ``tilt_resume`` (x <=
        tilt_resume matches the unmodified formula exactly, value *and*
        slope, since smootherstep's own derivative is 0 at that end too —
        so this only ever touches the span between the two, converging
        back to the real geometry on both sides rather than leaving a
        permanent offset in headstock thickness far from the nut).

        Leaving the rounded run-in untouched means it still blends toward
        the *original* corner position, so there is now a small, real
        gap between its last point and the newly placed corner right at
        the very tip of each side — accepted deliberately here, since it
        keeps every other point of the back surface, including that
        run-in, byte-identical to the already-approved curve.
        """
        radians = math.radians(headstock.angle.angle_degrees)
        count = neck_surface.profile_sample_count
        span = flat_end - tilt_resume
        rebuilt: list[tuple[Point3D, ...]] = []
        for row in rows:
            position = row[0].x
            raw_top_z = position * math.tan(radians)
            t = max(0.0, min(1.0, (flat_end - position) / span))
            weight = NeckBackSurface._smootherstep(t)
            top_z = raw_top_z * weight
            # The top edge's own distance-from-nut reference shifts with
            # this same weight: at weight = 0 the top face is level with
            # the nut (distance 0, i.e. full nut_width), at weight = 1 it
            # is headstock.plan's own distance at this position, exactly
            # as _angled_headstock_root_section computes it unmodified.
            top_distance = max(0.0, -position) * weight
            top_width = headstock.plan.width_at_distance(top_distance)
            top_half_width = top_width / 2.0
            new_row = list(row)
            new_row[0] = Point3D(position, -top_half_width, top_z)
            new_row[count - 1] = Point3D(position, top_half_width, top_z)
            rebuilt.append(tuple(new_row))
        return tuple(rebuilt)

    @staticmethod
    def _hermite_stations(
        start_row: tuple[Point3D, ...],
        start_tangent: tuple[Point3D, ...],
        end_row: tuple[Point3D, ...],
        end_tangent: tuple[Point3D, ...],
        start_x: float,
        end_x: float,
        segments: int,
        first_step: int = 0,
    ) -> tuple[tuple[Point3D, ...], ...]:
        """Return cubic Hermite-interpolated rows from start_x to end_x.

        Tangents are in absolute mm-per-mm slope, already scaled by the
        ``end_x - start_x`` span internally (standard Hermite parameter
        convention) so callers can pass real derivatives directly.
        """
        span = end_x - start_x
        sections = []
        for step in range(first_step, segments + 1):
            t = step / segments
            position = start_x + span * t
            t2 = t * t
            t3 = t2 * t
            h00 = 2.0 * t3 - 3.0 * t2 + 1.0
            h10 = t3 - 2.0 * t2 + t
            h01 = -2.0 * t3 + 3.0 * t2
            h11 = t3 - t2
            sections.append(
                tuple(
                    Point3D(
                        position,
                        h00 * p0.y
                        + h10 * m0.y * span
                        + h01 * p1.y
                        + h11 * m1.y * span,
                        h00 * p0.z
                        + h10 * m0.z * span
                        + h01 * p1.z
                        + h11 * m1.z * span,
                    )
                    for p0, m0, p1, m1 in zip(
                        start_row,
                        start_tangent,
                        end_row,
                        end_tangent,
                        strict=True,
                    )
                )
            )
        return tuple(sections)

    @staticmethod
    def _angled_headstock_root_section(
        headstock: HeadstockSolid,
        neck_surface: NeckBackSurface,
        position: float,
        lateral_edge_fillet_radius: float = 0.0,
    ) -> tuple[Point3D, ...]:
        """Return one flat cross-section on the angled headstock blank.

        The headstock is a *sheared* extrusion (its extrusion vector has a
        nonzero X component, ``thickness * sin(angle)``, since it is a
        perpendicular offset from a tilted top face, not a purely vertical
        one). That shear means the bottom face's boundary at a given X does
        not sit above the same plan distance as the top face's boundary at
        that same X — it sits above a plan distance further from the nut,
        by exactly that X shear, and is correspondingly a little wider.
        The row uses that wider bottom-face width as its one reference
        width for the full cross-section (edges included); the true,
        narrower top-face width is not tracked separately. The shear is a
        couple of millimetres against a half-width of several centimetres,
        so the resulting few percent narrowing of the very top edge is
        well inside where this formula already blends it toward the flat
        plateau, and staying with one width keeps this row consistent with
        every other row built by this same function.

        ``lateral_edge_fillet_radius`` softens the lateral edge (where the
        flat top meets the flat bottom). Unlike the neck's own back — a
        genuinely rounded D-profile everywhere, which is exactly why
        ``_heel_surface_point`` (back_surface.py) can soften it into the
        heel block with one superellipse spanning the full width — the
        headstock's top and back are real flat planes on an actual guitar,
        with rounding confined to a small radius right at the edge. So the
        row keeps a genuinely flat run (curvature exactly zero, not just
        small) across the middle of its width, matching that physical
        shape, and blends only the outer part of each side — sized to the
        given radius — from that flat run up to the flat top edge.
        Blending Y and Z as functions of the *same* fraction of the way
        through that outer part (rather than the interior points growing
        toward a separately-widening flat value) keeps the row monotonic
        by construction: nothing here can overshoot the flat run's width
        and fold back on itself before reaching the top edge, even though
        the bottom face is usually wider than the top one (the shear
        above pushes its source distance further from the nut). An
        earlier version did grow from that wider value and could fold
        back there, producing a self-intersecting row that broke the loft
        outright.
        """
        radians = math.radians(headstock.angle.angle_degrees)
        shear = headstock.thickness * math.sin(radians)
        top_width = headstock.plan.width_at_distance(max(0.0, -position))
        bottom_width = headstock.plan.width_at_distance(
            max(0.0, -position + shear)
        )
        top_half_width = top_width / 2.0
        bottom_half_width = bottom_width / 2.0
        top_z = position * math.tan(radians)
        bottom_z = top_z - headstock.thickness / math.cos(radians)
        count = neck_surface.profile_sample_count
        # The rounded outer part occupies this fraction of each side's
        # half-width, measured in from the true edge.
        rounding_fraction = (
            min(0.4, 1.5 * lateral_edge_fillet_radius / bottom_half_width)
            if lateral_edge_fillet_radius > 0.0 and bottom_half_width > 0.0
            else 0.0
        )
        flat_fraction = 1.0 - rounding_fraction
        # The innermost interior index reaches abs_u == 1.0 exactly. Sizing
        # the rounding zone's own denominator a little past that keeps blend
        # just short of 1.0 there, so that point stays distinct from the
        # true edge point (index 0 / count - 1) instead of landing exactly
        # on top of it — a coincident point that also breaks the loft.
        rounding_span = rounding_fraction * 1.08
        points: list[Point3D] = []
        for index in range(count):
            if index == 0:
                points.append(Point3D(position, -top_half_width, top_z))
                continue
            if index == count - 1:
                points.append(Point3D(position, top_half_width, top_z))
                continue
            lateral_u = 2.0 * (index - 1) / (count - 3) - 1.0
            abs_u = abs(lateral_u)
            if rounding_fraction > 0.0 and abs_u > flat_fraction:
                edge_progress = (abs_u - flat_fraction) / rounding_span
                blend = NeckBackSurface._smootherstep(edge_progress)
                magnitude = bottom_half_width + (
                    top_half_width - bottom_half_width
                ) * blend
                y = math.copysign(magnitude, lateral_u)
                z = bottom_z + (top_z - bottom_z) * blend
            else:
                y = bottom_half_width * lateral_u / flat_fraction
                z = bottom_z
            points.append(Point3D(position, y, z))
        return tuple(points)

    @staticmethod
    def _headstock_tip_sections(
        headstock: HeadstockSolid,
        neck_surface: NeckBackSurface,
        lateral_edge_fillet_radius: float,
        end_position: float,
    ) -> tuple[tuple[Point3D, ...], ...]:
        """Return a loft covering the headstock, tip to ``end_position``.

        Built entirely from ``_angled_headstock_root_section`` — the same
        row formula, with the same lateral rounding, used for the
        headstock-root transition's own blended run (see
        ``_headstock_transition_sections``) — rather than trimming a flat
        extrusion that has its lateral edges rounded by a separate, real
        circular fillet. That combination worked as two independently
        rounded surfaces that only approximately agreed: close enough to
        pass a volume/bbox sanity check, not close enough to avoid a
        visible bump where the real fillet's selected-edge range started.
        Building the whole tip from this one formula instead means there
        is no second rounding to disagree with — identical construction
        from the headstock's own tip all the way to the join.
        """
        tip_x = -headstock.plan.length
        segments = 32
        sections = []
        for step in range(segments + 1):
            u = step / segments
            # Bias sampling density toward the end: that is where this
            # loft has to agree with the following blended run's own
            # unblended starting value closely enough for one continuous
            # loft to actually track it, rather than chording across it.
            # The tip end has no such match to keep and can stay coarser.
            fraction = 1.0 - (1.0 - u) ** 2
            position = tip_x + (end_position - tip_x) * fraction
            sections.append(
                FreeCADScriptExporter._angled_headstock_root_section(
                    headstock,
                    neck_surface,
                    position,
                    lateral_edge_fillet_radius,
                )
            )
        return tuple(sections)

    @staticmethod
    def _headstock_root_sections(
        neck_surface: NeckBackSurface,
        root_swell: float,
    ) -> tuple[tuple[Point3D, ...], ...]:
        """Create a compact, freeform volute on the back of the neck.

        The headstock itself remains its normal angled solid.  These sections
        start directly at the nut and build only the rounded neck-side swell,
        avoiding the misleading planar triangular wedge that an extended
        headstock-root loft creates. Every section spans the full D profile,
        so the two lateral secondary curves are actual visible surfaces.
        """
        neck_length = neck_surface.nut_transition_length or 20.0
        sections: list[tuple[Point3D, ...]] = []

        # The exact nut row contains coincident points where the back profile
        # changes from its flat headstock seat to the D profile. A solid loft
        # cannot use that degenerate wire, so begin one small station inside
        # the neck; the volute still overlaps the neck continuously there.
        for index in range(1, 9):
            fraction = index / 8.0
            position = neck_length * fraction
            # The long primary curve controls the central lobe. The width of
            # the lobe contracts with the same tangent-continuous function;
            # _d_profile_root_section turns that lobe sideways into the D
            # profile through its secondary curves.
            primary_weight = 1.0 - fraction**2 * (3.0 - 2.0 * fraction)
            volute_width = max(
                0.5,
                neck_surface.neck_outline.nut_width * primary_weight,
            )
            extra_depth = max(0.02, root_swell * primary_weight)
            sections.append(
                FreeCADScriptExporter._d_profile_root_section(
                    neck_surface,
                    position,
                    volute_width,
                    extra_depth,
                )
            )
        return tuple(sections)

    @staticmethod
    def _d_profile_root_section(
        neck_surface: NeckBackSurface,
        position: float,
        volute_width: float,
        extra_depth: float,
    ) -> tuple[Point3D, ...]:
        """Return one cross-section of a conventional curved volute.

        The primary volute curve is supplied by the decreasing ``extra_depth``
        along the neck. Here, a secondary curve falls away from its centre
        line to both sides of the D profile. This pair of curves gives the
        classic under-nut swell its smooth, flared transition rather than a
        flat triangular face or a separate semicircular lump.
        """
        full_row = neck_surface._build_profile_row(position)
        half_volute_width = volute_width / 2.0
        top_points = list(full_row)
        bottom_points: list[Point3D] = []
        for point in full_row:
            lateral = point.y
            top_z = point.z
            normalized = min(1.0, abs(lateral) / half_volute_width)
            # Builders shape a volute's secondary curve as a reverse curve:
            # it leaves the high center almost flat, falls more quickly in
            # the middle, then settles flat again at the neck side. The
            # complementary quintic smoothstep has exactly those two tangent
            # endpoints and the required mid-span inflection. The *section*
            # still spans the full D profile, so this curve genuinely meets
            # both neck sides instead of ending as a narrow center strip.
            secondary_weight = 1.0 - (
                6.0 * normalized**5
                - 15.0 * normalized**4
                + 10.0 * normalized**3
            )
            bottom_z = top_z - max(0.02, extra_depth * secondary_weight)
            bottom_points.append(
                Point3D(
                    position,
                    lateral,
                    bottom_z,
                )
            )
        return (*top_points, *reversed(bottom_points))

    @staticmethod
    def _render_tuner_hole_cuts(
        headstock: HeadstockSolid,
        layout: TunerLayout | None,
        chamfer_depth: float,
        shape_variable: str = "headstock_shape",
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
            f"    {shape_variable} = require_shape(\n"
            f"        {shape_variable}.cut(cutter),\n"
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
            f"        {shape_variable} = require_shape(\n"
            f"            {shape_variable}.cut(chamfer),\n"
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
    def _render_inlay_cuts(layout: InlayLayout | None) -> str:
        """Return FreeCAD commands that cut barbed-wire position markers.

        Each marker is a flat vertical pocket: its floor sits a constant
        distance below the surface centerline rather than following the
        fretboard's own camber. Over a marker's small footprint the
        radiused surface drops only a few tenths of a millimetre away
        from the centerline, so the cut ends up marginally deeper than
        ``depth`` near a marker's outer edge and never shallower — a safe
        simplification given the fretboard's much larger material margin.
        """
        if layout is None:
            return ""

        outlines = tuple(
            tuple(Point3D(point.x, point.y, 0.0) for point in marker.outline)
            for marker in layout.markers
        )
        serialized_outlines = FreeCADScriptExporter._serialize_rows(outlines)
        return (
            f"INLAY_MARKER_OUTLINES = {serialized_outlines}\n"
            f"inlay_depth = {layout.depth}\n"
            f"inlay_surface_z = {layout.fretboard_surface.center_thickness}\n"
            "inlay_overcut = 0.6\n"
            "for inlay_index, outline in enumerate(\n"
            "    INLAY_MARKER_OUTLINES,\n"
            "    start=1,\n"
            "):\n"
            "    profile = [\n"
            "        App.Vector(x, y, inlay_surface_z + inlay_overcut)\n"
            "        for x, y, _ in outline\n"
            "    ]\n"
            "    profile.append(profile[0])\n"
            "    marker_face = Part.Face(Part.makePolygon(profile))\n"
            "    marker_shape = marker_face.extrude(\n"
            "        App.Vector(0.0, 0.0, -(inlay_depth + inlay_overcut))\n"
            "    )\n"
            "    fretboard_shape = require_shape(\n"
            "        fretboard_shape.cut(marker_shape).removeSplitter(),\n"
            '        f"inlay-marker cut {inlay_index}",\n'
            "    )\n"
        )

    @staticmethod
    def _render_body(
        body: BodySolid | None,
        object_name: str,
    ) -> str:
        """Return FreeCAD commands that build the solid body and its cuts.

        The body's top face sits at Z = 0, the same reference plane as
        the neck-back surface's own Z = 0 — the two are meant to meet
        flush, with the neck heel recessed into the neck-pocket cavity
        cut here. Both pickup routes, the bridge's pivot holes and
        sustain-block cavity (if any), and every extra cavity are also
        cut straight down from that same top face. The control, switch and
        battery cavities are cut up from the back face at Z =
        -thickness, each with its shallow cover recess. Drilled holes
        (pot/switch shafts, pickup-screw recesses) go straight down from
        the top face; only the jack bore runs sideways, in from the
        edge.
        """
        if body is None:
            return ""

        def outline_literal(points: Iterable[Point2D]) -> str:
            return json.dumps(
                [[point.x, point.y] for point in points],
                separators=(",", ":"),
            )

        overcut = 0.6
        lines = [
            f"BODY_OUTLINE_POINTS = {outline_literal(body.outline.points)}\n",
            f"body_thickness = {body.thickness}\n",
            f"body_overcut = {overcut}\n",
            "def cavity_cut(shape, outline_points, depth, label, from_back=False):\n",
            "    if from_back:\n",
            "        start_z = -body_thickness - body_overcut\n",
            "        direction = 1.0\n",
            "    else:\n",
            "        start_z = body_overcut\n",
            "        direction = -1.0\n",
            "    profile = [\n",
            "        App.Vector(x, y, start_z) for x, y in outline_points\n",
            "    ]\n",
            "    profile.append(profile[0])\n",
            "    face = Part.Face(Part.makePolygon(profile))\n",
            "    cavity_shape = face.extrude(\n",
            "        App.Vector(0.0, 0.0, direction * (depth + body_overcut))\n",
            "    )\n",
            "    return require_shape(shape.cut(cavity_shape), label)\n",
            (
                "body_shape = Part.Face(\n"
                "    Part.makePolygon(\n"
                "        [\n"
                "            App.Vector(x, y, 0.0)\n"
                "            for x, y in BODY_OUTLINE_POINTS\n"
                "        ]\n"
                "        + [\n"
                "            App.Vector(\n"
                "                BODY_OUTLINE_POINTS[0][0],\n"
                "                BODY_OUTLINE_POINTS[0][1],\n"
                "                0.0,\n"
                "            )\n"
                "        ]\n"
                "    )\n"
                ").extrude(App.Vector(0.0, 0.0, -body_thickness))\n"
            ),
            'body_shape = require_shape(body_shape, "body outline extrude")\n',
        ]
        cavity_cuts = [
            (body.neck_pocket, "neck pocket cut"),
            (body.bridge_pickup, "bridge pickup route cut"),
            (body.neck_pickup, "neck pickup route cut"),
        ]
        if body.bridge_mounting.sustain_block_cavity is not None:
            cavity_cuts.append(
                (body.bridge_mounting.sustain_block_cavity, "sustain-block cavity cut")
            )
        for index, extra_cavity in enumerate(body.extra_cavities, start=1):
            cavity_cuts.append((extra_cavity, f"extra cavity {index} cut"))
        for cavity, label in cavity_cuts:
            outline = outline_literal(cavity.outline)
            lines.append(
                f"body_shape = cavity_cut(body_shape, {outline}, "
                f"{cavity.depth}, {label!r})\n"
            )
        rear_cuts = [
            (body.control_cavity, "control cavity"),
            (body.switch_cavity, "switch cavity"),
            (body.battery_cavity, "battery cavity"),
        ]
        for rear, label in rear_cuts:
            if rear is None:
                continue
            for cavity, suffix in (
                (rear.cavity, "cut"),
                (rear.cover_recess, "cover recess cut"),
            ):
                outline = outline_literal(cavity.outline)
                lines.append(
                    f"body_shape = cavity_cut(body_shape, {outline}, "
                    f"{cavity.depth}, {label + ' ' + suffix!r}, from_back=True)\n"
                )
        for index, hole in enumerate(body.bridge_mounting.pivot_holes, start=1):
            lines.append(
                "pivot_hole = Part.makeCylinder(\n"
                f"    {body.bridge_mounting.pivot_hole_diameter / 2.0},\n"
                f"    {body.bridge_mounting.pivot_hole_depth} + body_overcut,\n"
                f"    App.Vector({hole.x}, {hole.y}, body_overcut),\n"
                "    App.Vector(0.0, 0.0, -1.0),\n"
                ")\n"
                "body_shape = require_shape(\n"
                "    body_shape.cut(pivot_hole),\n"
                f"    \"bridge pivot hole {index} cut\",\n"
                ")\n"
            )
        for drilled in body.holes:
            # A through hole (depth == thickness) gets the overcut at both
            # ends so it breaks cleanly out of the back face too.
            lines.append(
                "drilled_hole = Part.makeCylinder(\n"
                f"    {drilled.diameter / 2.0},\n"
                f"    {drilled.depth} + 2.0 * body_overcut,\n"
                f"    App.Vector({drilled.center_x}, {drilled.center_y}, "
                "body_overcut),\n"
                "    App.Vector(0.0, 0.0, -1.0),\n"
                ")\n"
                "body_shape = require_shape(\n"
                "    body_shape.cut(drilled_hole),\n"
                f"    {drilled.name.lower() + ' cut'!r},\n"
                ")\n"
            )
        jack = body.jack_hole
        jack_radians = math.radians(jack.direction_degrees)
        jack_direction = (
            math.cos(jack_radians),
            math.sin(jack_radians),
            0.0,
        )
        lines.append(
            "jack_bore = Part.makeCylinder(\n"
            f"    {jack.diameter / 2.0},\n"
            f"    {jack.depth},\n"
            f"    App.Vector({jack.start_x}, {jack.start_y}, "
            f"{-body.thickness / 2.0}),\n"
            f"    App.Vector{jack_direction},\n"
            ")\n"
            "body_shape = require_shape(\n"
            "    body_shape.cut(jack_bore),\n"
            '    "jack bore cut",\n'
            ")\n"
        )
        lines.append(
            "body_feature = document.addObject(\n"
            f'    "Part::Feature", "{object_name}"\n'
            ")\n"
        )
        lines.append("body_feature.Shape = body_shape\n")
        return "".join(lines)

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
        """Return one consistent-profile neck-back loft section.

        A FreeCAD Part loft requires corresponding profiles to retain the
        same edge structure. The heel therefore uses the same sampled profile
        as the playing neck: it is planar through the central mounting area
        and has only a small rounded relief at the two outer side edges.
        """
        return row
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

    @staticmethod
    def _validate_inlay_layout(
        surface: FretboardSurface,
        layout: InlayLayout | None,
    ) -> None:
        """Ensure an optional inlay layout was built from this surface."""
        if layout is None:
            return
        if layout.fretboard_surface is not surface:
            raise FreeCADBackendError(
                "Inlay layout must be built from the same fretboard surface."
            )
