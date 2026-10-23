"""Tests for sharp corners and straight spans in the drawn lines, and
round points in the drawn polygons."""

from dataclasses import replace

import pytest

from cncguitarwizard.geometry.exceptions import (
    BodyGeometryError,
    FretboardGeometryError,
    HeadstockGeometryError,
)
from cncguitarwizard.geometry.fretboard import FretboardSurface, InlayLayout
from cncguitarwizard.geometry.primitives import CORNER, ROUND, Point2D
from cncguitarwizard.geometry.primitives.bezier import bezier_point, hermite_spans
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import (
    YOUR_DESIGN_TEMPLATES,
    YourDesignShape,
    mirrored_shape,
    widened_shape,
)
from cncguitarwizard.presets.pickup_frames import FRAME_POINTS
from cncguitarwizard.presets.prototype001 import BODY_TEMPLATE_VALUES
from cncguitarwizard.presets.truss_rod_covers import (
    CUSTOM_COVER_RADIUS,
    check_custom_cover,
    truss_rod_cover_shape,
)
from cncguitarwizard.webapp import (
    _jsonable,
    body_editor_layout,
    headstock_editor_layout,
    import_outline,
    inlay_editor_layout,
    outline_template,
)

DRAWN = Prototype001Parameters().body_shape
assert isinstance(DRAWN, YourDesignShape)
# A drawn inlay: a tooth, wide on the bass side.
TOOTH = ((0.25, 0.8), (0.75, 0.8), (0.75, -0.5))
# A drawn six-in-line headstock round the default row of posts, its tip
# shaped by two points.
DRAWN_HEADSTOCK = {
    "nut_style": "slot",
    "locking_nut": "none",
    "headstock_angle": 0.0,
    "headstock_style": "6_inline",
    "headstock_outline": "drawn",
    "headstock_bass_edge": (
        (12.0, 26.0),
        (26.0, 35.0),
        (40.0, 39.5),
        (80.0, 29.4),
        (120.0, 19.4),
        (160.0, 9.3),
        (183.0, 2.8),
        (196.0, -5.0),
        (204.0, -20.0),
    ),
    "headstock_treble_edge": (
        (15.0, 23.0),
        (70.0, 24.5),
        (120.0, 26.5),
        (160.0, 30.0),
        (186.0, 36.0),
        (204.0, 39.0),
    ),
    "headstock_tip_points": ((3.5, 27.0), (4.5, 33.0)),
}


def cornered(points: tuple, *indices: int, mark: str = CORNER) -> tuple:  # type: ignore[type-arg]
    """``points`` with those marked sharp corners (or ``mark``)."""
    return tuple(
        (*point, mark) if index in indices else tuple(point)
        for index, point in enumerate(points)
    )


def distance_to_chord(point: Point2D, a: Point2D, b: Point2D) -> float:
    dx, dy = b.x - a.x, b.y - a.y
    return abs(dx * (point.y - a.y) - dy * (point.x - a.x)) / (dx * dx + dy * dy) ** 0.5


def test_the_outline_runs_straight_between_two_corners() -> None:
    shape = replace(DRAWN, control_points=cornered(DRAWN.control_points, 20, 21))
    outline = shape.outline_points(0.0)

    a, b = (Point2D(*shape.control_points[i][:2]) for i in (20, 21))
    for point in outline[20 * 8 : 21 * 8 + 1]:
        assert distance_to_chord(point, a, b) == pytest.approx(0.0, abs=1e-9)
    # Elsewhere it is as before.
    assert outline[: 20 * 8 - 8] == DRAWN.outline_points(0.0)[: 20 * 8 - 8]
    replace(Prototype001Parameters(), body_shape=shape).build()


def test_corners_stay_with_their_points_mirrored_and_widened() -> None:
    shape = replace(
        DRAWN,
        control_points=cornered(DRAWN.control_points, 5),
        heel_relief_points=((-20.0, 40.0), (10.0, 30.0, CORNER), (-20.0, -40.0)),
    )

    mirrored = mirrored_shape(shape)
    assert isinstance(mirrored, YourDesignShape)
    marked = [p for p in mirrored.control_points if len(p) == 3]
    assert marked == [(shape.control_points[5][0], -shape.control_points[5][1], CORNER)]
    assert mirrored.heel_relief_points[1] == (10.0, -30.0, CORNER)
    widened = widened_shape(shape, 12.0)
    assert widened.heel_relief_points[1] == (10.0, 36.0, CORNER)


def test_a_point_with_another_mark_is_refused() -> None:
    points = (*DRAWN.control_points[:-1], (*DRAWN.control_points[-1], "round"))
    with pytest.raises(BodyGeometryError, match='"corner"'):
        replace(DRAWN, control_points=points)  # type: ignore[arg-type]


def test_a_drawn_heel_relief_line_is_straight_between_corners() -> None:
    line = ((-20.0, 40.0), (10.0, 30.0, CORNER), (10.0, -30.0, CORNER), (-20.0, -40.0))
    parameters = replace(
        Prototype001Parameters(),
        body_heel_relief="contour",
        body_shape=replace(DRAWN, heel_relief_points=line),
    )
    (relief,) = [c for c in parameters.build().body.contours if c.name == "Heel relief"]
    heel_end = parameters.body_layout().heel_end
    # Between the two corners the line stands at x = heel end + 10 (on the
    # treble side: the relief stops at the centreline).
    treble = -parameters.bass_sign
    across = [p for p in relief.inner_edge() if 1e-9 < p.y * treble < 25.0]
    assert across
    assert all(p.x == pytest.approx(heel_end + 10.0, abs=1e-6) for p in across)


def test_the_pickguard_keeps_its_corners_and_the_editor_gets_them() -> None:
    template = body_editor_layout({"prototype": {}})["templates"]["stratocaster"]
    guard = [list(point) for point in template["shape"]["pickguard_points"]]
    guard[2] = [*guard[2], CORNER]
    guard[3] = [*guard[3], CORNER]
    shape = {**template["shape"], "pickguard_points": guard}
    prototype = {"body_shape": shape, "body_pickguard": True}

    layout = body_editor_layout({"prototype": prototype})
    points = layout["pickguard"]["points"]
    assert [index for index, point in enumerate(points) if len(point) == 3] == [2, 3]
    # The guard's outline runs straight between them.
    built = replace(
        Prototype001Parameters(),
        body_pickguard=True,
        body_shape=replace(
            DRAWN,
            control_points=tuple(map(tuple, shape["control_points"])),
            pickguard_points=tuple(map(tuple, guard)),
        ),
    )
    pickguard = built.body_layout().pickguard
    assert pickguard is not None
    assert pickguard.corners[2:4] == (True, True)


def test_a_drawn_headstock_edge_takes_corners() -> None:
    parameters = replace(
        Prototype001Parameters(),
        headstock_outline="drawn",
        headstock_bass_edge=(
            (45.0, 30.8),
            (95.0, 29.0, CORNER),
            (140.0, 24.0, CORNER),
            (170.0, 30.0),
        ),
        headstock_treble_edge=(
            (45.0, 30.8),
            (95.0, 29.0),
            (140.0, 24.0),
            (170.0, 18.0),
        ),
    )
    plan, _ = parameters.headstock_design()
    curve = plan.edge_curve("bass")
    # Straight between the corners at 95 and 140 mm.
    for distance in (100.0, 117.5, 135.0):
        assert curve.value_at(distance) == pytest.approx(
            29.0 + (distance - 95.0) * (24.0 - 29.0) / 45.0
        )


def test_a_drawn_pickup_frame_takes_corners() -> None:
    points = cornered(FRAME_POINTS["ring"], 1, 2)
    prototype = {"body_pickup_frame": "ring", "body_pickups": "H"}
    parameters = replace(
        Prototype001Parameters(),
        body_pickup_frame="ring",
        body_pickups="H",
        body_bridge_frame_points=points,
    )
    (frame,) = parameters.body_layout().pickup_frames
    assert frame.points == points
    a, b = (frame.placing.to_model(*points[i][:2]) for i in (1, 2))
    # Its outline (8 samples a span) straight from the one to the other.
    for point in frame.plate.outline[8:17]:
        assert distance_to_chord(point, a, b) == pytest.approx(0.0, abs=1e-9)

    layout = body_editor_layout(
        {"prototype": {**prototype, "body_bridge_frame_points": points}}
    )
    (shown,) = layout["frames"]
    assert [i for i, h in enumerate(shown["handles"]) if len(h) == 3] == [1, 2]
    with pytest.raises(BodyGeometryError, match="bridge pickup's frame"):
        replace(
            parameters, body_bridge_frame_points=((*points[0], "round"), *points[1:])
        ).body_layout()


def test_a_drawn_headstock_tip_takes_corners() -> None:
    drawn = replace(Prototype001Parameters(), **DRAWN_HEADSTOCK)
    *edge, end = drawn.headstock_bass_edge
    # The bass edge's end is the tip's -Y corner here (bass toward -Y).
    sharp = replace(
        drawn,
        headstock_bass_edge=(*edge, (*end, CORNER)),
        headstock_tip_points=((3.5, 27.0, CORNER), (4.5, 33.0)),
    )
    plan, _ = sharp.headstock_design()
    tip = plan.tip_outline()
    corner, first, second = (
        Point2D(-204.0, 20.0),
        Point2D(-207.5, 27.0),
        Point2D(-208.5, 33.0),
    )
    # Straight from the corner to the first tip point (16 samples a span),
    # curved on past it.
    for point in tip[:17]:
        assert distance_to_chord(point, corner, first) == pytest.approx(0.0, abs=1e-9)
    assert distance_to_chord(tip[24], first, second) > 0.01
    # The template's Bezier spans are the same curve.
    points, leaving, arriving = plan.tip_curve()
    for index, span in enumerate(hermite_spans(points, leaving, arriving)):
        for step in range(16):
            expected = tip[index * 16 + step]
            got = bezier_point(span, step / 16)
            assert (got.x, got.y) == pytest.approx((expected.x, expected.y))

    left = replace(sharp, handedness="left")
    assert left.built_tip_points() == ((4.5, -33.0), (3.5, -27.0, CORNER))
    with pytest.raises(HeadstockGeometryError, match="Headstock tip points"):
        replace(sharp, headstock_tip_points=((3.5, 27.0, "round"),)).headstock_design()


def test_a_template_read_back_unchanged_keeps_its_corners() -> None:
    shape = replace(DRAWN, control_points=cornered(DRAWN.control_points, 5, 20, 21))
    payload = {"prototype": {"body_shape": _jsonable(shape)}}
    svg = outline_template(payload, "body")["svg"]
    back = import_outline(payload, "body", svg)["values"]
    assert back["control_points"] == [list(p) for p in shape.control_points]

    # A sharp tip corner, beside a sharp tip point or a smooth one.
    drawn = replace(Prototype001Parameters(), **DRAWN_HEADSTOCK)
    *edge, end = drawn.headstock_bass_edge
    for first in ((3.5, 27.0, CORNER), (3.5, 27.0)):
        values = {
            **DRAWN_HEADSTOCK,
            "headstock_bass_edge": (*edge, (*end, CORNER)),
            "headstock_tip_points": (first, (4.5, 33.0)),
        }
        payload = {"prototype": _jsonable(values)}
        svg = outline_template(payload, "headstock")["svg"]
        back = import_outline(payload, "headstock", svg)["values"]
        assert back["headstock_bass_edge"][-1] == [*end, CORNER]
        assert back["headstock_tip_points"] == [list(first), [4.5, 33.0]]


def test_a_drawn_step_line_is_rounded_through_its_round_point() -> None:
    _, hexed = YOUR_DESIGN_TEMPLATES["alexi_hexed"]
    outer = cornered(hexed.step_points[0], 3, mark=ROUND)
    shape = replace(hexed, step_points=(outer, *hexed.step_points[1:]))
    parameters = replace(
        Prototype001Parameters(),
        body_shape=shape,
        **BODY_TEMPLATE_VALUES["alexi_hexed"],
    )
    layout = parameters.body_layout()
    assert layout.stepped_top is not None
    boundary = layout.stepped_top.boundaries[0]
    # The two sides at the round point sampled; the rest straight.
    assert len(boundary) == len(outer) - 2 + 2 * 8
    assert Point2D(layout.heel_end + outer[3][0], outer[3][1]) in boundary
    assert mirrored_shape(shape).step_points[0][3] == (outer[3][0], -outer[3][1], ROUND)

    view = body_editor_layout(
        {
            "prototype": {
                "body_shape": {
                    "kind": "your_design",
                    "control_points": [list(p) for p in shape.control_points],
                    "step_points": [
                        [list(p) for p in line] for line in shape.step_points
                    ],
                },
                **BODY_TEMPLATE_VALUES["alexi_hexed"],
            }
        }
    )
    assert view["steps"]["points"][0][3] == [*outer[3][:2], ROUND]
    with pytest.raises(BodyGeometryError, match="not two numbers"):
        replace(
            parameters,
            body_shape=replace(
                shape, step_points=(cornered(outer, 1), *shape.step_points[1:])
            ),
        ).body_layout()


def test_a_drawn_truss_rod_cover_curves_through_its_round_corners() -> None:
    points = ((0.0, 1.0), (1.0, 1.0, ROUND), (1.0, -1.0, ROUND), (0.0, -1.0))
    shape = truss_rod_cover_shape("custom", 30.0, 24.0, points, ((0.5, 0.0),))

    # Round across the far end (the three sides at its corners sampled),
    # the nut end's corners rounded off.
    assert len(shape.corners) == 1 + 3 * 8
    assert shape.radii.count(CUSTOM_COVER_RADIUS) == 2
    assert (30.0, 12.0) in shape.corners and (30.0, -12.0) in shape.corners
    assert max(u for u, _ in shape.corners) > 30.0 + 1.0
    assert check_custom_cover(points, ((0.5, 0.0),)) is None
    assert "two and" in str(
        check_custom_cover(((0, 1), (1, 1, CORNER), (1, -1)), ((0.5, 0.0),))
    )

    prototype = {
        "truss_rod_adjustment": "headstock",
        "truss_rod_cover_style": "custom",
        "truss_rod_cover_points": [list(p) for p in points],
        "truss_rod_cover_screws": [[0.5, 0.0]],
    }
    cover = headstock_editor_layout({"prototype": prototype})["truss_cover"]
    assert cover["corners"] == [list(p) for p in points]


def test_a_drawn_inlay_curves_through_its_round_corner() -> None:
    board = FretboardSurface(609.6, 24, 42.0, 56.0, 430.0, 6.0, 9)
    tooth = cornered(TOOTH, 2, mark=ROUND)
    sharp = InlayLayout(board, 2.0, style="custom", custom_points=TOOTH)
    rounded = InlayLayout(board, 2.0, style="custom", custom_points=tooth)
    assert len(rounded.markers[0].outline) > len(sharp.markers[0].outline)
    assert rounded.editable_points() == tooth

    prototype = {"inlay_style": "custom", "inlay_points": [list(p) for p in tooth]}
    assert inlay_editor_layout({"prototype": prototype})["points"][2] == [
        *TOOTH[2],
        ROUND,
    ]
    # Drawn curved in a template, and read back unchanged as drawn.
    payload = {"prototype": prototype}
    assert "cgwOutline" in outline_template(payload, "inlay", "dxf")["dxf"]
    svg = outline_template(payload, "inlay")["svg"]
    back = import_outline(payload, "inlay", svg)
    assert back["values"]["inlay_points"] == [list(p) for p in tooth]
    with pytest.raises(FretboardGeometryError, match="two and"):
        InlayLayout(board, 2.0, style="custom", custom_points=cornered(TOOTH, 2))
