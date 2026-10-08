"""A small DXF writer: AutoCAD R12 (AC1009) ASCII, in millimetres.

R12 is the DXF almost every CAD, CAM and laser program reads. Shapes are
closed ``POLYLINE``s (or open ones), ``CIRCLE``s, ``LINE``s, ``POINT``s and
``TEXT``, each on a named layer with an AutoCAD colour index.
"""

from __future__ import annotations

from collections.abc import Iterable

from ...geometry.primitives import Point2D

INSUNITS_MM = 4
"""``$INSUNITS`` for millimetres (read by the programs that look for it)."""


class DxfDocument:
    """A drawing's layers and entities, rendered as one R12 DXF file."""

    def __init__(self) -> None:
        self._layers: dict[str, int] = {}
        self._entities: list[str] = []

    def layer(self, name: str, colour: int) -> str:
        """Declare a layer (its AutoCAD colour index) and return its name."""
        self._layers.setdefault(name, colour)
        return name

    def polyline(
        self, points: Iterable[Point2D], layer: str, closed: bool = True
    ) -> None:
        """Add a polyline through ``points`` (closed by default)."""
        vertices = list(points)
        if closed and len(vertices) > 1 and vertices[0] == vertices[-1]:
            vertices.pop()
        if len(vertices) < 2:
            return
        parts = [
            _pairs((0, "POLYLINE"), (8, layer), (66, 1), (70, 1 if closed else 0))
            + _pairs((10, 0.0), (20, 0.0), (30, 0.0))
        ]
        parts += [
            _pairs((0, "VERTEX"), (8, layer), (10, point.x), (20, point.y), (30, 0.0))
            for point in vertices
        ]
        parts.append(_pairs((0, "SEQEND"), (8, layer)))
        self._entities.append("".join(parts))

    def circle(self, centre: Point2D, radius: float, layer: str) -> None:
        """Add a circle."""
        self._entities.append(
            _pairs(
                (0, "CIRCLE"),
                (8, layer),
                (10, centre.x),
                (20, centre.y),
                (30, 0.0),
                (40, radius),
            )
        )

    def point(self, at: Point2D, layer: str) -> None:
        """Add a point."""
        self._entities.append(
            _pairs((0, "POINT"), (8, layer), (10, at.x), (20, at.y), (30, 0.0))
        )

    def line(self, start: Point2D, end: Point2D, layer: str) -> None:
        """Add a straight line."""
        self._entities.append(
            _pairs(
                (0, "LINE"),
                (8, layer),
                (10, start.x),
                (20, start.y),
                (30, 0.0),
                (11, end.x),
                (21, end.y),
                (31, 0.0),
            )
        )

    def text(self, at: Point2D, height: float, value: str, layer: str) -> None:
        """Add a line of text, its baseline starting at ``at``."""
        self._entities.append(
            _pairs(
                (0, "TEXT"),
                (8, layer),
                (10, at.x),
                (20, at.y),
                (30, 0.0),
                (40, height),
                (1, value),
            )
        )

    def render(self) -> str:
        """Return the whole file."""
        header = _pairs(
            (0, "SECTION"),
            (2, "HEADER"),
            (9, "$ACADVER"),
            (1, "AC1009"),
            (9, "$INSUNITS"),
            (70, INSUNITS_MM),
            (9, "$MEASUREMENT"),
            (70, 1),
            (0, "ENDSEC"),
        )
        tables = (
            _pairs((0, "SECTION"), (2, "TABLES"))
            + _pairs((0, "TABLE"), (2, "LTYPE"), (70, 1))
            + _pairs(
                (0, "LTYPE"),
                (2, "CONTINUOUS"),
                (70, 0),
                (3, "Solid line"),
                (72, 65),
                (73, 0),
                (40, 0.0),
            )
            + _pairs((0, "ENDTAB"))
            + _pairs((0, "TABLE"), (2, "LAYER"), (70, len(self._layers)))
            + "".join(
                _pairs(
                    (0, "LAYER"), (2, name), (70, 0), (62, colour), (6, "CONTINUOUS")
                )
                for name, colour in self._layers.items()
            )
            + _pairs((0, "ENDTAB"), (0, "ENDSEC"))
        )
        entities = (
            _pairs((0, "SECTION"), (2, "ENTITIES"))
            + "".join(self._entities)
            + _pairs((0, "ENDSEC"))
        )
        return header + tables + entities + _pairs((0, "EOF"))


def _pairs(*pairs: tuple[int, str | int | float]) -> str:
    """Return group code / value pairs, one per two lines."""
    lines = []
    for code, value in pairs:
        if isinstance(value, float):
            text = f"{value:.4f}"
        else:
            text = str(value)
        lines.append(f"{code:>3}\n{text}\n")
    return "".join(lines)
