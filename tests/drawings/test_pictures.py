"""Tests for pictures in a drawing: PNGs decoded and their dark shapes traced."""

import base64
import struct
import zlib

import pytest

from cncguitarwizard.drawings import (
    DrawingError,
    TemplateFrame,
    read_template_outline,
    read_template_pattern,
    template_svg,
)
from cncguitarwizard.drawings.bitmap import picture_bytes, png_ink, traced_outlines
from cncguitarwizard.geometry.primitives import Point2D, closed_catmull_rom_spans

BODY = TemplateFrame((Point2D(0, 0), Point2D(100, 0), Point2D(0, 100)))


def _png(
    rows: list[bytes], colour: int, depth: int = 8, filters: int = 0, **chunks: bytes
) -> bytes:  # noqa: E501
    """A PNG of raw scanlines, each written with filter ``filters`` (or
    the filters in turn, for ``filters=-1``)."""
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colour]
    step = max(1, channels * depth // 8)
    previous = bytes(len(rows[0]))
    data = bytearray()
    for index, row in enumerate(rows):
        kind = index % 5 if filters == -1 else filters
        out = bytearray()
        for i, value in enumerate(row):
            left = row[i - step] if i >= step else 0
            up = previous[i]
            corner = previous[i - step] if i >= step else 0
            if kind == 1:
                value -= left
            elif kind == 2:
                value -= up
            elif kind == 3:
                value -= (left + up) >> 1
            elif kind == 4:
                p = left + up - corner
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - corner)
                value -= left if pa <= pb and pa <= pc else up if pb <= pc else corner
            out.append(value & 0xFF)
        data += bytes([kind]) + out
        previous = row

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + b"\0\0\0\0"

    width = len(rows[0]) * 8 // (channels * depth)
    header = struct.pack(">IIBBBBB", width, len(rows), depth, colour, 0, 0, 0)
    extra = b"".join(chunk(kind.encode(), body) for kind, body in chunks.items())
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + extra
        + chunk(b"IDAT", zlib.compress(bytes(data)))
        + chunk(b"IEND", b"")
    )


def _square_rows(colour: int) -> list[bytes]:
    """An 8 x 8 picture, a dark 4 x 4 square from (2, 2) on light."""
    pixel = {
        0: (b"\x00", b"\xff"),
        2: (b"\x10\x10\x10", b"\xf0\xf0\xf0"),
        3: (b"\x01", b"\x00"),
        4: (b"\x00\xff", b"\x00\x00"),
        6: (b"\x00\x00\x00\xff", b"\xff\xff\xff\xff"),
    }[colour]
    return [
        b"".join(pixel[0] if 2 <= x < 6 and 2 <= y < 6 else pixel[1] for x in range(8))
        for y in range(8)
    ]


@pytest.mark.parametrize("colour", [0, 2, 3, 4, 6])
@pytest.mark.parametrize("filters", [0, -1])
def test_every_png_colour_type_and_filter_is_read(colour: int, filters: int) -> None:
    chunks = {"PLTE": b"\xff\xff\xff\x00\x00\x00"} if colour == 3 else {}
    data = _png(_square_rows(colour), colour, filters=filters, **chunks)
    width, height, ink = png_ink(data)
    assert (width, height) == (8, 8)
    assert [list(row) for row in ink] == [
        [1 if 2 <= x < 6 and 2 <= y < 6 else 0 for x in range(8)] for y in range(8)
    ]


def test_a_one_bit_png_and_transparency() -> None:
    # 1-bit grey: the left half dark.
    rows = [bytes([0b00001111]) for _ in range(4)]
    _, _, ink = png_ink(_png(rows, 0, depth=1))
    assert [list(row) for row in ink] == [[1, 1, 1, 1, 0, 0, 0, 0]] * 4
    # A palette's dark entry made transparent by tRNS is no ink.
    data = _png(_square_rows(3), 3, PLTE=b"\xff\xff\xff\x00\x00\x00", tRNS=b"\xff\x00")
    assert not any(any(row) for row in png_ink(data)[2])
    with pytest.raises(DrawingError, match="not a PNG"):
        png_ink(b"GIF89a")


def test_dark_shapes_are_traced_round_and_round_their_holes() -> None:
    (loop,) = traced_outlines(8, 8, png_ink(_png(_square_rows(0), 0))[2])
    assert loop[0] == loop[-1]
    assert sorted(set(loop)) == [(2, 2), (2, 6), (6, 2), (6, 6)]
    # A frame round a hole: a loop round it, and one round the hole.
    ring = [
        bytearray(
            1 if 1 <= x < 7 and 1 <= y < 7 and not (3 <= x < 5 and 3 <= y < 5) else 0
            for x in range(8)
        )
        for y in range(8)
    ]
    loops = traced_outlines(8, 8, ring)
    assert sorted(len(set(loop)) for loop in loops) == [4, 4]
    # Two squares touching at a corner stay two shapes.
    touching = [
        bytearray([1, 1, 0, 0]),
        bytearray([1, 1, 0, 0]),
        bytearray([0, 0, 1, 1]),
        bytearray([0, 0, 1, 1]),
    ]
    assert len(traced_outlines(4, 4, touching)) == 2


def _template(extra: str) -> str:
    points = [Point2D(x, y) for x, y in ((0, -150), (400, -150), (400, 150), (0, 150))]
    svg = template_svg("body", BODY, closed_catmull_rom_spans(points), [], (), ())
    return svg.replace("</svg>", f"{extra}</svg>")


def test_a_picture_pasted_beside_the_outline_is_traced_into_the_pattern() -> None:
    data = base64.b64encode(_png(_square_rows(0), 0)).decode()
    # An 8 mm picture at x 100, y -40 in the page (model Y 40 down to 32),
    # in no particular layer: its square is 4 mm from (102, 38) to (106, 34).
    picture = (
        f'<image x="100" y="-40" width="8" height="8" preserveAspectRatio="none" '
        f'xlink:href="data:image/png;base64,{data}" '
        'xmlns:xlink="http://www.w3.org/1999/xlink"/>'
    )
    # And a line drawn beside the outline, not in the Pattern layer.
    line = '<path d="M 50,0 L 80,0"/>'
    svg = _template(picture + line)
    read = read_template_pattern(svg, BODY)
    assert read is not None and read.pictures == 1 and read.beside == 1
    square = [line for line in read.lines if len(line) > 2]
    (loop,) = square
    xs = [p.x for p in loop]
    ys = [p.y for p in loop]
    assert (min(xs), max(xs), min(ys), max(ys)) == pytest.approx((102, 106, 34, 38))
    # The outline is still the outline; the rest is beside it.
    assert read_template_outline(svg, BODY).ignored == 1


def test_a_picture_that_cannot_be_traced_says_why() -> None:
    jpeg = (
        '<image x="0" y="0" width="5" height="5" href="data:image/jpeg;base64,AAAA"/>'
    )
    linked = '<image x="0" y="0" width="5" height="5" href="cross.png"/>'
    read = read_template_pattern(_template(jpeg + linked), BODY)
    assert read is not None and read.pictures == 0 and not read.lines
    assert "Only a PNG" in read.untraced[0]
    assert "linked from a file" in read.untraced[1]
    with pytest.raises(DrawingError):
        picture_bytes("data:image/png;base64,***")


def test_a_pasted_picture_becomes_the_body_engraving() -> None:
    from cncguitarwizard.webapp import import_outline, outline_template

    payload = {"prototype": {}}
    svg = outline_template(payload, "body")["svg"]
    data = base64.b64encode(_png(_square_rows(0), 0)).decode()
    # A 40 mm picture on the lower bout, pasted into the Outline layer.
    picture = (
        f'<image x="250" y="40" width="40" height="40" preserveAspectRatio="none" '
        f'xlink:href="data:image/png;base64,{data}" '
        'xmlns:xlink="http://www.w3.org/1999/xlink"/>'
    )
    layer = '<g id="cgwOutlineLayer"'
    start = svg.index(layer)
    end = svg.index("</g>", start)
    result = import_outline(payload, "body", svg[:end] + picture + svg[end:])
    values = result["values"]
    assert values["body_engraving_pattern"] == "drawn"
    (square,) = values["body_engraving_lines"]
    assert len(square) == 5
    assert "1 picture traced" in result["message"]
