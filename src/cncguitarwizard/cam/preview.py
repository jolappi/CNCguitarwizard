"""Standalone SVG plots of a setup's toolpaths for visual checking."""

from __future__ import annotations

from collections.abc import Callable, Sequence

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
    (deep), a bar under the part saying how deep the red is. Consecutive
    moves at one depth are joined into a single path element, so even a
    long program stays a small file. The outline is
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
    band_note = (
        f"Shaded bands show the {tool_diameter:g} mm tool width; thin lines are "
        "the tool centre."
        if tool_diameter
        else ""
    )
    # Wide enough for the title lines over a small part (a sans-serif
    # letter is about 0.55 of its size wide), and for the depth bar.
    width = max(
        max_x - min_x + 2.0 * margin,
        margin + 0.55 * max(6.0 * len(setup.description), 4.5 * len(band_note)),
        margin + _LEGEND_WIDTH,
    )
    # The depth bar grows with the plot, so it reads at the size a big
    # part is shown, in room of its own under the part.
    legend_scale = max(1.0, width / 200.0)
    legend_room = 8.0 * legend_scale if setup.toolpaths else 0.0
    height = max_y - min_y + 2.0 * margin + legend_room
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
    if band_note:
        parts.append(
            f'<text x="{margin:.1f}" y="{margin * 0.6 + 7:.1f}" font-size="4.5" '
            f'font-family="sans-serif" fill="#555">{band_note}</text>'
        )
    if setup.toolpaths:
        bar_top = height - margin * 0.5 - 3.0 * legend_scale
        parts.extend(_depth_legend(margin, bar_top, legend_scale, colour, deepest))
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
            if previous is not None and (previous.x != move.x or previous.y != move.y):
                if move.rapid:
                    flush()
                    rapids.append(
                        f"M{sx(previous.x)},{sy(previous.y)} L{sx(move.x)},{sy(move.y)}"
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


_LEGEND_WIDTH = 72.0
"""Room the depth bar and its words take across the plot at its least, in mm."""


def _depth_legend(
    left: float,
    top: float,
    scale: float,
    colour: Callable[[float], str],
    deepest: float,
) -> list[str]:
    """Return the bar saying which colour cuts how deep, under the part.

    Args:
        left: Where the bar starts across the plot.
        top: The bar's top, in the room under the part.
        scale: How much larger than its least the bar is drawn (1 or more).
        colour: A depth's colour, as the cuts are drawn.
        deepest: The deepest cut's depth (negative).

    Returns:
        SVG elements: a bar (40 mm at its least) from the surface's colour
        to the deepest cut's, "0 mm" over its start, the deepest depth over
        its end and "cut depth" after it.
    """
    bar, tall, size = 40.0 * scale, 3.0 * scale, 4.0 * scale
    text = f'font-size="{size:.1f}" font-family="sans-serif" fill="#555"'
    depth = f"{deepest:.1f}".replace("-", "−")  # a minus sign, not a hyphen
    return [
        '<defs><linearGradient id="toolpath-depth" x1="0" x2="1" y1="0" y2="0">'
        f'<stop offset="0" stop-color="{colour(0.0)}"/>'
        f'<stop offset="1" stop-color="{colour(deepest)}"/>'
        "</linearGradient></defs>",
        f'<rect x="{left:.1f}" y="{top:.1f}" width="{bar:.1f}" height="{tall:.1f}" '
        'fill="url(#toolpath-depth)"/>',
        f'<text x="{left:.1f}" y="{top - 0.3 * size:.1f}" {text}>0 mm</text>',
        f'<text x="{left + bar:.1f}" y="{top - 0.3 * size:.1f}" text-anchor="end" '
        f"{text}>{depth} mm</text>",
        f'<text x="{left + bar + 0.75 * size:.1f}" y="{top + 0.65 * size:.1f}" '
        f"{text}>cut depth</text>",
    ]


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
