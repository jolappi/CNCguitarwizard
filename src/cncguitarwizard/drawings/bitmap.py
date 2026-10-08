"""Pictures in a drawing, traced: the dark shapes of a PNG as outlines.

A picture pasted into the template (a scanned or downloaded graphic) is
read without any library: the PNG is decoded here (every colour type and
bit depth, not interlaced), its pixels marked as ink where they are dark
and opaque, and the ink's edges traced into closed outlines in the
picture's own pixels — each a loop round a dark shape or round a hole in
one.
"""

from __future__ import annotations

import base64
import binascii
import struct
import zlib
from collections.abc import Sequence

from .exceptions import DrawingError

INK_LEVEL = 128
"""A pixel is ink below this lightness (0 to 255) and at least this
opaque."""

MAX_CELLS = 480
"""The most cells a traced picture is read in, along either side: a
bigger one is read in blocks of pixels, each ink where half of it is."""

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def picture_bytes(href: str) -> bytes:
    """Return a picture's file from its ``data:`` URI.

    Raises:
        DrawingError: If it is a file's name (not in the drawing) or not
            a PNG.
    """
    if not href.startswith("data:"):
        raise DrawingError(
            "A picture linked from a file, not kept in the drawing, cannot be "
            "read: embed it (Inkscape asks on import) or trace it into paths."
        )
    header, _, payload = href.partition(",")
    if "image/png" not in header or ";base64" not in header:
        raise DrawingError(
            "Only a PNG picture can be traced here; trace it into paths in the "
            "drawing program (Inkscape: Path > Trace Bitmap)."
        )
    try:
        return base64.b64decode("".join(payload.split()), validate=True)
    except (binascii.Error, ValueError) as error:
        raise DrawingError(f"The picture cannot be read ({error}).") from error


def png_ink(data: bytes) -> tuple[int, int, list[bytearray]]:
    """Return a PNG's width, height and ink: one row of 0/1 per pixel row.

    A pixel is ink where it is darker than ``INK_LEVEL`` and at least
    that opaque.

    Raises:
        DrawingError: If it is not a PNG this can read.
    """
    if not data.startswith(PNG_SIGNATURE):
        raise DrawingError("The picture is not a PNG.")
    position = len(PNG_SIGNATURE)
    header = b""
    palette = b""
    transparent = b""
    compressed = bytearray()
    while position + 8 <= len(data):
        (length,) = struct.unpack(">I", data[position : position + 4])
        kind = data[position + 4 : position + 8]
        body = data[position + 8 : position + 8 + length]
        position += 12 + length
        if kind == b"IHDR":
            header = body
        elif kind == b"PLTE":
            palette = body
        elif kind == b"tRNS":
            transparent = body
        elif kind == b"IDAT":
            compressed += body
        elif kind == b"IEND":
            break
    if len(header) < 13:
        raise DrawingError("The picture's PNG has no header.")
    width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", header)
    if interlace:
        raise DrawingError(
            "The picture is an interlaced PNG: save it without interlacing, or "
            "trace it into paths in the drawing program."
        )
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(colour)
    if channels is None or depth not in (1, 2, 4, 8, 16):
        raise DrawingError("The picture's PNG colour type cannot be read.")
    try:
        raw = zlib.decompress(bytes(compressed))
    except zlib.error as error:
        raise DrawingError(f"The picture's PNG data is broken ({error}).") from error
    bits = channels * depth
    stride = (width * bits + 7) // 8
    step = max(1, bits // 8)
    rows = _unfiltered(raw, height, stride, step)
    ink: list[bytearray] = []
    for row in rows:
        samples = _samples(row, width * channels, depth)
        ink.append(
            _ink_row(samples, width, colour, depth, channels, palette, transparent)
        )
    return width, height, ink


def _unfiltered(raw: bytes, height: int, stride: int, step: int) -> list[bytes]:
    """Return a PNG's scanlines with their filters undone."""
    rows: list[bytes] = []
    previous = bytearray(stride)
    position = 0
    for _ in range(height):
        if position + 1 + stride > len(raw):
            raise DrawingError("The picture's PNG data is cut short.")
        kind = raw[position]
        line = bytearray(raw[position + 1 : position + 1 + stride])
        position += 1 + stride
        if kind == 1:
            for i in range(step, stride):
                line[i] = (line[i] + line[i - step]) & 0xFF
        elif kind == 2:
            for i in range(stride):
                line[i] = (line[i] + previous[i]) & 0xFF
        elif kind == 3:
            for i in range(stride):
                left = line[i - step] if i >= step else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 0xFF
        elif kind == 4:
            for i in range(stride):
                a = line[i - step] if i >= step else 0
                b = previous[i]
                c = previous[i - step] if i >= step else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                guess = a if pa <= pb and pa <= pc else b if pb <= pc else c
                line[i] = (line[i] + guess) & 0xFF
        elif kind != 0:
            raise DrawingError("The picture's PNG data has an unknown filter.")
        rows.append(bytes(line))
        previous = line
    return rows


def _samples(row: bytes, count: int, depth: int) -> Sequence[int]:
    """Return a scanline's ``count`` samples: 8-bit ones as they are, a
    16-bit sample's high byte, 1, 2 and 4-bit ones unpacked."""
    if depth == 8:
        return row
    if depth == 16:
        return row[0::2]
    mask = (1 << depth) - 1
    values = [
        (byte >> shift) & mask for byte in row for shift in range(8 - depth, -1, -depth)
    ]
    return values[:count]


def _ink_row(
    samples: Sequence[int],
    width: int,
    colour: int,
    depth: int,
    channels: int,
    palette: bytes,
    transparent: bytes,
) -> bytearray:
    row = bytearray(width)
    scale = 255 // ((1 << depth) - 1) if depth < 8 else 1
    for x in range(width):
        base = x * channels
        alpha = 255
        if colour == 3:
            index = samples[base]
            r, g, b = palette[3 * index : 3 * index + 3] or b"\0\0\0"
            if index < len(transparent):
                alpha = transparent[index]
            light = (299 * r + 587 * g + 114 * b) // 1000
        elif colour in (0, 4):
            light = samples[base] * scale
            if colour == 4:
                alpha = samples[base + 1]
        else:
            r, g, b = samples[base], samples[base + 1], samples[base + 2]
            light = (299 * r + 587 * g + 114 * b) // 1000
            if colour == 6:
                alpha = samples[base + 3]
        row[x] = 1 if light < INK_LEVEL and alpha >= INK_LEVEL else 0
    return row


def traced_outlines(
    width: int, height: int, ink: Sequence[bytearray]
) -> list[list[tuple[float, float]]]:
    """Return the ink's edges as closed loops, in pixels (Y down).

    A big picture is read in square blocks of pixels (``MAX_CELLS`` along
    its longer side at most), a block ink where half of its pixels are.
    Each loop follows the cells' edges, round a shape or a hole, and ends
    where it began; its straight runs are one segment each.
    """
    block = max(1, -(-max(width, height) // MAX_CELLS))
    columns = -(-width // block)
    rows = -(-height // block)
    cells = [bytearray(columns) for _ in range(rows)]
    for r in range(rows):
        top = r * block
        lines = ink[top : min(height, top + block)]
        for c in range(columns):
            left = c * block
            right = min(width, left + block)
            count = sum(sum(line[left:right]) for line in lines)
            if 2 * count >= len(lines) * (right - left):
                cells[r][c] = 1

    def filled(r: int, c: int) -> bool:
        return 0 <= r < rows and 0 <= c < columns and cells[r][c] == 1

    # Every edge between an ink cell and a blank one, ink on its right
    # (Y down), from vertex to vertex.
    edges: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for r in range(rows):
        for c in range(columns):
            if not cells[r][c]:
                continue
            if not filled(r - 1, c):
                edges.setdefault((c, r), []).append((c + 1, r))
            if not filled(r, c + 1):
                edges.setdefault((c + 1, r), []).append((c + 1, r + 1))
            if not filled(r + 1, c):
                edges.setdefault((c + 1, r + 1), []).append((c, r + 1))
            if not filled(r, c - 1):
                edges.setdefault((c, r + 1), []).append((c, r))
    loops: list[list[tuple[float, float]]] = []
    while edges:
        start = next(iter(edges))
        loop = [start]
        here, came = start, None
        while True:
            ways = edges.get(here)
            if not ways:
                break
            # Where two shapes touch corner to corner, keep them apart:
            # turn right (toward the ink) before going on.
            way = ways[0]
            if came is not None and len(ways) > 1:
                dx, dy = here[0] - came[0], here[1] - came[1]
                turned = (here[0] - dy, here[1] + dx)
                way = turned if turned in ways else ways[0]
            ways.remove(way)
            if not ways:
                del edges[here]
            came, here = here, way
            if here == start:
                break
            loop.append(here)
        corners = _corners(loop)
        if len(corners) >= 3:
            loops.append([(x * block, y * block) for x, y in (*corners, corners[0])])
    return loops


def _corners(loop: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    """Return a closed loop's points where it turns (its straight runs
    one segment each)."""
    count = len(loop)
    kept = []
    for index, point in enumerate(loop):
        before, after = loop[index - 1], loop[(index + 1) % count]
        if (point[0] - before[0], point[1] - before[1]) != (
            after[0] - point[0],
            after[1] - point[1],
        ):
            kept.append(point)
    return kept
