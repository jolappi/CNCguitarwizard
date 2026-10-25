"""When a setting does anything: the settings that matter only beside
other settings' values, for the web app to show only those that do.

``APPLIES_WHEN`` maps a setting (a design's or its machining's) to the
conditions, on the design's settings, under which it changes the
instrument or its programs at all: any one of them, each holding when every setting it
names has one of its values (``NOT_EMPTY`` standing for any text but
none, ``ABOVE_ZERO`` for any number above nought); a setting it does not
name always applies. The web app hides a
setting, in its form and wherever a copy of it stands, while none of its
conditions hold (a heel's thickness on a neck run through the body, whose
heel is the body's own wood). Each rule was found by building the
instrument with the setting changed and seeing nothing change while its
conditions do not hold (``tests/test_setting_conditions.py`` checks every
one again); where that depends on more than the settings named (a drawn
pickguard, the instrument's own tuners), the setting is shown.
"""

from __future__ import annotations

NOT_EMPTY = "<any text>"
"""A condition's value standing for any text but none (lettering typed)."""

ABOVE_ZERO = "<above 0>"
"""A condition's value standing for any number above nought (a separate
top's thickness)."""

Condition = dict[str, tuple[str | bool, ...]]
"""The values each named setting must have, any one of them."""

BOLTED_OR_SET = ("bolt_on", "set")
"""Neck joints with a heel in a pocket: screwed in or glued."""

RUNS_THROUGH = ("neck_through", "one_piece")
"""Neck joints whose neck blank is the body's own centre."""

HEEL_RELIEVED = ("contour", "notch", "bevel")
"""``body_heel_relief`` kinds that relieve the heel at all."""

NECK_PLATES = ("plate", "asymmetric")
"""``body_neck_plate`` kinds that hold the neck with a plate."""

NO_LOCKING_NUT = ("auto", "none")
"""``locking_nut`` values that may leave the nut a nut ("auto" fits one
only with a Floyd Rose bridge)."""

ANY_LOCKING_NUT = ("auto", "r2", "r3", "r7", "r8")
"""``locking_nut`` values that may fit a locking nut."""

CONTROLS = (
    "almond_2",
    "gibson_4",
    "rear_3",
    "superstrat",
    "volume_1",
    "active_4",
    "tele",
    "jazz_bass",
    "pickguard",
)
"""``body_controls`` layouts with any controls at all."""

REAR_COVERED = tuple(c for c in CONTROLS if c != "pickguard")
"""Control layouts in rear cavities under cover plates."""

WITH_A_NECK_PICKUP = ("HH", "HSH", "HSS", "SSS", "SS", "PJ", "JJ", "P", "RR", "custom")
"""``body_pickups`` layouts with a pickup at the neck (``P``'s and
``PJ``'s unproven, so kept)."""

WITH_A_MIDDLE_PICKUP = ("HSH", "HSS", "SSS", "PJ", "P", "custom")
"""Layouts with a middle single coil (``P``'s and ``PJ``'s kept)."""

WITH_A_BRIDGE_SINGLE_COIL = ("SSS", "SS", "PJ", "P", "custom")
"""Layouts with a single coil at the bridge (``P``'s and ``PJ``'s kept)."""

WITH_HUMBUCKERS = ("HH", "HSH", "HSS", "H", "PJ", "P", "custom")
"""Layouts with a framed humbucker (``P``'s and ``PJ``'s kept)."""

SYMMETRIC_HEADSTOCKS = ("3+3", "2+2", "4+4")
"""Headstock styles with as many tuners each side, none in a row."""

OTHER_HEADSTOCKS = (
    "6_inline",
    "6_inline_reverse",
    "4+2",
    "2+4",
    "4_inline",
    "4_inline_reverse",
    "4+1",
    "1+4",
    "3+2",
    "2+3",
    "5_inline",
    "5_inline_reverse",
    "4+3",
    "3+4",
    "7_inline",
    "7_inline_reverse",
    "8_inline",
    "8_inline_reverse",
)
"""Headstock styles with tuners in a row on a side."""


def _when(names: str, *conditions: Condition) -> dict[str, tuple[Condition, ...]]:
    """Return the conditions for each of the space-separated setting names."""
    return {name: conditions for name in names.split()}


APPLIES_WHEN: dict[str, tuple[Condition, ...]] = {
    # The neck's joint: a heel in a pocket, bolted or glued.
    **_when(
        "heel_thickness heel_mounting_length heel_root_length neck_heel_end "
        "body_neck_pocket_length neck_angle body_heel_relief",
        {"neck_joint": BOLTED_OR_SET},
    ),
    **_when("set_neck_glue_gap", {"neck_joint": ("set",)}),
    **_when(
        "body_neck_pocket_clearance body_neck_plate body_neck_bolt_hole_diameter "
        "body_neck_bolt_edge_wall body_neck_bolt_end_wall "
        "body_neck_bolt_center_offset",
        {"neck_joint": ("bolt_on",)},
    ),
    **_when(
        "body_neck_ferrule_diameter body_neck_ferrule_depth "
        "body_neck_bolts_outward body_neck_bolt_spacing_x body_neck_bolt_spacing_y",
        {"neck_joint": ("bolt_on",), "body_neck_plate": ("ferrules",)},
    ),
    **_when(
        "body_neck_plate_length body_neck_plate_width body_neck_plate_hole_inset",
        {"neck_joint": ("bolt_on",), "body_neck_plate": NECK_PLATES},
    ),
    **_when(
        "body_neck_plate_clip",
        {"neck_joint": ("bolt_on",), "body_neck_plate": ("asymmetric",)},
    ),
    **_when(
        "body_heel_relief_depth body_heel_relief_reach body_heel_relief_line",
        {"neck_joint": BOLTED_OR_SET, "body_heel_relief": HEEL_RELIEVED},
    ),
    # A neck run through the body falls to its thickness ahead of it.
    **_when("neck_through_heel_ramp", {"neck_joint": RUNS_THROUGH}),
    **_when("neck_through_width", {"neck_joint": ("neck_through",)}),
    # The heel's and the headstock's joints drawn, and the volute.
    **_when(
        "heel_root_flat_points heel_root_neck_points", {"heel_root_style": ("drawn",)}
    ),
    **_when(
        "headstock_pointed_volute_depth headstock_pointed_volute_length "
        "headstock_volute_style headstock_volute_points "
        "headstock_volute_headstock_points headstock_volute_neck_points",
        {"headstock_pointed_volute": (True,)},
    ),
    **_when("headstock_root_style", {"headstock_pointed_volute": (False,)}),
    **_when(
        "headstock_root_flat_points headstock_root_neck_points",
        {"headstock_pointed_volute": (False,), "headstock_root_style": ("drawn",)},
    ),
    # Tuners in a row: their spacing and the tip beyond the last.
    **_when(
        "tuner_inline_first_distance tuner_inline_spacing tuner_post_diameter "
        "tuner_tip_margin",
        {"headstock_style": OTHER_HEADSTOCKS},
    ),
    # Lettering on the headstock, once there is any.
    **_when(
        "headstock_engraving_font headstock_engraving_height "
        "headstock_engraving_x headstock_engraving_y headstock_engraving_angle",
        {"headstock_engraving_text": (NOT_EMPTY,)},
    ),
    # The nut: its slot in the board, a zero fret's gap.
    **_when(
        "nut_slot_depth nut_slot_lip nut_slot_taper nut_thickness",
        {"nut_style": ("slot", "zero_fret")},
    ),
    **_when("zero_fret_gap", {"nut_style": ("zero_fret",)}),
    **_when(
        "locking_nut_screw_depth locking_nut_screw_diameter",
        {"locking_nut": ANY_LOCKING_NUT},
    ),
    **_when("fret_height", {"locking_nut": ANY_LOCKING_NUT}, {"nut_jig": (True,)}),
    **_when(
        "fretboard_nut_corner_radius",
        {"locking_nut": NO_LOCKING_NUT, "nut_style": ("shelf",)},
        {"locking_nut": ("r3",)},
    ),
    **_when("nut_jig_height nut_jig_slot_play nut_jig_thickness", {"nut_jig": (True,)}),
    # The fretboard's end and scallops.
    **_when("fretboard_end_extension", {"fretboard_end": ("auto", "fret")}),
    **_when(
        "fretboard_scallop_from_fret fretboard_scallop_depth fretboard_scallop_land",
        {"fretboard_scalloped": (True,)},
    ),
    # Carbon rods, when fitted; their own size when not a stock one.
    **_when(
        "neck_carbon_rod_size neck_carbon_rod_start neck_carbon_rod_length "
        "neck_carbon_rod_offset",
        {"neck_carbon_rods": (True,)},
    ),
    **_when(
        "neck_carbon_rod_width neck_carbon_rod_depth",
        {"neck_carbon_rods": (True,), "neck_carbon_rod_size": ("custom",)},
    ),
    # The truss rod: the standard one's step, pocket and sleeve, the
    # low-profile one's own channel, a cover over the headstock's trough.
    # (A vintage rod's adjuster stays shown: choosing another goes back
    # to a rod routed from the top.)
    **_when(
        "truss_rod_width truss_rod_depth truss_rod_axis_depth "
        "truss_rod_pocket_length truss_rod_step_length",
        {"truss_rod_profile": ("standard",)},
    ),
    **_when(
        "truss_rod_low_profile_width truss_rod_low_profile_depth",
        {"truss_rod_profile": ("low_profile",)},
    ),
    **_when(
        "truss_rod_access_length",
        {"truss_rod_profile": ("standard",), "truss_rod_spoke_wheel": ("auto", "yes")},
    ),
    **_when("truss_rod_start", {"truss_rod_adjustment": ("heel",)}),
    **_when(
        "truss_rod_sleeve_bore",
        {
            "truss_rod_adjustment": ("heel",),
            "truss_rod_spoke_wheel": ("auto", "yes"),
            "truss_rod_profile": ("standard",),
        },
    ),
    **_when(
        "truss_rod_sleeve_length",
        {
            "truss_rod_adjustment": ("heel",),
            "truss_rod_spoke_wheel": ("auto", "yes"),
            "truss_rod_profile": ("standard",),
        },
    ),
    **_when(
        "truss_rod_sleeve_diameter",
        {
            "truss_rod_adjustment": ("heel",),
            "truss_rod_spoke_wheel": ("auto", "yes"),
            "truss_rod_profile": ("standard",),
            "truss_rod_sleeve_bore": (True,),
        },
    ),
    **_when(
        "truss_rod_trough truss_rod_key_hole_diameter truss_rod_cover "
        "truss_rod_cover_style truss_rod_cover_length truss_rod_cover_width "
        "truss_rod_cover_points truss_rod_cover_screws",
        {"truss_rod_adjustment": ("headstock",)},
    ),
    # The body: pickups by layout, their frames.
    **_when(
        "body_neck_pickup body_middle_pickup body_bridge_pickup",
        {"body_pickups": ("custom",)},
    ),
    **_when(
        "body_neck_pickup_offset body_neck_pickup_angle",
        {"body_pickups": WITH_A_NECK_PICKUP},
    ),
    **_when("body_middle_pickup_angle", {"body_pickups": WITH_A_MIDDLE_PICKUP}),
    **_when(
        "body_bridge_single_coil_angle", {"body_pickups": WITH_A_BRIDGE_SINGLE_COIL}
    ),
    **_when(
        "body_pickup_frame body_pickup_screw_spacing",
        {"body_pickups": WITH_HUMBUCKERS},
    ),
    **_when(
        "body_pickup_frame_thickness",
        {
            "body_pickups": WITH_HUMBUCKERS,
            "body_pickup_frame": ("ring", "horns", "hook"),
        },
    ),
    **_when(
        "body_pickup_frame_direction",
        {
            "body_pickups": WITH_HUMBUCKERS,
            "body_pickup_frame": ("ring", "horns", "hook"),
        },
    ),
    # The controls, their cavities and covers, the switch.
    **_when(
        "body_pot_shaft_hole_diameter body_wire_channels",
        {"body_controls": CONTROLS},
    ),
    **_when(
        "body_rear_cavity_top_wall",
        {"body_controls": CONTROLS},
        {"body_battery_box": (True,)},
    ),
    **_when(
        "body_cover_recess_depth",
        {"body_controls": REAR_COVERED},
        {"body_battery_box": (True,)},
    ),
    **_when(
        "body_switch body_switch_shaft_hole_diameter",
        {"body_controls": ("almond_2", "gibson_4", "rear_3", "volume_1")},
    ),
    **_when("body_pickguard", {"body_controls": REAR_COVERED + ("none",)}),
    **_when(
        "body_pickguard_style body_pickguard_margin body_pickguard_thickness",
        {"body_pickguard": (True,)},
        {"body_controls": ("pickguard",)},
    ),
    **_when("body_jack_plate", {"body_jack": ("side", "plate", "top")}),
    **_when(
        "body_jack_plate_thickness",
        {"body_jack": ("side", "plate", "top"), "body_jack_plate": (True,)},
    ),
    # The top: a carved top takes all of it, a stepped one all but the
    # carve; only a flat top takes an arm contour, a bevel round its edge or
    # an epoxy tray (and only a body of its own a tray).
    **_when("body_stepped_top", {"body_carved_top": (False,)}),
    **_when(
        "body_top_step_insets body_top_step_height",
        {"body_carved_top": (False,), "body_stepped_top": (True,)},
    ),
    **_when(
        "body_arm_contour_depth body_arm_contour_width body_arm_contour_length "
        "body_arm_contour_position body_top_bevel_width",
        {"body_carved_top": (False,), "body_stepped_top": (False,)},
    ),
    **_when(
        "body_epoxy_tray_depth body_epoxy_tray_rim",
        {
            "neck_joint": BOLTED_OR_SET,
            "body_carved_top": (False,),
            "body_stepped_top": (False,),
        },
    ),
    # The body's other features, when fitted.
    **_when(
        "body_battery_count body_battery_cavity_length body_battery_cavity_width "
        "body_battery_cavity_depth body_battery_cover_margin",
        {"body_battery_box": (True,)},
    ),
    **_when(
        "body_carve_depth body_carve_margin body_carve_rim",
        {"body_carved_top": (True,)},
    ),
    # A separate top on a body of its own only; its chambers with one only.
    **_when("body_cap_thickness", {"neck_joint": BOLTED_OR_SET}),
    **_when(
        "body_chambers",
        {"neck_joint": BOLTED_OR_SET, "body_cap_thickness": (ABOVE_ZERO,)},
    ),
    **_when(
        "body_engraving_pattern body_engraving_seed body_engraving_depth "
        "body_engraving_spacing body_engraving_margin body_engraving_clearance",
        {"body_engraving": (True,)},
    ),
    **_when(
        "body_strap_guide_thickness body_strap_guide_gap body_strap_width "
        "body_strap_guide_screw_diameter body_strap_guide_screw_depth",
        {"body_strap_guide": (True,)},
    ),
    # Machining: a feature's own cutter, when the design has the feature.
    **_when(
        "carve_tool_diameter carve_finish carve_flat_tool_diameter "
        "carve_step_down carve_flat_step_down",
        {"body_carved_top": (True,)},
    ),
    **_when("nut_jig_tool_diameter", {"nut_jig": (True,)}),
}


def holds(condition: Condition, values: dict[str, object]) -> bool:
    """Return whether every setting ``condition`` names has one of its
    values in ``values`` (``NOT_EMPTY``: any text but none; ``ABOVE_ZERO``:
    any number above nought)."""
    return all(_fits(values[other], allowed) for other, allowed in condition.items())


def _fits(value: object, allowed: tuple[str | bool, ...]) -> bool:
    """Return whether ``value`` is one of ``allowed``, or what a marker in it
    stands for."""
    if ABOVE_ZERO in allowed:
        return (
            isinstance(value, int | float)
            and not isinstance(value, bool)
            and value > 0.0
        )
    return value in allowed or (NOT_EMPTY in allowed and value != "")


def applies(name: str, values: dict[str, object]) -> bool:
    """Return whether setting ``name`` changes the instrument beside the
    other settings' ``values`` (``APPLIES_WHEN``: any of its conditions)."""
    conditions = APPLIES_WHEN.get(name)
    return conditions is None or any(holds(c, values) for c in conditions)
