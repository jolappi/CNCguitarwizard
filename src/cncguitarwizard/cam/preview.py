"""Standalone SVG plots of a setup's toolpaths for visual checking."""

from __future__ import annotations

from collections.abc import Sequence

from ..geometry.primitives import Point2D
from .gcode import Setup
from .planar import polygon_bounds
from .toolpath import Move


def render_setup_svg(
    setup: Setup,
    outline: Sequence[Point2D],
    tool_diameter: float | None = None,
) -> str:
    """Return an SVG of every move in ``setup`` over the part outline.

    Rapids are dashed grey, cuts are coloured from blue (shallow) to red
    (deep). Consecutive moves at one depth are joined into a single path
    element, so even a long program stays a small file. The outline is
    drawn in the setup's own machine frame, so a flipped setup shows the
    mirrored part. When ``tool_diameter`` is given (or the setup carries
    its own tool), every cut is also drawn as a translucent band that
    wide, so the material actually removed is visible rather than only
    the tool-centre line — two pockets that share a wall then meet on
    the drawing exactly as they do in the wood.
    """
    if tool_diameter is None and setup.tool is not None:
        tool_diameter = setup.tool.tool_diameter
    min_x, min_y, max_x, max_y = polygon_bounds(outline)
    margin = 20.0
    width = max_x - min_x + 2.0 * margin
    height = max_y - min_y + 2.0 * margin
    deepest = min((path.deepest_z() for path in setup.toolpaths), default=-1.0)
    deepest = min(deepest, -1e-6)

    def sx(x: float) -> str:
        return f"{x - min_x + margin:.2f}"

    def sy(y: float) -> str:
        return f"{max_y - y + margin:.2f}"

    def colour(z: float) -> str:
        fraction = min(1.0, max(0.0, z / deepest))
        return f"rgb({int(40 + 200 * fraction)},60,{int(220 - 180 * fraction)})"

    parts = [
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width:.2f} {height:.2f}" '
            f'width="{width * 1.5:.0f}" height="{height * 1.5:.0f}">'
        ),
        f'<rect width="{width:.2f}" height="{height:.2f}" fill="white"/>',
        '<path d="'
        + " ".join(
            f"{'M' if index == 0 else 'L'}{sx(point.x)},{sy(point.y)}"
            for index, point in enumerate(outline)
        )
        + ' Z" fill="#f1e4c8" stroke="#6b4a1f" stroke-width="0.8"/>',
        f'<text x="{margin:.1f}" y="{margin * 0.6:.1f}" font-size="6" '
        f'font-family="sans-serif">{_escape(setup.description)}</text>',
    ]
    if tool_diameter:
        parts.append(
            f'<text x="{margin:.1f}" y="{margin * 0.6 + 7:.1f}" font-size="4.5" '
            'font-family="sans-serif" fill="#555">Shaded bands show the '
            f'{tool_diameter:g} mm tool width; thin lines are the tool centre.'
            "</text>"
        )
    for path in setup.toolpaths:
        rapids: list[str] = []
        run: list[str] = []
        run_z: float | None = None
        previous: Move | None = None

        def flush() -> None:
            if len(run) > 1 and run_z is not None:
                data = "M" + run[0] + " L" + " ".join(run[1:])
                if tool_diameter:
                    parts.append(
                        f'<path d="{data}" fill="none" stroke="{colour(run_z)}" '
                        f'stroke-width="{tool_diameter:.2f}" stroke-opacity="0.25" '
                        'stroke-linecap="round" stroke-linejoin="round"/>'
                    )
                parts.append(
                    f'<path d="{data}" fill="none" stroke="{colour(run_z)}" '
                    'stroke-width="0.45"/>'
                )
            run.clear()

        for move in path.moves:
            if previous is not None and (
                previous.x != move.x or previous.y != move.y
            ):
                if move.rapid:
                    flush()
                    rapids.append(
                        f"M{sx(previous.x)},{sy(previous.y)} "
                        f"L{sx(move.x)},{sy(move.y)}"
                    )
                else:
                    if run_z != move.z or not run:
                        flush()
                        run_z = move.z
                        run.append(f"{sx(previous.x)},{sy(previous.y)}")
                    run.append(f"{sx(move.x)},{sy(move.y)}")
            previous = move
        flush()
        if rapids:
            parts.append(
                f'<path d="{" ".join(rapids)}" fill="none" stroke="#999" '
                'stroke-width="0.3" stroke-dasharray="1.5,1"/>'
            )
    parts.append(
        f'<circle cx="{sx(0.0)}" cy="{sy(0.0)}" r="2" fill="none" '
        'stroke="#000" stroke-width="0.5"/>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
