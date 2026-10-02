"""Single-stroke fonts for engraving text: each letter a few centre lines.

An engraving bit cuts along a line, so the letters are drawn as strokes
(lines and arcs through their middles), not outlines. ``GLYPHS`` is a
plain geometric sans drawn here: capitals 10 units tall, lowercase with a
7 unit x-height and 3 unit descenders, digits and a little punctuation.
``FONTS`` adds a script and a gothic converted from SVG fonts.
``text_lines`` sets a string in any of them at any height, position and
angle.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from .exceptions import GeometryException
from .fonts import gothic, script
from .primitives import Point2D

Stroke = tuple[tuple[float, float], ...]
"""One pen stroke: points in glyph units (capital height 10)."""

CAP_HEIGHT = 10.0
"""Height of a capital, in glyph units."""

LETTER_GAP = 2.5
"""Space between two letters, in glyph units."""

SPACE_WIDTH = 6.0
"""Width of a space, in glyph units."""

ARC_STEP_DEGREES = 10.0
"""Angle between the points an arc stroke is drawn through."""


def _arc(cx: float, cy: float, r: float, start: float, end: float) -> Stroke:
    """Return an arc from ``start`` to ``end`` degrees (either way round)."""
    count = max(2, math.ceil(abs(end - start) / ARC_STEP_DEGREES))
    return tuple(
        (
            cx + r * math.cos(math.radians(start + (end - start) * k / count)),
            cy + r * math.sin(math.radians(start + (end - start) * k / count)),
        )
        for k in range(count + 1)
    )


def _join(*parts: Stroke) -> Stroke:
    """Return strokes run together into one, dropping repeated points."""
    points: list[tuple[float, float]] = []
    for part in parts:
        for point in part:
            if not points or math.dist(points[-1], point) > 1e-6:
                points.append(point)
    return tuple(points)


def _dot(x: float, y: float) -> Stroke:
    return ((x, y), (x, y + 0.4))


_O_CAP = _arc(5.0, 5.0, 5.0, 90.0, 450.0)
_BOWL = _arc(3.5, 3.5, 3.5, 90.0, 450.0)

GLYPHS: dict[str, tuple[float, tuple[Stroke, ...]]] = {
    # Capitals.
    "A": (7.0, (((0, 0), (3.5, 10), (7, 0)), ((1.3, 3.8), (5.7, 3.8)))),
    "B": (
        7.0,
        (
            _join(
                ((0, 0), (0, 10), (4, 10)),
                _arc(4, 7.5, 2.5, 90, -90),
                ((4, 5), (0, 5)),
            ),
            _join(((0, 5), (4.5, 5)), _arc(4.5, 2.5, 2.5, 90, -90), ((4.5, 0), (0, 0))),
        ),
    ),
    "C": (8.6, (_arc(5, 5, 5, 45, 315),)),
    "D": (
        8.0,
        (_join(((0, 0), (0, 10), (3, 10)), _arc(3, 5, 5, 90, -90), ((3, 0), (0, 0))),),
    ),
    "E": (6.5, (((6, 10), (0, 10), (0, 0), (6, 0)), ((0, 5), (4.5, 5)))),
    "F": (6.5, (((6, 10), (0, 10), (0, 0)), ((0, 5), (4.5, 5)))),
    "G": (10.0, (_join(_arc(5, 5, 5, 45, 360), ((10, 5), (6, 5))),)),
    "H": (7.0, (((0, 0), (0, 10)), ((7, 0), (7, 10)), ((0, 5), (7, 5)))),
    "I": (0.0, (((0, 0), (0, 10)),)),
    "J": (5.0, (_join(((5, 10), (5, 3)), _arc(2.5, 3, 2.5, 0, -180)),)),
    "K": (6.5, (((0, 0), (0, 10)), ((6, 10), (0, 4)), ((2, 6), (6.5, 0)))),
    "L": (6.0, (((0, 10), (0, 0), (6, 0)),)),
    "M": (8.0, (((0, 0), (0, 10), (4, 3), (8, 10), (8, 0)),)),
    "N": (7.0, (((0, 0), (0, 10), (7, 0), (7, 10)),)),
    "O": (10.0, (_O_CAP,)),
    "P": (
        6.5,
        (
            _join(
                ((0, 0), (0, 10), (4, 10)), _arc(4, 7.5, 2.5, 90, -90), ((4, 5), (0, 5))
            ),
        ),
    ),
    "Q": (10.0, (_O_CAP, ((6.5, 3), (10, 0)))),
    "R": (
        7.0,
        (
            _join(
                ((0, 0), (0, 10), (4, 10)), _arc(4, 7.5, 2.5, 90, -90), ((4, 5), (0, 5))
            ),
            ((3.5, 5), (7, 0)),
        ),
    ),
    "S": (6.0, (_join(_arc(3.5, 7.5, 2.5, 30, 270), _arc(3.5, 2.5, 2.5, 90, -150)),)),
    "T": (7.0, (((0, 10), (7, 10)), ((3.5, 10), (3.5, 0)))),
    "U": (
        7.0,
        (
            _join(
                ((0, 10), (0, 3.5)), _arc(3.5, 3.5, 3.5, 180, 360), ((7, 3.5), (7, 10))
            ),
        ),
    ),
    "V": (7.0, (((0, 10), (3.5, 0), (7, 10)),)),
    "W": (10.0, (((0, 10), (2.5, 0), (5, 7), (7.5, 0), (10, 10)),)),
    "X": (7.0, (((0, 10), (7, 0)), ((7, 10), (0, 0)))),
    "Y": (7.0, (((0, 10), (3.5, 5), (7, 10)), ((3.5, 5), (3.5, 0)))),
    "Z": (7.0, (((0, 10), (7, 10), (0, 0), (7, 0)),)),
    # Lowercase.
    "a": (7.0, (_BOWL, ((7, 7), (7, 0)))),
    "b": (7.0, (((0, 10), (0, 0)), _BOWL)),
    "c": (6.5, (_arc(3.5, 3.5, 3.5, 45, 315),)),
    "d": (7.0, (_BOWL, ((7, 10), (7, 0)))),
    "e": (7.0, (_join(((0, 3.5), (7, 3.5)), _arc(3.5, 3.5, 3.5, 0, 320)),)),
    "f": (
        5.0,
        (_join(_arc(4.5, 8.5, 1.5, 20, 180), ((3, 8.5), (3, 0))), ((1, 6.5), (5, 6.5))),
    ),
    "g": (7.0, (_BOWL, _join(((7, 7), (7, -0.5)), _arc(3.5, -0.5, 3.5, 0, -160)))),
    "h": (6.0, (((0, 10), (0, 0)), _join(_arc(3, 4, 3, 180, 0), ((6, 4), (6, 0))))),
    "i": (0.0, (((0, 7), (0, 0)), _dot(0, 9))),
    "j": (3.0, (_join(((3, 7), (3, -1.5)), _arc(1.5, -1.5, 1.5, 0, -180)), _dot(3, 9))),
    "k": (5.5, (((0, 10), (0, 0)), ((5, 7), (0, 2.5)), ((1.8, 4), (5.5, 0)))),
    "l": (0.0, (((0, 10), (0, 0)),)),
    "m": (
        9.0,
        (
            ((0, 7), (0, 0)),
            _join(_arc(2.25, 4.75, 2.25, 180, 0), ((4.5, 4.75), (4.5, 0))),
            _join(_arc(6.75, 4.75, 2.25, 180, 0), ((9, 4.75), (9, 0))),
        ),
    ),
    "n": (6.0, (((0, 7), (0, 0)), _join(_arc(3, 4, 3, 180, 0), ((6, 4), (6, 0))))),
    "o": (7.0, (_BOWL,)),
    "p": (7.0, (((0, 7), (0, -3)), _BOWL)),
    "q": (7.0, (_BOWL, ((7, 7), (7, -3)))),
    "r": (4.5, (((0, 7), (0, 0)), _arc(3, 4, 3, 180, 60))),
    "s": (
        4.5,
        (_join(_arc(2.5, 5.25, 1.75, 30, 270), _arc(2.5, 1.75, 1.75, 90, -150)),),
    ),
    "t": (
        4.5,
        (_join(((2, 10), (2, 1.5)), _arc(3.5, 1.5, 1.5, 180, 300)), ((0, 7), (4.5, 7))),
    ),
    "u": (
        7.0,
        (_join(((0, 7), (0, 3.5)), _arc(3.5, 3.5, 3.5, 180, 360)), ((7, 7), (7, 0))),
    ),
    "v": (6.0, (((0, 7), (3, 0), (6, 7)),)),
    "w": (9.0, (((0, 7), (2, 0), (4.5, 5.5), (7, 0), (9, 7)),)),
    "x": (6.0, (((0, 7), (6, 0)), ((6, 7), (0, 0)))),
    "y": (6.0, (((0, 7), (3, 0)), ((6, 7), (1.5, -3)))),
    "z": (6.0, (((0, 7), (6, 7), (0, 0), (6, 0)),)),
    # Digits.
    "0": (
        7.0,
        (
            _join(
                _arc(3.5, 6.5, 3.5, 0, 180),
                ((0, 6.5), (0, 3.5)),
                _arc(3.5, 3.5, 3.5, 180, 360),
                ((7, 3.5), (7, 6.5)),
            ),
        ),
    ),
    "1": (3.0, (((0, 8), (3, 10), (3, 0)),)),
    "2": (7.0, (_join(_arc(3.5, 6.5, 3.5, 160, -40), ((0, 0), (7, 0))),)),
    "3": (6.0, (_join(_arc(3.5, 7.5, 2.5, 150, -90), _arc(3.5, 2.5, 2.5, 90, -150)),)),
    "4": (7.0, (((5, 0), (5, 10), (0, 3), (7, 3)),)),
    "5": (
        7.0,
        (_join(((6, 10), (1, 10), (0.8, 5.6)), _arc(3.4, 3.4, 3.4, 140, -140)),),
    ),
    "6": (7.0, (_BOWL, _arc(7, 3.5, 7, 180, 120))),
    "7": (7.0, (((0, 10), (7, 10), (2.5, 0)),)),
    "8": (7.0, (_arc(3.5, 7.6, 2.4, 270, 630), _arc(3.5, 2.6, 2.6, 90, 450))),
    "9": (7.0, (_arc(3.5, 6.5, 3.5, 90, 450), _arc(0, 6.5, 7, 0, -60))),
    # Punctuation.
    ".": (0.0, (_dot(0, 0),)),
    ",": (1.0, (((1, 0.5), (0, -1.5)),)),
    "-": (4.0, (((0, 4), (4, 4)),)),
    "'": (0.0, (((0, 10), (0, 7.5)),)),
    "!": (0.0, (((0, 10), (0, 3)), _dot(0, 0))),
    "?": (
        6.0,
        (_join(_arc(3, 7.5, 2.5, 160, -60), ((4.25, 5.33), (3, 3))), _dot(3, 0)),
    ),
    "/": (6.0, (((0, 0), (6, 10)),)),
    ":": (0.0, (_dot(0, 0), _dot(0, 6))),
    "&": (
        7.5,
        (
            _join(
                ((7.5, 0), (1.5, 6.5)),
                _arc(3, 8, 2, 225, -45),
                ((4.4, 6.6), (0, 2.5)),
                _arc(2.5, 2.5, 2.5, 180, 300),
                ((3.75, 0.33), (7, 4)),
            ),
        ),
    ),
    "+": (6.0, (((0, 5), (6, 5)), ((3, 2), (3, 8)))),
    "#": (
        7.0,
        (
            ((2, 0), (3, 10)),
            ((5, 0), (6, 10)),
            ((0.5, 3.5), (7, 3.5)),
            ((0.5, 6.5), (7, 6.5)),
        ),
    ),
}
"""Each glyph's width and strokes, in glyph units (its left edge at 0)."""


@dataclass(frozen=True, slots=True)
class Font:
    """A single-stroke font: its glyphs and how they set.

    Args:
        cap_height: Height of a capital, in the glyphs' units.
        glyphs: Each character's advance (or width) and strokes.
        letter_gap: Space added after each glyph, in its units (the
            converted fonts' advances include their own).
        space_width: Width of a space, unless the font has a glyph for it.
    """

    cap_height: float
    glyphs: Mapping[str, tuple[float, Sequence[Sequence[tuple[float, float]]]]]
    letter_gap: float = 0.0
    space_width: float = 0.0

    def advance(self, character: str) -> float:
        """Return how far ``character`` moves the pen, in glyph units."""
        if character in self.glyphs:
            return self.glyphs[character][0] + self.letter_gap
        if character == " ":
            return self.space_width
        raise GeometryException(f"The lettering has no glyph for {character!r}.")


FontName = Literal["sans", "script", "gothic"]
"""The engraving fonts, by name (see ``FONTS``)."""

FONTS: dict[str, Font] = {
    "sans": Font(CAP_HEIGHT, GLYPHS, LETTER_GAP, SPACE_WIDTH),
    "script": Font(script.CAP_HEIGHT, script.GLYPHS),
    "gothic": Font(gothic.CAP_HEIGHT, gothic.GLYPHS),
}
"""The plain geometric sans above, Hershey Script (medium) and Hershey
Gothic English (converted from SVG fonts, ``geometry.fonts``)."""


def text_width(text: str, font: str = "sans") -> float:
    """Return how wide ``text`` sets in ``font``, in its glyph units.

    Raises:
        GeometryException: For a character the font has no glyph for.
    """
    face = FONTS[font]
    widths = [face.advance(character) for character in text]
    return sum(widths) - (face.letter_gap if widths and text[-1] != " " else 0.0)


def text_lines(
    text: str,
    height: float,
    centre: Point2D,
    angle_degrees: float,
    font: str = "sans",
) -> tuple[tuple[Point2D, ...], ...]:
    """Return ``text``'s strokes in ``font``, set ``height`` tall about ``centre``.

    The capitals are ``height`` tall; the line of text is centred on
    ``centre`` both ways (its capitals' middle on it) and runs along
    ``angle_degrees`` from +X, the letters' tops to its left.

    Raises:
        GeometryException: For a non-positive height, an unknown font or a
            character the font has no glyph for.
    """
    if not math.isfinite(height) or height <= 0.0:
        raise GeometryException("The lettering's height must be positive.")
    if font not in FONTS:
        raise GeometryException(
            f"Unknown lettering font {font!r}: choose one of {', '.join(FONTS)}."
        )
    face = FONTS[font]
    unknown = sorted({c for c in text if c != " " and c not in face.glyphs})
    if unknown:
        raise GeometryException(
            f"The lettering has no glyph for {''.join(unknown)!r}: use letters, "
            "digits and punctuation."
        )
    scale = height / face.cap_height
    angle = math.radians(angle_degrees)
    along = (math.cos(angle), math.sin(angle))
    up = (-math.sin(angle), math.cos(angle))
    left = -text_width(text, font) / 2.0
    middle = face.cap_height / 2.0
    lines: list[tuple[Point2D, ...]] = []
    for character in text:
        if character in face.glyphs:
            for stroke in face.glyphs[character][1]:
                lines.append(
                    tuple(
                        _placed(left + x, y - middle, scale, centre, along, up)
                        for x, y in stroke
                    )
                )
        left += face.advance(character)
    return tuple(lines)


def _placed(
    u: float,
    v: float,
    scale: float,
    centre: Point2D,
    along: tuple[float, float],
    up: tuple[float, float],
) -> Point2D:
    return Point2D(
        centre.x + (u * along[0] + v * up[0]) * scale,
        centre.y + (u * along[1] + v * up[1]) * scale,
    )
