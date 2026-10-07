"""Tests for the truss-rod cover styles and a cover drawn in the headstock
editor."""

from dataclasses import replace

import pytest

from cncguitarwizard.cam.covers import plan_cover_machining
from cncguitarwizard.cam.neck import NeckMachiningParameters, plan_neck_machining
from cncguitarwizard.cam.parameters import MachiningParameters
from cncguitarwizard.geometry.exceptions import NeckGeometryError
from cncguitarwizard.geometry.primitives import point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.truss_rod_covers import (
    TRUSS_ROD_COVER_STYLES,
    editable_cover_points,
    truss_rod_cover_shape,
)
from cncguitarwizard.webapp import headstock_editor_layout, parameter_schema

HEADSTOCK = replace(Prototype001Parameters(), truss_rod_adjustment="headstock")


def _cover(parameters: Prototype001Parameters):  # type: ignore[no-untyped-def]
    (cover,) = [c for c in parameters.build().covers if c.name == "Truss rod cover"]
    return cover


@pytest.mark.parametrize(
    ("style", "screws"), [("bell", 3), ("ibanez", 2), ("prs", 2), ("rectangle", 3)]
)
def test_every_style_covers_the_trough_on_the_face(style: str, screws: int) -> None:
    parameters = replace(HEADSTOCK, truss_rod_cover_style=style)
    cover = _cover(parameters)
    channel = parameters.truss_rod(parameters.neck_outline())
    assert len(cover.holes) == screws
    assert not cover.recessed
    # Its nut end 0.5 mm short of the nut shelf, over the trough's own.
    trough = channel.adjuster_boundary
    assert max(p.x for p in cover.outline) == pytest.approx(
        max(p.x for p in trough) - 0.5, abs=1e-6
    )
    assert all(
        point_in_polygon(p, cover.outline)
        for p in trough
        if p.x <= max(q.x for q in cover.outline)
    )
    # Its own program cuts it to its outline, screwed onto the face.
    (setup,) = plan_cover_machining((cover,), MachiningParameters()).setups
    assert "headstock face" in " ".join(setup.notes)


def test_a_rectangle_is_sized_round_the_trough_and_any_size_can_be_given() -> None:
    rectangle = replace(HEADSTOCK, truss_rod_cover_style="rectangle")
    channel = rectangle.truss_rod(rectangle.neck_outline())
    # 8 mm of trough: 8.5 mm past its far end, 6 mm past its sides.
    assert rectangle.truss_rod_cover_size(channel) == pytest.approx((16.0, 20.0))
    assert HEADSTOCK.truss_rod_cover_size(channel) == (41.0, 28.5)
    sized = replace(HEADSTOCK, truss_rod_cover_length=34.0, truss_rod_cover_width=32.0)
    xs = [p.x for p in _cover(sized).outline]
    assert max(xs) - min(xs) == pytest.approx(34.0, abs=0.01)
    # A rectangle's sides are straight: its width is all there.
    wide = replace(rectangle, truss_rod_cover_length=20.0, truss_rod_cover_width=24.0)
    ys = [p.y for p in _cover(wide).outline]
    assert max(ys) - min(ys) == pytest.approx(24.0, abs=0.01)


def test_a_cover_drawn_in_the_editor_is_kept_and_mirrored() -> None:
    shape = truss_rod_cover_shape("bell", 41.0, 28.5)
    points, screws = editable_cover_points(shape, 41.0, 28.5)
    # Wider on the treble side: a drawn cover need not be symmetric.
    points = tuple((u, v * 1.25 if v > 0.0 else v) for u, v in points)
    drawn = replace(
        HEADSTOCK,
        truss_rod_cover_style="custom",
        truss_rod_cover_points=points,
        truss_rod_cover_screws=screws,
        truss_rod_cover_length=41.0,
        truss_rod_cover_width=28.5,
    )
    right = _cover(drawn)
    left = _cover(replace(drawn, handedness="left"))
    assert max(p.y for p in right.outline) > -min(p.y for p in right.outline) + 3.0
    assert sorted(round(p.y, 3) for p in right.outline) == sorted(
        round(-p.y, 3) for p in left.outline
    )


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"truss_rod_cover_width": 9.0}, "does not cover the trough"),
        (
            {"truss_rod_cover_style": "rectangle", "truss_rod_cover_length": 60.0},
            "runs into tuner",
        ),
        (
            {
                "truss_rod_cover_style": "custom",
                "truss_rod_cover_points": ((0, 1), (1, 1), (1, -1), (0, -1)),
                "truss_rod_cover_screws": ((0.1, 0.0),),
            },
            "screw 1 is in the trough",
        ),
        (
            {
                "truss_rod_cover_style": "custom",
                "truss_rod_cover_points": ((0, 1), (1, -1), (1, 1), (0, -1)),
                "truss_rod_cover_screws": ((0.8, 0.0),),
            },
            "sides cross",
        ),
        ({"truss_rod_cover_style": "custom"}, "at least three corners"),
    ],
)
def test_a_cover_that_does_not_fit_says_why(change: dict, problem: str) -> None:
    with pytest.raises(NeckGeometryError, match=problem):
        replace(HEADSTOCK, **change).build()
    layout = headstock_editor_layout(
        {
            "prototype": {
                "truss_rod_adjustment": "headstock",
                **{
                    key: list(map(list, value)) if isinstance(value, tuple) else value
                    for key, value in change.items()
                },
            }
        }
    )
    # The editor still draws it, and says why.
    assert "error" not in layout
    assert problem in layout["truss_cover"]["problem"]


def test_the_lettering_keeps_clear_of_the_cover() -> None:
    lettered = replace(HEADSTOCK, headstock_engraving_text="JONE")
    geometry = lettered.build()
    cover = [c for c in geometry.covers if c.name == "Truss rod cover"][0]
    lettering = geometry.headstock_engraving
    assert lettering is not None
    # By default it sits past the cover's far end, as a Gibson's logo.
    assert max(p.x for line in lettering.lines for p in line) < min(
        p.x for p in cover.outline
    )
    with pytest.raises(NeckGeometryError, match="under the truss-rod cover"):
        replace(lettered, headstock_engraving_x=-20.0).build()


def test_the_cover_screws_pilots_are_started_in_the_face() -> None:
    geometry = HEADSTOCK.build()
    plan = plan_neck_machining(geometry, NeckMachiningParameters())
    assert plan.small_holes is not None
    pilots = plan.small_holes.toolpaths
    assert [p.name for p in pilots] == [
        "Truss rod cover screw 1 pilot",
        "Truss rod cover screw 2 pilot",
        "Truss rod cover screw 3 pilot",
    ]
    # From the face, below the glue face behind the seat: started 2 mm
    # deep with the 3 mm drill.
    far = min(move.z for move in pilots[2].moves)
    near = min(move.z for move in pilots[0].moves)
    assert far < near < -2.0
    assert "started 2 mm deep in the headstock face" in " ".join(plan.small_holes.notes)
    # A laminated neck's face is cut later: drilled by hand through the cover.
    laminated = plan_neck_machining(
        geometry, NeckMachiningParameters(blank="laminated")
    )
    assert laminated.small_holes is None


def test_the_editor_gets_the_cover_and_the_form_its_styles() -> None:
    layout = headstock_editor_layout(
        {"prototype": {"truss_rod_adjustment": "headstock"}}
    )
    cover = layout["truss_cover"]
    assert cover["style"] == "bell" and cover["problem"] is None
    assert (cover["length"], cover["width"], cover["back"]) == (41.0, 28.5, -5.5)
    assert len(cover["corners"]) == 29 and len(cover["screw_points"]) == 3
    # No cover with the adjuster at the heel.
    assert headstock_editor_layout({"prototype": {}})["truss_cover"] is None
    fields = {
        field["name"]: field
        for group in parameter_schema()["prototype"]
        for field in group["fields"]
    }
    style = fields["truss_rod_cover_style"]
    assert style["options"] == list(TRUSS_ROD_COVER_STYLES)
    assert style["labels"]["bell"] == "Gibson bell (3 screws)"
    assert style["advanced"] is False
    assert fields["truss_rod_cover_points"]["type"] == "json"


def test_a_bell_is_wide_at_the_nut_and_round_at_its_top() -> None:
    cover = _cover(HEADSTOCK)
    back = max(p.x for p in cover.outline)

    def width_at(depth: float) -> float:
        x = back - depth
        near = [p.y for p in cover.outline if abs(p.x - x) < 1.5]
        return max(near) - min(near)

    # Gibson's: its foot over the trough the widest, narrowing to its top.
    assert width_at(1.0) > width_at(20.0) > width_at(36.0)
    assert width_at(1.0) == pytest.approx(28.5, abs=2.0)
    # Two screws in the foot's corners either side of the trough, one in
    # the top, on the centreline.
    (a, b, c) = cover.holes
    assert a.center_x == b.center_x and a.center_y == -b.center_y
    assert c.center_y == 0.0 and c.center_x < a.center_x - 25.0
