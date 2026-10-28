"""Glue for running the Prototype001 build inside a browser (Pyodide).

The static web page in ``site/`` loads the package as a wheel into
Pyodide and calls the two functions here: ``parameter_schema`` to draw
its form, and ``run_build`` to produce every FreeCAD-free artifact in
the browser's virtual file system. Both speak plain JSON-compatible
dictionaries so the JavaScript side needs no knowledge of the
dataclasses.
"""

from __future__ import annotations

import ast
import base64
import dataclasses
import functools
import inspect
import io
import itertools
import json
import math
import re
import textwrap
import types
import typing
import zipfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .backends.freecad import (
    EXPORT_FORMATS,
    export_script_name,
    render_format_export,
)
from .backends.freecad.script_exporter import FreeCADScriptExporter
from .backends.occt.model import FORMATS as MODEL_FORMATS
from .cam import (
    POST_PROCESSOR_LABELS,
    FretboardMachiningParameters,
    GCodeWriter,
    MachiningParameters,
    plan_feature_machining,
    plan_fretboard_radius,
    program_stem,
)
from .cam.parameters import INDEX_PIN_DIAMETER
from .cam.planar import simplified
from .drawings import (
    ReadOutline,
    ReferenceShape,
    TemplateFrame,
    fit_closed_spline,
    fit_headstock,
    read_template_outline,
    read_template_pattern,
    template_dxf,
    template_svg,
)
from .drawings.outlines import headstock_spans
from .drawings.template import thinned
from .exceptions import CNCGuitarWizardError
from .field_help import FIELD_HELP
from .geometry.body import (
    BRIDGE_KINDS,
    BRIDGE_LABELS,
    BRIDGE_MAX_STRINGS,
    BRIDGE_MIN_STRINGS,
    BRIDGE_NOTES,
    JackHole,
    KahlerBridgeSpec,
    bridge_spec_from_dict,
)
from .geometry.exceptions import GeometryException
from .geometry.fret import FretCalculator
from .geometry.fretboard.inlay_layout import (
    CUSTOM_ROUND_SAMPLES,
    DEFAULT_CUSTOM_POINTS,
    custom_limits,
)
from .geometry.fretboard.runes import DEFAULT_RUNES, RUNES
from .geometry.lettering import text_lines
from .geometry.neck import (
    LOCKING_NUT_SPECS,
    TunerLayout,
    drawn_back_line,
    drawn_whole,
)
from .geometry.primitives import (
    CORNER,
    ROUND,
    DrawnPoint,
    Point2D,
    closed_catmull_rom_spans,
    drawn_points,
    drawn_polygon,
    point_in_polygon,
)
from .presets import Prototype001Geometry, Prototype001Parameters
from .presets.body_shapes import (
    BODY_SHAPE_KINDS,
    BODY_SHAPE_LABELS,
    OUTLINE_SAMPLES_PER_SEGMENT,
    YOUR_DESIGN_START_POINTS,
    YOUR_DESIGN_TEMPLATES,
    YourDesignShape,
    body_shape_from_dict,
    narrow_y,
    widen_drawn,
    widened_shape,
)
from .presets.controls import CONTROL_LABELS, SCREW_CLEARANCE
from .presets.pickup_frames import PickupFrame
from .presets.pickups import PICKUP_CONFIGURATIONS
from .presets.prototype001 import (
    BODY_TEMPLATE_VALUES,
    DRAWN_JOINT_TIP_CLEARANCE,
    HEEL_LINE_SETTINGS,
    INSTRUMENT_OVERRIDES,
    NECK_TEMPLATE_RESETS,
    NECK_TEMPLATES,
    ROOT_LINE_SETTINGS,
)
from .presets.styles import STYLES
from .presets.truss_rod_covers import editable_cover_points, truss_rod_cover_shape
from .render.preview3d import DETAILS, PreviewPart, detail_parts, preview_parts
from .render.svg import (
    render_fretboard_svg,
    render_neck_svg,
    render_plan_view_svg,
    render_volute_view_svg,
)
from .setting_conditions import ABOVE_ZERO, APPLIES_WHEN, NOT_EMPTY
from .setting_pictures import SETTING_PICTURES
from .workflows import Prototype001Build

_VARIANT_LABELS: dict[str, str] = {**BRIDGE_LABELS, **BODY_SHAPE_LABELS}

# Readable names for choice fields whose options are short codes.
_CHOICE_LABELS: dict[str, dict[str, str]] = {
    "handedness": {
        "right": "Right-handed (as drawn)",
        "left": "Left-handed (the mirror image)",
    },
    "neck_carbon_rod_size": {
        "3.2x6.35": "3.2 x 6.35 mm (1/8 x 1/4 in)",
        "4x4": "4 x 4 mm",
        "3.2x9.5": "3.2 x 9.5 mm (1/8 x 3/8 in, StewMac; needs a thick neck)",
        "custom": "Custom: neck_carbon_rod_width x neck_carbon_rod_depth",
    },
    "neck_joint": {
        "bolt_on": "Bolt-on (the heel screwed into a pocket)",
        "set": "Set neck (the heel glued into a tight pocket, Gibson style)",
        "neck_through": (
            "Neck-through (the neck runs on as the body's centre, wings glued on)"
        ),
        "one_piece": "One piece (the neck and the whole body from one blank)",
    },
    "body_controls": CONTROL_LABELS,
    "post_processor": POST_PROCESSOR_LABELS,
    "neck_back_cut": {
        "rough_and_finish": "Flat end mill roughs, ball nose finishes (two programs)",
        "ball": "Ball nose alone, roughing then finishing (one program)",
    },
    "neck_blank": {
        "solid": "One plank as thick as the headstock needs",
        "laminated": "Neck plank first, headstock block glued on after",
    },
    "truss_rod_profile": {
        "standard": "Standard two-way rod (11 mm pocket at its adjusting end)",
        "low_profile": "Low-profile two-way rod (straight 6.35 x 9.5 mm channel)",
    },
    "truss_rod_install": {
        "top": "From the top, under the fretboard",
        "back": (
            "Vintage: from the back, under a walnut strip (adjusted at the "
            "headstock: a 1970s bullet rod)"
        ),
    },
    "truss_rod_spoke_wheel": {
        "auto": "Auto (a spoke wheel at the heel, none at the headstock)",
        "yes": "Spoke wheel",
        "no": "No spoke wheel: a nut at the heel's end, a key notch at the head",
    },
    "nut_style": {
        "shelf": "On the neck's shelf, in front of the fretboard",
        "slot": "Fender / Telecaster: in a slot at the fretboard's end",
        "zero_fret": "Zero fret on the nut line, the nut a string guide behind it",
    },
    "locking_nut": {
        "auto": (
            "Auto (Floyd Rose Original nut with a Floyd Rose or Lo-Pro Edge bridge)"
        ),
        "none": "Plain nut",
        "r2": "Floyd Rose R2 locking nut (41.3 mm)",
        "r3": "Floyd Rose R3 locking nut (42.85 mm)",
        "r7": "Floyd Rose 7-string locking nut (47.6 mm)",
        "r8": "Floyd Rose 8-string locking nut (53.8 mm)",
    },
    "body_engraving_pattern": {
        "scroll": "Scrolls (Design by Jone)",
        "evh_stripes": "EVH stripes (taped, criss-crossing)",
        "flame": "Flame (wavy lines across the body)",
        "ripples": "Ripples (rings over rings)",
        "crackle": "Crackle (random cells)",
        "camo": "Camo (woodland relief, four levels)",
        "pinstripe": "Pinstripe (round the edge, Jackson RR / Alexi Hexed)",
        "drawn": "Drawn (lines from the body editor's Import SVG)",
    },
    "headstock_volute_style": {
        "arrow": "Rounded arrow",
        "drawn": "Drawn: its crest and both ends (in the headstock editor)",
    },
    "headstock_root_style": {
        "smooth": "Smooth",
        "drawn": "Drawn: two lines (in the headstock editor, flat headstock)",
    },
    "heel_root_style": {
        "smooth": "Smooth",
        "drawn": "Drawn: two lines (on Design › Neck)",
    },
    "truss_rod_cover_style": {
        "bell": "Gibson bell (3 screws)",
        "ibanez": "Ibanez / ESP style (2 screws)",
        "prs": "PRS style teardrop (2 screws)",
        "rectangle": "Rounded rectangle (3 screws)",
        "custom": "Custom (drawn in the headstock editor)",
    },
    "inlay_style": {
        "barbed_wire": "Barbed wire (two at the 12th and 24th)",
        "barbed_wire_2": "Barbed wire 2 (a traced knot, one piece at every marker)",
        "dot": "Dots (two at the 12th and 24th)",
        "block": "Blocks (Gibson)",
        "trapezoid": "Trapezoids (Les Paul)",
        "sharktooth": "Sharktooth (Jackson)",
        "parallelogram": "Parallelograms",
        "diamond": "Diamonds",
        "split_block": "Split blocks (Gibson)",
        "runes": "Runes (the Elder Futhark, one chosen for each fret)",
        "cross": "Crosses (upright Latin crosses)",
        "iron_cross": "Iron crosses (cross pattée)",
        "ankh": "Ankhs (traced from a photograph, the wood in the loop kept)",
        "custom": "Custom (drawn in the Inlay design window)",
    },
    "body_jack": {
        "side": "Side jack (Les Paul style plate or barrel jack)",
        "cup": "Cup jack or Electrosocket (7/8 in counterbore)",
        "strat": "Round top cavity (a 1 in pocket under a top plate)",
        "oval": "Stratocaster oval plate (its football route from the top)",
        "plate": "On the Jazz Bass control plate (no bore from the edge)",
        "top": "In the top, into the rear control cavity (SG, Explorer style)",
    },
    "body_pickguard_style": {
        "stratocaster": "Stratocaster (beside the neck, a tail past the bridge)",
        "superstrat": "Superstrat (close round the pickups)",
        "sg_small": "SG '61 small guard (drawn for the SG body)",
        "sg_batwing": "SG batwing guard (drawn for the SG body)",
    },
    "body_heel_relief": {
        "none": "None (a flat back)",
        "contour": "Contour (a smooth slope, deepest at the body's edge)",
        "notch": "Notch (a flat step down, a wall where it ends)",
        "bevel": "Bevel (a flat slope along the neck, for a tilted neck plate)",
    },
    "body_heel_relief_line": {
        "around": "Round the heel (a curve behind it, the whole heel)",
        "pocket": "Along the neck pocket (its outline, the whole heel)",
        "corner": "Across the treble corner (a straight 45° line)",
    },
    "body_pickup_frame": {
        "none": "None",
        "ring": "Plain ring (a rounded rectangle round the route)",
        "horns": "Horns (a horn either end toward the neck, round toward the bridge)",
        "hook": "Hook (a hooked bass end, a long horn on the treble side)",
    },
    "body_pickup_frame_direction": {
        "auto": "Horns toward the neck, turned round where they do not fit",
        "neck": "Horns toward the neck",
        "bridge": "Horns toward the bridge (turned round)",
    },
    "headstock_engraving_font": {
        "sans": "Plain sans (single stroke)",
        "script": "Script (Hershey Script)",
        "gothic": "Gothic (Hershey Gothic English)",
    },
    "body_switch": {
        "toggle": "3-way toggle (1/2 in hole, 12.7 mm)",
        "micro": "Micro (mini) toggle (1/4 in hole, 6.35 mm)",
    },
    "body_pickups_follow_fan": {
        "auto": "Auto (turn, except with a Tune-o-matic)",
        "yes": "Turn with the frets",
        "no": "Keep square",
    },
}

INSTRUMENT_LABELS: dict[str, str] = {
    "electric_guitar": "Electric guitar",
    "seven_string_guitar": "7-string guitar",
    "eight_string_guitar": "8-string guitar",
    "bass_guitar": "Bass guitar",
    "five_string_bass": "5-string bass",
    "headless_guitar": "Headless guitar",
    "headless_bass": "Headless bass",
}

# The handful of parameters a builder normally touches; the form shows
# every other field of the same group behind an "Advanced" fold.
_BASIC_FIELDS: frozenset[str] = frozenset(
    {
        "string_count",
        "scale_length",
        "fret_count",
        "fret_slant_angle",
        "truss_rod_adjustment",
        "truss_rod_install",
        "truss_rod_spoke_wheel",
        "truss_rod_profile",
        "truss_rod_rod_length",
        "bass_scale_length",
        "perpendicular_fret",
        "nut_width",
        "fretboard_radius",
        "fretboard_thickness",
        "fretboard_one_piece",
        "fretboard_binding_width",
        "fret_slot_end_inset",
        "fretboard_scalloped",
        "fretboard_scallop_from_fret",
        "fretboard_scallop_depth",
        "inlay_style",
        "final_fret_width",
        "first_fret_thickness",
        "twelfth_fret_thickness",
        "neck_profile_exponent",
        "heel_width",
        "neck_angle",
        "heel_thickness",
        "headstock_style",
        "headstock_outline",
        "headstock_length",
        "headstock_angle",
        "headstock_thickness",
        "headstock_pointed_volute",
        "tuner_hole_diameter",
        "body_thickness",
        "body_shape",
        "body_pickups",
        "body_bridge",
        "body_controls",
        "body_switch",
        "body_jack",
        "body_jack_plate",
        "body_pickguard",
        "body_pickguard_style",
        "body_pickup_frame",
        "body_pickup_frame_direction",
        "body_pickup_frame_thickness",
        "body_engraving",
        "body_engraving_pattern",
        "body_engraving_seed",
        "body_battery_box",
        "body_battery_count",
        "locking_nut",
        "nut_style",
        "nut_jig",
        "nut_jig_gauges",
        "body_pickups_follow_fan",
        "body_bridge_follows_fan",
        "body_top_edge_radius",
        "body_back_edge_radius",
        "body_top_bevel_width",
        "body_back_bevel_width",
        "body_top_binding_width",
        "body_arm_contour_depth",
        "body_belly_cut_depth",
        "body_leg_contour_depth",
        "body_carved_top",
        "body_carve_depth",
        "body_stepped_top",
        "body_neck_pickup_offset",
        "body_bridge_pickup_offset",
        "tool_diameter",
        "tool_tip",
        "post_processor",
        "spindle_dwell",
        "z_lift_rate",
        "combine_programs",
        "machine_x_travel",
        "machine_y_travel",
        "neck_blank",
        "neck_back_cut",
        "spindle_speed",
        "feed_rate",
        "plunge_rate",
        "step_down",
        "step_over",
        "tab_count",
        "handedness",
        "neck_joint",
        "neck_carbon_rods",
        "neck_carbon_rod_size",
        "carve_tool_diameter",
        "carve_step_down",
        "carve_finish",
        "carve_flat_tool_diameter",
        "carve_flat_step_down",
        "ball_tool_diameter",
        "ball_step_down",
        "fret_slot_tool_diameter",
        "fret_slot_spindle_speed",
        "fret_slot_step_down",
        "inlay_tool_diameter",
        "inlay_spindle_speed",
        "inlay_step_down",
        "fretboard_blank_length",
        "fretboard_blank_width",
        "fretboard_blank_thickness",
        "fretboard_carrier_thickness",
        "truss_rod_cover_style",
        "truss_rod_cover_length",
        "truss_rod_cover_width",
    }
)

# Variant fields whose form offers only some of their kinds. The body is
# always a drawn one, edited in the body editor (the traced DXF is its
# "Design by Jone" template); Python still takes every kind.
_FORM_KINDS: dict[str, frozenset[str]] = {
    "body_shape": frozenset({"your_design"}),
}

# Per variant kind (bridges and body shapes), the fields worth checking
# against the hardware in hand; the rest of a kind's fields are its
# "Advanced" fold. A kind not listed here shows all of its fields.
_BASIC_VARIANT_FIELDS: dict[str, frozenset[str]] = {
    "design_by_jone": frozenset(),
    "your_design": frozenset(),
    "kahler_7300": frozenset(
        {
            "baseplate_length",
            "baseplate_width",
            "baseplate_offset",
            "baseplate_depth",
            "plate_overhang",
        }
    ),
    "floyd_rose": frozenset({"treble_side", "pivot_offset", "pivot_stud_spacing"}),
    "lo_pro_edge": frozenset({"treble_side", "pivot_offset"}),
    "vintage_tremolo": frozenset(
        {"treble_side", "screw_offset", "screw_spacing", "plate_width"}
    ),
    "tune_o_matic": frozenset(
        {
            "post_spacing",
            "compensation",
            "bass_setback",
            "stud_spacing",
            "tailpiece_offset",
        }
    ),
    "hardtail": frozenset(
        {"string_through", "string_spacing", "string_hole_offset", "screw_count"}
    ),
    "single_string": frozenset(
        {"string_spacing", "unit_length", "unit_width", "front_reach", "string_through"}
    ),
}

_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Instrument", ("handedness",)),
    (
        "Scale and fretboard",
        (
            "string_count",
            "scale_length",
            "bass_scale_length",
            "perpendicular_fret",
            "fret_count",
            "fret",
            "inlay",
        ),
    ),
    (
        "Neck",
        (
            "final_fret",
            "first_fret",
            "twelfth",
            "neck",
            "nut_",
            "locking_nut",
            "truss",
        ),
    ),
    ("Heel", ("heel",)),
    ("Headstock and tuners", ("headstock", "tuner")),
    ("Body", ("body",)),
    ("Fillets and sampling", ("joint_fillet", "profile_sample", "segments")),
)


def parameter_schema() -> dict[str, Any]:
    """Describe both parameter sets for a generated form.

    Returns:
        ``{"instruments", "prototype": [...groups...], "machining":
        [...groups...]}``; ``instruments`` maps each instrument to
        ``{"label", "overrides"}``, the defaults that differ for it,
        where every group is ``{"title", "fields"}`` and every field is
        ``{"name", "type", "default", "advanced"}`` with ``type`` one of
        ``float``, ``int``, ``bool``, ``optional_float``, ``json``
        (tuples), ``choice`` (a ``Literal`` of strings, listed in
        ``options``) or ``variant`` — a choice between dataclasses that
        each carry a ``kind`` field (the bridge), described by
        ``variants``: ``{kind: {"label", "max_strings", "min_strings",
        "fields"}}`` (the string counts a bridge kind is made for, ``None``
        for any). ``advanced`` is
        true for the rarely changed fields the form folds away.
        ``export_formats`` the other 3D formats the built model is
        exported to (``format_export``), each by extension to what it is
        for; ``model_formats`` those the page makes itself, in the browser
        (``backends.occt``); ``setting_pictures`` each setting's picture
        (``setting_pictures.SETTING_PICTURES``), ``{"view", "parts"}``: the
        view of ``setting_views`` it is drawn on and the parts picked out
        there, the first pattern that finds one; ``applies_when`` the
        settings that do anything only beside other settings' values
        (``setting_conditions.APPLIES_WHEN``), each to its conditions, any
        one of them the values other settings must have (``any_text``
        standing for any text but none), the page hiding it while none
        hold. ``locking_nut_widths``
        maps each locking nut to its width, the least ``nut_width`` it fits
        (the form widens the neck to it);
        ``neck_templates`` each neck template (``NECK_TEMPLATES``) to
        ``{"label", "values", "resets"}``, the values the headstock editor
        loads and the settings it puts back to their defaults
        (``NECK_TEMPLATE_RESETS`` the template does not set);
        ``pickup_configurations`` each named pickup layout to its
        ``[neck, middle, bridge]`` types (the body editor turns a layout
        into "custom" to remove one pickup); ``runes`` the Elder Futhark's
        runes in order, each ``{"name", "glyph", "meaning"}``, for
        ``inlay_runes``; ``styles`` each instrument style (``STYLES``) to
        ``{"label", "instruments"}``, the instruments it is offered for
        (``style_design`` gives its settings).
    """
    return {
        "instruments": {
            instrument: {
                "label": INSTRUMENT_LABELS[instrument],
                "overrides": _jsonable(overrides),
            }
            for instrument, overrides in INSTRUMENT_OVERRIDES.items()
        },
        "prototype": _group_fields(Prototype001Parameters),
        "neck_templates": {
            key: {
                "label": label,
                "values": _jsonable(values),
                "resets": sorted(NECK_TEMPLATE_RESETS - set(values)),
            }
            for key, (label, values) in NECK_TEMPLATES.items()
        },
        "pickup_configurations": {
            name: list(types) for name, types in PICKUP_CONFIGURATIONS.items()
        },
        "locking_nut_widths": {
            kind: spec.width for kind, spec in LOCKING_NUT_SPECS.items()
        },
        "runes": [
            {"name": rune.name, "glyph": rune.glyph, "meaning": rune.meaning}
            for rune in RUNES.values()
        ],
        "export_formats": dict(EXPORT_FORMATS),
        "model_formats": dict(MODEL_FORMATS),
        "setting_pictures": {
            name: {"view": view, "parts": list(parts)}
            for name, (view, parts) in SETTING_PICTURES.items()
        },
        "applies_when": {
            name: [
                {other: list(values) for other, values in condition.items()}
                for condition in conditions
            ]
            for name, conditions in APPLIES_WHEN.items()
        },
        "any_text": NOT_EMPTY,
        "above_zero": ABOVE_ZERO,
        "styles": {
            key: {"label": style.label, "instruments": list(style.instruments)}
            for key, style in STYLES.items()
        },
        "machining": [
            {
                "title": "Machining",
                "fields": _describe_fields(MachiningParameters, _BASIC_FIELDS),
            }
        ],
    }


def upgrade_design(design: dict[str, Any]) -> dict[str, Any]:
    """Bring a saved design's values up to this version's before it loads.

    Designs saved before the headstock editor have ``headstock_outline``
    "fitted", the default then. With no edges drawn a "drawn" outline is
    that same fitted outline, so such a design loads as "drawn": the
    headstock editor opens on it, as on a new design, with the settings
    shown in it. A headless neck, or edges kept from a drawing, stay
    fitted as saved.

    Designs saved before the index pins followed the tool have
    ``index_pin_diameter`` 6, the default then: it loads empty, 6 mm
    dowels as before, or as wide as the tool where it is wider (where 6
    was refused).

    Designs saved before the Latin cross markers were renamed have
    ``inlay_style`` "iommi_cross": they load as "cross".

    Designs saved before an epoxy tray's walls took its rim's width have
    a ``body_epoxy_tray_wall`` of their own: it is dropped, so the design
    loads with the walls as wide as the rim (and nothing skipped).

    Designs saved before a Kahler 7300's cutout was placed as Kahler's
    installation guide places it have its ``baseplate_offset`` at
    ``KAHLER_DXF_OFFSET``, the default then (the cutout 16.5 mm behind the
    saddles): it loads as the default now, the saddles just inside it.

    Args:
        design: The saved design, ``{"instrument", "prototype", ...}``.

    Returns:
        A copy with the outdated values brought up to date.
    """
    machining = dict(design.get("machining") or {})
    if machining.get("index_pin_diameter") == INDEX_PIN_DIAMETER:
        machining["index_pin_diameter"] = None
    prototype = dict(design.get("prototype") or {})
    overrides = INSTRUMENT_OVERRIDES.get(design.get("instrument", ""), {})
    if (
        prototype.get("headstock_outline") == "fitted"
        and not prototype.get("headless", overrides.get("headless", False))
        and not prototype.get("headstock_bass_edge")
        and not prototype.get("headstock_treble_edge")
    ):
        prototype["headstock_outline"] = "drawn"
    if prototype.get("inlay_style") == "iommi_cross":
        prototype["inlay_style"] = "cross"
    prototype.pop("body_epoxy_tray_wall", None)
    bridge = prototype.get("body_bridge")
    if (
        isinstance(bridge, dict)
        and bridge.get("kind") == "kahler_7300"
        and bridge.get("baseplate_offset") == KAHLER_DXF_OFFSET
    ):
        prototype["body_bridge"] = {
            **bridge,
            "baseplate_offset": KahlerBridgeSpec().baseplate_offset,
        }
    upgraded = {**design, "prototype": prototype}
    if "machining" in design:
        upgraded["machining"] = machining
    return upgraded


DESIGN_FORMAT = "cncguitarwizard-design"
"""The ``format`` entry of a design saved with the web app's Save design."""

KAHLER_DXF_OFFSET = 44.245
"""A Kahler 7300 cutout's centre behind the scale line as the Prototype001
DXF drew it, the default until it was placed as Kahler places it
(``upgrade_design``)."""


def style_design(instrument: str, style: str, name: str = "") -> dict[str, Any]:
    """Return an instrument style as a design, for the page to load whole.

    The style's settings (``InstrumentStyle.prototype_values``) over the
    instrument's defaults, as Save design writes a design; every setting
    it does not make is the instrument's default.

    Args:
        instrument: An ``INSTRUMENT_OVERRIDES`` key.
        style: A ``STYLES`` key offered for that instrument.
        name: The guitar's name, kept.

    Returns:
        ``{"format", "version", "name", "instrument", "prototype",
        "machining"}``, or ``{"error": message}`` for a style not offered
        for the instrument.
    """
    chosen = STYLES.get(style)
    if chosen is None or instrument not in chosen.instruments:
        return {"error": f"There is no {style!r} style for {instrument!r}."}
    return {
        "format": DESIGN_FORMAT,
        "version": 1,
        "name": name,
        "instrument": instrument,
        "prototype": _jsonable(chosen.prototype_values(instrument)),
        "machining": _jsonable(chosen.machining_values(instrument)),
    }


def neck_through_changes(values: dict[str, Any]) -> dict[str, str]:
    """Return the settings that turn a design into a neck-through one.

    For easy mode's Neck-through tick, where the settings are hidden: the
    joint, and what a neck run through the body cannot keep — a round
    (Stratocaster) heel end goes square, a neck plate gives way to
    ferrules, and a truss rod adjusted at the heel with no spoke wheel is
    adjusted at the headstock instead.

    Args:
        values: The design's settings (the page's form values); a missing
            one counts as the default.

    Returns:
        The settings to change, by name, with their new values.
    """
    defaults = Prototype001Parameters()
    current = {
        name: values.get(name, getattr(defaults, name))
        for name in (
            "neck_joint",
            "neck_heel_end",
            "body_neck_plate",
            "truss_rod_adjustment",
            "truss_rod_spoke_wheel",
        )
    }
    wanted = {
        "neck_joint": "neck_through",
        "neck_heel_end": "square",
        "body_neck_plate": "ferrules",
    }
    if (
        current["truss_rod_adjustment"] == "heel"
        and current["truss_rod_spoke_wheel"] == "no"
    ):
        wanted["truss_rod_adjustment"] = "headstock"
    return {name: value for name, value in wanted.items() if current[name] != value}


@dataclasses.dataclass(frozen=True, slots=True)
class LoadedDesign:
    """A saved design's values, ready to build.

    Attributes:
        name: The guitar's name ("" when it has none).
        parameters: The instrument's defaults with the design's values.
        machining: The design's body machining values.
        skipped: The settings this version does not know, which were
            skipped (``name``, or ``name.field`` inside a bridge or body
            shape).
    """

    name: str
    parameters: Prototype001Parameters
    machining: MachiningParameters
    skipped: tuple[str, ...]


def load_design(design: dict[str, Any]) -> LoadedDesign:
    """Turn a design saved with the web app's Save design into parameters.

    It is read as the web app loads one: brought up to date first
    (``upgrade_design``), a value the file lacks is the instrument's
    default, and a setting this version does not know is skipped and
    listed.

    Args:
        design: The saved design, as read from its JSON file.

    Returns:
        The design's name, parameters and machining values, and the
        settings skipped.

    Raises:
        CNCGuitarWizardError: If it is not a design, names an unknown
            instrument, or its values make no valid instrument.
        TypeError: If a value has the wrong type.
        ValueError: If a value is out of range.
    """
    if not isinstance(design, dict) or design.get("format") != DESIGN_FORMAT:
        raise CNCGuitarWizardError("This is not a CNCguitarwizard design file.")
    instrument = design.get("instrument")
    if instrument not in INSTRUMENT_OVERRIDES:
        raise CNCGuitarWizardError(f"Unknown instrument {instrument!r}.")
    design = upgrade_design(design)
    skipped: list[str] = []
    prototype = _known_values(
        Prototype001Parameters, design.get("prototype") or {}, skipped
    )
    machining = _known_values(
        MachiningParameters, design.get("machining") or {}, skipped
    )
    parameters = dataclasses.replace(
        Prototype001Parameters.for_instrument(instrument), **_coerce(prototype)
    )
    name = design.get("name")
    return LoadedDesign(
        name=name if isinstance(name, str) else "",
        parameters=parameters,
        machining=MachiningParameters(**_coerce(machining)),
        skipped=tuple(skipped),
    )


def _known_values(
    cls: type, values: dict[str, Any], skipped: list[str]
) -> dict[str, Any]:
    """Return the values that are fields of ``cls``, noting the others.

    A bridge or body shape keeps only its own kind's fields; one of a
    kind this version does not have is skipped whole (``name.kind``).
    """
    names = {field.name for field in dataclasses.fields(cls)}
    known: dict[str, Any] = {}
    for name, value in values.items():
        if name not in names:
            skipped.append(name)
            continue
        if isinstance(value, dict) and "kind" in value:
            spec_class = {**BRIDGE_KINDS, **BODY_SHAPE_KINDS}.get(value["kind"])
            if spec_class is None:
                skipped.append(f"{name}.kind")
                continue
            own = {"kind"} | {field.name for field in dataclasses.fields(spec_class)}
            skipped.extend(f"{name}.{key}" for key in value if key not in own)
            value = {key: item for key, item in value.items() if key in own}
        known[name] = value
    return known


def _editor_group(name: str) -> str | None:
    """Return which draggable group a body feature belongs to, if any.

    ``control`` (every "Control ..." feature: the cavity, its cover and
    screws, a layout's own pots, a control plate), ``switch`` (cavity,
    cover and shaft hole), ``pot:N`` (one pot hole, zero-based),
    ``pickup:neck`` / ``pickup:middle`` / ``pickup:bridge`` (a route and
    its screw recesses), ``battery`` (the battery box, its cover and
    screws), ``bolt:N`` (a neck bolt's ferrule and hole), ``jack``,
    ``pickguard`` (the guard and its screw spots in the body) and
    ``strap_guide`` (the flame strap guide's plate and screw pilots); the
    neck, its pocket and the bridge do not move.
    """
    if name.startswith("Control "):
        return "control"
    if name.startswith("Switch"):
        return "switch"
    if name.startswith("Battery"):
        return "battery"
    if name.startswith("Jack"):
        return "jack"
    if name.startswith("Pickguard"):
        return "pickguard"
    if name.startswith("Strap guide"):
        return "strap_guide"
    if name.startswith("Pot ") and name.endswith("shaft hole"):
        return f"pot:{int(name.split()[1]) - 1}"
    if name.startswith("Neck bolt "):
        return f"bolt:{int(name.split()[2]) - 1}"
    if name.startswith("Neck pickup"):
        return "pickup:neck"
    if name.startswith("Middle pickup"):
        return "pickup:middle"
    if name.startswith("Bridge pickup"):
        return "pickup:bridge"
    return None


REPAIR_FIRST = (
    "neck_bolts",
    "body_heel_relief_line",
    "heel_relief_points",
    "body_neck_plate",
    "strap_guide_offset",
    "strap_guide_y",
    "strap_guide_angle_degrees",
)
"""The settings ``repair_design`` tries first: those the editors' commonest
problems come from (a neck bolt with no room, a heel relief line or a neck
plate that does not fit, a strap guide placed where it does not), so a
feature in the way is moved before what it is in the way of is put back."""


def design_problems(payload: dict[str, Any]) -> list[str]:
    """Return what the body, headstock and inlay editors would show in red.

    Each editor's error and every problem its layout reports (a neck bolt
    with no room, a humbucker frame or lettering that does not fit), and
    each of the body's features that falls outside its outline.

    Args:
        payload: ``{"prototype": {...}}`` as for ``start_build``.

    Returns:
        The messages, in the editors' order; empty when all is well.
    """
    found: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ("error", "problem") and isinstance(item, str) and item:
                    found.append(item)
                elif key == "problems" and isinstance(item, list):
                    found.extend(str(problem) for problem in item if problem)
                else:
                    collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    body = body_editor_layout(payload)
    collect(body)
    found.extend(
        f"{name} falls outside the outline." for name in body.get("outside", [])
    )
    collect(headstock_editor_layout(payload))
    collect(inlay_editor_layout(payload))
    return found


def repair_design(
    payload: dict[str, Any], changes: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return which changed settings to put back so no editor shows red.

    A design put back in the page (or loaded) must not stay in error. The
    settings it changed from their defaults are tried at their defaults,
    those the commonest problems come from first (``REPAIR_FIRST``): one
    at a time, keeping each that leaves fewer problems; then, if some are
    left, more together in turn until none are (the defaults themselves
    show none); and last, any of those put back for nothing get the
    design's own value again.

    Args:
        payload: ``{"prototype": {...}}`` as for ``start_build``.
        changes: The changed settings as the form holds them, each
            ``{"set", "name", "default"}`` (``set`` ``"prototype"`` or a
            variant's, ``"prototype.body_shape"``; a variant's own kind with
            ``"kind": true``, its whole variant put back).

    Returns:
        ``{"problems", "reset", "remaining"}``: what was wrong, the indices
        into ``changes`` to put back (in order) and what is still wrong.
    """

    def applied(indices: list[int]) -> dict[str, Any]:
        result = payload
        for index in indices:
            result = _with_default(result, changes[index])
        return result

    problems = design_problems(payload)
    remaining = problems
    reset: list[int] = []
    order = sorted(
        range(len(changes)),
        key=lambda index: changes[index]["name"] not in REPAIR_FIRST,
    )
    # One at a time, whichever leaves fewer problems.
    while remaining:
        for index in order:
            if index in reset:
                continue
            left = design_problems(applied([*reset, index]))
            if len(left) < len(remaining):
                reset.append(index)
                remaining = left
                break
        else:
            break
    # More together, in turn, until none are left.
    for index in order:
        if not remaining:
            break
        if index not in reset:
            reset.append(index)
            remaining = design_problems(applied(reset))
    # The design's own value again where its default was not needed.
    if not remaining:
        for index in reversed(list(reset)):
            without = [other for other in reset if other != index]
            if not design_problems(applied(without)):
                reset = without
    return {"problems": problems, "reset": reset, "remaining": remaining}


def _with_default(payload: dict[str, Any], change: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``payload`` with one setting at its default."""
    copy: dict[str, Any] = json.loads(json.dumps(payload))
    target = copy
    for part in str(change["set"]).split("."):
        target = target.setdefault(part, {})
    if change.get("kind"):
        target[change["name"]] = {"kind": change["default"]}
    else:
        target[change["name"]] = change["default"]
    return copy


def body_editor_layout(payload: dict[str, Any]) -> dict[str, Any]:
    """Describe the body features for the web app's outline editor.

    Everything is in the body's own frame — X from the heel end, Y from
    the centerline — the frame ``YourDesignShape.control_points`` use, so
    the editor can draw the features and the points on one grid. Nothing
    is validated: the outline being drawn may not yet contain them. Each
    feature the editor may drag carries a ``group`` (see
    ``_editor_group``); dropping one moves the matching form fields.

    Args:
        payload: ``{"prototype": {...}}`` as for ``start_build``.

    Returns:
        ``{"heel_end", "scale_line", "samples_per_segment", "widening",
        "start_points", "templates", "polygons", "circles", "jack"}``, or
        ``{"error": message}``. ``mirrored``: the design is shown mirrored
        (a left-handed build); ``neck_through``: ``{"width"}`` of a
        neck-through's centre block (its glue lines at +-width / 2), or
        ``None``. ``scale_line`` is the bridge line's X on
        the centerline (a multiscale's mean scale). ``widening`` is the
        body's opening along the centreline (see
        ``body_shapes.widen_points``), which the editor applies to the
        drawn control points as Python does.
        ``templates`` maps a key to ``{"label", "shape", "values"}``, the
        shape as the form's JSON and ``values`` the other parameters the
        template sets (``BODY_TEMPLATE_VALUES``: the Alexi Hexed's look).
        ``polygons`` is a list of ``{"name", "role", "group", "points"}``
        with ``role`` one of ``neck``, ``pocket``,
        ``pickup``, ``bridge``, ``bridge_plate`` (what a bridge such as a
        Kahler covers on the top past its routes), ``top_control``,
        ``rear``, ``cover``, ``neck_plate`` (a bolt-on neck's plate on the
        back; its bolts then have no group, staying at its holes),
        ``strap_guide`` (the flame strap guide's plate on the back),
        ``contour_top`` (an arm contour), ``contour_back`` (a belly cut, a
        leg contour),
        ``tray`` and ``tray_wall`` (an epoxy tray and the walls it leaves) or
        ``plateau`` (a carved top's flat plateau, the top falling outside it);
        ``steps`` a stepped top's lines ``{"points", "automatic"}`` or
        ``None`` (see ``_steps_view``); ``circles`` a list of
        ``{"name", "group", "x", "y", "r"}``;
        ``jack`` ``{"group", "x", "y", "x2", "y2", "r", "cup",
        "reaches_controls"}`` (``cup`` a cup jack's counterbore ``{"x2",
        "y2", "r"}`` or ``None``; ``reaches_controls`` whether the bore
        ends in the control cavity); ``control``
        ``{"centre", "axis", "ends", "sides"}`` — the control cavity's
        centre, its long axis (a unit vector), the two ends of its cover
        (or the Tele plate) on that axis and its two sides square to it,
        the editor's stretch handles — or ``None`` without a control
        layout; ``pickups`` maps each fitted pickup's group to
        ``{"centre", "field"}``, the point it turns about and the angle
        field a turn changes, and ``bass_sign`` the side the bass strings
        are on (a counter-clockwise turn in the plan changes that field by
        the turn times ``bass_sign``); ``pickguard`` ``{"points",
        "automatic", "openings", "holes"}`` — the guard's control points
        (laid out automatically or drawn), its pickup and switch openings
        and its holes — or ``None``;
        ``arm_contour``, ``belly_cut`` and ``leg_contour`` ``{"points",
        "automatic"}`` — the lines where they start (see
        ``_contour_line``) — or ``None``, and ``heel_relief`` the same;
        ``outside`` the names of the features that fall outside the
        outline (as the editor checks it); ``problems``
        what the build refuses that is
        drawn anyway (``BodyLayout.problems``: a heel relief's corner line
        drawn as the U, neck bolts with no room where they are asked to go);
        ``frames`` each humbucker frame's ``{"position", "field", "turned",
        "adjusted", "problem", "points", "handles", "origin", "along", "across",
        "stretch", "openings", "holes"}`` — its points in its own frame (as
        its ``field`` holds them) and as handles in the editor's frame, the
        frame's origin and the directions of its own axes there (a handle
        dragged to ``p`` is at ``a = (p - origin)·along``, ``c`` the same
        across, narrowed by half the ``stretch``), and why it does not fit,
        or ``None``;
        ``round_points`` ``{"top", "back"}``: the shape's
        ``top_round_points`` / ``back_round_points`` (as its field holds
        them), each two the ends of a stretch of the edge a bevel all round
        leaves to the roundover;
        ``engraving`` the decorative engraving's lines, or ``None``;
        ``relief`` a relief engraving's shapes ``{"outline", "depth"}``
        (camo), empty for none;
        ``strap_guide`` ``{"x", "y", "angle"}`` — the flame strap guide's
        centre (``x`` from the heel end) and its bar's angle, where it is
        built — or ``None`` without one.
    """
    try:
        built = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
        # The editor works on the design as drawn (right-handed) and shows
        # it mirrored for a left-handed build.
        parameters = dataclasses.replace(built, handedness="right")
        layout = parameters.body_layout()
        neck = parameters.neck_outline()
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}
    heel_end = layout.heel_end

    def local(points: Any) -> list[list[float]]:
        return [[round(point.x - heel_end, 2), round(point.y, 2)] for point in points]

    def polygon(name: str, role: str, points: Any) -> dict[str, Any]:
        return {
            "name": name,
            "role": role,
            "group": _editor_group(name),
            "points": local(points),
        }

    through = parameters.neck_runs_through
    polygons: list[dict[str, Any]] = [
        polygon("Neck", "neck", neck.boundary),
        # A neck-through body has no pocket: the neck runs on through.
        *(
            []
            if through
            else [
                polygon(layout.neck_pocket.name, "pocket", layout.neck_pocket.outline)
            ]
        ),
        *(
            [polygon(access.name, "pocket", access.outline)]
            if (access := layout.truss_rod_access) is not None
            else []
        ),
    ]
    for pickup in (layout.neck_pickup, layout.middle_pickup, layout.bridge_pickup):
        if pickup is None:
            continue
        polygons.append(polygon(pickup.name, "pickup", pickup.outline))
    if layout.bridge_footprint:
        polygons.append(
            polygon("Bridge plate", "bridge_plate", layout.bridge_footprint)
        )
    for cavity in (*layout.extra_cavities, *layout.through_cavities):
        polygons.append(polygon(cavity.name, "bridge", cavity.outline))
    for cavity in layout.controls.top_cavities:
        polygons.append(polygon(cavity.name, "top_control", cavity.outline))
    # A carved top's plateau, and the contours, go under everything else on
    # the body (after the neck).
    if layout.carved_top is not None:
        polygons.insert(
            1, polygon("Carved top plateau", "plateau", layout.carved_top.plateau)
        )

    for offset, contour in enumerate(layout.contours, start=1):
        polygons.insert(
            offset,
            polygon(contour.name, f"contour_{contour.face}", contour.region()),
        )
    # An epoxy tray under everything but the neck too, its walls over it.
    if layout.epoxy_tray is not None:
        tray = [polygon("Epoxy tray", "tray", layout.epoxy_tray.outline)]
        tray += [
            polygon("Epoxy tray wall", "tray_wall", wall)
            for wall in layout.epoxy_tray.walls
        ]
        polygons[1:1] = tray
    for rear in (
        layout.control_cavity,
        layout.switch_cavity,
        layout.controls.battery_cavity,
        *layout.extra_rear_cavities,
    ):
        if rear is None:
            continue
        cover = rear.cover_recess
        polygons.append(polygon(cover.name, "cover", cover.outline))
        for pocket in rear.pockets:
            polygons.append(polygon(pocket.name, "rear", pocket.outline))
    circles: list[dict[str, Any]] = [
        {
            "name": hole.name,
            "group": _editor_group(hole.name),
            "x": round(hole.center_x - heel_end, 2),
            "y": round(hole.center_y, 2),
            "r": hole.diameter / 2.0,
        }
        for hole in layout.holes
    ]
    if layout.neck_plate:
        polygons.append(polygon("Neck plate", "neck_plate", layout.neck_plate))
    strap_guide: dict[str, float] | None = None
    if layout.strap_guide is not None:
        guide = layout.strap_guide
        polygons.append(polygon("Strap guide plate", "strap_guide", guide.outline))
        strap_guide = {
            "x": round(guide.centre.x - heel_end, 1),
            "y": round(guide.centre.y, 1),
            "angle": round(guide.angle_degrees, 1),
        }
    circles += [
        {
            "name": hole.name,
            # A neck plate's bolts stay at its holes.
            "group": (
                None
                if layout.neck_plate and hole.name.startswith("Neck bolt ")
                else _editor_group(hole.name)
            ),
            "x": round(hole.center_x - heel_end, 2),
            "y": round(hole.center_y, 2),
            "r": hole.diameter / 2.0,
            "rear": True,
        }
        for hole in (*layout.rear_holes, *layout.controls.back_marks)
    ]
    circles += [
        {
            "name": hole.name,
            "group": _editor_group(hole.name),
            "x": round(hole.center_x - heel_end, 2),
            "y": round(hole.center_y, 2),
            "r": hole.diameter / 2.0,
        }
        for hole in layout.controls.top_marks
    ]
    mounting = layout.bridge_mounting
    circles += [
        {
            "name": "Pivot stud",
            "group": None,
            "x": round(pivot.x - heel_end, 2),
            "y": round(pivot.y, 2),
            "r": mounting.pivot_hole_diameter / 2.0,
        }
        for pivot in mounting.pivot_holes
    ]
    control: dict[str, Any] | None = None
    controls = layout.controls
    if controls.control_centre is not None and controls.control_axis is not None:
        centre, axis = controls.control_centre, controls.control_axis
        across = Point2D(-axis.y, axis.x)

        def handles(direction: Point2D) -> list[list[float]]:
            reach = [
                (p.x - centre.x) * direction.x + (p.y - centre.y) * direction.y
                for p in controls.covers[0].outline
            ]
            return local(
                Point2D(centre.x + direction.x * r, centre.y + direction.y * r)
                for r in (min(reach), max(reach))
            )

        control = {
            "centre": local((centre,))[0],
            "axis": [round(axis.x, 6), round(axis.y, 6)],
            "ends": handles(axis),
            "sides": handles(across),
        }
    control_outlines = [
        *((controls.control_cavity.cavity.outline,) if controls.control_cavity else ()),
        *(top.outline for top in controls.top_cavities if top.name == "Control cavity"),
    ]
    # The features outside the outline, as the editor finds them: contours
    # follow the outline, and the pocket may open onto the horn gap (only
    # its tail wall must be in wood).
    body = [Point2D(x, y) for x, y in local(layout.outline.points)]
    outside = {
        polygon["name"]
        for polygon in polygons
        if polygon["role"] not in ("neck", "plateau", "tray", "tray_wall")
        and not polygon["role"].startswith("contour")
        and any(
            not point_in_polygon(Point2D(x, y), body)
            for x, y in polygon["points"]
            if polygon["role"] != "pocket" or x > -1.0
        )
    } | {
        circle["name"]
        for circle in circles
        if not point_in_polygon(Point2D(circle["x"], circle["y"]), body)
    }
    return {
        "heel_end": round(heel_end, 2),
        "mirrored": built.left_handed,
        "neck_through": (
            {"width": round(parameters.neck_through_block_width(layout), 2)}
            if parameters.neck_joint == "neck_through"
            else None
        ),
        "scale_line": round(parameters.centre_scale, 3),
        "samples_per_segment": OUTLINE_SAMPLES_PER_SEGMENT,
        "widening": parameters.body_widening_amount(),
        "start_points": [list(point) for point in YOUR_DESIGN_START_POINTS],
        "templates": {
            key: {
                "label": label,
                "shape": _jsonable(shape),
                "values": _jsonable(BODY_TEMPLATE_VALUES.get(key, {})),
            }
            for key, (label, shape) in YOUR_DESIGN_TEMPLATES.items()
        },
        "polygons": polygons,
        "circles": circles,
        "outside": sorted(outside),
        "jack": _jack_view(layout.jack_hole, heel_end, control_outlines),
        "control": control,
        "pickups": {
            f"pickup:{position}": {
                "centre": [round(x - heel_end, 2), 0.0],
                "field": f"body_{position}_pickup_angle",
            }
            for position, x in layout.pickup_centres
        },
        "bass_sign": parameters.bass_sign,
        "steps": _steps_view(parameters, layout, local),
        "round_points": {
            face: [list(point) for point in getattr(parameters.body_shape, field)]
            for face, field in (
                ("top", "top_round_points"),
                ("back", "back_round_points"),
            )
        },
        "pickguard": (
            {
                "points": _marked(
                    local(layout.pickguard.control_points), layout.pickguard.corners
                ),
                "automatic": layout.pickguard.automatic,
                # As cut: meeting the pickup frames on it or beside it.
                "outline": local(layout.pickguard.plate.outline),
                "openings": [
                    local(slot.outline) for slot in layout.pickguard.plate.slots
                ],
                "holes": [
                    {
                        "x": round(hole.center_x - heel_end, 2),
                        "y": round(hole.center_y, 2),
                        "r": hole.diameter / 2.0,
                    }
                    for hole in layout.pickguard.plate.holes
                ],
            }
            if layout.pickguard is not None
            else None
        ),
        "frames": [
            {
                "position": frame.position,
                "field": f"body_{frame.position}_frame_points",
                "turned": frame.turned,
                "adjusted": frame.adjusted,
                "problem": frame.problem,
                "points": [list(point) for point in frame.points],
                "handles": _frame_handles(frame, local),
                "origin": [
                    round(frame.placing.origin.x - heel_end, 3),
                    round(frame.placing.origin.y, 3),
                ],
                "along": list(frame.placing.along),
                "across": list(frame.placing.across),
                "stretch": frame.placing.stretch,
                "openings": [local(slot.outline) for slot in frame.plate.slots],
                "holes": [
                    {
                        "x": round(hole.center_x - heel_end, 2),
                        "y": round(hole.center_y, 2),
                        "r": hole.diameter / 2.0,
                    }
                    for hole in frame.plate.holes
                ],
            }
            for frame in layout.pickup_frames
        ],
        "arm_contour": _contour_line(
            parameters, layout.contours, local, "Arm contour", "arm_contour_points"
        ),
        "belly_cut": _contour_line(
            parameters, layout.contours, local, "Belly cut", "belly_cut_points"
        ),
        "leg_contour": _contour_line(
            parameters, layout.contours, local, "Leg contour", "leg_contour_points"
        ),
        "heel_relief": _contour_line(
            parameters, layout.contours, local, "Heel relief", "heel_relief_points"
        ),
        # What the build refuses that is drawn anyway, and why.
        "problems": list(layout.problems),
        "engraving": (
            [local(line) for line in layout.engraving.lines]
            if layout.engraving is not None
            else None
        ),
        # A relief's shapes and their depths (camo).
        "relief": (
            [
                {"outline": local(shape.outline), "depth": shape.depth}
                for shape in layout.engraving.pockets
            ]
            if layout.engraving is not None
            else []
        ),
        "strap_guide": strap_guide,
    }


def _jack_view(
    jack: JackHole | None,
    heel_end: float,
    control_outlines: list[tuple[Point2D, ...]],
) -> dict[str, Any] | None:
    """Return the jack bore for the body editor, ``None`` on a control plate.

    ``reaches_controls`` says whether the bore ends in a control cavity.
    """
    if jack is None:
        return None
    radians = math.radians(jack.direction_degrees)
    jack_end = Point2D(
        jack.start_x + jack.depth * math.cos(radians),
        jack.start_y + jack.depth * math.sin(radians),
    )
    return {
        "group": "jack",
        "x": round(jack.start_x - heel_end, 2),
        "y": round(jack.start_y, 2),
        "x2": round(jack.start_x - heel_end + jack.depth * math.cos(radians), 2),
        "y2": round(jack.start_y + jack.depth * math.sin(radians), 2),
        "r": jack.diameter / 2.0,
        "cup": (
            {
                "x2": round(
                    jack.start_x - heel_end + jack.cup_depth * math.cos(radians), 2
                ),
                "y2": round(jack.start_y + jack.cup_depth * math.sin(radians), 2),
                "r": jack.cup_diameter / 2.0,
            }
            if jack.cup_diameter
            else None
        ),
        "reaches_controls": any(
            point_in_polygon(jack_end, outline) for outline in control_outlines
        ),
    }


STEP_HANDLE_TOLERANCE = 1.5
"""How far an automatic step's line may stray from its handles' straight
lines, in mm: the fewer handles the editor shows it with."""


def _marked(points: list[list[float]], corners: Sequence[bool]) -> list[list[Any]]:
    """Return a drawing's editor points, its sharp corners marked as drawn
    (see ``spline.CORNER``); ``corners`` empty for none."""
    return [
        [*point, CORNER] if sharp else point
        for point, sharp in zip(points, corners or (False,) * len(points), strict=True)
    ]


def _frame_handles(
    frame: PickupFrame, local: Callable[[Sequence[Point2D]], list[list[float]]]
) -> list[list[Any]]:
    """Return a pickup frame's handles in the editor, its corners marked."""
    points, corners = drawn_points(frame.points)
    return _marked(
        local([frame.placing.to_model(point.x, point.y) for point in points]), corners
    )


def _steps_view(
    parameters: Prototype001Parameters, layout: Any, local: Any
) -> dict[str, Any] | None:
    """Return a stepped top's lines for the editor, or ``None``.

    ``{"points", "automatic"}``: each step's points (straight lines
    between them, the outermost first) — the shape's drawn
    ``step_points`` as widened, a point rounded through marked as drawn,
    or the automatic steps simplified to handles within
    ``STEP_HANDLE_TOLERANCE``.
    """
    steps = layout.stepped_top
    if steps is None:
        return None
    shape = widened_shape(parameters.body_shape, parameters.body_widening_amount())
    if shape.step_points:
        return {
            "points": [[list(point) for point in line] for line in shape.step_points],
            "automatic": False,
        }
    return {
        "points": [
            local(simplified(boundary, STEP_HANDLE_TOLERANCE))
            for boundary in steps.boundaries
        ],
        "automatic": True,
    }


CONTOUR_HANDLES = 7
"""How many handles an automatic contour's line gets in the editor."""


def _contour_line(
    parameters: Prototype001Parameters,
    contours: Any,
    local: Any,
    name: str,
    field: str,
) -> dict[str, Any] | None:
    """Return where a contour (``name``) starts, for the editor, or ``None``.

    ``{"points", "automatic"}``: the shape's drawn points (``field``, as
    widened for the instrument); or, for an automatic contour,
    ``CONTOUR_HANDLES`` points spread evenly along its inner edge (its
    ends on the body's edge) and ``"line"``, that edge itself, drawn as it
    is cut (a heel relief by the pocket follows the pocket's corners,
    which a curve through the handles would round off).
    """
    contour = next((c for c in contours if c.name == name), None)
    if contour is None:
        return None
    shape = widened_shape(parameters.body_shape, parameters.body_widening_amount())
    drawn = getattr(shape, field)
    if drawn:
        return {"points": [list(point) for point in drawn], "automatic": False}
    inner = contour.inner_edge()
    # How far along the edge each of its points is.
    along = [0.0]
    for a, b in itertools.pairwise(inner):
        along.append(along[-1] + math.hypot(b.x - a.x, b.y - a.y))

    def nearest(distance: float) -> int:
        # The edge's point nearest that far along it.
        return min(range(len(inner)), key=lambda i: abs(along[i] - distance))

    picks = [
        nearest(along[-1] * k / (CONTOUR_HANDLES - 1)) for k in range(CONTOUR_HANDLES)
    ]
    return {
        "points": local(inner[i] for i in picks),
        "automatic": True,
        "line": local(inner),
    }


def inlay_editor_layout(payload: dict[str, Any]) -> dict[str, Any]:
    """Describe the fret markers for the web app's inlay editor.

    Drawn as built right-handed (the bass edge at -Y), shown mirrored for a
    left-handed build. The editor shows the first marker's fret space and
    edits its shape as ``inlay_points`` (see ``InlayLayout.custom_points``).

    Args:
        payload: ``{"prototype": {...}}`` as for ``start_build``.

    Returns:
        ``{"fret", "front", "back", "nut_half", "final_half",
        "final_position", "bass_sign", "mirrored", "custom", "points",
        "limits", "markers", "holes", "frets", "runes", "problem"}`` or
        ``{"error": message}``: the
        first marker's fret, its fret space from ``front`` to ``back`` (mm
        from the nut), the board's half-width at the nut and at the last
        fret (``final_position`` from the nut), the marker's shape as
        ``[along, across]`` points (the drawn one, or the style's own at
        that fret), ``limits`` (``along`` from and to, ``across`` either
        side: ``custom_limits``) inside which a drawn corner fits every
        marker, every marker's outline, the wood left inside any (``holes``,
        an ankh's loop) and every fret's line for the board's preview,
        ``runes`` each marker fret's rune
        ``{"fret", "rune"}`` (nut first, ``inlay_runes`` starting over; empty
        but for the ``runes`` style), and ``problem``, why the markers cannot
        be cut as drawn (``None`` when they can).
    """
    try:
        built = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
        parameters = dataclasses.replace(built, handedness="right")
        surface = parameters.fretboard_surface()
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}
    positions = {
        fret.number: fret.distance_from_nut
        for fret in FretCalculator.calculate(
            surface.scale_length, surface.fret_count, surface.frets_per_octave
        )
    }
    single, double = parameters.marker_frets()
    frets = sorted((*single, *double))
    if not frets:
        return {"error": "No fret has a marker (inlay_single_marker_frets)."}
    first = frets[0]
    final = positions[surface.fret_count]
    problem: str | None = None
    markers: list[list[list[float]]] = []
    holes: list[list[list[float]]] = []
    # As drawn, a round corner marked (see InlayLayout.custom_points).
    points: list[list[Any]] = [
        [float(point[0]), float(point[1]), *point[2:]]
        for point in parameters.inlay_points
        if len(point) in (2, 3)
    ]
    try:
        layout = parameters.inlay_design(surface)
        markers = [
            [[round(p.x, 2), round(p.y, 2)] for p in marker.outline]
            for marker in layout.markers
        ]
        holes = [
            [[round(p.x, 2), round(p.y, 2)] for p in hole]
            for marker in layout.markers
            for hole in marker.holes
        ]
        points = [list(point) for point in layout.editable_points()]
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        problem = str(error)
    if not points:
        points = [[along, across] for along, across in DEFAULT_CUSTOM_POINTS]
    skew = surface.skew

    half_at = surface.half_width_at

    (low, high), across = custom_limits(surface, frets)
    # Each marker fret's rune, nut first (inlay_runes, starting over), for
    # the editor to change them.
    names = parameters.inlay_runes or DEFAULT_RUNES
    runes = (
        [
            {"fret": fret, "rune": names[index % len(names)]}
            for index, fret in enumerate(frets)
        ]
        if parameters.inlay_style == "runes"
        else []
    )

    def fret_line(position: float) -> list[list[float]]:
        half = half_at(position)
        return [
            [round(position + skew.at(position) * y, 2), round(y, 2)]
            for y in (-half, half)
        ]

    return {
        "fret": first,
        "front": round(0.0 if first == 1 else positions[first - 1], 3),
        "back": round(positions[first], 3),
        "nut_half": surface.nut_width / 2.0,
        "final_half": surface.last_fret_width / 2.0,
        "final_position": round(final, 3),
        "bass_sign": parameters.marker_bass_sign,
        "mirrored": built.left_handed,
        "custom": parameters.inlay_style == "custom",
        "points": points,
        "limits": {"along": [low, high], "across": across},
        "markers": markers,
        "holes": holes,
        "frets": [fret_line(0.0)]
        + [fret_line(positions[n]) for n in range(1, surface.fret_count + 1)],
        "runes": runes,
        "problem": problem,
    }


def headstock_editor_layout(payload: dict[str, Any]) -> dict[str, Any]:
    """Describe the headstock for the web app's edge editor.

    Coordinates are the model's: X is negative past the nut (the
    headstock extends that way), Y from the centerline. Edges are lists of
    ``[distance from the nut, half-width]`` ending at the tip, the form
    ``headstock_bass_edge`` / ``headstock_treble_edge`` take.

    Args:
        payload: ``{"prototype": {...}}`` as for ``start_build``.

    Returns:
        ``{"nut_half_width", "bass_sign", "min_edge_distance",
        "hole_clearance", "sample_step", "start_edges": {"bass", "treble"},
        "holes"}`` or ``{"error": message}``. ``start_edges`` are the
        fitted outline's edges, sampled halfway to the shoulder, at the
        shoulder, at seven points along the taper and at the tip (ten
        handles a side); ``holes`` is a list of ``{"side", "x", "y", "r"}``
        in the order ``tuner_hole_points`` takes them, the least wood
        between two of them ``hole_clearance``; ``lettering``
        the headstock's lettering (see ``_headstock_lettering``), or ``None``;
        ``engraving`` the lines drawn on its face (see
        ``_headstock_drawn_engraving``), or ``None``; ``volute`` the volute
        on its back to draw (see ``_volute_drawing``), or ``None``; ``root``
        a flat headstock's drawn root (see ``_root_drawing``), or ``None``.
    """
    try:
        built = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
        # As drawn (right-handed), shown mirrored for a left-handed build.
        parameters = dataclasses.replace(built, handedness="right")
        try:
            fitted, _ = dataclasses.replace(
                parameters, headstock_outline="fitted"
            ).headstock_design()
        except CNCGuitarWizardError:
            # A drawing stands on its own; the fitted outline Start over
            # brings back may not (a headstock_length far past the
            # tuners), so the editor starts from the drawing meanwhile.
            fitted = parameters.headstock_plan()
            if not fitted.is_drawn:
                raise
        centres = parameters.tuner_centres()
        # A locking nut wider than the neck is refused here too.
        nut = _nut_drawing(parameters)
        lettering = _headstock_lettering(built)
        engraving = _headstock_drawn_engraving(built)
        truss_cover = _truss_cover_drawing(parameters)
        volute = _volute_drawing(parameters)
        root_drawing = _root_drawing(parameters)
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}
    root = parameters.headstock_root_length
    stations = [root / 2.0]
    stations += [root + (fitted.length - root) * step / 8.0 for step in range(8)]
    stations.append(fitted.length)
    start_edges = {
        side: [
            [round(distance, 1), round(fitted.half_width_at(distance, side), 1)]
            for distance in stations
        ]
        for side in ("bass", "treble")
    }
    return {
        "lettering": lettering,
        "engraving": engraving,
        "truss_cover": truss_cover,
        "volute": volute,
        "root": root_drawing,
        "nut": nut,
        "mirrored": built.left_handed,
        "nut_half_width": parameters.nut_width / 2.0,
        "bass_sign": fitted.bass_sign,
        "min_edge_distance": parameters.tuner_edge_offset,
        "hole_clearance": parameters.tuner_hole_clearance,
        "sample_step": 2.5,
        "start_edges": start_edges,
        "holes": [
            {
                "side": side,
                "x": round(x, 2),
                "y": round(y, 2),
                "r": parameters.tuner_hole_diameter / 2.0,
            }
            for side, x, y in centres
        ],
    }


VOLUTE_LINE_FIELDS = {
    "crest": "headstock_volute_points",
    "headstock": "headstock_volute_headstock_points",
    "neck": "headstock_volute_neck_points",
}
"""The setting each of a drawn volute's lines is kept in."""

DRAWN_LINE_ROOM = 1.0
"""How far, in mm, the editors keep a drawn line's point inside its limits
and clear of the lines either side of it."""


def _line_drawing(
    parameters: Prototype001Parameters,
    fields: dict[str, str],
    halves: dict[str, tuple[DrawnPoint, ...]],
    whole: dict[str, tuple[Point2D, ...]],
) -> dict[str, dict[str, Any]]:
    """Return lines drawn across the neck's back, for an editor to draw.

    Each ``{"field", "points", "whole", "drawn", "line"}``: the setting it
    is kept in; the points it holds, ``[along, across]`` seen from behind
    (along from its origin toward the headstock), half the line from the
    centre line out or, its sides differing, the whole of it from the -Y
    side to the +Y side (``"whole"``, see ``drawn_whole``), a ``"corner"``
    mark kept, where drawing starts while none are drawn; whether they are
    drawn; the whole line in the model frame.
    """
    return {
        name: {
            "field": field,
            "points": [list(point) for point in halves[name]],
            "whole": drawn_whole(halves[name]),
            "drawn": bool(getattr(parameters, field)),
            "line": [[round(p.x, 2), round(p.y, 2)] for p in whole[name]],
        }
        for name, field in fields.items()
    }


def _volute_drawing(parameters: Prototype001Parameters) -> dict[str, Any] | None:
    """Return the volute for the headstock editor to draw, or ``None``.

    ``{"style", "lines", "outline"}``: its style; for a drawn one its three
    lines, ``{"crest", "headstock", "neck"}`` each ``{"field", "points",
    "drawn", "line"}`` (the setting it is kept in; the points it holds,
    half the line seen from behind, ``[behind the nut, across]`` from the
    centre line out, a ``"corner"`` mark kept, where drawing starts while
    none are drawn; whether they are drawn; the whole line in the model
    frame); for the rounded arrow its outline seen from behind (where it
    adds a tenth of a millimetre or more), to show, no handles. ``None``
    without a volute.
    """
    volute = parameters.volute(parameters.neck_outline())
    if volute is None:
        return None
    if parameters.headstock_volute_style == "drawn":
        whole = {
            "crest": volute.crest,
            "headstock": volute.headstock_end,
            "neck": volute.neck_end,
        }
        return {
            "style": "drawn",
            "origin": 0.0,
            "lines": _line_drawing(
                parameters,
                VOLUTE_LINE_FIELDS,
                parameters.volute_lines(volute.half_width),
                whole,
            ),
            "outline": None,
            # Each point kept clear of the lines either side (see
            # _transition_drawing).
            "limits": list(_root_limits(parameters)),
            "order": ["neck", "crest", "headstock"],
            "toward": -1.0,
            "treble": -parameters.bass_sign,
        }
    # The arrow's edge: down each side, where it adds a tenth of a mm.
    edge: list[list[float]] = []
    for step in range(81):
        x = volute.point - (volute.point + volute.length) * step / 80.0
        across = [
            y / 4.0
            for y in range(round(volute.half_width * 4) + 1)
            if volute.extra(x, y / 4.0) >= 0.1
        ]
        if across:
            edge.append([round(x, 2), max(across)])
    outline = edge + [[x, -y] for x, y in reversed(edge)]
    return {"style": "arrow", "lines": None, "outline": outline}


def _transition_drawing(
    parameters: Prototype001Parameters,
    style_field: str,
    fields: dict[str, str],
    halves: dict[str, tuple[DrawnPoint, ...]],
    origin: float,
    limits: tuple[float, float],
    toward: float,
) -> dict[str, Any]:
    """Return a joint drawn as two lines for an editor to draw.

    ``{"origin", "style", "style_field", "lines", "limits", "order",
    "toward", "treble"}``: where its lines' points are measured from (see
    ``_line_drawing``), its style setting's value ("smooth" until a line
    is drawn, which makes it "drawn") and name, its two lines, ``{"flat",
    "neck"}``, and where along the neck their points may go (``limits``,
    the model's ``x``), the lines in order from the neck's side to the
    block's, which ``toward`` is along the neck (1 the body, -1 the
    headstock), so an editor keeps each point clear of the line either
    side of it; and which side the treble is (1 the +Y side, -1 the -Y),
    the side a line's two sides are made alike as.
    """
    whole = {name: drawn_back_line(points, origin) for name, points in halves.items()}
    return {
        "origin": round(origin, 4),
        "style": getattr(parameters, style_field),
        "style_field": style_field,
        "lines": _line_drawing(parameters, fields, halves, whole),
        "limits": [round(limits[0], 2), round(limits[1], 2)],
        "order": ["neck", "flat"],
        "toward": toward,
        "treble": -parameters.bass_sign,
    }


def _root_limits(parameters: Prototype001Parameters) -> tuple[float, float]:
    """Return where a line drawn on the back behind the nut may go along
    the neck, a little inside the model's own limits: short of the
    headstock's tip (``DRAWN_JOINT_TIP_CLEARANCE``) and of the first fret.
    A drawing that does not stand yet (its edges dragged across each
    other) is as long as ``headstock_length`` meanwhile, so the editor
    still opens on it.
    """
    scale = parameters.neck_outline().scale_length
    first = FretCalculator.calculate(scale, 1)[-1].distance_from_nut
    try:
        length = parameters.headstock_plan().length
    except CNCGuitarWizardError:
        length = parameters.headstock_length
    reach = length - DRAWN_JOINT_TIP_CLEARANCE
    return -reach + DRAWN_LINE_ROOM, first - DRAWN_LINE_ROOM


def _root_drawing(parameters: Prototype001Parameters) -> dict[str, Any] | None:
    """Return the headstock's root, how the neck's back runs into it, for
    the headstock editor; ``None`` with the volute on (its lines are drawn
    instead) or no headstock.

    Its two lines, drawn or (smooth) where drawing them starts: see
    ``_transition_drawing``.
    """
    if parameters.headstock_pointed_volute or parameters.headless:
        return None
    half_width = parameters.neck_outline().nut_width / 2.0
    return _transition_drawing(
        parameters,
        "headstock_root_style",
        ROOT_LINE_SETTINGS,
        parameters.root_lines(half_width),
        0.0,
        _root_limits(parameters),
        -1.0,
    )


BUILDS_KEPT = 4
"""How many designs' builds the drawings keep (``_built``)."""


def _built(parameters: Prototype001Parameters, *, wired: bool) -> Prototype001Geometry:
    """Return ``parameters`` built, the last few designs' builds kept.

    A page shown asks for one design's drawings several times over (the
    neck's, the heel editor's, the settings' pictures, the back's), each
    a build of a second or more on a phone: built once, the others are
    quick. The geometry is immutable, so a kept one is safely shared.

    Args:
        parameters: The design.
        wired: As for ``Prototype001Parameters.build``.

    Returns:
        The design's geometry.
    """
    try:
        hash(parameters)
    except TypeError:  # a value the form never sends (a list): built afresh
        return parameters.build(wired=wired)
    return _kept_build(parameters, wired)


@functools.lru_cache(maxsize=BUILDS_KEPT)
def _kept_build(
    parameters: Prototype001Parameters, wired: bool
) -> Prototype001Geometry:
    return parameters.build(wired=wired)


HEEL_EDITOR_REACH = 130.0
"""How far ahead of the heel's block the heel editor shows the neck, in mm."""


def heel_editor_layout(payload: dict[str, Any]) -> dict[str, Any]:
    """Describe the heel's back for the web app's heel editor.

    Coordinates are the model's: X from the nut toward the body, Y from
    the centre line. The neck's back is seen from behind, from
    ``HEEL_EDITOR_REACH`` ahead of the heel's block to the heel's end.

    Args:
        payload: ``{"prototype": {...}}`` as for ``start_build``.

    Returns:
        ``{"outline", "block", "heel_end", "twelfth", "heel", "problem"}``
        or ``{"error": message}``: the back's outline there (a closed list
        of ``[x, y]``), where the block's flat begins (the drawn lines'
        origin), the heel's end and the 12th fret's X (the drawn lines lie
        between the fret and the block), the heel's two lines, drawn or
        (smooth) where drawing them starts (see ``_transition_drawing``),
        and why the design does not build, or ``None``: the lines are
        drawn as they are set even so (the neck as with a smooth heel), so
        they can be mended.
    """
    try:
        built = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
        parameters = dataclasses.replace(built, handedness="right")
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}
    problem = None
    try:
        geometry = _built(parameters, wired=False)
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        problem = f"{type(error).__name__}: {error}"
        try:
            smooth = dataclasses.replace(parameters, heel_root_style="smooth")
            geometry = _built(smooth, wired=False)
        except (CNCGuitarWizardError, TypeError, ValueError):
            return {"error": problem}
    surface = geometry.neck_surface
    neck = surface.neck_outline
    block = neck.last_fret_position - surface.heel_flat_start_offset
    rows = [row for row in surface.mesh.rows if row[0].x >= block - HEEL_EDITOR_REACH]
    outline = [[round(row[0].x, 2), round(row[0].y, 2)] for row in rows] + [
        [round(row[-1].x, 2), round(row[-1].y, 2)] for row in reversed(rows)
    ]
    twelfth = surface.station_positions_reference(12)
    try:
        drawing = _transition_drawing(
            parameters,
            "heel_root_style",
            HEEL_LINE_SETTINGS,
            parameters.heel_lines(neck.heel_width / 2.0),
            block,
            (twelfth + DRAWN_LINE_ROOM, block),
            1.0,
        )
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}
    return {
        "outline": outline,
        "block": round(block, 2),
        "heel_end": round(neck.last_fret_position + neck.heel_length, 2),
        "twelfth": round(twelfth, 2),
        "heel": drawing,
        "problem": problem,
    }


BACK_VIEW_PAST = 12.0
"""How far past either end of what is drawn on the back its view runs, in
mm."""


def back_view(payload: dict[str, Any], where: str = "nut") -> dict[str, Any]:
    """Return the back as it is lofted, seen from behind and above.

    To see while drawing on the back what it looks like: round the nut
    the volute, or the headstock's root with the volute off (the
    headstock editor), round the heel its runout (Design › Neck). The back
    as FreeCAD lofts it (``FreeCADScriptExporter.neck_loft_rows``), from a
    little past one end of the lines to a little past the other (the
    heel's end), drawn by ``render.svg.render_volute_view_svg``.

    Args:
        payload: ``{"prototype": {...}}`` as for ``start_build``.
        where: ``"nut"`` or ``"heel"``.

    Returns:
        ``{"svg": ...}``, ``{"svg": None}`` with nothing to draw there (no
        headstock), or ``{"error": message}``.
    """
    try:
        built = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
        # As drawn (right-handed), as the editors show it.
        geometry = _built(dataclasses.replace(built, handedness="right"), wired=False)
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}
    surface = geometry.neck_surface
    neck = surface.neck_outline
    volute = geometry.volute
    if where == "heel":
        block = neck.last_fret_position - surface.heel_flat_start_offset
        lines = built.heel_lines(neck.heel_width / 2.0)
        xs = [p.x for points in lines.values() for p in drawn_back_line(points, block)]
        span = (min(xs), neck.last_fret_position + neck.heel_length - BACK_VIEW_PAST)
    elif volute is not None and volute.drawn:
        span = (
            min(point.x for point in volute.headstock_end),
            max(point.x for point in volute.neck_end),
        )
    elif volute is not None:
        span = (-volute.length, volute.point)
    elif built.headless:
        return {"svg": None}
    else:
        lines = built.root_lines(neck.nut_width / 2.0)
        xs = [p.x for points in lines.values() for p in drawn_back_line(points)]
        span = (min(xs), max(xs))
    start, end = span[0] - BACK_VIEW_PAST, span[1] + BACK_VIEW_PAST
    rows = FreeCADScriptExporter.neck_loft_rows(
        surface,
        geometry.headstock,
        geometry.joint_fillet_radius,
        geometry.volute,
    )
    near = [row for row in rows if start <= row[0].x <= end]
    if where == "heel":
        return {
            "svg": render_volute_view_svg(
                near, 1.0, "The heel seen from behind and above, as it is lofted"
            )
        }
    return {"svg": render_volute_view_svg(near)}


def _truss_cover_drawing(parameters: Prototype001Parameters) -> dict[str, Any] | None:
    """Return the truss-rod cover for the headstock editor, or ``None``.

    ``{"outline", "screws", "screw_radius", "trough", "back", "length",
    "width", "style", "corners", "screw_points", "problem"}``: the cover's
    outline and screw centres and the trough under it (model frame, as
    drawn); its nut end's X, its size and style; its corners and screws as
    ``truss_rod_cover_points`` / ``_screws`` would hold them (a drawn
    cover's own, its round corners marked), for the editor to move one or
    add one (a drawn, ``custom``, cover from then on); and why it does not
    fit, or ``None``. Drawn even where it does
    not fit, so it can be mended. ``None`` where there is no cover (a heel
    adjuster, say).
    """
    try:
        channel = parameters.truss_rod(parameters.neck_outline())
        placed = parameters.truss_rod_cover_outline(channel)
    except (CNCGuitarWizardError, TypeError, ValueError):
        return None
    if placed is None:
        return None
    outline, screws = placed
    length, width = parameters.truss_rod_cover_size(channel)
    shape = truss_rod_cover_shape(
        parameters.truss_rod_cover_style,
        length,
        width,
        parameters.truss_rod_cover_points,
        parameters.truss_rod_cover_screws,
    )
    editable, screw_points = editable_cover_points(shape, length, width)
    # A drawn cover's corners as drawn: a round one marked, not the curve
    # through it.
    drawn = parameters.truss_rod_cover_style == "custom"
    corners = (parameters.truss_rod_cover_points or editable) if drawn else editable
    try:
        plan, tuners = parameters.headstock_design()
        problem = parameters.truss_rod_cover_problem(channel, plan, tuners)
    except (CNCGuitarWizardError, TypeError, ValueError):
        problem = None  # the headstock's own problem is shown instead
    return {
        "outline": [[round(p.x, 2), round(p.y, 2)] for p in outline],
        "screws": [[round(p.x, 2), round(p.y, 2)] for p in screws],
        "screw_radius": SCREW_CLEARANCE / 2.0,
        "trough": [[round(p.x, 2), round(p.y, 2)] for p in channel.adjuster_boundary],
        "back": round(max(p.x for p in channel.adjuster_boundary) - 0.5, 3),
        "length": round(length, 2),
        "width": round(width, 2),
        "style": parameters.truss_rod_cover_style,
        "corners": [list(point) for point in corners],
        "screw_points": [list(point) for point in screw_points],
        "problem": problem,
    }


def _nut_drawing(parameters: Prototype001Parameters) -> dict[str, Any]:
    """Return the nut for the headstock editor (model frame).

    ``{"nut", "board", "zero_fret", "locking"}``: the nut's outline; the
    fretboard running on past the nut line (a slotted or zero-fret nut's,
    a locking nut's shelf), or ``None``; a zero fret's line on the nut
    line, or ``None``; whether it is a locking nut.
    """
    nut = parameters.locking_nut_placed()
    lean = parameters.fret_skew.at(0.0)
    half = parameters.nut_width / 2.0

    def quad(front: float, back: float, reach: float) -> list[list[float]]:
        return [
            [round(lean * y + x, 2), round(y, 2)]
            for x, y in ((front, -reach), (front, reach), (back, reach), (back, -reach))
        ]

    if nut is None:
        return {
            "nut": quad(0.0, -parameters.nut_seat_length(), half),
            "board": None,
            "zero_fret": None,
            "locking": False,
        }
    return {
        "nut": quad(
            nut.front,
            nut.front - nut.spec.depth,
            nut.spec.width / 2.0 if nut.is_locking else half,
        ),
        "board": quad(0.0, -nut.seat_length, half) if nut.on_fretboard else None,
        "zero_fret": (
            [[round(-lean * half, 2), -half], [round(lean * half, 2), half]]
            if nut.zero_fret
            else None
        ),
        "locking": nut.is_locking,
    }


def _headstock_lettering(parameters: Prototype001Parameters) -> dict[str, Any] | None:
    """Return the headstock's lettering for its editor, or ``None`` without any.

    ``{"lines", "centre", "problem"}``: its strokes and centre (model
    frame, as the editor draws it) and why it does not fit, or ``None``.
    Drawn even where it does not fit, so it can be dragged clear. For a
    left-handed build, the lettering as built mirrored back into the
    drawn frame: the editor shows that frame mirrored, so the text reads
    the right way round there, and its centre is the one the form keeps.
    """
    text = parameters.headstock_engraving_text.strip()
    if not text:
        return None
    outline_problem: str | None = None
    tuners: TunerLayout | None = None
    try:
        plan, tuners = parameters.headstock_design()
    except CNCGuitarWizardError as error:
        # A drawn outline that no longer fits its tuners (a changed scale
        # moves an in-line row's posts), or edges dragged across each
        # other: the editor still opens on the drawing, and says why.
        if parameters.headstock_outline != "drawn":
            raise
        outline_problem = str(error)
        try:
            plan = parameters.headstock_plan()
        except CNCGuitarWizardError:
            return {"lines": [], "centre": [0.0, 0.0], "problem": outline_problem}
    headstock = parameters.headstock_solid(plan)
    centre = parameters.headstock_engraving_centre(headstock)
    flip = -1.0 if parameters.left_handed else 1.0
    try:
        lines = text_lines(
            text,
            parameters.headstock_engraving_height,
            centre,
            parameters.headstock_engraving_direction(),
            parameters.headstock_engraving_font,
        )
    except GeometryException as error:
        return {
            "lines": [],
            "centre": [centre.x, flip * centre.y],
            "problem": outline_problem or str(error),
        }
    problem = outline_problem
    if tuners is not None:
        try:
            parameters.headstock_lettering(
                headstock, tuners, parameters.truss_rod(parameters.neck_outline())
            )
        except CNCGuitarWizardError as error:
            problem = str(error)
    return {
        "lines": [
            [[round(p.x, 2), round(flip * p.y, 2)] for p in line] for line in lines
        ],
        "centre": [round(centre.x, 2), round(flip * centre.y, 2)],
        "problem": problem,
    }


def _headstock_drawn_engraving(
    parameters: Prototype001Parameters,
) -> dict[str, Any] | None:
    """Return the lines drawn on the headstock face for its editor, or ``None``.

    ``{"lines", "problem"}``: the lines as drawn (``headstock_engraving_lines``,
    the editor's frame) and why they cannot be cut, or ``None`` (an outline
    that cannot be laid out says so itself).
    """
    lines = [
        [[x, y] for x, y in line]
        for line in parameters.headstock_engraving_lines
        if len(line) >= 2
    ]
    if not lines:
        return None
    problem: str | None = None
    try:
        plan, tuners = parameters.headstock_design()
        problem = parameters.headstock_drawn_engraving_problem(
            parameters.headstock_solid(plan),
            tuners,
            parameters.truss_rod(parameters.neck_outline()),
        )
    except CNCGuitarWizardError:
        pass
    return {"lines": lines, "problem": problem}


_ACTIVE_BUILD: Prototype001Build | None = None


class _LaidOutError(CNCGuitarWizardError):
    """An editor layout's own error message, passed on as it is."""


_BODY_MARKS = (Point2D(0.0, 0.0), Point2D(100.0, 0.0), Point2D(0.0, 100.0))
"""The body template's registration marks: X from the heel end, Y."""

_HEADSTOCK_MARKS = (Point2D(0.0, 0.0), Point2D(-100.0, 0.0), Point2D(0.0, 50.0))
"""The headstock template's registration marks, in the model frame."""

_INLAY_MARKS = (Point2D(-15.0, 0.0), Point2D(-15.0, 20.0), Point2D(-35.0, 0.0))
"""The inlay template's registration marks: X from the marker's fret
toward the nut (its fret space starts at 0), Y across, as built
right-handed."""

INLAY_IMPORT_TOLERANCE = 0.05
"""How near (mm) the corners read from a drawn marker keep to its line: a
curve drawn there comes back as corners this close to it."""

_REFERENCE_COLOURS = {
    "neck": "#8a6a3a",
    "pocket": "#4a7ab5",
    "pickup": "#2f8f5b",
    "bridge": "#9a5bb5",
    "bridge_plate": "#9a5bb5",
    "top_control": "#c27a1e",
    "rear": "#8c8c8c",
    "cover": "#b0b0b0",
}
"""The reference layer's colour for each kind of body feature."""


def outline_template(
    payload: dict[str, Any], part: str, kind: str = "svg"
) -> dict[str, Any]:
    """Return the body's, the headstock's or a marker's outline as a template.

    The template (see ``drawings.template_svg``) is drawn 1:1 in
    millimetres, as the editor shows the design (mirrored for a
    left-handed build, a seven- or eight-string body widened): its
    *Outline* layer the outline, a node at every handle; its *Reference*
    layer, locked, what the outline is drawn round — the neck, routes,
    cavities and bridge line, or the nut, tuner holes (and the edge's
    clearance round them) and truss-rod cover, or the first marker's
    fret space and where its corners fit — and three registration
    marks. As DXF for a CAD program (``drawings.template_dxf``) it has the
    same layers, the outline a polyline with a point at every handle.
    ``import_outline`` reads either back.

    Args:
        payload: ``{"prototype": {...}}`` as for ``start_build``.
        part: ``"body"`` (a drawn, Your design, body), ``"headstock"``
            (a drawn headstock) or ``"inlay"`` (the fret markers' shape,
            drawn on the first marker as in the inlay editor).
        kind: ``"svg"`` or ``"dxf"``.

    Returns:
        ``{kind: text}`` or ``{"error": message}``.
    """
    renders = {"svg": template_svg, "dxf": template_dxf}
    if kind not in renders:
        return {"error": f"There is no {kind!r} template."}
    render = renders[kind]
    try:
        if part == "body":
            return {kind: _body_template(payload, render)}
        if part == "headstock":
            return {kind: _headstock_template(payload, render)}
        if part == "inlay":
            return {kind: _inlay_template(payload, render)}
        return {"error": f"There is no {part!r} outline."}
    except _LaidOutError as error:
        return {"error": str(error)}
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}


def import_outline(payload: dict[str, Any], part: str, svg: str) -> dict[str, Any]:
    """Return the form values that draw an outline read from a template.

    The template is an SVG or a DXF file, told apart by its text. The
    outline is placed by the template's registration marks and turned
    into the editor's own handles (``drawings.fit_closed_spline``,
    ``drawings.fit_headstock``), every one on the drawn line, as many as
    keep the editor's curve within 0.25 mm of it; a marker's into its
    corners (a curve into corners within ``INLAY_IMPORT_TOLERANCE`` of
    it), each held where it fits every marker. An outline exported and
    read back unchanged comes back as it was.

    Args:
        payload: ``{"prototype": {...}}`` as for ``start_build``.
        part: ``"body"``, ``"headstock"`` or ``"inlay"``.
        svg: The SVG or DXF file's text.

    Returns:
        ``{"values": {...}, "message": text}`` — for a body
        ``{"control_points"}`` (the ``body_shape`` field) and its drawn
        engraving where it changed, for a headstock ``{"headstock_outline",
        "headstock_bass_edge", "headstock_treble_edge",
        "headstock_tip_points"}`` and ``"headstock_engraving_lines"`` where
        the lines drawn on its face changed, for a marker
        ``{"inlay_style", "inlay_points"}`` — or ``{"error": message}``.
    """
    try:
        if part == "body":
            return _import_body(payload, svg)
        if part == "headstock":
            return _import_headstock(payload, svg)
        if part == "inlay":
            return _import_inlay(payload, svg)
        return {"error": f"There is no {part!r} outline."}
    except _LaidOutError as error:
        return {"error": str(error)}
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}


def _drawn_body(payload: dict[str, Any]) -> tuple[YourDesignShape, dict[str, Any]]:
    """Return the drawn body and its editor layout."""
    parameters = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
    shape = parameters.body_shape
    if not isinstance(shape, YourDesignShape):
        raise CNCGuitarWizardError(
            "Only a drawn body (Your design) has an outline to edit."
        )
    layout = body_editor_layout(payload)
    if "error" in layout:
        raise _LaidOutError(layout["error"])
    return shape, layout


def _body_template(
    payload: dict[str, Any], render: Callable[..., str] = template_svg
) -> str:
    shape, layout = _drawn_body(payload)
    widening = float(layout["widening"] or 0.0)
    points, corners = drawn_points(widen_drawn(shape.control_points, widening))
    xs = [point.x for point in points]
    ys = [abs(point.y) for point in points]
    references = [
        ReferenceShape(
            polygon["name"],
            tuple(Point2D(x, y) for x, y in polygon["points"]),
            colour=_REFERENCE_COLOURS.get(polygon["role"], "#4a7ab5"),
            dashed=polygon["role"] in ("cover", "contour_top", "contour_back"),
        )
        for polygon in layout["polygons"]
    ]
    references += [
        ReferenceShape(
            circle["name"],
            (Point2D(circle["x"], circle["y"]),),
            radius=circle["r"],
            colour="#c27a1e",
        )
        for circle in layout["circles"]
    ]
    if layout["jack"] is not None:
        jack = layout["jack"]
        references.append(
            ReferenceShape(
                "Jack bore",
                (Point2D(jack["x"], jack["y"]), Point2D(jack["x2"], jack["y2"])),
                closed=False,
                colour="#c27a1e",
            )
        )
    reach = max(ys) + 10.0
    bridge = layout["scale_line"] - layout["heel_end"]
    references += [
        ReferenceShape(
            "Centreline",
            (Point2D(min(xs) - 10.0, 0.0), Point2D(max(xs) + 10.0, 0.0)),
            closed=False,
            colour="#999999",
            dashed=True,
        ),
        ReferenceShape(
            "Bridge line (the scale length)",
            (
                Point2D(bridge, -reach),
                Point2D(bridge, reach),
            ),
            closed=False,
            colour="#d33",
            dashed=True,
        ),
    ]
    if layout["neck_through"] is not None:
        half = layout["neck_through"]["width"] / 2.0
        references += [
            ReferenceShape(
                "Neck-through block glue line",
                (Point2D(min(xs), side * half), Point2D(max(xs), side * half)),
                closed=False,
                colour="#8a6a3a",
                dashed=True,
            )
            for side in (-1.0, 1.0)
        ]
    return render(
        "CNCguitarwizard body outline",
        TemplateFrame(_BODY_MARKS, bool(layout["mirrored"])),
        closed_catmull_rom_spans(points, corners),
        references,
        (
            "CNCguitarwizard body outline, 1:1 in millimetres. Edit the black "
            "path in layer Outline (or draw a new closed one there); draw lines "
            "to engrave into the top in layer Pattern.",
            "Keep layer Reference and its three red registration marks; read it "
            "back with Import SVG in the body editor.",
        ),
        pattern=_engraving_view(layout),
    )


def _engraving_view(layout: dict[str, Any]) -> tuple[tuple[Point2D, ...], ...]:
    """Return the body editor layout's engraving lines (empty for none)."""
    return tuple(
        tuple(Point2D(x, y) for x, y in line) for line in layout["engraving"] or ()
    )


def _import_body(payload: dict[str, Any], svg: str) -> dict[str, Any]:
    _, layout = _drawn_body(payload)
    widening = float(layout["widening"] or 0.0)
    frame = TemplateFrame(_BODY_MARKS, bool(layout["mirrored"]))
    read = read_template_outline(svg, frame)
    fit = fit_closed_spline(read.points, read.nodes, corners=read.corners)
    points: list[list[float | str]] = [
        [round(point.x, 2), round(narrow_y(point.y, widening), 2)]
        for point in fit.points
    ]
    for point, sharp in zip(points, fit.corners):
        if sharp:
            point.append(CORNER)
    values: dict[str, Any] = {"control_points": points}
    message = _import_message(len(points), fit.deviation, read)
    # The pattern, where it was changed: the top's engraving drawn from now
    # on, or none when it was all taken out.
    lines, said = _read_pattern(svg, frame, _engraving_view(layout))
    if lines:
        values.update(
            body_engraving=True,
            body_engraving_pattern="drawn",
            body_engraving_lines=lines,
        )
        message = (
            message[:-1]
            + f"; and its pattern, {_count(len(lines), 'line')} to engrave"
            + said
            + "."
        )
    elif lines is not None:
        values["body_engraving"] = False
        message = message[:-1] + f"; its pattern was taken out{said}."
    elif said:
        message = message[:-1] + said + "."
    return {"values": values, "message": message}


def _read_pattern(
    svg: str, frame: TemplateFrame, shown: Sequence[Sequence[Point2D]]
) -> tuple[list[list[list[float]]] | None, str]:
    """Return a template's pattern where it was changed, and what was read.

    The pattern is every line in its *Pattern* layer, every shape drawn
    beside the outline and every picture traced
    (``read_template_pattern``). Returns its lines thinned to within
    0.05 mm, as ``[x, y]`` points — ``None`` where there is none to read or
    it is the one the template was given (``shown``), empty where it was
    all taken out — and a note of the shapes beside the outline and the
    pictures traced or left out (``" (...)"``, or ``""`` for none).
    """
    pattern = read_template_pattern(svg, frame, tolerance=None)
    if pattern is None:
        return None, ""
    notes = [
        *(
            [f"{_count(pattern.beside, 'shape')} drawn beside the outline"]
            if pattern.beside
            else []
        ),
        *(
            [f"{_count(pattern.pictures, 'picture')} traced"]
            if pattern.pictures
            else []
        ),
        *(f"a picture left out: {reason}" for reason in pattern.untraced),
    ]
    said = f" ({'; '.join(notes)})" if notes else ""
    if _same_lines(pattern.lines, shown):
        return None, said
    return [
        [[round(p.x, 2), round(p.y, 2)] for p in thinned(line, 0.05)]
        for line in pattern.lines
    ], said


def _same_lines(
    read: Sequence[Sequence[Point2D]], shown: Sequence[Sequence[Point2D]]
) -> bool:
    """Return whether lines read back are those the template was given: as
    many, each through the same points (within 0.01 mm)."""
    return len(read) == len(shown) and all(
        len(line) == len(original)
        and all(
            abs(p.x - q.x) <= 0.01 and abs(p.y - q.y) <= 0.01
            for p, q in zip(line, original, strict=True)
        )
        for line, original in zip(read, shown, strict=True)
    )


def _drawn_headstock(
    payload: dict[str, Any],
) -> tuple[Prototype001Parameters, dict[str, Any]]:
    """Return the design as drawn (right-handed, its edges drawn) and layout."""
    layout = headstock_editor_layout(payload)
    if "error" in layout:
        raise _LaidOutError(layout["error"])
    built = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
    if built.headless:
        raise CNCGuitarWizardError("A headless neck has no headstock to draw.")
    parameters = dataclasses.replace(
        built, handedness="right", headstock_outline="drawn"
    )
    if not (parameters.headstock_bass_edge and parameters.headstock_treble_edge):
        # Not drawn yet: the fitted outline the editor starts from.
        parameters = dataclasses.replace(
            parameters,
            headstock_bass_edge=tuple(map(tuple, layout["start_edges"]["bass"])),
            headstock_treble_edge=tuple(map(tuple, layout["start_edges"]["treble"])),
            headstock_tip_points=(),
        )
    return parameters, layout


def _headstock_template(
    payload: dict[str, Any], render: Callable[..., str] = template_svg
) -> str:
    parameters, layout = _drawn_headstock(payload)
    plan = parameters.headstock_plan()
    half = layout["nut_half_width"]
    references = [
        ReferenceShape(
            "Neck",
            (
                Point2D(0.0, -half),
                Point2D(70.0, -half),
                Point2D(70.0, half),
                Point2D(0.0, half),
            ),
            colour="#8a6a3a",
        ),
        ReferenceShape(
            "Centreline",
            (Point2D(-plan.reach - 15.0, 0.0), Point2D(70.0, 0.0)),
            closed=False,
            colour="#999999",
            dashed=True,
        ),
    ]
    nut = layout["nut"]
    for name, points in (("Nut", nut["nut"]), ("Fretboard past the nut", nut["board"])):
        if points:
            references.append(
                ReferenceShape(name, tuple(Point2D(x, y) for x, y in points))
            )
    clearance = layout["min_edge_distance"]
    for hole in layout["holes"]:
        centre = (Point2D(hole["x"], hole["y"]),)
        references += [
            ReferenceShape("Tuner hole", centre, radius=hole["r"], colour="#2f8f5b"),
            ReferenceShape(
                f"Keep the edge outside: {clearance:g} mm round the tuner hole",
                centre,
                radius=hole["r"] + clearance,
                colour="#2f8f5b",
                dashed=True,
            ),
        ]
    cover = layout["truss_cover"]
    if cover is not None:
        references.append(
            ReferenceShape(
                "Truss-rod cover",
                tuple(Point2D(x, y) for x, y in cover["outline"]),
                colour="#9a5bb5",
            )
        )
    lettering = layout["lettering"]
    references += [
        ReferenceShape(
            "Lettering (headstock_engraving_text)",
            tuple(Point2D(x, y) for x, y in line),
            closed=False,
            colour="#1f6fb2",
        )
        for line in (lettering["lines"] if lettering else ())
    ]
    return render(
        "CNCguitarwizard headstock outline",
        TemplateFrame(_HEADSTOCK_MARKS, bool(layout["mirrored"])),
        headstock_spans(plan),
        references,
        (
            "CNCguitarwizard headstock outline, 1:1 in millimetres. Edit the "
            "black path in layer Outline: from the nut on one side round the "
            "tip to the nut on the other.",
            "Draw what is engraved on the face in layer Pattern (or beside the "
            "outline, or paste a picture: its dark shapes are traced).",
            "Keep layer Reference and its three red registration marks; read it "
            "back with Import SVG in the headstock editor.",
        ),
        pattern=_headstock_engraving_view(parameters),
    )


def _headstock_engraving_view(
    parameters: Prototype001Parameters,
) -> tuple[tuple[Point2D, ...], ...]:
    """Return the lines drawn on the headstock face, as drawn (none: empty)."""
    return tuple(
        tuple(Point2D(x, y) for x, y in line)
        for line in parameters.headstock_engraving_lines
        if len(line) >= 2
    )


def _import_headstock(payload: dict[str, Any], svg: str) -> dict[str, Any]:
    parameters, layout = _drawn_headstock(payload)
    frame = TemplateFrame(_HEADSTOCK_MARKS, bool(layout["mirrored"]))
    read = read_template_outline(svg, frame)
    fit = fit_headstock(
        read.points,
        layout["nut_half_width"],
        layout["bass_sign"],
        read.nodes,
        corners=read.corners,
    )
    # The headstock is drawn as read; its tuners are the editor's to check.
    dataclasses.replace(
        parameters,
        headstock_bass_edge=fit.bass_edge,
        headstock_treble_edge=fit.treble_edge,
        headstock_tip_points=fit.tip_points,
    ).headstock_plan()
    handles = len(fit.bass_edge) + len(fit.treble_edge) + len(fit.tip_points)
    values: dict[str, Any] = {
        "headstock_outline": "drawn",
        "headstock_bass_edge": [list(point) for point in fit.bass_edge],
        "headstock_treble_edge": [list(point) for point in fit.treble_edge],
        "headstock_tip_points": [list(point) for point in fit.tip_points],
    }
    message = _import_message(handles, fit.deviation, read)
    # What is engraved on the face, where it was changed: the lines drawn
    # from now on (engraved as the lettering is), or none.
    lines, said = _read_pattern(svg, frame, _headstock_engraving_view(parameters))
    if lines is not None:
        values["headstock_engraving_lines"] = lines
        message = message[:-1] + (
            f"; and its engraving, {_count(len(lines), 'line')}{said}."
            if lines
            else f"; its engraving was taken out{said}."
        )
    elif said:
        message = message[:-1] + said + "."
    return {"values": values, "message": message}


def _laid_out_inlay(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the inlay editor's layout, or raise why there is none."""
    layout = inlay_editor_layout(payload)
    if "error" in layout:
        raise _LaidOutError(layout["error"])
    return layout


def _inlay_half(layout: dict[str, Any], x: float) -> float:
    """Return the board's half-width ``x`` mm from the nut (its taper)."""
    nut, final = layout["nut_half"], layout["final_half"]
    return float(nut + (final - nut) * x / layout["final_position"])


def _inlay_mm(layout: dict[str, Any], along: float, across: float) -> Point2D:
    """Return a marker's ``[along, across]`` corner in its template: X from
    the fret space's nut-side fret, Y across (as built right-handed)."""
    length = layout["back"] - layout["front"]
    x = along * length
    return Point2D(
        x, layout["bass_sign"] * across * _inlay_half(layout, layout["front"] + x)
    )


def _inlay_share(layout: dict[str, Any], point: Point2D) -> tuple[float, float]:
    """Return a template point as ``[along, across]`` (see ``_inlay_mm``)."""
    length = layout["back"] - layout["front"]
    half = _inlay_half(layout, layout["front"] + point.x)
    return point.x / length, layout["bass_sign"] * point.y / half


def _inlay_outline(layout: dict[str, Any]) -> list[Point2D]:
    """Return the editor's marker in mm: straight between its corners, but
    curving through a round one (see ``InlayLayout.custom_points``)."""
    shape, rounds = drawn_points([tuple(point) for point in layout["points"]], ROUND)
    return [
        _inlay_mm(layout, point.x, point.y)
        for point in drawn_polygon(shape, rounds, CUSTOM_ROUND_SAMPLES)
    ]


def _inlay_template(
    payload: dict[str, Any], render: Callable[..., str] = template_svg
) -> str:
    layout = _laid_out_inlay(payload)
    length = layout["back"] - layout["front"]
    pad = 6.0

    def edge(x: float, side: float) -> Point2D:
        return Point2D(x, side * _inlay_half(layout, layout["front"] + x))

    low, high = layout["limits"]["along"]
    across = layout["limits"]["across"]
    corners = _inlay_outline(layout)
    fret = layout["fret"]
    references = [
        ReferenceShape(
            "Fretboard",
            (
                edge(-pad, -1.0),
                edge(length + pad, -1.0),
                edge(length + pad, 1.0),
                edge(-pad, 1.0),
            ),
            colour="#8a6a3a",
        ),
        ReferenceShape(
            "The nut" if fret == 1 else f"Fret {fret - 1}",
            (edge(0.0, -1.0), edge(0.0, 1.0)),
            closed=False,
            colour="#999999",
        ),
        ReferenceShape(
            f"Fret {fret}",
            (edge(length, -1.0), edge(length, 1.0)),
            closed=False,
            colour="#999999",
        ),
        ReferenceShape(
            "Centreline",
            (Point2D(-pad, 0.0), Point2D(length + pad, 0.0)),
            closed=False,
            colour="#999999",
            dashed=True,
        ),
        ReferenceShape(
            "Keep the corners inside: 1 mm from the frets and the board's edges "
            "in every marker's fret space",
            tuple(
                _inlay_mm(layout, along, side)
                for along, side in (
                    (low, -across),
                    (high, -across),
                    (high, across),
                    (low, across),
                )
            ),
            colour="#d9902a",
            dashed=True,
        ),
    ]
    return render(
        "CNCguitarwizard inlay marker",
        TemplateFrame(_INLAY_MARKS, bool(layout["mirrored"])),
        tuple((a, a, b, b) for a, b in zip(corners, corners[1:] + corners[:1])),
        references,
        (
            f"CNCguitarwizard inlay marker, 1:1 in millimetres: the first marker's "
            f"fret space (fret {fret}), the nut to the left.",
            "Edit the black path in layer Outline: its corners are the marker's "
            "(rounded 1 mm when cut); a curve comes back as corners.",
            "Every marker is this shape fitted to its own fret space. Keep layer "
            "Reference and its red marks; read it back with Import SVG.",
        ),
    )


def _import_inlay(payload: dict[str, Any], svg: str) -> dict[str, Any]:
    layout = _laid_out_inlay(payload)
    read = read_template_outline(
        svg, TemplateFrame(_INLAY_MARKS, bool(layout["mirrored"]))
    )
    corners = _polygon_corners(read.points, INLAY_IMPORT_TOLERANCE)
    if len(corners) < 3:
        raise CNCGuitarWizardError("A marker needs at least three corners.")
    # As the editor's own marker would read back.
    shown = _polygon_corners(_inlay_outline(layout), INLAY_IMPORT_TOLERANCE)
    moved = 0
    points: list[list[Any]]
    if len(corners) == len(shown) and all(
        math.hypot(a.x - b.x, a.y - b.y) <= 0.01
        for a, b in zip(corners, shown, strict=True)
    ):
        # Unchanged: the editor's own corners, exactly, round ones marked.
        points = [[float(p[0]), float(p[1]), *p[2:]] for p in layout["points"]]
    else:
        low, high = layout["limits"]["along"]
        limit = layout["limits"]["across"]
        points = []
        for corner in corners:
            along, side = _inlay_share(layout, corner)
            kept = (min(high, max(low, along)), min(limit, max(-limit, side)))
            moved += kept != (along, side)
            points.append([round(kept[0], 4), round(kept[1], 4)])
    message = f"Imported the marker: {_count(len(points), 'corner')}"
    if abs(read.scale - 1.0) > 0.005:
        message += (
            f" (its program had scaled it by {read.scale:.3g}; the registration "
            "marks set it right)"
        )
    if moved:
        message += (
            f"; {_count(moved, 'corner')} moved inside the dashed line, to keep "
            "1 mm from the frets and the board's edges"
        )
    return {
        "values": {"inlay_style": "custom", "inlay_points": points},
        "message": message + ".",
    }


def _polygon_corners(points: Sequence[Point2D], tolerance: float) -> list[Point2D]:
    """Return a closed outline's corners: where it turns, a curve as corners
    within ``tolerance`` of it (the start too, unless it lies on a side)."""
    corners = list(thinned([*points, points[0]], tolerance)[:-1])
    if len(corners) > 3:
        a, b, c = corners[-1], corners[0], corners[1]
        length = math.hypot(c.x - a.x, c.y - a.y)
        off = abs((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x))
        if length > 0.0 and off / length <= tolerance:
            corners.pop(0)
    return corners


def _import_message(handles: int, deviation: float, read: ReadOutline) -> str:
    """Say what an import made of the drawing."""
    message = (
        f"Imported the outline: {handles} handles, within "
        f"{max(deviation, 0.01):.2f} mm of the drawing"
    )
    if abs(read.scale - 1.0) > 0.005:
        message += (
            f" (its program had scaled it by {read.scale:.3g}; the registration "
            "marks set it right)"
        )
    return message + "."


def _count(number: int, thing: str) -> str:
    """Return ``3 lines``, ``1 line``."""
    return f"{number} {thing}{'' if number == 1 else 's'}"


def _group_title(group: str) -> str:
    """Return what an editor group is called in a feature program's name."""
    if group.startswith("pickup:"):
        return f"{group.split(':')[1]} pickup"
    if group.startswith(("pot:", "bolt:")):
        kind, index = group.split(":")
        return f"{'pot' if kind == 'pot' else 'neck bolt'} {int(index) + 1}"
    return {
        "control": "controls",
        "switch": "switch cavity",
        "battery": "battery box",
        "strap_guide": "strap guide",
    }.get(group, group)


def quick_model(payload: dict[str, Any], details: Sequence[str] = ()) -> dict[str, Any]:
    """Return the quick 3D model, to turn and look at in the page.

    The design's own surfaces as triangle meshes (``render.preview3d``),
    made in a second or two where the build's exact model takes minutes:
    to try a change and see it. The last few designs' models and detail
    sets are kept, so a set ticked, or a design changed back, is drawn at
    once.

    Args:
        payload: ``{"prototype": {...}}`` as for ``start_build``.
        details: The detail sets to add, keys of ``render.preview3d.DETAILS``
            (``"neck"``: frets, markers and the nut, ...); none for none.

    Returns:
        ``{"parts": [...]}``, each ``{"name", "colour", "positions",
        "triangles"}``, the positions little-endian 32-bit floats (x, y, z
        a vertex, in mm) and the triangles 32-bit indices, both base64; or
        ``{"error": message}`` when the design does not build.
    """
    try:
        parameters = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
        base: Callable[..., tuple[PreviewPart, ...]] = _quick_base
        detail_set: Callable[..., tuple[PreviewPart, ...]] = _quick_details
        try:
            hash(parameters)
        except TypeError:  # a value the form never sends (a list): made afresh
            base, detail_set = _quick_base.__wrapped__, _quick_details.__wrapped__
        parts = base(parameters)
        for detail in details:
            parts += detail_set(parameters, detail)
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}
    return {
        "parts": [
            {
                "name": part.name,
                "colour": part.colour,
                "positions": base64.b64encode(part.float32()).decode("ascii"),
                "triangles": base64.b64encode(part.uint32()).decode("ascii"),
            }
            for part in parts
        ]
    }


def _quick_built(parameters: Prototype001Parameters) -> Prototype001Geometry:
    """Return the design built for the quick model: wired only under a
    separate top, whose wire channels are routes in the core (seen with the
    top hidden); else not, the quicker."""
    return _built(parameters, wired=parameters.cap_thickness > 0.0)


@functools.lru_cache(maxsize=BUILDS_KEPT)
def _quick_base(parameters: Prototype001Parameters) -> tuple[PreviewPart, ...]:
    """Return the quick model's body, neck and fretboard (``quick_model``)."""
    geometry = _quick_built(parameters)
    rows = FreeCADScriptExporter.neck_loft_rows(
        geometry.neck_surface,
        geometry.headstock,
        geometry.joint_fillet_radius,
        geometry.volute,
    )
    return preview_parts(geometry, rows)


@functools.lru_cache(maxsize=BUILDS_KEPT * len(DETAILS))
def _quick_details(
    parameters: Prototype001Parameters, detail: str
) -> tuple[PreviewPart, ...]:
    """Return one of the quick model's detail sets (``quick_model``)."""
    return detail_parts(_quick_built(parameters), parameters, detail)


def part_views(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the neck's and the fretboard's drawings for their own pages.

    The application like UI's Design › Neck and Design › Fretboard show
    them (see ``render.svg.neck_views``): the part from above, from the
    side and in section, a scalloped board's scallops with it.

    Args:
        payload: ``{"prototype": {...}}`` as for ``start_build``.

    Returns:
        ``{"neck", "fretboard"}``, each an SVG document, or ``{"error":
        message}`` when the design does not build.
    """
    try:
        parameters = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
        geometry = _built(parameters, wired=False)
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}
    return {
        "neck": render_neck_svg(geometry),
        "fretboard": render_fretboard_svg(geometry),
    }


def setting_views(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the design's drawings the settings' pictures are made from.

    Each part in them carries its name (``<title>``), the parts a
    setting's picture picks out (``setting_pictures``): the instrument
    from the front, and the neck and the fretboard from above, from the
    side and in section, as on their own pages.

    Args:
        payload: ``{"prototype": {...}}`` as for ``start_build``.

    Returns:
        ``{"plan", "neck", "fretboard"}``, each an SVG document, or
        ``{"error": message}`` when the design does not build.
    """
    try:
        parameters = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
        geometry = _built(parameters, wired=True)
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}
    return {
        "plan": render_plan_view_svg(geometry),
        "neck": render_neck_svg(geometry),
        "fretboard": render_fretboard_svg(geometry),
    }


_PICTURE_VIEWS: dict[str, Callable[..., str]] = {
    "plan": render_plan_view_svg,
    "neck": render_neck_svg,
    "fretboard": render_fretboard_svg,
}
"""Each setting picture's view (``setting_views``) by its name."""


def setting_variation(payload: dict[str, Any], name: str) -> dict[str, Any]:
    """Return a setting's view of the design with the setting changed.

    What a setting does, for its picture: the setting's view of the design
    (``setting_pictures``) with the setting at another value, drawn on the
    design's own view's frame so the two lie one over the other — a number
    20 % larger (or smaller, or from 0 to its default or a little), and
    further while its parts move too little to be seen (a fretboard's
    radius: ``PICTURE_LEAST_MOVE`` of their size), a tick box the other
    way, a choice the next one that builds: the first that builds and
    moves them enough, else the one that moves them most.

    Args:
        payload: ``{"prototype": {...}}`` as for ``start_build``.
        name: The setting, a ``Prototype001Parameters`` field.

    Returns:
        ``{"now", "value", "view"}``: the setting's value now and the one
        drawn (as the form holds them), and the view; ``{"same": True}``
        when no value tried changes the drawing (a machining setting, say:
        it changes how a part is cut, not its shape); or ``{"error":
        message}`` for a design that does not build.
    """
    try:
        parameters = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
        geometry = parameters.build()
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}
    if name not in SETTING_PICTURES or not hasattr(parameters, name):
        return {"same": True}
    view_name, patterns = SETTING_PICTURES[name]
    render = _PICTURE_VIEWS[view_name]
    now = render(geometry)
    current = getattr(parameters, name)
    best: tuple[float, Any, str] | None = None
    for value in _variations(name, current):
        try:
            varied = dataclasses.replace(parameters, **{name: value}).build()
            view = render(varied, frame_of=geometry)
        except (CNCGuitarWizardError, TypeError, ValueError):
            continue
        if view == now:
            continue
        moved = _picture_move(now, view, patterns)
        if best is None or moved > best[0]:
            best = (moved, value, view)
        if moved >= PICTURE_LEAST_MOVE:
            break
    # Its parts not moved at all: what it changes lies elsewhere.
    if best is None or best[0] == 0.0:
        return {"same": True}
    _, value, view = best
    return {"now": _jsonable(current), "value": _jsonable(value), "view": view}


PICTURE_LEAST_MOVE = 0.03
"""How far a setting's parts must move in its picture to be seen there, a
share of their size: a change that moves them less is tried further."""


def _picture_move(now: str, varied: str, patterns: Sequence[str]) -> float:
    """Return how far a picture's parts moved, a share of their size.

    The parts the first of ``patterns`` that finds one picks out (by their
    ``<title>``), each compared point by point with its own size (its box,
    where it is drawn with more or fewer points), the most any moved; 1
    where their number changed.
    """
    for pattern in patterns:
        before, after = _named_parts(now, pattern), _named_parts(varied, pattern)
        if before or after:
            break
    if len(before) != len(after) or not before:
        return 1.0
    most = 0.0
    for (numbers, size, box), (others, _, other_box) in zip(before, after, strict=True):
        if len(numbers) != len(others):
            numbers, others = list(box), list(other_box)
        if numbers:
            moved = max(abs(a - b) for a, b in zip(numbers, others, strict=True))
            most = max(most, moved / (size or 1.0))
    return most


_SHAPE_NUMBERS = re.compile(r'\b(d|points|cx|cy|r|x1|y1|x2|y2)="([^"]*)"')
"""A drawn part's attributes that place it, and their values."""


def _named_parts(
    svg: str, pattern: str
) -> list[tuple[list[float], float, tuple[float, ...]]]:
    """Return a drawing's parts whose name ``pattern`` finds, in order:
    the numbers that place each, how large it is across (its box's
    longer side) and its box (left, top, right, bottom)."""
    found = re.compile(pattern)
    parts: list[tuple[list[float], float, tuple[float, ...]]] = []
    for attributes, title in re.findall(r"<\w+\b([^>]*)><title>([^<]*)</title>", svg):
        if not found.search(title):
            continue
        values = {
            key: [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", value)]
            for key, value in _SHAPE_NUMBERS.findall(attributes)
        }
        numbers = [
            number
            for key in ("d", "points", "cx", "cy", "r", "x1", "y1", "x2", "y2")
            for number in values.get(key, [])
        ]
        pairs = values.get("d", []) or values.get("points", [])
        xs, ys = pairs[0::2], pairs[1::2]
        if "cx" in values:
            r = values.get("r", [0.0])[0]
            xs = [values["cx"][0] - r, values["cx"][0] + r]
            ys = [values["cy"][0] - r, values["cy"][0] + r]
        if "x1" in values:
            xs = values["x1"] + values.get("x2", [])
            ys = values.get("y1", []) + values.get("y2", [])
        box = (min(xs), min(ys), max(xs), max(ys)) if xs and ys else ()
        size = max(box[2] - box[0], box[3] - box[1]) if box else 0.0
        parts.append((numbers, size, box))
    return parts


def _variations(name: str, current: Any) -> list[Any]:
    """Return the values a setting's picture tries it at, in turn."""
    annotation = typing.get_type_hints(Prototype001Parameters)[name]
    if isinstance(current, bool):
        return [not current]
    options = [
        option for option in typing.get_args(annotation) if isinstance(option, str)
    ]
    if options:
        # The ones after the current one, then round from the first.
        at = options.index(current) if current in options else -1
        return [*options[at + 1 :], *options[: max(at, 0)]]
    if isinstance(current, int | float):
        default = getattr(Prototype001Parameters(), name)
        if current:
            values: list[float] = [
                current * factor for factor in (1.2, 0.8, 1.5, 0.6, 2.0, 0.5, 3.0)
            ]
        else:
            values = [*([default] if default else []), 1.0, 5.0, 10.0]
        # Whole numbers by the setting's kind (a design may hold 4 for 4.0).
        if annotation is int:
            whole = [round(value) for value in values] + [current + 1, current - 1]
            return [value for value in dict.fromkeys(whole) if value != current]
        return [round(value, 2) for value in values]
    return []


def fretboard_radius_program(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the NC program cutting only the fretboard's radius, for a
    board already made (``cam.plan_fretboard_radius``): Design ›
    Fretboard's *Radius only (NC)*.

    Args:
        payload: ``{"prototype": {...}, "machining": {...}}`` as for
            ``start_build``.

    Returns:
        ``{"name", "text"}`` or ``{"error": message}``.
    """
    try:
        parameters = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
        machining = MachiningParameters(**_coerce(payload.get("machining", {})))
        fretboard = FretboardMachiningParameters().with_form_settings(machining)
        setup = plan_fretboard_radius(parameters.build(), fretboard)
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}
    writer = GCodeWriter.for_parameters(machining)
    return {
        "name": f"{program_stem(setup, machining)}{writer.extension}",
        "text": writer.render(setup, machining),
    }


def feature_programs(payload: dict[str, Any], group: str) -> dict[str, Any]:
    """Return NC programs for one body feature, zeroed on the feature.

    The body editor's groups (see ``_editor_group``) name the feature: its
    pockets and holes are cut on their own with the work zero at their
    centre, for a feature left out of a body already cut, and its cover
    plates get their sheet programs (``cam.plan_feature_machining``).

    Args:
        payload: ``{"prototype": {...}, "machining": {...}}`` as for
            ``start_build``.
        group: The dragged feature's group, e.g. ``"battery"``.

    Returns:
        ``{"title", "files": [{"name", "text"}]}`` or ``{"error": message}``.
    """
    if group == "jack":
        return {"error": "The jack's bore enters from the edge: drill it by hand."}
    try:
        parameters = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
        machining = MachiningParameters(**_coerce(payload.get("machining", {})))
        geometry = parameters.build()
        title = _group_title(group)
        setups = plan_feature_machining(
            geometry.body,
            geometry.covers,
            lambda name: _editor_group(name) == group,
            title,
            machining,
        )
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}
    writer = GCodeWriter.for_parameters(machining)
    return {
        "title": title,
        "files": [
            {
                "name": f"{program_stem(setup, machining)}{writer.extension}",
                "text": writer.render(setup, machining),
            }
            for setup in setups
        ],
    }


def start_build(
    payload: dict[str, Any], output_directory: str = "/build"
) -> dict[str, Any]:
    """Validate the parameters and prepare a stepwise build.

    Returns ``{"stages": [labels...]}`` or ``{"error": message}``. Call
    ``advance_build`` once per stage, then ``finish_build``.
    """
    global _ACTIVE_BUILD
    _ACTIVE_BUILD = None
    try:
        parameters = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
        machining = MachiningParameters(**_coerce(payload.get("machining", {})))
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}
    _ACTIVE_BUILD = Prototype001Build(
        Path(output_directory),
        parameters,
        run_freecad=False,
        machining=machining,
    )
    return {"stages": list(_ACTIVE_BUILD.labels)}


def advance_build() -> dict[str, Any]:
    """Run the next stage of the prepared build.

    Returns ``{"completed", "total", "done", "next"}`` or ``{"error"}``
    (which also discards the build).
    """
    global _ACTIVE_BUILD
    build = _ACTIVE_BUILD
    if build is None:
        return {"error": "No build has been started."}
    try:
        build.advance()
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        _ACTIVE_BUILD = None
        return {"error": f"{type(error).__name__}: {error}"}
    labels = build.labels
    return {
        "completed": build.completed,
        "total": len(labels),
        "done": build.done,
        "next": None if build.done else labels[build.completed],
    }


def finish_build() -> dict[str, Any]:
    """Collect the finished build's files, report and plan view."""
    global _ACTIVE_BUILD
    build = _ACTIVE_BUILD
    if build is None or not build.done or build.geometry is None:
        return {"error": "The build has not finished."}
    _ACTIVE_BUILD = None
    result = build.result
    files: dict[str, str] = {}
    for path in (
        result.python_path,
        result.macro_path,
        result.report_path,
        result.parameter_sheet_path,
        *result.gcode_paths,
        *result.toolpath_preview_paths,
        *result.dxf_paths,
    ):
        files[path.name] = path.read_text(encoding="utf-8")
    report = json.loads(files[result.report_path.name])
    global _LAST_BUILD
    _LAST_BUILD = (files, report)
    return {
        "files": files,
        "report": report,
        "plan_view": render_plan_view_svg(build.geometry),
    }


_LAST_BUILD: tuple[dict[str, str], dict[str, Any]] | None = None
"""The last finished build's files and report, for ``nc_archive``."""

_PART_ORDER = (
    "Body",
    "Wing bass",
    "Wing treble",
    "Neck",
    "Fretboard",
    "Inlays",
    "Nut jig",
    "Covers",
)
"""The parts in the order they are made (an unknown part goes last)."""


def archive_name(name: str) -> str:
    """Return ``name`` made safe for a file name, or ``cncguitarwizard``.

    Letters (accented ones too), digits, spaces, dots, dashes and
    underscores stay; anything else becomes a dash.
    """
    safe = re.sub(r"[^\w .-]+", "-", name.strip())
    # "Jone / #1" gives "Jone-1", not "Jone - -1".
    safe = re.sub(r"[\s-]*-[\s-]*", "-", safe).strip(" .-")
    return safe[:80] or "cncguitarwizard"


def format_export(name: str) -> dict[str, str]:
    """Return the FreeCAD script that exports the built model to one
    other 3D format (``backends.freecad.formats``), to run beside it.

    Returns:
        ``{"name": "Prototype001_export_stl.py", "text": source}``, or
        ``{"error": message}`` for an unknown format.
    """
    try:
        source = render_format_export([name])
    except CNCGuitarWizardError as error:
        return {"error": str(error)}
    return {"name": export_script_name([name]), "text": source}


def nc_archive(name: str = "") -> dict[str, str]:
    """Return the last build's NC programs in one ZIP, named for the guitar.

    Inside a folder named ``name``, one folder a part, each program
    numbered in running order (``Neck/02_Neck_top_6mm_flathead.nc``), and a
    ``README.txt`` listing them with their tools and run times.

    Returns:
        ``{"name": "<name>.zip", "data": base64}``, or ``{"error": message}``
        before a build has finished.
    """
    if _LAST_BUILD is None:
        return {"error": "Build the guitar first."}
    files, report = _LAST_BUILD
    title = archive_name(name)
    programs = sorted(
        report["gcode"].items(),
        key=lambda item: (
            _PART_ORDER.index(item[1]["part"])
            if item[1]["part"] in _PART_ORDER
            else len(_PART_ORDER),
            item[1]["part"],
            item[1]["step"],
        ),
    )
    lines = [
        f"{name.strip() or title} - NC programs from CNCguitarwizard",
        f"Generated {report.get('generated_utc', '')}",
        "",
        "Each part's programs, numbered in the order to run them.",
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        part = None
        for program, info in programs:
            if info["part"] != part:
                part = info["part"]
                lines += ["", f"{part}:"]
            folder = archive_name(info["part"])
            entry = f"{info['step']:02d}_{info['file']}"
            archive.writestr(f"{title}/{folder}/{entry}", files[info["file"]])
            lines.append(
                f"  {folder}/{entry}  {info['tool']}, "
                f"about {info['estimated_minutes']:g} min"
            )
        archive.writestr(f"{title}/README.txt", "\n".join(lines) + "\n")
    return {
        "name": f"{title}.zip",
        "data": base64.b64encode(buffer.getvalue()).decode("ascii"),
    }


def run_build(
    payload: dict[str, Any], output_directory: str = "/build"
) -> dict[str, Any]:
    """Build every FreeCAD-free artifact from JSON parameter overrides.

    Runs every stage at once (``start_build`` / ``advance_build`` /
    ``finish_build`` do the same in steps).

    Args:
        payload: ``{"prototype": {...}, "machining": {...}}`` with values
            as produced by the form: numbers, booleans, ``None``, lists
            for tuple fields, and ``{"kind": ...}`` objects for variants.
        output_directory: Where to write, on whatever file system the
            interpreter has (Pyodide's in the browser).

    Returns:
        ``{"files": {name: text}, "report": {...}, "plan_view": svg}`` or
        ``{"error": message}`` when the parameters are rejected.
    """
    started = start_build(payload, output_directory)
    if "error" in started:
        return started
    while True:
        step = advance_build()
        if "error" in step:
            return step
        if step["done"]:
            break
    return finish_build()


def _group_fields(cls: type) -> list[dict[str, Any]]:
    """Split a dataclass's fields into titled groups by name prefix."""
    # The instrument is chosen above the form (it picks the defaults).
    described = [
        field
        for field in _describe_fields(cls, _BASIC_FIELDS)
        if field["name"] != "instrument"
    ]
    groups: list[dict[str, Any]] = [
        {"title": title, "fields": []} for title, _ in _GROUPS
    ]
    other: list[dict[str, Any]] = []
    for field in described:
        for group, (_, prefixes) in zip(groups, _GROUPS, strict=True):
            if any(field["name"].startswith(prefix) for prefix in prefixes):
                group["fields"].append(field)
                break
        else:
            other.append(field)
    if other:
        groups.append({"title": "Other", "fields": other})
    return [group for group in groups if group["fields"]]


def _describe_fields(
    cls: type, basic: frozenset[str] | None = None
) -> list[dict[str, Any]]:
    """Return name, form type, default and advanced flag for every init field.

    Args:
        cls: The dataclass to describe.
        basic: Names of the fields shown up front; every other field is
            marked ``advanced``. ``None`` marks nothing advanced.
    """
    hints = typing.get_type_hints(cls)
    described = []
    for field in dataclasses.fields(cls):
        if not field.init:
            continue
        # Its default, or the one its factory makes (a field with neither,
        # none in a parameter set, would show empty).
        default: Any
        if field.default is not dataclasses.MISSING:
            default = field.default
        elif callable(field.default_factory):
            default = field.default_factory()
        else:
            default = None
        entry: dict[str, Any] = {
            "name": field.name,
            "type": _form_type(hints[field.name]),
            "default": _jsonable(default),
            "advanced": basic is not None and field.name not in basic,
        }
        if text := _field_help(cls).get(field.name):
            entry["help"] = text
        if entry["type"] == "choice":
            entry["options"] = [
                str(option) for option in typing.get_args(hints[field.name])
            ]
            if field.name in _CHOICE_LABELS:
                entry["labels"] = _CHOICE_LABELS[field.name]
        variants = _variant_classes(hints[field.name])
        if field.name in _FORM_KINDS:
            variants = {
                kind: variant
                for kind, variant in variants.items()
                if kind in _FORM_KINDS[field.name]
            }
        if variants:
            entry["type"] = "variant"
            entry["variants"] = {
                kind: {
                    "label": _VARIANT_LABELS.get(kind, kind),
                    # A setup note shown under the kind while it is chosen.
                    "note": BRIDGE_NOTES.get(kind),
                    "max_strings": BRIDGE_MAX_STRINGS.get(kind),
                    "min_strings": BRIDGE_MIN_STRINGS.get(kind),
                    "fields": [
                        described_field
                        for described_field in _describe_fields(
                            variant, _BASIC_VARIANT_FIELDS.get(kind)
                        )
                        if described_field["name"] != "kind"
                    ],
                }
                for kind, variant in variants.items()
            }
        described.append(entry)
    return described


HELP_LIMIT = 900
"""The longest help text a field's tooltip shows, in characters."""


@functools.cache
def _field_help(cls: type) -> dict[str, str]:
    """Return what each of a dataclass's fields means, for its tooltip.

    Taken from the code's own documentation, so it never drifts from it:
    the class docstring's ``Args:`` entries, a string right after a field
    (an attribute docstring), and the comment block above a field — which
    also explains the fields right after it that it names (the
    multiscale block above ``bass_scale_length`` covers
    ``perpendicular_fret``), and the first block elsewhere that names it.
    ``field_help.FIELD_HELP`` comes first: plain words for the settings
    shown up front, and those the code leaves unexplained.
    """
    names = {field.name for field in dataclasses.fields(cls) if field.init}
    found: dict[str, str] = {}
    try:
        source = textwrap.dedent(inspect.getsource(cls))
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError):
        tree = None
    if tree is not None and isinstance(tree.body[0], ast.ClassDef):
        lines = source.splitlines()
        block: str | None = None
        body = tree.body[0].body
        for index, statement in enumerate(body):
            if not (
                isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
            ):
                continue
            name = statement.target.id
            comment: list[str] = []
            line = statement.lineno - 2
            while line >= 0 and lines[line].strip().startswith("#"):
                comment.insert(0, lines[line].strip().lstrip("#").strip())
                line -= 1
            if comment:
                block = " ".join(comment)
                found.setdefault(name, _focus(block, name, own=True))
            elif block is not None and _mentions(block, name):
                found.setdefault(name, _focus(block, name))
            else:
                block = None
            following = body[index + 1] if index + 1 < len(body) else None
            if (
                isinstance(following, ast.Expr)
                and isinstance(following.value, ast.Constant)
                and isinstance(following.value.value, str)
            ):
                found[name] = " ".join(following.value.value.split())
        # A field no block right above explains: the first block in the
        # class that names it.
        blocks: list[str] = []
        comment = []
        for text in lines:
            if text.strip().startswith("#"):
                comment.append(text.strip().lstrip("#").strip())
            elif comment:
                blocks.append(" ".join(comment))
                comment = []
        for name in names - found.keys():
            for block_text in blocks:
                if _mentions(block_text, name):
                    found[name] = _focus(block_text, name)
                    break
    found.update(_args_help(inspect.getdoc(cls) or ""))
    found.update(FIELD_HELP)
    return {
        name: _shorten(text) for name, text in found.items() if name in names and text
    }


def _mentions(text: str, name: str) -> bool:
    """Whether ``text`` names the field ``name``.

    A wildcard names a group: ``truss_rod_step_*`` or
    ``body_*_binding_width`` (``body_*`` alone is too wide to).
    """
    if re.search(rf"\b{re.escape(name)}\b", text):
        return True
    for pattern in re.findall(r"\b[\w]*\*[\w*]*", text):
        if pattern.count("_") < 2:
            continue
        regex = "".join(r"\w+" if c == "*" else re.escape(c) for c in pattern)
        if re.fullmatch(regex, name):
            return True
    return False


def _focus(text: str, name: str, own: bool = False) -> str:
    """Return a comment block cut to what it says about ``name``.

    The field's ``own`` block (right above it): whole when short, else its
    first sentence and every sentence naming the field. Another field's
    block: only the sentences naming it (all of it if none do alone).
    """
    if own and len(text) <= HELP_LIMIT // 2:
        return text
    sentences = _sentences(text)
    naming = [sentence for sentence in sentences if _mentions(sentence, name)]
    if not own:
        return " ".join(naming) or text
    return " ".join([sentences[0], *(s for s in naming if s != sentences[0])])


def _sentences(text: str) -> list[str]:
    """Return ``text``'s sentences and clauses: split after ". " or "; ".

    Never inside brackets, nor after "e.g." or "i.e."; a sentence may
    start with a field's name, in lower case.
    """
    parts: list[str] = []
    depth = 0
    start = 0
    for index, character in enumerate(text):
        if character in "([":
            depth += 1
        elif character in ")]":
            depth = max(0, depth - 1)
        elif (
            character in ".;"
            and depth == 0
            and text[index + 1 : index + 2] == " "
            and not text[max(0, index - 3) : index + 1].endswith(("e.g.", "i.e."))
        ):
            parts.append(text[start : index + 1].strip())
            start = index + 2
    if text[start:].strip():
        parts.append(text[start:].strip())
    return parts


def _args_help(doc: str) -> dict[str, str]:
    """Return a Google style docstring's ``Args:`` entries, one line each."""
    entries: dict[str, str] = {}
    inside = False
    current: str | None = None
    for line in doc.splitlines():
        if line.strip() == "Args:":
            inside = True
            continue
        if not inside:
            continue
        if line and not line.startswith(" "):
            break  # the next section (Raises:, Returns:)
        match = re.match(r"^    (\w+)(?: \([^)]*\))?: (.*)$", line)
        if match:
            current = match.group(1)
            entries[current] = match.group(2).strip()
        elif current is not None and line.strip():
            entries[current] += " " + line.strip()
    return entries


def _shorten(text: str) -> str:
    """Return ``text`` cut to ``HELP_LIMIT`` characters at a sentence or word."""
    text = " ".join(text.split())
    if len(text) <= HELP_LIMIT:
        return text
    cut = text[:HELP_LIMIT]
    end = max(cut.rfind(". "), cut.rfind("; "))
    return (cut[: end + 1] if end > HELP_LIMIT // 2 else cut.rsplit(" ", 1)[0]) + " …"


def _variant_classes(annotation: Any) -> dict[str, type[Any]]:
    """Return ``{kind: class}`` when the annotation is a union of kinded specs."""
    origin = typing.get_origin(annotation)
    members = (
        list(typing.get_args(annotation))
        if origin in (types.UnionType, typing.Union)
        else [annotation]
    )
    variants: dict[str, type[Any]] = {}
    for member in members:
        if not (isinstance(member, type) and dataclasses.is_dataclass(member)):
            return {}
        kind_field = next(
            (field for field in dataclasses.fields(member) if field.name == "kind"),
            None,
        )
        if kind_field is None or kind_field.default is dataclasses.MISSING:
            return {}
        variants[str(kind_field.default)] = member
    return variants


def _form_type(annotation: Any) -> str:
    """Map a field annotation to the form control it needs."""
    origin = typing.get_origin(annotation)
    if origin is typing.Literal:
        return "choice"
    if origin in (types.UnionType, typing.Union):
        members = [arg for arg in typing.get_args(annotation) if arg is not type(None)]
        if len(members) == 1 and members[0] is float:
            return "optional_float"
        return "json"
    if annotation is bool:
        return "bool"
    if annotation is int:
        return "int"
    if annotation is float:
        return "float"
    if annotation is str:
        return "str"
    return "json"


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _jsonable(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _coerce(values: dict[str, Any]) -> dict[str, Any]:
    """Turn JSON lists back into the tuples the dataclasses expect."""
    return {name: _tuplify(value) for name, value in values.items()}


def _tuplify(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_tuplify(item) for item in value)
    if isinstance(value, dict) and "kind" in value:
        if value["kind"] in BRIDGE_KINDS:
            return bridge_spec_from_dict(value)
        if value["kind"] in BODY_SHAPE_KINDS:
            return body_shape_from_dict(value)
        raise CNCGuitarWizardError(
            f"Unknown bridge or body shape kind {value['kind']!r}."
        )
    return value
