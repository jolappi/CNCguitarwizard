"""The Elder Futhark's runes, drawn as strokes for fret markers.

Each rune is a few straight strokes in its own box, one unit tall and
``Rune.width`` wide (x to the right, y up), as it is carved: a stave and
its branches. ``rune_outlines`` draws them with a round pen
(``stroke_outlines``) at ``RUNE_STROKE`` of the height, an area a rune
closes in filled (an inlay piece cannot hold an island of wood), so each
gives one solid piece, or two for Jera's two hooks.

The meanings are the usual modern ones, short.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass

from ..exceptions import FretboardGeometryError
from ..primitives import Point2D, stroke_outlines

RUNE_STROKE = 0.12
"""A rune's stroke width as a share of its height."""

RUNE_CELL = 0.012
"""The grid a rune's outline is traced on, as a share of its height."""

RUNE_TOLERANCE = 0.002
"""How far a rune's outline may stray from its traced one, as a share of
its height."""


@dataclass(frozen=True, slots=True)
class Rune:
    """One rune: its glyph, what it stands for and how it is drawn.

    Args:
        name: Its name, ``"algiz"``.
        glyph: The Unicode rune, ``"ᛉ"``.
        meaning: What it stands for, in a few words.
        strokes: Its strokes as polylines of ``(x, y)`` in its box.
        width: Its box's width (its height is 1).
    """

    name: str
    glyph: str
    meaning: str
    strokes: tuple[tuple[tuple[float, float], ...], ...]
    width: float = 0.6


RUNES: dict[str, Rune] = {
    rune.name: rune
    for rune in (
        Rune(
            "fehu",
            "ᚠ",
            "wealth, cattle",
            (
                ((0.0, 0.0), (0.0, 1.0)),
                ((0.0, 0.75), (0.5, 1.0)),
                ((0.0, 0.45), (0.5, 0.75)),
            ),
            0.5,
        ),
        Rune(
            "uruz",
            "ᚢ",
            "strength, the aurochs",
            (((0.0, 0.0), (0.0, 1.0), (0.5, 0.7), (0.5, 0.0)),),
            0.5,
        ),
        Rune(
            "thurisaz",
            "ᚦ",
            "the thorn, protection, a giant",
            (
                ((0.0, 0.0), (0.0, 1.0)),
                ((0.0, 0.75), (0.45, 0.5), (0.0, 0.25)),
            ),
            0.45,
        ),
        Rune(
            "ansuz",
            "ᚨ",
            "Odin, wisdom, the spoken word",
            (
                ((0.0, 0.0), (0.0, 1.0)),
                ((0.0, 1.0), (0.5, 0.75)),
                ((0.0, 0.75), (0.5, 0.5)),
            ),
            0.5,
        ),
        Rune(
            "raidho",
            "ᚱ",
            "the journey, the ride",
            (((0.0, 0.0), (0.0, 1.0), (0.45, 0.78), (0.0, 0.55), (0.5, 0.0)),),
            0.5,
        ),
        Rune(
            "kaunan",
            "ᚲ",
            "the torch, knowledge",
            (((0.45, 0.85), (0.0, 0.5), (0.45, 0.15)),),
            0.45,
        ),
        Rune(
            "gebo",
            "ᚷ",
            "a gift, partnership",
            (
                ((0.0, 0.0), (0.6, 1.0)),
                ((0.0, 1.0), (0.6, 0.0)),
            ),
        ),
        Rune(
            "wunjo",
            "ᚹ",
            "joy, harmony",
            (((0.0, 0.0), (0.0, 1.0), (0.45, 0.78), (0.0, 0.55)),),
            0.45,
        ),
        Rune(
            "hagalaz",
            "ᚺ",
            "hail, a sudden change",
            (
                ((0.0, 0.0), (0.0, 1.0)),
                ((0.5, 0.0), (0.5, 1.0)),
                ((0.0, 0.65), (0.5, 0.35)),
            ),
            0.5,
        ),
        Rune(
            "naudiz",
            "ᚾ",
            "need, endurance",
            (
                ((0.25, 0.0), (0.25, 1.0)),
                ((0.0, 0.65), (0.5, 0.35)),
            ),
            0.5,
        ),
        Rune("isa", "ᛁ", "ice, stillness", (((0.0, 0.0), (0.0, 1.0)),), 0.0),
        Rune(
            "jera",
            "ᛃ",
            "the year, the harvest",
            (
                ((0.25, 0.95), (0.0, 0.75), (0.25, 0.55)),
                ((0.35, 0.45), (0.6, 0.25), (0.35, 0.05)),
            ),
        ),
        Rune(
            "eihwaz",
            "ᛇ",
            "the yew, defence, endurance",
            (
                ((0.25, 0.0), (0.25, 1.0)),
                ((0.25, 1.0), (0.5, 0.8)),
                ((0.25, 0.0), (0.0, 0.2)),
            ),
            0.5,
        ),
        Rune(
            "perthro",
            "ᛈ",
            "fate, mystery",
            (
                (
                    (0.45, 0.62),
                    (0.45, 0.78),
                    (0.0, 1.0),
                    (0.0, 0.0),
                    (0.45, 0.22),
                    (0.45, 0.38),
                ),
            ),
            0.45,
        ),
        Rune(
            "algiz",
            "ᛉ",
            "protection, the elk",
            (
                ((0.3, 0.0), (0.3, 1.0)),
                ((0.3, 0.55), (0.0, 0.95)),
                ((0.3, 0.55), (0.6, 0.95)),
            ),
        ),
        Rune(
            "sowilo",
            "ᛊ",
            "the sun, victory, success",
            (((0.4, 1.0), (0.0, 0.6), (0.4, 0.4), (0.0, 0.0)),),
            0.4,
        ),
        Rune(
            "tiwaz",
            "ᛏ",
            "Tyr, victory, honour",
            (
                ((0.3, 0.0), (0.3, 1.0)),
                ((0.0, 0.7), (0.3, 1.0), (0.6, 0.7)),
            ),
        ),
        Rune(
            "berkano",
            "ᛒ",
            "the birch, growth, new beginnings",
            (
                (
                    (0.0, 0.0),
                    (0.0, 1.0),
                    (0.45, 0.75),
                    (0.0, 0.5),
                    (0.45, 0.25),
                    (0.0, 0.0),
                ),
            ),
            0.45,
        ),
        Rune(
            "ehwaz",
            "ᛖ",
            "the horse, movement, trust",
            (((0.0, 0.0), (0.0, 1.0), (0.3, 0.7), (0.6, 1.0), (0.6, 0.0)),),
        ),
        Rune(
            "mannaz",
            "ᛗ",
            "mankind, the self",
            (
                ((0.0, 0.0), (0.0, 1.0), (0.6, 0.6)),
                ((0.6, 0.0), (0.6, 1.0), (0.0, 0.6)),
            ),
        ),
        Rune(
            "laguz",
            "ᛚ",
            "water, the flow of life",
            (((0.0, 0.0), (0.0, 1.0), (0.45, 0.75)),),
            0.45,
        ),
        Rune(
            "ingwaz",
            "ᛜ",
            "Ing, fertility, completion",
            (((0.3, 0.95), (0.6, 0.5), (0.3, 0.05), (0.0, 0.5), (0.3, 0.95)),),
        ),
        Rune(
            "dagaz",
            "ᛞ",
            "the day, dawn, breakthrough",
            (((0.0, 0.0), (0.0, 1.0), (0.6, 0.0), (0.6, 1.0), (0.0, 0.0)),),
        ),
        Rune(
            "othala",
            "ᛟ",
            "heritage, home, ancestry",
            (((0.0, 0.0), (0.58, 0.64), (0.3, 1.0), (0.02, 0.64), (0.6, 0.0)),),
        ),
    )
}
"""The Elder Futhark, in its order (fehu, uruz, thurisaz...)."""

DEFAULT_RUNES: tuple[str, ...] = (
    "fehu",
    "uruz",
    "thurisaz",
    "ansuz",
    "algiz",
    "sowilo",
    "tiwaz",
    "ehwaz",
    "mannaz",
    "othala",
)
"""The runes the marker frets get by default, nut first (wealth, strength,
protection, wisdom, protection, the sun, victory, the horse, mankind,
heritage); more frets than these start over."""


RUNE_EDITOR_TOLERANCE = 0.02
"""How far a rune's outline may stray for an editor's handles, as a share
of its height (fewer points than the cut one)."""


@functools.cache
def rune_outlines(
    name: str, tolerance: float = RUNE_TOLERANCE
) -> tuple[tuple[Point2D, ...], ...]:
    """Return a rune's pieces drawn with its strokes, in its unit box.

    Each counter-clockwise, in the rune's box (one unit tall, x to the
    right, y up; the strokes' round ends reach ``RUNE_STROKE / 2`` past
    it), an area the rune closes in filled, its points within
    ``tolerance`` of the traced outline.

    Raises:
        FretboardGeometryError: For a name not in ``RUNES``.
    """
    rune = RUNES.get(name)
    if rune is None:
        raise FretboardGeometryError(
            f"Unknown rune {name!r}; use one of {', '.join(RUNES)}."
        )
    return stroke_outlines(
        [[Point2D(x, y) for x, y in stroke] for stroke in rune.strokes],
        RUNE_STROKE / 2.0,
        RUNE_CELL,
        tolerance,
    )
