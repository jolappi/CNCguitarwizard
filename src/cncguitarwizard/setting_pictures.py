"""Where each setting shows on the guitar, for its picture in the web app.

Beside a setting the web app shows a small picture of the guitar being
designed, the parts that setting shapes picked out, larger when clicked.
It is one of the design's own drawings (``webapp.setting_views``): the
whole instrument from the front (``"plan"``, ``render_plan_view_svg``),
the neck or the fretboard from above, from the side and in section
(``"neck"``, ``"fretboard"``, ``render.svg.neck_views``), each part of
which carries its name. A setting's picture names its view and the parts
to pick out as regular expressions matched against those names, tried in
turn: the first that finds a part in the design is the one shown (the
battery box's cavity, say, or the body itself while there is none).
"""

from __future__ import annotations

SettingPicture = tuple[str, tuple[str, ...]]
"""A setting's picture: its view, and the parts to pick out in it, the
first pattern that finds one."""

_BODY = r"^Body$"
_NUT_AND_BRIDGE = (
    r"^(Nut|Locking nut)$|^Bridge (post|pivot|baseplate|screw)|^Tailpiece"
    r"|^String \d+ (ferrule|through)|^Floyd Rose (recess|block route)"
)
_BRIDGE = (
    r"^Bridge (post|pivot|baseplate|screw|ground)|^Tailpiece|^String \d+"
    r"|^Floyd Rose|^Trem claw"
)
_FRET_SLOTS = r"^(Fret slot \d+|Zero fret slot)$"
_SIDE_SLOTS = r"^Fret slot \d+, from the side$"
_MARKERS = r"^Marker, fret \d+$"
_BEHIND_NUT = r"^The nut$"
_POCKET = r"^Neck pocket$|^Neck-through block$"
_TRUSS_ROD = r"^Truss rod"
_TRUSS_ROD_ENDS = r"^Truss rod (access|adjuster trough)$"
_TUNERS = r"^Tuner hole"
_HEADSTOCK = r"^Headstock$"
_PICKUPS = r"pickup route$"
_CONTROLS = r"^Control|^(Control )?[Pp]ot \d+ shaft hole$|^Switch"
_JACK = r"^Output jack$|^Jack (cavity|hole)$"
_NECK_BOLTS = r"^Neck bolt \d+"


def _same(view: str, names: str, *patterns: str) -> dict[str, SettingPicture]:
    """Return one picture for each of the space-separated setting names."""
    return {name: (view, patterns) for name in names.split()}


SETTING_PICTURES: dict[str, SettingPicture] = {
    "handedness": ("plan", (r"^(Body|Headstock|Neck)$",)),
    # Scale and fretboard
    **_same("plan", "string_count scale_length", _NUT_AND_BRIDGE),
    **_same(
        "fretboard",
        "fret_count frets_per_octave fret_slant_angle bass_scale_length "
        "perpendicular_fret fret_slot_width fret_slot_end_inset",
        _FRET_SLOTS,
    ),
    **_same("fretboard", "fret_slot_depth fret_height", _SIDE_SLOTS),
    "fretboard_end_extension": ("fretboard", (r"^The fretboard from the side$",)),
    "fretboard_nut_corner_radius": ("fretboard", (_BEHIND_NUT,)),
    "fretboard_end": ("plan", (r"^Fretboard$|^Neck pocket$",)),
    **_same(
        "fretboard",
        "fretboard_radius fretboard_thickness",
        r"^The fretboard at fret 12$",
    ),
    "fretboard_binding_width": ("fretboard", (r"^The binding$", r"^The fretboard$")),
    **_same(
        "fretboard",
        "fretboard_scalloped fretboard_scallop_from_fret fretboard_scallop_depth "
        "fretboard_scallop_land",
        r"^Scallop after fret",
        r"^The fretboard$",
    ),
    **_same(
        "fretboard",
        "inlay_depth inlay_single_marker_frets inlay_double_marker_frets "
        "inlay_style inlay_dot_diameter inlay_block_length_fraction "
        "inlay_block_edge_margin inlay_points inlay_runes",
        _MARKERS,
    ),
    # Neck
    **_same(
        "neck",
        "nut_width nut_string_spacing nut_shelf_length nut_style nut_thickness "
        "nut_slot_depth nut_slot_lip nut_slot_taper nut_jig nut_jig_thickness "
        "nut_jig_height nut_jig_gauges nut_jig_slot_play nut_end_u_trim_depth "
        "nut_end_u_side_fillet_radius zero_fret_gap",
        _BEHIND_NUT,
    ),
    **_same(
        "plan",
        "locking_nut locking_nut_screw_diameter locking_nut_screw_depth",
        r"^(Locking nut|Nut)$",
    ),
    **_same(
        "plan",
        "final_fret_width neck_joint neck_heel_end set_neck_glue_gap heel_width "
        "heel_mounting_length heel_length heel_nose_radius heel_block_overlap "
        "heel_root_length heel_scoop_depth heel_root_center_extension "
        "heel_root_style heel_root_flat_points heel_root_neck_points",
        _POCKET,
    ),
    "neck_through_width": ("plan", (r"^Neck-through block$", _POCKET)),
    # The neck's back falling to the body's thickness ahead of the body.
    "neck_through_heel_ramp": ("neck", (r"^The neck from the side$",)),
    "first_fret_thickness": ("neck", (r"^Fret 1: the neck$",)),
    "twelfth_fret_thickness": ("neck", (r"^Fret 12: the neck$",)),
    "neck_profile_exponent": ("neck", (r"^Fret (1|12): the neck$",)),
    **_same(
        "neck",
        "neck_angle heel_thickness joint_fillet_radius",
        r"^The neck from the side$",
    ),
    **_same(
        "plan",
        "truss_rod_start truss_rod_rod_length truss_rod_stock_lengths "
        "truss_rod_length truss_rod_width truss_rod_depth truss_rod_step_length "
        "truss_rod_step_width truss_rod_step_depth truss_rod_pocket_length "
        "truss_rod_pocket_width truss_rod_pocket_depth truss_rod_sleeve_length "
        "truss_rod_sleeve_diameter truss_rod_axis_depth truss_rod_install "
        "truss_rod_profile truss_rod_low_profile_width truss_rod_low_profile_depth "
        "truss_rod_sleeve_bore truss_rod_sleeve_routed truss_rod_trough",
        _TRUSS_ROD,
    ),
    **_same(
        "plan",
        "truss_rod_adjustment truss_rod_nut_diameter truss_rod_nut_length "
        "truss_rod_access_length truss_rod_spoke_wheel truss_rod_key_hole_diameter",
        _TRUSS_ROD_ENDS,
        _TRUSS_ROD,
    ),
    **_same(
        "plan",
        "truss_rod_cover truss_rod_cover_style truss_rod_cover_length "
        "truss_rod_cover_width truss_rod_cover_points truss_rod_cover_screws",
        r"^Truss rod adjuster trough$",
        _HEADSTOCK,
    ),
    **_same(
        "plan",
        "neck_carbon_rods neck_carbon_rod_size neck_carbon_rod_width "
        "neck_carbon_rod_depth neck_carbon_rod_start neck_carbon_rod_length "
        "neck_carbon_rod_offset",
        r"^Carbon fibre rod$",
        r"^Neck$",
    ),
    # Headstock and tuners
    **_same(
        "plan",
        "headstock_style headstock_bass_side headstock_length "
        "headstock_shoulder_width headstock_tip_width headstock_shoulder_shift "
        "headstock_tip_shift headstock_outline headstock_bass_edge "
        "headstock_treble_edge headstock_tip_points headstock_angle "
        "headstock_thickness headstock_face_drop headstock_face_transition "
        "headstock_engraving_text headstock_engraving_font "
        "headstock_engraving_height headstock_engraving_x headstock_engraving_y "
        "headstock_engraving_angle headstock_engraving_depth "
        "headstock_engraving_lines headless headless_length",
        _HEADSTOCK,
    ),
    **_same(
        "plan",
        "tuner_hole_diameter tuner_station_distances tuner_side_offsets "
        "tuner_inline_first_distance tuner_inline_spacing tuner_inline_offsets "
        "tuner_hole_points tuner_edge_offset tuner_tip_margin tuner_post_diameter "
        "tuner_edge_clearance tuner_hole_clearance tuner_chamfer_depth",
        _TUNERS,
    ),
    **_same(
        "neck",
        "headstock_root_length headstock_volute_length headstock_volute_depth "
        "headstock_volute_peak_fraction headstock_root_swell "
        "headstock_pointed_volute headstock_pointed_volute_depth "
        "headstock_pointed_volute_length headstock_volute_style "
        "headstock_volute_points headstock_volute_headstock_points "
        "headstock_volute_neck_points headstock_root_style "
        "headstock_root_flat_points headstock_root_neck_points "
        "headstock_root_side_extension headstock_outer_d_profile_guide_extension",
        _BEHIND_NUT,
    ),
    # Body
    **_same(
        "plan",
        "body_thickness body_shape body_widening body_top_edge_radius "
        "body_back_edge_radius body_top_binding_width body_top_binding_depth "
        "body_back_binding_width body_back_binding_depth body_engraving "
        "body_engraving_pattern body_engraving_seed body_engraving_depth "
        "body_engraving_spacing body_engraving_margin body_engraving_clearance "
        "body_engraving_lines",
        _BODY,
    ),
    **_same(
        "plan",
        "body_neck_pocket_length body_neck_pocket_clearance",
        r"^Neck pocket$",
    ),
    **_same(
        "plan",
        "body_neck_pickup body_neck_pickup_offset body_neck_pickup_angle",
        r"^Neck pickup route$",
        _PICKUPS,
    ),
    **_same(
        "plan",
        "body_middle_pickup body_middle_pickup_offset body_middle_pickup_angle",
        r"^Middle pickup route$",
        _PICKUPS,
    ),
    **_same(
        "plan",
        "body_bridge_pickup body_bridge_pickup_offset body_bridge_pickup_clearance "
        "body_bridge_single_coil_angle body_bridge_pickup_angle",
        r"^Bridge pickup route$",
        _PICKUPS,
    ),
    **_same(
        "plan",
        "body_pickups body_pickup_route_depth body_pickups_follow_fan",
        _PICKUPS,
    ),
    **_same(
        "plan",
        "body_pickup_screw_spacing body_pickup_screw_recess_diameter "
        "body_pickup_screw_recess_extra_depth",
        r"pickup .*screw recess$",
        _PICKUPS,
    ),
    **_same(
        "plan",
        "body_pickup_frame body_pickup_frame_direction body_pickup_frame_thickness "
        "body_neck_frame_points body_middle_frame_points body_bridge_frame_points",
        r"pickup frame screw",
        _PICKUPS,
    ),
    **_same(
        "plan",
        "body_bridge body_bridge_follows_fan bridge_string_spacing",
        _BRIDGE,
    ),
    **_same(
        "plan",
        "body_string_ferrule_diameter body_string_ferrule_depth",
        r"^String \d+ ferrule",
        _BRIDGE,
    ),
    **_same(
        "plan",
        "body_arm_contour_depth body_arm_contour_width body_arm_contour_length "
        "body_arm_contour_position",
        r"^Arm contour$",
        _BODY,
    ),
    **_same(
        "plan",
        "body_belly_cut_depth body_belly_cut_width body_belly_cut_length "
        "body_belly_cut_position",
        r"^Belly cut$",
        _BODY,
    ),
    **_same(
        "plan",
        "body_leg_contour_depth body_leg_contour_width body_leg_contour_length "
        "body_leg_contour_position",
        r"^Leg contour$",
        _BODY,
    ),
    "body_top_bevel_width": ("plan", (r"^Top bevel$", _BODY)),
    "body_back_bevel_width": ("plan", (r"^Back bevel$", _BODY)),
    "body_bevel_angle": ("plan", (r"^(Top|Back) bevel$", _BODY)),
    **_same(
        "plan",
        "body_epoxy_tray_depth body_epoxy_tray_rim",
        r"^Epoxy tray",
        _BODY,
    ),
    **_same(
        "plan",
        "body_heel_relief body_heel_relief_depth body_heel_relief_reach "
        "body_heel_relief_line",
        r"^Heel relief$",
        r"^Neck pocket$",
    ),
    "body_controls": ("plan", (_CONTROLS,)),
    "body_rear_cavity_top_wall": ("plan", (r"cavity \(back\)$",)),
    "body_cover_recess_depth": ("plan", (r"cover recess \(back\)$",)),
    **_same(
        "plan",
        "body_pickguard body_pickguard_thickness body_pickguard_margin "
        "body_pickguard_style",
        r"^Pickguard screw",
        _BODY,
    ),
    **_same(
        "plan",
        "body_carved_top body_carve_depth body_carve_rim body_carve_margin",
        r"^Carved top's plateau$",
        _BODY,
    ),
    **_same(
        "plan",
        "body_stepped_top body_top_step_insets body_top_step_height",
        r"^Stepped top's step$",
        _BODY,
    ),
    **_same(
        "plan",
        "body_battery_box body_battery_count body_battery_cavity_length "
        "body_battery_cavity_width body_battery_cavity_depth "
        "body_battery_cover_margin",
        r"^Battery cavity",
        _BODY,
    ),
    **_same(
        "plan",
        "body_strap_guide body_strap_width body_strap_guide_gap "
        "body_strap_guide_thickness body_strap_guide_screw_diameter "
        "body_strap_guide_screw_depth",
        r"^Strap guide",
        _BODY,
    ),
    "body_switch": ("plan", (r"^Switch",)),
    "body_switch_shaft_hole_diameter": ("plan", (r"^Switch shaft hole$", r"^Switch")),
    "body_pot_shaft_hole_diameter": ("plan", (r"^(Control )?[Pp]ot \d+ shaft hole$",)),
    **_same(
        "plan",
        "body_jack body_jack_diameter body_jack_depth body_jack_plate "
        "body_jack_plate_thickness",
        _JACK,
    ),
    "body_wire_channels": ("plan", (r"wire (hole|channel)$",)),
    **_same(
        "plan",
        "body_neck_bolt_spacing_x body_neck_bolt_spacing_y "
        "body_neck_bolt_center_offset body_neck_bolt_end_wall "
        "body_neck_bolt_edge_wall body_neck_bolts_outward",
        _NECK_BOLTS,
        _POCKET,
    ),
    **_same(
        "plan",
        "body_neck_ferrule_diameter body_neck_ferrule_depth",
        r"^Neck bolt \d+ ferrule",
        _POCKET,
    ),
    "body_neck_bolt_hole_diameter": (
        "plan",
        (r"^Neck bolt \d+ hole", _POCKET),
    ),
    **_same(
        "plan",
        "body_neck_plate body_neck_plate_length body_neck_plate_width "
        "body_neck_plate_hole_inset body_neck_plate_clip",
        r"^Neck plate \(back\)$",
        _NECK_BOLTS,
        _POCKET,
    ),
    # Machining: the programs of one part.
    **_same(
        "neck",
        "neck_blank neck_back_cut",
        r"^The neck from the side$",
    ),
    **_same(
        "fretboard",
        "fretboard_blank_length fretboard_blank_width fretboard_blank_thickness "
        "fretboard_carrier_thickness",
        r"^The fretboard$",
    ),
    **_same("fretboard", "fret_slot_spindle_speed fret_slot_step_down", _FRET_SLOTS),
    **_same("fretboard", "inlay_spindle_speed inlay_step_down", _MARKERS),
    "nut_jig_tool_diameter": ("neck", (_BEHIND_NUT,)),
    **_same(
        "plan",
        "carve_tool_diameter carve_finish",
        r"^Carved top's plateau$",
        _BODY,
    ),
    **_same(
        "plan",
        "engraving_tool_angle engraving_step_down engraving_feed_rate "
        "relief_tool_diameter",
        _BODY,
    ),
}
"""Each setting's picture (``SettingPicture``), by its field name."""

NO_PICTURE = frozenset(
    {
        # How finely the model is sampled: nowhere in particular.
        "profile_sample_count",
        "segments_per_region",
        # The machine and its cutting, for every part alike.
        "tool_diameter",
        "tool_tip",
        "spindle_speed",
        "feed_rate",
        "plunge_rate",
        "rapid_rate",
        "step_down",
        "step_over",
        "finishing_allowance",
        "safe_height",
        "through_overshoot",
        "tab_count",
        "tab_length",
        "tab_height",
        "index_pin_diameter",
        "index_pin_positions",
        "index_pin_wall",
        "stock_margin",
        "stock_edge_margin",
        "small_hole_tool_diameter",
        "profile_overlap",
        "raster_link_spacing",
        "post_processor",
        "spindle_dwell",
        "combine_programs",
        "machine_x_travel",
        "machine_y_travel",
    }
)
"""The settings with no picture: none of them shapes one place."""
