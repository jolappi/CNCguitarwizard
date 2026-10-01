"""Glue for running the Prototype001 build inside a browser (Pyodide).

The static web page in ``site/`` loads the package as a wheel into
Pyodide and calls the two functions here: ``parameter_schema`` to draw
its form, and ``run_build`` to produce every FreeCAD-free artifact in
the browser's virtual file system. Both speak plain JSON-compatible
dictionaries so the JavaScript side needs no knowledge of the
dataclasses.
"""

from __future__ import annotations

import dataclasses
import json
import math
import types
import typing
from pathlib import Path
from typing import Any

from .cam import (
    POST_PROCESSOR_LABELS,
    GCodeWriter,
    MachiningParameters,
    plan_feature_machining,
)
from .exceptions import CNCGuitarWizardError
from .geometry.body import (
    BRIDGE_KINDS,
    BRIDGE_LABELS,
    BRIDGE_MAX_STRINGS,
    bridge_spec_from_dict,
)
from .geometry.neck import LOCKING_NUT_SPECS
from .geometry.primitives import Point2D, point_in_polygon
from .presets import Prototype001Parameters
from .presets.body_shapes import (
    BODY_SHAPE_KINDS,
    BODY_SHAPE_LABELS,
    OUTLINE_SAMPLES_PER_SEGMENT,
    YOUR_DESIGN_START_POINTS,
    YOUR_DESIGN_TEMPLATES,
    body_shape_from_dict,
)
from .presets.controls import CONTROL_LABELS
from .presets.pickups import PICKUP_CONFIGURATIONS
from .presets.prototype001 import INSTRUMENT_OVERRIDES
from .render.svg import render_plan_view_svg
from .workflows import Prototype001Build

_VARIANT_LABELS: dict[str, str] = {**BRIDGE_LABELS, **BODY_SHAPE_LABELS}

# Readable names for choice fields whose options are short codes.
_CHOICE_LABELS: dict[str, dict[str, str]] = {
    "body_controls": CONTROL_LABELS,
    "post_processor": POST_PROCESSOR_LABELS,
    "neck_blank": {
        "solid": "One plank as thick as the headstock needs",
        "laminated": "Neck plank first, headstock block glued on after",
    },
    "locking_nut": {
        "auto": "Auto (Floyd Rose Original R2 with a Floyd Rose bridge)",
        "none": "Plain nut",
        "r2": "Floyd Rose R2 locking nut (41.3 mm)",
        "r3": "Floyd Rose R3 locking nut (42.85 mm)",
    },
    "body_jack": {
        "side": "Side jack (Les Paul style plate or barrel jack)",
        "cup": "Cup jack or Electrosocket (7/8 in counterbore)",
        "strat": "Stratocaster style top plate (cavity from the top)",
    },
    "body_pickguard_style": {
        "stratocaster": "Stratocaster (beside the neck, a tail past the bridge)",
        "superstrat": "Superstrat (close round the pickups)",
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
        "truss_rod_rod_length",
        "bass_scale_length",
        "perpendicular_fret",
        "nut_width",
        "fretboard_radius",
        "fretboard_thickness",
        "inlay_style",
        "final_fret_width",
        "first_fret_thickness",
        "twelfth_fret_thickness",
        "neck_profile_exponent",
        "heel_width",
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
        "body_battery_box",
        "body_battery_count",
        "locking_nut",
        "body_pickups_follow_fan",
        "body_bridge_follows_fan",
        "body_top_edge_radius",
        "body_back_edge_radius",
        "body_top_binding_width",
        "body_arm_contour_depth",
        "body_belly_cut_depth",
        "body_neck_pickup_offset",
        "body_bridge_pickup_offset",
        "tool_diameter",
        "tool_tip",
        "post_processor",
        "spindle_dwell",
        "neck_blank",
        "spindle_speed",
        "feed_rate",
        "plunge_rate",
        "step_down",
        "step_over",
        "tab_count",
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
    "floyd_rose": frozenset({"treble_side", "pivot_offset", "pivot_stud_spacing"}),
    "tune_o_matic": frozenset(
        {"post_spacing", "compensation", "stud_spacing", "tailpiece_offset"}
    ),
    "hardtail": frozenset({"string_spacing", "string_hole_offset", "screw_count"}),
}

_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
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
        ``{"label", "overrides"}``, the defaults that differ for it
        where every group is ``{"title", "fields"}`` and every field is
        ``{"name", "type", "default", "advanced"}`` with ``type`` one of
        ``float``, ``int``, ``bool``, ``optional_float``, ``json``
        (tuples), ``choice`` (a ``Literal`` of strings, listed in
        ``options``) or ``variant`` — a choice between dataclasses that
        each carry a ``kind`` field (the bridge), described by
        ``variants``: ``{kind: {"label", "fields"}}``. ``advanced`` is
        true for the rarely changed fields the form folds away.
        ``locking_nut_widths`` maps each locking nut to its width, the
        least ``nut_width`` it fits (the form widens the neck to it);
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
        ``{"error": message}``. ``scale_line`` is the bridge line's X on
        the centerline (a multiscale's mean scale). ``widening`` is the
        body's opening along the centreline (see
        ``body_shapes.widen_points``), which the editor applies to the
        drawn control points as Python does.
        ``templates`` maps a key to ``{"label", "shape"}``, the shape as
        the form's JSON. ``polygons`` is a list of ``{"name", "role",
        "group", "points"}`` with ``role`` one of ``neck``, ``pocket``,
        ``pickup``, ``bridge``, ``bridge_plate`` (what a bridge such as a
        Kahler covers on the top past its routes), ``top_control``,
        ``rear``, ``cover``,
        ``contour_top`` (an arm contour) or ``contour_back`` (a belly cut);
        ``circles`` a list of ``{"name", "group", "x", "y", "r"}``;
        ``jack`` ``{"group", "x", "y", "x2", "y2", "r", "cup",
        "reaches_controls"}`` (``cup`` a cup jack's counterbore ``{"x2",
        "y2", "r"}`` or ``None``; ``reaches_controls`` whether the bore
        ends in the control cavity); ``control``
        ``{"centre", "axis", "ends", "sides"}`` — the control cavity's
        centre, its long axis (a unit vector), the two ends of its cover
        (or the Tele plate) on that axis and its two sides square to it,
        the editor's stretch handles — or ``None`` without a control
        layout; ``pickguard`` ``{"points", "automatic", "openings",
        "holes"}`` — the guard's control points (laid out automatically or
        drawn), its pickup and switch openings and its holes — or ``None``.
    """
    try:
        parameters = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
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

    polygons: list[dict[str, Any]] = [
        polygon("Neck", "neck", neck.boundary),
        polygon(layout.neck_pocket.name, "pocket", layout.neck_pocket.outline),
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
    # Contours go under everything else on the body (after the neck).
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
    jack = layout.jack_hole
    radians = math.radians(jack.direction_degrees)
    jack_end = Point2D(
        jack.start_x + jack.depth * math.cos(radians),
        jack.start_y + jack.depth * math.sin(radians),
    )
    control_outlines = [
        *((controls.control_cavity.cavity.outline,) if controls.control_cavity else ()),
        *(top.outline for top in controls.top_cavities if top.name == "Control cavity"),
    ]
    return {
        "heel_end": round(heel_end, 2),
        "scale_line": round(parameters.centre_scale, 3),
        "samples_per_segment": OUTLINE_SAMPLES_PER_SEGMENT,
        "widening": parameters.body_widening_amount(),
        "start_points": [list(point) for point in YOUR_DESIGN_START_POINTS],
        "templates": {
            key: {"label": label, "shape": _jsonable(shape)}
            for key, (label, shape) in YOUR_DESIGN_TEMPLATES.items()
        },
        "polygons": polygons,
        "circles": circles,
        "jack": {
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
        },
        "control": control,
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
        ``holes`` is a list of ``{"side", "x", "y", "r"}``.
    """
    try:
        parameters = Prototype001Parameters(**_coerce(payload.get("prototype", {})))
        fitted, _ = dataclasses.replace(
            parameters, headstock_outline="fitted"
        ).headstock_design()
        centres = parameters.tuner_centres()
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


_ACTIVE_BUILD: Prototype001Build | None = None


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
    ):
        files[path.name] = path.read_text(encoding="utf-8")
    report = json.loads(files[result.report_path.name])
    return {
        "files": files,
        "report": report,
        "plan_view": render_plan_view_svg(build.geometry),
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
