"""Tests for single-feature programs zeroed on the feature."""

from dataclasses import replace

import pytest

from cncguitarwizard.cam import (
    MachiningParameters,
    ToolpathError,
    plan_feature_machining,
)
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.webapp import feature_programs


@pytest.fixture(scope="module")
def geometry():  # type: ignore[no-untyped-def]
    return replace(Prototype001Parameters(), body_battery_box=True).build()


def test_a_battery_box_is_cut_on_its_own_zeroed_at_its_centre(geometry) -> None:  # type: ignore[no-untyped-def]
    setups = plan_feature_machining(
        geometry.body,
        geometry.covers,
        lambda name: name.startswith("Battery"),
        "battery box",
        MachiningParameters(),
    )

    names = [setup.name for setup in setups]
    assert names == [
        "Feature_battery_box_back",
        "Feature_battery_box_back_small_holes",
        "Cover_battery_cavity",
    ]
    back = setups[0]
    assert "centre of the battery box" in (back.work_zero or "")
    # Only the battery box: its recess and cavity, no other cavity.
    assert [path.name for path in back.toolpaths] == [
        "Battery cavity cover recess",
        "Battery cavity",
    ]
    # Every cut lies round the zero, within the cover recess's reach.
    recess = geometry.body.battery_cavity.cover_recess.outline
    reach = max(
        max(p.x for p in recess) - min(p.x for p in recess),
        max(p.y for p in recess) - min(p.y for p in recess),
    )
    for path in back.toolpaths:
        for move in path.moves:
            assert abs(move.x) <= reach / 2.0 + 1e-6
            assert abs(move.y) <= reach / 2.0 + 1e-6


def test_a_top_feature_is_cut_from_the_top(geometry) -> None:  # type: ignore[no-untyped-def]
    setups = plan_feature_machining(
        geometry.body,
        geometry.covers,
        lambda name: name.startswith("Bridge pickup"),
        "bridge pickup",
        MachiningParameters(),
    )

    assert [setup.name for setup in setups] == ["Feature_bridge_pickup_top"]
    assert setups[0].toolpaths[0].name == "Bridge pickup route"


def test_nothing_to_cut_is_refused(geometry) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ToolpathError, match="Nothing on the body"):
        plan_feature_machining(
            geometry.body,
            geometry.covers,
            lambda name: False,
            "nothing",
            MachiningParameters(),
        )


def test_the_web_app_makes_a_dragged_features_files() -> None:
    payload = {"prototype": {"body_battery_box": True}}

    battery = feature_programs(payload, "battery")
    assert battery["title"] == "battery box"
    assert [f["name"] for f in battery["files"]][-1] == "Cover_battery_cavity.nc"
    assert "G0 X0.000 Y0.000" in battery["files"][0]["text"]
    assert "drill it by hand" in feature_programs(payload, "jack")["error"]
