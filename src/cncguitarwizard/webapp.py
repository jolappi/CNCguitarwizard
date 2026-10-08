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
import json
import math
import re
import textwrap
import types
import typing
import zipfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .cam import (
    POST_PROCESSOR_LABELS,
    GCodeWriter,
    MachiningParameters,
    plan_feature_machining,
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
    JackHole,
    bridge_spec_from_dict,
)
from .geometry.exceptions import GeometryException
from .geometry.fret import FretCalculator
from .geometry.fretboard.inlay_layout import DEFAULT_CUSTOM_POINTS, custom_limits
from .geometry.lettering import text_lines
from .geometry.neck import LOCKING_NUT_SPECS, TunerLayout
from .geometry.primitives import Point2D, closed_catmull_rom_spans, point_in_polygon
from .presets import Prototype001Parameters
from .presets.body_shapes import (
    BODY_SHAPE_KINDS,
    BODY_SHAPE_LABELS,
    OUTLINE_SAMPLES_PER_SEGMENT,
    YOUR_DESIGN_START_POINTS,
    YOUR_DESIGN_TEMPLATES,
    YourDesignShape,
    body_shape_from_dict,
    narrow_y,
    widen_points,
    widened_shape,
)
from .presets.controls import CONTROL_LABELS, SCREW_CLEARANCE
from .presets.pickups import PICKUP_CONFIGURATIONS
from .presets.prototype001 import (
    BODY_TEMPLATE_VALUES,
    INSTRUMENT_OVERRIDES,
    NECK_TEMPLATE_RESETS,
    NECK_TEMPLATES,
)
from .presets.truss_rod_covers import editable_cover_points, truss_rod_cover_shape
from .render.svg import render_plan_view_svg
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
        "auto": "Auto (Floyd Rose Original nut with a Floyd Rose bridge)",
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
        "custom": "Custom (drawn in the Inlay design window)",
    },
    "body_jack": {
        "side": "Side jack (Les Paul style plate or barrel jack)",
        "cup": "Cup jack or Electrosocket (7/8 in counterbore)",
        "strat": "Stratocaster style top plate (cavity from the top)",
        "plate": "On the Jazz Bass control plate (no bore from the edge)",
    },
    "body_pickguard_style": {
        "stratocaster": "Stratocaster (beside the neck, a tail past the bridge)",
        "superstrat": "Superstrat (close round the pickups)",
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
        "truss_rod_spoke_wheel",
        "truss_rod_profile",
        "truss_rod_rod_length",
        "bass_scale_length",
        "perpendicular_fret",
        "nut_width",
        "fretboard_radius",
        "fretboard_thickness",
        "fretboard_binding_width",
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
        "tuner_hole_diameter",
        "body_thickness",
        "body_shape",
        "body_pickups",
        "body_bridge",
        "body_controls",
        "body_switch",
        "body_jack",
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
        "body_top_binding_width",
        "body_arm_contour_depth",
        "body_belly_cut_depth",
        "body_carved_top",
        "body_carve_depth",
        "body_stepped_top",
        "body_neck_pickup_offset",
        "body_bridge_pickup_offset",
        "tool_diameter",
        "tool_tip",
        "post_processor",
        "spindle_dwell",
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
        "carve_finish",
        "fret_slot_spindle_speed",
        "fret_slot_step_down",
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
        ``locking_nut_widths`` maps each locking nut to its width, the
        least ``nut_width`` it fits (the form widens the neck to it);
        ``neck_templates`` each neck template (``NECK_TEMPLATES``) to
        ``{"label", "values", "resets"}``, the values the headstock editor
        loads and the settings it puts back to their defaults
        (``NECK_TEMPLATE_RESETS`` the template does not set);
        ``pickup_configurations`` each named pickup layout to its
        ``[neck, middle, bridge]`` types (the body editor turns a layout
        into "custom" to remove one pickup).
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
    upgraded = {**design, "prototype": prototype}
    if "machining" in design:
        upgraded["machining"] = machining
    return upgraded


DESIGN_FORMAT = "cncguitarwizard-design"
"""The ``format`` entry of a design saved with the web app's Save design."""


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
    screws), ``bolt:N`` (a neck bolt's ferrule and hole), ``jack`` and
    ``pickguard`` (the guard and its screw spots in the body); the neck,
    its pocket and the bridge do not move.
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
        ``rear``, ``cover``,
        ``contour_top`` (an arm contour), ``contour_back`` (a belly cut) or
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
        ``arm_contour`` and ``belly_cut`` ``{"points", "automatic"}`` — the
        lines where they start (see ``_contour_line``) — or ``None``;
        ``frames`` each humbucker frame's ``{"position", "field", "turned",
        "adjusted", "problem", "points", "handles", "origin", "along", "across",
        "stretch", "openings", "holes"}`` — its points in its own frame (as
        its ``field`` holds them) and as handles in the editor's frame, the
        frame's origin and the directions of its own axes there (a handle
        dragged to ``p`` is at ``a = (p - origin)·along``, ``c`` the same
        across, narrowed by half the ``stretch``), and why it does not fit,
        or ``None``;
        ``engraving`` the decorative engraving's lines, or ``None``;
        ``relief`` a relief engraving's shapes ``{"outline", "depth"}``
        (camo), empty for none.
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
    circles = [
        {
            "name": hole.name,
            "group": _editor_group(hole.name),
            "x": round(hole.center_x - heel_end, 2),
            "y": round(hole.center_y, 2),
            "r": hole.diameter / 2.0,
        }
        for hole in layout.holes
    ]
    circles += [
        {
            "name": hole.name,
            "group": _editor_group(hole.name),
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
        "pickguard": (
            {
                "points": local(layout.pickguard.control_points),
                "automatic": layout.pickguard.automatic,
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
                "handles": local(
                    [frame.placing.to_model(a, c) for a, c in frame.points]
                ),
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


def _steps_view(
    parameters: Prototype001Parameters, layout: Any, local: Any
) -> dict[str, Any] | None:
    """Return a stepped top's lines for the editor, or ``None``.

    ``{"points", "automatic"}``: each step's points (straight lines
    between them, the outermost first) — the shape's drawn
    ``step_points`` as widened, or the automatic steps simplified to
    handles within ``STEP_HANDLE_TOLERANCE``.
    """
    steps = layout.stepped_top
    if steps is None:
        return None
    drawn = bool(parameters.built_body_shape.step_points)
    return {
        "points": [
            local(boundary if drawn else simplified(boundary, STEP_HANDLE_TOLERANCE))
            for boundary in steps.boundaries
        ],
        "automatic": not drawn,
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
    widened for the instrument), or ``CONTOUR_HANDLES`` points along the
    automatic contour's inner edge, its ends on the body's edge.
    """
    contour = next((c for c in contours if c.name == name), None)
    if contour is None:
        return None
    shape = widened_shape(parameters.body_shape, parameters.body_widening_amount())
    drawn = getattr(shape, field)
    if drawn:
        return {"points": [[x, y] for x, y in drawn], "automatic": False}
    inner = contour.inner_edge()
    picks = [
        round(k * (len(inner) - 1) / (CONTOUR_HANDLES - 1))
        for k in range(CONTOUR_HANDLES)
    ]
    return {"points": local(inner[i] for i in picks), "automatic": True}


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
        "limits", "markers", "frets", "problem"}`` or ``{"error": message}``: the
        first marker's fret, its fret space from ``front`` to ``back`` (mm
        from the nut), the board's half-width at the nut and at the last
        fret (``final_position`` from the nut), the marker's shape as
        ``[along, across]`` points (the drawn one, or the style's own at
        that fret), ``limits`` (``along`` from and to, ``across`` either
        side: ``custom_limits``) inside which a drawn corner fits every
        marker, every marker's outline and every fret's line for the
        board's preview, and ``problem``, why the markers cannot be cut as
        drawn (``None`` when they can).
    """
    try:
        built = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
        parameters = dataclasses.replace(built, handedness="right")
        surface = parameters.fretboard_surface()
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}
    positions = {
        fret.number: fret.distance_from_nut
        for fret in FretCalculator.calculate(surface.scale_length, surface.fret_count)
    }
    frets = sorted(
        fret
        for fret in (
            *parameters.inlay_single_marker_frets,
            *parameters.inlay_double_marker_frets,
        )
        if 1 <= fret <= surface.fret_count
    )
    if not frets:
        return {"error": "No fret has a marker (inlay_single_marker_frets)."}
    first = frets[0]
    final = positions[surface.fret_count]
    problem: str | None = None
    markers: list[list[list[float]]] = []
    points: list[list[float]] = [
        [float(value) for value in point]
        for point in parameters.inlay_points
        if len(point) == 2
    ]
    try:
        layout = parameters.inlay_design(surface)
        markers = [
            [[round(p.x, 2), round(p.y, 2)] for p in marker.outline]
            for marker in layout.markers
        ]
        points = [[along, across] for along, across in layout.editable_points()]
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        problem = str(error)
    if not points:
        points = [[along, across] for along, across in DEFAULT_CUSTOM_POINTS]
    skew = surface.skew

    def half_at(position: float) -> float:
        return (
            surface.nut_width
            + (surface.last_fret_width - surface.nut_width) * position / final
        ) / 2.0

    (low, high), across = custom_limits(surface, frets)

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
        "bass_sign": parameters.bass_sign,
        "mirrored": built.left_handed,
        "custom": parameters.inlay_style == "custom",
        "points": points,
        "limits": {"along": [low, high], "across": across},
        "markers": markers,
        "frets": [fret_line(0.0)]
        + [fret_line(positions[n]) for n in range(1, surface.fret_count + 1)],
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
        "sample_step", "start_edges": {"bass", "treble"}, "holes"}`` or
        ``{"error": message}``. ``start_edges`` are the fitted outline's
        edges, sampled halfway to the shoulder, at the shoulder, at seven
        points along the taper and at the tip (ten handles a side);
        ``holes`` is a list of ``{"side", "x", "y", "r"}``; ``lettering``
        the headstock's lettering (see ``_headstock_lettering``), or ``None``;
        ``engraving`` the lines drawn on its face (see
        ``_headstock_drawn_engraving``), or ``None``.
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
        "nut": nut,
        "mirrored": built.left_handed,
        "nut_half_width": parameters.nut_width / 2.0,
        "bass_sign": fitted.bass_sign,
        "min_edge_distance": parameters.tuner_edge_offset,
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


def _truss_cover_drawing(parameters: Prototype001Parameters) -> dict[str, Any] | None:
    """Return the truss-rod cover for the headstock editor, or ``None``.

    ``{"outline", "screws", "screw_radius", "trough", "back", "length",
    "width", "style", "corners", "screw_points", "problem"}``: the cover's
    outline and screw centres and the trough under it (model frame, as
    drawn); its nut end's X, its size and style; its corners and screws as
    ``truss_rod_cover_points`` / ``_screws`` would hold them, for the
    editor to move one or add one (a drawn, ``custom``, cover from then
    on); and why it does not fit, or ``None``. Drawn even where it does
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
    corners, screw_points = editable_cover_points(shape, length, width)
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


def outline_template(payload: dict[str, Any], part: str) -> dict[str, Any]:
    """Return the body's, the headstock's or a marker's outline as an SVG template.

    The template (see ``drawings.template_svg``) is drawn 1:1 in
    millimetres, as the editor shows the design (mirrored for a
    left-handed build, a seven- or eight-string body widened): its
    *Outline* layer the outline, a node at every handle; its *Reference*
    layer, locked, what the outline is drawn round — the neck, routes,
    cavities and bridge line, or the nut, tuner holes (and the edge's
    clearance round them) and truss-rod cover, or the first marker's
    fret space and where its corners fit — and three registration
    marks. ``import_outline`` reads it back.

    Args:
        payload: ``{"prototype": {...}}`` as for ``start_build``.
        part: ``"body"`` (a drawn, Your design, body), ``"headstock"``
            (a drawn headstock) or ``"inlay"`` (the fret markers' shape,
            drawn on the first marker as in the inlay editor).

    Returns:
        ``{"svg": text}`` or ``{"error": message}``.
    """
    try:
        if part == "body":
            return {"svg": _body_template(payload)}
        if part == "headstock":
            return {"svg": _headstock_template(payload)}
        if part == "inlay":
            return {"svg": _inlay_template(payload)}
        return {"error": f"There is no {part!r} outline."}
    except _LaidOutError as error:
        return {"error": str(error)}
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}


def import_outline(payload: dict[str, Any], part: str, svg: str) -> dict[str, Any]:
    """Return the form values that draw an outline read from a template.

    The outline is placed by the template's registration marks and turned
    into the editor's own handles (``drawings.fit_closed_spline``,
    ``drawings.fit_headstock``), every one on the drawn line, as many as
    keep the editor's curve within 0.25 mm of it; a marker's into its
    corners (a curve into corners within ``INLAY_IMPORT_TOLERANCE`` of
    it), each held where it fits every marker. An outline exported and
    read back unchanged comes back as it was.

    Args:
        payload: ``{"prototype": {...}}`` as for ``start_build``.
        part: ``"body"``, ``"headstock"`` or ``"inlay"``.
        svg: The SVG file's text.

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


def _body_template(payload: dict[str, Any]) -> str:
    shape, layout = _drawn_body(payload)
    widening = float(layout["widening"] or 0.0)
    points = [Point2D(x, y) for x, y in widen_points(shape.control_points, widening)]
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
    return template_svg(
        "CNCguitarwizard body outline",
        TemplateFrame(_BODY_MARKS, bool(layout["mirrored"])),
        closed_catmull_rom_spans(points),
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
    fit = fit_closed_spline(read.points, read.nodes)
    points = [
        [round(point.x, 2), round(narrow_y(point.y, widening), 2)]
        for point in fit.points
    ]
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


def _headstock_template(payload: dict[str, Any]) -> str:
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
    return template_svg(
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
        read.points, layout["nut_half_width"], layout["bass_sign"], read.nodes
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


def _inlay_template(payload: dict[str, Any]) -> str:
    layout = _laid_out_inlay(payload)
    length = layout["back"] - layout["front"]
    pad = 6.0

    def edge(x: float, side: float) -> Point2D:
        return Point2D(x, side * _inlay_half(layout, layout["front"] + x))

    low, high = layout["limits"]["along"]
    across = layout["limits"]["across"]
    corners = [_inlay_mm(layout, along, side) for along, side in layout["points"]]
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
    return template_svg(
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
    shown = [_inlay_mm(layout, along, side) for along, side in layout["points"]]
    moved = 0
    if len(corners) == len(shown) and all(
        math.hypot(a.x - b.x, a.y - b.y) <= 0.01
        for a, b in zip(corners, shown, strict=True)
    ):
        # Unchanged: the editor's own corners, exactly.
        points = [[float(v) for v in point] for point in layout["points"]]
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
    }.get(group, group)


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
                "name": f"{setup.name}{writer.extension}",
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


def nc_archive(name: str = "") -> dict[str, str]:
    """Return the last build's NC programs in one ZIP, named for the guitar.

    Inside a folder named ``name``, one folder a part, each program
    numbered in running order (``Neck/02_Neck_top.nc``), and a
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
        default = (
            field.default
            if field.default is not dataclasses.MISSING
            else field.default_factory()  # type: ignore[misc]
        )
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
