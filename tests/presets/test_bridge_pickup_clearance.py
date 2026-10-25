"""Tests for the bridge pickup's clearance ahead of the chosen bridge.

Regression: the bridge pickup used to sit at the same place whatever the
bridge, so a hardtail's baseplate screw holes fell inside its route and a
Tune-o-matic's post holes ended just behind it.
"""

from dataclasses import replace

import pytest

from cncguitarwizard.geometry.body import (
    BridgeSpec,
    FloydRoseSpec,
    HardtailSpec,
    KahlerBridgeSpec,
    TuneOMaticSpec,
)
from cncguitarwizard.geometry.exceptions import BodyGeometryError
from cncguitarwizard.geometry.primitives import point_in_polygon
from cncguitarwizard.presets import Prototype001Parameters

BRIDGES: tuple[BridgeSpec, ...] = (
    KahlerBridgeSpec(),
    FloydRoseSpec(),
    TuneOMaticSpec(),
    HardtailSpec(),
)


def bridge_fronts(parameters: Prototype001Parameters) -> list[float]:
    """Return the nut-ward edge of every bridge route and hole as placed."""
    layout = parameters.body_layout()
    hardware = parameters.body_bridge.hardware(
        parameters.centre_scale, parameters.body_thickness
    )
    hole_names = {hole.name for hole in hardware.holes}
    cavity_names = {
        cavity.name for cavity in (*hardware.top_cavities, *hardware.through_cavities)
    }
    return [
        *(
            hole.center_x - hole.diameter / 2.0
            for hole in layout.holes
            if hole.name in hole_names
        ),
        *(
            cavity.min_x
            for cavity in (*layout.extra_cavities, *layout.through_cavities)
            if cavity.name in cavity_names
        ),
    ]


@pytest.mark.parametrize("bridge", BRIDGES, ids=lambda spec: spec.kind)
@pytest.mark.parametrize("fanned", [False, True], ids=["single", "multiscale"])
def test_the_bridge_pickup_keeps_its_clearance_ahead_of_every_bridge(
    bridge: BridgeSpec, fanned: bool
) -> None:
    parameters = replace(
        Prototype001Parameters(),
        body_bridge=bridge,
        bass_scale_length=647.7 if fanned else None,
    )
    layout = parameters.body_layout()
    route = layout.bridge_pickup
    assert route is not None

    assert route.max_x <= min(bridge_fronts(parameters)) - (
        parameters.body_bridge_pickup_clearance - 1e-9
    )
    for hole in layout.holes:
        if "pickup" not in hole.name:
            assert not point_in_polygon(hole.center, route.outline), hole.name
    parameters.build()


def test_the_hardtail_screws_stay_out_of_the_bridge_pickup_route() -> None:
    parameters = replace(Prototype001Parameters(), body_bridge=HardtailSpec())
    route = parameters.body_layout().bridge_pickup
    assert route is not None

    # Screw line 10 mm ahead of the 609.6 mm scale, Ø 3 pilots, 3 mm wood.
    assert route.max_x == pytest.approx(609.6 - 10.0 - 1.5 - 3.0)


def test_the_tune_o_matic_posts_keep_their_wood() -> None:
    parameters = replace(Prototype001Parameters(), body_bridge=TuneOMaticSpec())
    route = parameters.body_layout().bridge_pickup
    assert route is not None

    # The treble post 1.6 mm behind the saddle line (moved off the 609.6
    # mm scale line by the Tune-o-matic's 2 degree neck angle; the bass
    # post sits further back), Ø 11.2 inserts, 3 mm wood.
    saddles = parameters.bridge_scale_line()
    assert saddles == pytest.approx(608.56, abs=0.01)
    assert route.max_x == pytest.approx(saddles + 1.6 - 5.6 - 3.0)


def test_a_bridge_pickup_reaches_past_the_saddle_line_up_to_a_kahlers_plate() -> None:
    # Regression: the route stopped at the saddle line, 11.5 mm short of
    # the Kahler's plate, and a pickup dragged nearer jumped back. A Kahler
    # set that far back (as the Prototype001 DXF drew it; its cutout now
    # starts just ahead of the saddles by default).
    parameters = replace(
        Prototype001Parameters(),
        body_bridge=KahlerBridgeSpec(baseplate_offset=44.245),
        body_bridge_pickup_offset=14.2,
    )
    layout = parameters.body_layout()
    route = layout.bridge_pickup
    assert route is not None
    hardware = parameters.body_bridge.hardware(
        parameters.centre_scale, parameters.body_thickness
    )
    plate = min(point.x for point in hardware.footprint)
    scale = parameters.centre_scale

    # Where it was put: 6.3 mm past the saddle line, clear of the plate.
    assert (route.min_x + route.max_x) / 2.0 == pytest.approx(scale - 14.2)
    assert route.max_x > scale
    assert plate - route.max_x > parameters.body_bridge_pickup_clearance
    # Asked nearer, it stops body_bridge_pickup_clearance short of it.
    nearest = replace(parameters, body_bridge_pickup_offset=0.0).body_layout()
    assert nearest.bridge_pickup is not None
    assert nearest.bridge_pickup.max_x == pytest.approx(
        plate - parameters.body_bridge_pickup_clearance
    )


def test_a_bridge_pickups_centre_never_passes_the_saddle_line() -> None:
    # With the Kahler's plate allowed under it, the strings' end still
    # holds the pickup: its centre stays ahead of the saddle line.
    parameters = replace(
        Prototype001Parameters(),
        body_bridge_pickup_offset=-30.0,
        body_bridge_pickup_clearance=-30.0,
    )
    route = parameters.body_layout().bridge_pickup
    assert route is not None

    assert (route.min_x + route.max_x) / 2.0 == pytest.approx(parameters.centre_scale)


@pytest.mark.parametrize("bridge", BRIDGES, ids=lambda spec: spec.kind)
def test_the_bridge_pickup_stays_ahead_of_a_fanned_saddle_line(
    bridge: BridgeSpec,
) -> None:
    parameters = replace(
        Prototype001Parameters(),
        body_bridge=bridge,
        body_pickups="MM",
        bass_scale_length=647.7,
        body_bridge_pickup_offset=0.0,
    )
    route = parameters.body_layout().bridge_pickup
    assert route is not None

    # Its centre, on the centreline, where the fanned line crosses at the
    # scale.
    assert (route.min_x + route.max_x) / 2.0 <= parameters.centre_scale + 1e-9


def test_a_bridge_pickup_that_cannot_clear_the_bridge_is_refused() -> None:
    # A hand-placed middle pickup that fits ahead of the Kahler's bridge
    # pickup, but not once a hardtail pushes the bridge pickup forward.
    parameters = replace(
        Prototype001Parameters(), body_pickups="HSS", body_middle_pickup_offset=85.0
    )
    parameters.build()

    with pytest.raises(BodyGeometryError, match="cannot clear the hardtail"):
        replace(parameters, body_bridge=HardtailSpec()).body_layout()
