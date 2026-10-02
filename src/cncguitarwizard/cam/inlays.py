"""Cut the fretboard's marker inlays out of sheet, to fit their pockets.

Round dots are bought ready-made (or cut from rod), so only the other
styles — barbed wire and blocks — get a program: every marker as its own
piece, nested in rows on one sheet as thick as the pockets are deep.

The pocket and the piece are both cut with the fretboard's inlay end
mill, and neither can be sharper than it: the pocket keeps a tool-radius
round in every corner the tool turns inside, the piece in every corner
cut into it. Both therefore follow the marker outline rounded both ways
by the tool radius (``inlay_fit_outline``), the piece
``INLAY_FIT_CLEARANCE`` smaller all round, so each piece drops into its
pocket.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

from ..geometry.fretboard import InlayMarker
from ..geometry.primitives import Point2D
from .exceptions import ToolpathError
from .gcode import Setup
from .operations import profile
from .planar import offset_polygon, polygon_bounds, segment_distance

if TYPE_CHECKING:
    from ..geometry.fretboard import InlayLayout
    from .fretboard import FretboardMachiningParameters

INLAY_FIT_CLEARANCE = 0.1
"""How much smaller than its pocket a piece is cut, per side, in mm."""

INLAY_PIECE_GAP = 3.0
"""Sheet left between neighbouring pieces, beyond the tool, in mm."""

INLAY_ROW_LENGTH = 150.0
"""Longest row of pieces along X before the next row starts, in mm."""

INLAY_SHEET_MARGIN = 5.0
"""Sheet left around the nested pieces on every side, in mm."""

THIN_TOLERANCE = 0.005
"""How far a point may lie off a straight run and still be dropped, in mm."""

THIN_RUN = 32
"""Most points dropped in a row, however straight the run."""


@dataclass(frozen=True, slots=True)
class InlayMachiningPlan:
    """The program that cuts the marker pieces from one sheet.

    Args:
        pieces: The sheet program.
        stock_length: Sheet length (X) the nested pieces need.
        stock_width: Sheet width (Y) the nested pieces need.
        stock_thickness: Sheet thickness — the pockets' depth.
        origin_x: Always ``0`` — the work zero is the sheet's centre.
        origin_y: Always ``0``.
        index_pin_positions: Always empty — the sheet is taped down.
        preview_outlines: The sheet's outline, for the program's preview.
    """

    pieces: Setup
    stock_length: float
    stock_width: float
    stock_thickness: float
    origin_x: float = 0.0
    origin_y: float = 0.0
    index_pin_positions: tuple[tuple[float, float], ...] = ()
    preview_outlines: tuple[tuple[Point2D, ...], ...] = ()

    @property
    def setups(self) -> tuple[Setup, ...]:
        """Return the sheet program."""
        return (self.pieces,)


@lru_cache(maxsize=128)
def inlay_fit_outline(
    outline: tuple[Point2D, ...], tool_radius: float
) -> tuple[Point2D, ...]:
    """Return a marker outline as an end mill of ``tool_radius`` can cut it.

    The outline is grown and shrunk back by the radius, rounding the
    corners that turn into it, then shrunk and grown back, rounding the
    corners that point out and dropping any barb narrower than the tool.
    A pocket follows the result exactly, and so does a piece cut round
    it (or round any outline shrunk from it). Results are cached, as the
    pockets and the pieces both ask for them.

    Raises:
        ToolpathError: If the tool cannot fit in the outline at all.
    """
    result = outline
    for inward in (False, True, True, False):
        result = _fine_offset(result, tool_radius, inward=inward)
        if not result:
            raise ToolpathError(
                f"An inlay marker is too narrow for a {2.0 * tool_radius:g} mm tool."
            )
    return result


def plan_inlay_machining(
    layout: InlayLayout, parameters: FretboardMachiningParameters
) -> InlayMachiningPlan | None:
    """Plan the sheet program for the marker pieces.

    Returns ``None`` for round ``dot`` markers, or when there are none.
    The pieces are nested in fret order, left to right in rows of up to
    ``INLAY_ROW_LENGTH``, each row behind the last (+Y), and keep the
    orientation they have on the board seen from above, so the face up
    on the sheet is the face that shows.

    Raises:
        ToolpathError: If a marker is too narrow for the inlay tool.
    """
    if layout.style == "dot" or not layout.markers:
        return None
    tool = parameters.inlay
    thickness = layout.depth
    pieces = [
        (marker, _piece_outline(marker, tool.tool_radius)) for marker in layout.markers
    ]
    spacing = tool.tool_diameter + INLAY_PIECE_GAP
    placed: list[tuple[InlayMarker, tuple[Point2D, ...]]] = []
    x = y = row_depth = 0.0
    for marker, outline in pieces:
        min_x, min_y, max_x, max_y = polygon_bounds(outline)
        if x > 0.0 and x + (max_x - min_x) > INLAY_ROW_LENGTH:
            x, y, row_depth = 0.0, y + row_depth + spacing, 0.0
        placed.append(
            (
                marker,
                tuple(Point2D(p.x - min_x + x, p.y - min_y + y) for p in outline),
            )
        )
        x += max_x - min_x + spacing
        row_depth = max(row_depth, max_y - min_y)
    all_points = [point for _, outline in placed for point in outline]
    min_x, min_y, max_x, max_y = polygon_bounds(all_points)
    centre = Point2D((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
    through = thickness + tool.through_overshoot
    paths = []
    for marker, outline in placed:
        centred = tuple(Point2D(p.x - centre.x, p.y - centre.y) for p in outline)
        # Named as its pocket is, by where it sits across the board.
        across = sum(p.y for p in marker.outline) / len(marker.outline)
        paths.append(
            profile(
                f"Inlay fret {marker.fret_number} at y={across:.0f}",
                centred,
                through,
                tool,
            )
        )
    sheet_length = max_x - min_x + 2.0 * (tool.tool_diameter + INLAY_SHEET_MARGIN)
    sheet_width = max_y - min_y + 2.0 * (tool.tool_diameter + INLAY_SHEET_MARGIN)
    setup = Setup(
        "Fretboard_inlay_pieces",
        f"Fretboard inlay pieces - {len(placed)} markers cut from "
        f"{thickness:g} mm sheet",
        tuple(paths),
        (
            f"Sheet {thickness:g} mm thick (pearloid, acrylic or other inlay "
            f"material), at least {sheet_length:.0f} x {sheet_width:.0f} mm, "
            "on double-sided tape on a spoilboard: the pieces have no tabs.",
            "Show face up; the pieces lie as on the board seen from above, "
            "in fret order, left to right, rows from the front.",
            f"Same inlay end mill as the pockets; each piece is cut "
            f"{INLAY_FIT_CLEARANCE:g} mm smaller than its pocket all round.",
            "Glue the pieces in and level them with the board's radius.",
        ),
        tool=tool,
        work_zero="the centre of the nested pieces, Z at the sheet top",
    )
    return InlayMachiningPlan(
        setup,
        stock_length=sheet_length,
        stock_width=sheet_width,
        stock_thickness=thickness,
        preview_outlines=(
            (
                Point2D(-sheet_length / 2.0, -sheet_width / 2.0),
                Point2D(sheet_length / 2.0, -sheet_width / 2.0),
                Point2D(sheet_length / 2.0, sheet_width / 2.0),
                Point2D(-sheet_length / 2.0, sheet_width / 2.0),
            ),
        ),
    )


def _piece_outline(marker: InlayMarker, tool_radius: float) -> tuple[Point2D, ...]:
    """Return one piece's outline: its pocket's, less the fit clearance."""
    fitted = inlay_fit_outline(marker.outline, tool_radius)
    piece = _fine_offset(fitted, INLAY_FIT_CLEARANCE, inward=True)
    if not piece:
        raise ToolpathError(f"Inlay fret {marker.fret_number} is too small to cut.")
    return piece


def _fine_offset(
    polygon: tuple[Point2D, ...], distance: float, *, inward: bool
) -> tuple[Point2D, ...]:
    """Return an offset sampled finely enough for millimetre-sized barbs.

    The straight runs' samples are thinned out again, so the next offset
    checks against a short list of edges.
    """
    offset = offset_polygon(
        polygon, distance, inward=inward, arc_spacing=0.05, sample_spacing=0.1
    )
    return _thin(offset) if offset else ()


def _thin(points: tuple[Point2D, ...]) -> tuple[Point2D, ...]:
    """Drop the points that lie within ``THIN_TOLERANCE`` of a straight run."""
    kept = [points[0]]
    run: list[Point2D] = []
    for point in points[1:]:
        # A long run is cut short anyway, so the check stays quick.
        if run and (
            len(run) >= THIN_RUN
            or any(
                segment_distance(skipped, kept[-1], point) > THIN_TOLERANCE
                for skipped in run
            )
        ):
            kept.append(run[-1])
            run = [point]
        else:
            run.append(point)
    kept.extend(run[-1:])
    return tuple(kept)
