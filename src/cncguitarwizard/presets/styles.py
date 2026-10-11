"""Instrument styles: a whole instrument to start from in one choice.

Prototype001 has many settings. A style sets the ones that make a
familiar instrument — a body template, a neck template and the settings
that go with them (its pickups, bridge, controls, neck joint, scale,
frets and inlays) — so the web app's *Style* choice, under the
instrument, is the quick way in: choose an instrument and a style,
build, and change what you like from there. Each is a mockup of the
familiar shape, not the maker's own.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from ..geometry.body import FloydRoseSpec, HardtailSpec, TuneOMaticSpec
from .body_shapes import YOUR_DESIGN_TEMPLATES
from .prototype001 import (
    BODY_TEMPLATE_VALUES,
    NECK_TEMPLATES,
    Instrument,
    Prototype001Parameters,
)


@dataclass(frozen=True, slots=True)
class InstrumentStyle:
    """A whole instrument's settings, chosen at once.

    Args:
        label: Its name in the web app.
        instruments: The instruments it is offered for
            (``prototype001.INSTRUMENT_OVERRIDES`` keys).
        body: Its body template (a ``YOUR_DESIGN_TEMPLATES`` key); the
            template's own other values (``BODY_TEMPLATE_VALUES``) come
            with it.
        neck: Its neck template (a ``NECK_TEMPLATES`` key), or ``None``
            to keep the instrument's own neck.
        values: Its other ``Prototype001Parameters`` settings.
    """

    label: str
    instruments: tuple[Instrument, ...]
    body: str
    neck: str | None = None
    values: Mapping[str, Any] = field(default_factory=dict)

    def prototype_values(self, instrument: Instrument) -> dict[str, Any]:
        """Return every setting it makes for ``instrument``, over the
        instrument's defaults.

        The body template's shape and its own values, the neck template's
        values, then the style's own; a bridge made for a string count
        (a Floyd Rose) set for the instrument's.
        """
        _, shape = YOUR_DESIGN_TEMPLATES[self.body]
        values: dict[str, Any] = {
            "body_shape": shape,
            **BODY_TEMPLATE_VALUES.get(self.body, {}),
        }
        if self.neck is not None:
            values.update(NECK_TEMPLATES[self.neck][1])
        values.update(self.values)
        strings = Prototype001Parameters.for_instrument(instrument).string_count
        bridge = values.get("body_bridge")
        if bridge is not None and getattr(bridge, "string_count", strings) != strings:
            values["body_bridge"] = replace(bridge, string_count=strings)
        return values


GUITAR: tuple[Instrument, ...] = ("electric_guitar",)
"""A six-string guitar: the styles whose neck templates are drawn for six."""

GUITARS: tuple[Instrument, ...] = (
    "electric_guitar",
    "seven_string_guitar",
    "eight_string_guitar",
)
"""Every fretted guitar with a headstock."""

BASSES: tuple[Instrument, ...] = ("bass_guitar", "five_string_bass")
"""Every bass with a headstock."""

FENDER_SCALE = 647.7
"""Fender's scale length, in mm (25.5 in)."""

GIBSON_SCALE = 628.65
"""Gibson's scale length, in mm (24.75 in)."""

TELE_PICKUPS = {
    "body_neck_pickup_offset": 31.4,
    "body_bridge_pickup_offset": 28.6,
    "body_bridge_single_coil_angle": 16.0,
}
"""A Telecaster's pickups where a '52's sit on its body (Wikimedia
Commons, "Fender Telecaster American Vintage 1952 transparent.png", its
outline fitted to the Telecaster template's to within 3 mm): the neck
pickup's centre 31.4 mm behind the heel end, the bridge pickup's 28.6 mm
ahead of the saddle line, slanted 16 degrees, its treble end back."""

STRAT_PICKUPS = {
    "body_neck_pickup_offset": 24.7,
    "body_middle_pickup_offset": 83.8,
    "body_bridge_pickup_offset": 36.9,
    "body_bridge_single_coil_angle": 10.0,
}
"""A Stratocaster's pickups where the user's Stratocaster drawing routes
them (stratbody.dxf, aligned on its neck pocket's end, as the
Stratocaster template is): the neck and middle pickups' centres 24.7 and
83.8 mm behind the heel end, the bridge pickup's 36.9 mm ahead of the
saddle line, slanted 10 degrees."""

GIBSON = {
    "scale_length": GIBSON_SCALE,
    "fret_count": 22,
    # The bridge humbucker's centre 39.6 mm ahead of the saddles, as on
    # a '59 Les Paul and a '61 SG.
    "body_bridge_pickup_offset": 39.6,
    "neck_joint": "set",
    "body_pickups": "HH",
    "body_bridge": TuneOMaticSpec(),
}
"""What a Gibson style shares: its scale, 22 frets, a glued neck, two
humbuckers and a Tune-o-matic."""

STYLES: dict[str, InstrumentStyle] = {
    "design_by_jone": InstrumentStyle("Design by Jone", GUITARS, "design_by_jone"),
    "stratocaster": InstrumentStyle(
        "Fender Stratocaster style",
        GUITAR,
        "stratocaster",
        "stratocaster",
        {
            "scale_length": FENDER_SCALE,
            "fret_count": 22,
            "body_pickups": "SSS",
            **STRAT_PICKUPS,
            "body_bridge": HardtailSpec(),
            "body_controls": "pickguard",
            "body_pickguard": True,
            "body_jack": "strat",
            "body_neck_plate": "plate",
            "body_arm_contour_depth": 10.0,
            "body_belly_cut_depth": 12.0,
            "inlay_style": "dot",
        },
    ),
    "telecaster": InstrumentStyle(
        "Fender Telecaster style",
        GUITAR,
        "telecaster",
        "telecaster",
        {
            "scale_length": FENDER_SCALE,
            "fret_count": 22,
            **TELE_PICKUPS,
            "body_pickups": "SS",
            "body_bridge": HardtailSpec(),
            "body_controls": "tele",
            "body_jack": "cup",
            "body_neck_plate": "plate",
            "inlay_style": "dot",
        },
    ),
    "les_paul": InstrumentStyle(
        "Gibson Les Paul style",
        GUITAR,
        "les_paul",
        "gibson",
        {
            **GIBSON,
            "body_controls": "gibson_4",
            "body_carved_top": True,
            "inlay_style": "trapezoid",
        },
    ),
    "sg": InstrumentStyle(
        "Gibson SG style",
        GUITAR,
        "sg",
        "gibson",
        {
            **GIBSON,
            "body_controls": "gibson_4",
            # As on a '61 reissue: the toggle up on the treble horn level
            # with the bridge, the jack in the top beside the lower pots.
            "body_shape": replace(
                YOUR_DESIGN_TEMPLATES["sg"][1],
                switch_cavity_offset=204.5,
                switch_cavity_y=114.7,
                switch_cover_offset=204.5,
                switch_cover_y=114.7,
                jack_offset=323.4,
                jack_y=64.7,
            ),
            "body_jack": "top",
            "inlay_style": "trapezoid",
        },
    ),
    "flying_v": InstrumentStyle(
        "Gibson Flying V style",
        GUITAR,
        "flying_v",
        "flying_v",
        {**GIBSON, "body_controls": "rear_3", "inlay_style": "dot"},
    ),
    "explorer": InstrumentStyle(
        "Gibson Explorer style",
        GUITAR,
        "explorer",
        "explorer",
        {**GIBSON, "body_controls": "rear_3", "inlay_style": "dot"},
    ),
    "jackson_rr": InstrumentStyle(
        "Jackson RR style",
        GUITARS,
        "jackson_rr",
        values={
            "neck_joint": "neck_through",
            "body_pickups": "HH",
            "body_bridge": FloydRoseSpec(),
            "body_controls": "rear_3",
            # As on a Jackson Rhoads: the toggle among the three pots down
            # the treble wing (sharing their cavity), the jack into the
            # wing's inner edge below them.
            "body_shape": replace(
                YOUR_DESIGN_TEMPLATES["jackson_rr"][1],
                switch_cavity_offset=163.4,
                switch_cavity_y=81.8,
                switch_cover_offset=163.4,
                switch_cover_y=81.8,
                jack_offset=215.0,
                jack_y=83.2,
                jack_direction_degrees=180.0,
            ),
            "inlay_style": "sharktooth",
        },
    ),
    # Not for eight strings: their Floyd Rose reaches past the inner step.
    "alexi_hexed": InstrumentStyle(
        "ESP LTD Alexi Hexed style",
        ("electric_guitar", "seven_string_guitar"),
        "alexi_hexed",
        values={"neck_joint": "neck_through", "inlay_style": "sharktooth"},
    ),
    "mockingbird": InstrumentStyle(
        "B.C. Rich Mockingbird style",
        GUITAR,
        "mockingbird",
        "mockingbird",
        {
            "neck_joint": "neck_through",
            "body_pickups": "HH",
            "body_bridge": TuneOMaticSpec(),
            "inlay_style": "diamond",
        },
    ),
    "jazz_bass": InstrumentStyle(
        "Fender Jazz Bass style",
        BASSES,
        "jazz_bass",
        values={
            "body_pickups": "JJ",
            "body_controls": "jazz_bass",
            "body_pickguard": True,
            "body_neck_plate": "plate",
            "inlay_style": "dot",
        },
    ),
}
"""Every style, in the order the web app offers them."""
