"""Tests for the pickguard: its shape, openings, screws and the Strat controls."""

from dataclasses import replace

import pytest

from cncguitarwizard.cam import MachiningParameters, plan_cover_machining
from cncguitarwizard.geometry.body.bridges import (
    FloydRoseSpec,
    HardtailSpec,
    KahlerBridgeSpec,
    TuneOMaticSpec,
)
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.presets.body_shapes import YOUR_DESIGN_TEMPLATES, YourDesignShape
from cncguitarwizard.webapp import body_editor_layout

STRAT = YOUR_DESIGN_TEMPLATES["stratocaster"][1]
# Design by Jone without its drawn guard: the automatic one.
JONE_AUTO = replace(YOUR_DESIGN_TEMPLATES["design_by_jone"][1], pickguard_points=())


def _guard(geometry):  # type: ignore[no-untyped-def]
    (guard,) = [cover for cover in geometry.covers if cover.name == "Pickguard"]
    return guard


def test_there_is_no_pickguard_unless_asked() -> None:
    geometry = Prototype001Parameters().build()

    assert all(cover.name != "Pickguard" for cover in geometry.covers)


@pytest.mark.parametrize(("layout", "openings"), [("HH", 2), ("SSS", 3), ("H", 1)])
def test_the_guard_has_an_opening_over_every_pickup(layout: str, openings: int) -> None:
    geometry = replace(
        Prototype001Parameters(),
        body_shape=STRAT,
        body_pickups=layout,
        body_pickguard=True,
    ).build()
    guard = _guard(geometry)

    assert guard.face == "top"
    names = [slot.name for slot in guard.slots if slot.name.endswith("opening")]
    assert len(names) == openings
    # Each opening lies inside its route, and inside the guard.
    for slot in guard.slots:
        assert all(point_in_polygon(p, guard.outline) for p in slot.outline)
    # Screws round its edge, each with a spot in the body.
    screws = [hole for hole in guard.holes if hole.name.startswith("Screw")]
    spots = [m for m in geometry.body.control_top_marks if "Pickguard" in m.name]
    assert len(screws) >= 6 and len(spots) == len(screws)


def test_the_guard_reaches_past_the_bridges_front_either_side_of_it() -> None:
    from cncguitarwizard.presets.pickguard import BRIDGE_WRAP

    geometry = replace(
        Prototype001Parameters(), body_shape=STRAT, body_pickguard=True
    ).build()
    guard = _guard(geometry)
    (bridge,) = geometry.body.extra_cavities
    bridge_front = min(p.x for p in bridge.outline)

    # It covers none of the bridge's route...
    assert not any(point_in_polygon(p, guard.outline) for p in bridge.outline)
    assert not any(point_in_polygon(p, bridge.outline) for p in guard.outline)
    # ...but runs on beside it, on both sides.
    for side in (-1.0, 1.0):
        beside = [p for p in guard.outline if side * p.y > 0.0]
        assert max(p.x for p in beside) > bridge_front + BRIDGE_WRAP / 2.0
    assert all(point_in_polygon(p, geometry.body.outline.points) for p in guard.outline)


def test_strat_controls_sit_in_the_guard_past_the_bridge() -> None:
    parameters = replace(
        Prototype001Parameters(),
        body_shape=replace(STRAT, pickguard_points=()),
        body_pickups="SSS",
        body_controls="pickguard",
        body_pickguard=True,
    )
    geometry = parameters.build()
    guard = _guard(geometry)
    body = geometry.body

    # Three pots and a blade switch go through the guard, over a cavity
    # routed from the top; there is no rear control cavity.
    pots = [hole for hole in guard.holes if hole.name.startswith("Control pot")]
    assert len(pots) == 3
    assert any(slot.name == "Control switch slot" for slot in guard.slots)
    assert body.control_cavity is None
    (cavity,) = [c for c in body.control_top_cavities if c.name == "Control cavity"]
    assert all(point_in_polygon(p, guard.outline) for p in cavity.outline)
    # So the guard runs on past the bridge, on the controls' side.
    bridge_front = min(p.x for c in body.extra_cavities for p in c.outline)
    assert max(p.x for p in guard.outline) > bridge_front
    # Its program is cut from sheet like any cover.
    plan = plan_cover_machining(geometry.covers, MachiningParameters())
    assert plan is not None
    assert "Cover_pickguard" in [setup.name for setup in plan.setups]


def test_strat_controls_bring_their_guard() -> None:
    # body_pickguard off: the controls in the guard bring it anyway.
    geometry = replace(Prototype001Parameters(), body_controls="pickguard").build()
    guard = _guard(geometry)
    pots = [hole for hole in guard.holes if hole.name.startswith("Control pot")]
    assert len(pots) == 3


def test_a_drawn_guard_is_kept_and_checked_against_the_body() -> None:
    # Design by Jone comes with its own drawn guard.
    template = body_editor_layout({"prototype": {"body_pickguard": True}})["pickguard"]
    assert not template["automatic"]
    points = tuple((x + 0.0, y * 0.9) for x, y in template["points"])
    shape = replace(YourDesignShape(), pickguard_points=points)
    drawn = replace(
        Prototype001Parameters(), body_shape=shape, body_pickguard=True
    ).body_layout()

    assert drawn.pickguard is not None and not drawn.pickguard.automatic
    off_body = replace(shape, pickguard_points=tuple((x, y * 4.0) for x, y in points))
    with pytest.raises(BodyGeometryError, match="runs off the body"):
        replace(
            Prototype001Parameters(), body_shape=off_body, body_pickguard=True
        ).build()


def test_the_automatic_guard_wraps_round_the_neck_like_a_strats() -> None:
    parameters = replace(
        Prototype001Parameters(), body_shape=STRAT, body_pickguard=True
    )
    layout = parameters.body_layout()
    guard = layout.pickguard
    assert guard is not None
    pocket = layout.neck_pocket.outline
    heel_end = layout.heel_end

    # It reaches forward beside the neck on the side with wood there...
    front = min(p.x for p in guard.plate.outline)
    assert front < heel_end - 30.0
    # ...with a notch the neck sits in: the pocket's middle is not covered.
    middle = sum(p.y for p in pocket) / len(pocket)
    from cncguitarwizard.geometry.primitives import Point2D

    assert not point_in_polygon(Point2D(heel_end - 10.0, middle), guard.plate.outline)


def test_the_editor_gets_the_guards_openings_and_holes() -> None:
    guard = body_editor_layout({"prototype": {"body_pickguard": True}})["pickguard"]

    assert len(guard["openings"]) == 2  # the two humbuckers
    assert guard["holes"] and all(
        {"x", "y", "r"} <= set(hole) for hole in guard["holes"]
    )


def test_the_pickup_openings_are_rectangles() -> None:
    geometry = replace(
        Prototype001Parameters(), body_shape=STRAT, body_pickguard=True
    ).build()
    guard = _guard(geometry)

    openings = [slot for slot in guard.slots if slot.name.endswith("opening")]
    assert openings
    for opening in openings:
        assert len(opening.outline) == 4


def test_a_dragged_guard_gets_its_own_programs() -> None:
    from cncguitarwizard.webapp import feature_programs

    result = feature_programs({"prototype": {"body_pickguard": True}}, "pickguard")

    assert result["title"] == "pickguard"
    names = [f["name"] for f in result["files"]]
    # Its screw spots in the body, zeroed on the guard, and the guard itself.
    assert names[0].startswith("Feature_pickguard_top")
    assert names[-1] == "Cover_pickguard.nc"


@pytest.mark.parametrize("name", ["stratocaster", "superstrat"])
def test_on_the_longer_horns_side_the_guard_does_not_follow_the_horn(
    name: str,
) -> None:
    from cncguitarwizard.presets.pickguard import PICKGUARD_STYLES, PICKUP_HUG

    style = PICKGUARD_STYLES[name]
    layout = replace(
        Prototype001Parameters(),
        body_shape=JONE_AUTO,
        body_pickguard=True,
        body_pickguard_style=name,
    ).body_layout()
    guard = layout.pickguard
    assert guard is not None
    outline = layout.outline.points
    # Design by Jone's longer horn is on -y here.
    assert min(p.x for p in outline if p.y < 0) < min(p.x for p in outline if p.y > 0)
    routes = [r for r in (layout.neck_pickup, layout.bridge_pickup) if r is not None]
    reach = max(-p.y for r in routes for p in r.outline) + PICKUP_HUG
    low_side = [p for p in guard.plate.outline if p.y < 0.0]
    # Its edge runs past the pickups, from the neck to the bridge, flaring
    # out toward the bridge (a little more where the spline rounds a
    # corner)...
    assert max(-p.y for p in low_side) <= reach + style.flare + 2.0
    assert max(-p.y for p in low_side) >= reach + style.flare - 2.0
    # ...in by the waist between the pickups, if the style has one...
    if style.waist:
        neck_end = max(p.x for p in routes[0].outline)
        bridge_start = min(p.x for p in routes[1].outline)
        between = [p for p in low_side if neck_end < p.x < bridge_start]
        assert min(-p.y for p in between) == pytest.approx(reach - style.waist, abs=1.0)
    # ...and reaches only the style's way forward beside the neck.
    front = min(p.x for p in low_side)
    assert layout.heel_end - style.long_side_wrap - 4.0 < front < layout.heel_end


def test_a_stratocaster_guard_has_a_tail_past_the_bridge() -> None:
    from cncguitarwizard.presets.pickguard import PICKGUARD_STYLES

    layout = replace(
        Prototype001Parameters(), body_shape=JONE_AUTO, body_pickguard=True
    ).body_layout()
    guard = layout.pickguard
    assert guard is not None
    (bridge,) = layout.extra_cavities
    bridge_front = min(p.x for p in bridge.outline)
    tail = PICKGUARD_STYLES["stratocaster"].tail

    # On the shorter horn's side (+y here) it runs on well past the
    # bridge's front, on the other only a little.
    high = max(p.x for p in guard.plate.outline if p.y > 0.0)
    low = max(p.x for p in guard.plate.outline if p.y < 0.0)
    assert bridge_front + tail - 8.0 < high < bridge_front + tail + 2.0
    assert low < bridge_front + 20.0


def test_the_stratocaster_template_has_a_traced_strat_guard() -> None:
    geometry = replace(
        Prototype001Parameters(), body_shape=STRAT, body_pickguard=True
    ).build()
    layout = replace(
        Prototype001Parameters(), body_shape=STRAT, body_pickguard=True
    ).body_layout()
    guard = _guard(geometry)

    assert layout.pickguard is not None and not layout.pickguard.automatic
    openings = [s for s in guard.slots if s.name.endswith("opening")]
    assert len(openings) == 2
    (bridge,) = geometry.body.extra_cavities
    assert not any(point_in_polygon(p, guard.outline) for p in bridge.outline)
    assert not any(point_in_polygon(p, bridge.outline) for p in guard.outline)


def test_a_drawn_guard_not_over_the_controls_gives_way() -> None:
    # The traced HH guard has no room for a Stratocaster's controls: the
    # automatic guard, made round them, takes its place.
    parameters = replace(
        Prototype001Parameters(),
        body_shape=STRAT,
        body_pickguard=True,
        body_pickups="SSS",
        body_controls="pickguard",
    )
    layout = parameters.body_layout()
    assert layout.pickguard is not None and layout.pickguard.automatic
    geometry = parameters.build()
    guard = _guard(geometry)
    (cavity,) = [
        c for c in geometry.body.control_top_cavities if c.name == "Control cavity"
    ]
    assert all(point_in_polygon(p, guard.outline) for p in cavity.outline)


def test_on_the_shorter_horns_side_the_guard_follows_the_horn() -> None:
    layout = replace(
        Prototype001Parameters(), body_shape=JONE_AUTO, body_pickguard=True
    ).body_layout()
    guard = layout.pickguard
    assert guard is not None
    outline = layout.outline.points
    horn_tip = min((p for p in outline if p.y > 0), key=lambda p: p.x)

    # Round into the horn, near its tip...
    assert min(p.x for p in guard.plate.outline if p.y > 0) < horn_tip.x + 30.0
    # ...but not across the cutaway between it and the neck.
    pocket_side = max(p.y for p in layout.neck_pocket.outline)
    from cncguitarwizard.geometry.primitives import Point2D

    cutaway = Point2D(layout.heel_end - 10.0, (pocket_side + horn_tip.y) / 2.0)
    assert not point_in_polygon(cutaway, outline)
    assert not point_in_polygon(cutaway, guard.plate.outline)


@pytest.mark.parametrize("layout", ["PJ", "JJ", "P", "MM", "RR"])
@pytest.mark.parametrize("instrument", ["bass_guitar", "five_string_bass"])
def test_the_jazz_bass_template_has_the_strat_guard_fitted_to_it(
    instrument: str, layout: str
) -> None:
    parameters = replace(
        Prototype001Parameters.for_instrument(instrument),  # type: ignore[arg-type]
        body_pickguard=True,
        body_pickups=layout,
    )
    geometry = parameters.build()
    guard = _guard(geometry)

    pickguard = parameters.body_layout().pickguard
    assert pickguard is not None and not pickguard.automatic
    # Every pickup opening lies wholly in it; the bridge's screws clear it.
    openings = [s for s in guard.slots if s.name.endswith(("opening", "1", "2"))]
    assert openings
    for opening in openings:
        assert all(point_in_polygon(p, guard.outline) for p in opening.outline)
    bridge = [h for h in geometry.body.holes if h.name.startswith("Bridge screw")]
    assert bridge
    assert not any(point_in_polygon(h.center, guard.outline) for h in bridge)


@pytest.mark.parametrize(
    "template", ["design_by_jone", "stratocaster", "jackson_rr", "les_paul"]
)
@pytest.mark.parametrize(
    "bridge", [FloydRoseSpec(), KahlerBridgeSpec(), TuneOMaticSpec(), HardtailSpec()]
)
def test_a_drawn_guard_steps_round_whichever_bridge_is_fitted(
    template: str, bridge: object
) -> None:
    from cncguitarwizard.presets.pickguard import PICKUP_MARGIN

    geometry = replace(
        Prototype001Parameters(),
        body_shape=YOUR_DESIGN_TEMPLATES[template][1],
        body_pickguard=True,
        body_bridge=bridge,
    ).build()
    guard = _guard(geometry)

    # None of the bridge's routes or holes under it — but where they
    # reach in among the bridge pickup's route, the pickup comes first.
    pickup_end = max(
        p.x
        for c in geometry.body.top_cavities
        if c.name.endswith("pickup route")
        for p in c.outline
    )
    clear_from = pickup_end + PICKUP_MARGIN + 1.0
    routes = [c for c in geometry.body.extra_cavities if "pickup" not in c.name]
    for route in routes:
        beyond = [p for p in route.outline if p.x > clear_from]
        assert not any(point_in_polygon(p, guard.outline) for p in beyond)
    holes = [
        h
        for h in geometry.body.holes
        if h.name.startswith(("Bridge screw", "Bridge post", "Tailpiece"))
        and h.center_x - h.diameter / 2.0 > clear_from
    ]
    assert not any(point_in_polygon(h.center, guard.outline) for h in holes)


@pytest.mark.parametrize(
    "template", ["design_by_jone", "stratocaster", "jackson_rr", "les_paul"]
)
@pytest.mark.parametrize("drawn", [True, False])
def test_a_guard_keeps_clear_of_a_kahlers_plate(template: str, drawn: bool) -> None:
    from cncguitarwizard.geometry.primitives import Point2D

    shape = YOUR_DESIGN_TEMPLATES[template][1]
    parameters = replace(
        Prototype001Parameters(),
        body_shape=shape if drawn else replace(shape, pickguard_points=()),
        body_pickguard=True,
        body_bridge=KahlerBridgeSpec(),
    )
    guard = _guard(parameters.build())
    (cutout,) = parameters.body_layout().extra_cavities
    overhang = KahlerBridgeSpec().plate_overhang

    # The plate sits on the top, reaching past its cutout all round.
    xs = [p.x for p in cutout.outline]
    ys = [p.y for p in cutout.outline]
    plate = (
        Point2D(min(xs) - overhang, min(ys) - overhang),
        Point2D(max(xs) + overhang, min(ys) - overhang),
        Point2D(max(xs) + overhang, max(ys) + overhang),
        Point2D(min(xs) - overhang, max(ys) + overhang),
    )
    assert not any(point_in_polygon(p, plate) for p in guard.outline)
    assert not any(point_in_polygon(p, guard.outline) for p in plate)


def test_clear_of_bridge_cuts_a_notch_on_the_bridges_side() -> None:
    from cncguitarwizard.geometry.primitives import Point2D
    from cncguitarwizard.presets.pickguard import (
        DRAWN_BRIDGE_CLEARANCE,
        clear_of_bridge,
    )

    square = [Point2D(0, -50), Point2D(100, -50), Point2D(100, 50), Point2D(0, 50)]
    bridge = [(Point2D(80, -20), Point2D(120, -20), Point2D(120, 20), Point2D(80, 20))]
    for points in (square, list(reversed(square))):
        fitted = clear_of_bridge(points, bridge)
        front = 80 - DRAWN_BRIDGE_CLEARANCE
        half = 20 + DRAWN_BRIDGE_CLEARANCE
        # The bridge's box is out of it, the rest of the square kept.
        assert not point_in_polygon(Point2D(90, 0), fitted)
        assert point_in_polygon(Point2D(front - 1, 0), fitted)
        assert point_in_polygon(Point2D(90, half + 1), fitted)
        assert point_in_polygon(Point2D(90, -half - 1), fitted)


@pytest.mark.parametrize("style", ["stratocaster", "superstrat"])
def test_on_a_v_the_guard_follows_the_shorter_wing_out(style: str) -> None:
    from cncguitarwizard.presets.pickguard import WING_REACH

    rr = replace(YOUR_DESIGN_TEMPLATES["jackson_rr"][1], pickguard_points=())
    parameters = replace(
        Prototype001Parameters(),
        body_shape=rr,
        body_pickguard=True,
        body_pickguard_style=style,
    )
    geometry = parameters.build()
    guard = _guard(geometry)
    outline = geometry.body.outline.points

    # The RR's wings reach past the bridge; the +y one is the shorter.
    upper_tip = max(p.x for p in outline if p.y > 0)
    lower_tip = max(p.x for p in outline if p.y < 0)
    assert upper_tip < lower_tip
    # The guard runs out along the shorter wing, WING_REACH past the
    # bridge's front...
    (bridge,) = geometry.body.extra_cavities
    bridge_front = min(p.x for p in bridge.outline)
    reach = max(p.x for p in guard.outline if p.y > 0) - bridge_front
    assert WING_REACH - 6.0 < reach < WING_REACH + 2.0
    # ...but not along the longer one.
    bridge_end = max(p.x for p in bridge.outline)
    assert max(p.x for p in guard.outline if p.y < 0) < bridge_end


@pytest.mark.parametrize(
    "template", ["design_by_jone", "stratocaster", "jackson_rr", "les_paul"]
)
@pytest.mark.parametrize("drawn", [True, False])
def test_the_truss_rods_spoke_wheel_is_left_uncovered(
    template: str, drawn: bool
) -> None:
    from cncguitarwizard.geometry.primitives import Point2D

    shape = YOUR_DESIGN_TEMPLATES[template][1]
    parameters = replace(
        Prototype001Parameters(),
        body_shape=shape if drawn else replace(shape, pickguard_points=()),
        body_pickguard=True,
    )
    guard = _guard(parameters.build())
    layout = parameters.body_layout()
    access = layout.truss_rod_access
    assert access is not None

    # Its notch past the pocket, and 2 mm round it, stay clear of the guard.
    xs = [p.x for p in access.outline]
    ys = [p.y for p in access.outline]
    clear = [
        Point2D(x, y)
        for x in (layout.heel_end + 0.5, max(xs), max(xs) + 2.0)
        for y in (min(ys) - 2.0, 0.0, max(ys) + 2.0)
    ]
    assert not any(point_in_polygon(p, guard.outline) for p in clear)


def test_a_headstock_adjusted_truss_rod_leaves_the_guard_alone() -> None:
    parameters = replace(
        Prototype001Parameters(), body_pickguard=True, truss_rod_adjustment="headstock"
    )
    layout = parameters.body_layout()

    assert layout.truss_rod_access is None and layout.pickguard is not None
