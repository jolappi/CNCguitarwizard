"""What the web form's fields mean, where the code's own words fall short.

``webapp`` shows every field's meaning as a tooltip, taken from the code's
documentation (docstrings and the comments above the parameters); the
entries here come first. They cover the settings shown up front, in a
sentence or two for someone new to guitar making, and the advanced ones
the code leaves unexplained.
"""

from __future__ import annotations

FIELD_HELP: dict[str, str] = {
    # The instrument
    "handedness": (
        "Right-handed builds the instrument as drawn; left-handed builds its "
        "mirror image (body, electronics, bass side, headstock), the design "
        "itself staying as drawn."
    ),
    "string_count": (
        "How many strings: 6, 7 or 8 on a guitar, 4 or 5 on a bass. The "
        "tuners, the nut's and bridge's spacing, the pickups and the body's "
        "width follow it."
    ),
    "scale_length": (
        "The scale: the strings' vibrating length from the nut to the "
        "bridge saddles, in mm (609.6 = 24 in, Gibson; 647.7 = 25.5 in, "
        "Fender; 863.6 = 34 in, bass). With fanned frets it is the treble "
        "side's."
    ),
    "bass_scale_length": (
        "Fanned frets (multiscale): the bass side's scale, in mm, longer than "
        "scale_length (the treble side's); the frets fan between the two. "
        "Empty: one scale for every string."
    ),
    "perpendicular_fret": (
        "With fanned frets: the fret that stays square across the neck (0 = "
        "the nut; 7 is common, so the frets fan most at the bridge end)."
    ),
    "fret_count": (
        "How many frets (22 or 24 on a guitar, 20 to 24 on a bass); the "
        "fretboard ends fretboard_end_extension past the last one."
    ),
    "fret_slant_angle": (
        "Tilts every fret, and both ends of the fretboard, by this many "
        "degrees: a slanted rather than fanned fretboard. Positive moves each "
        "fret's treble end toward the bridge; 0 keeps them square."
    ),
    # Neck
    "neck_joint": (
        "How the neck joins the body: bolt-on (its heel screwed into a pocket "
        "in the body), set (its heel glued into a tight pocket), neck-through "
        "(the neck blank runs on through the body as its centre, the two body "
        "wings glued to its sides) or one piece (the neck and the whole body "
        "cut from one blank)."
    ),
    "nut_width": (
        "The fretboard's and neck's width at the nut, in mm (42 to 43 on a guitar)."
    ),
    "final_fret_width": (
        "The fretboard's width at the last fret, in mm; the neck tapers from "
        "nut_width to this."
    ),
    "heel_width": "The neck's width at the heel, past the last fret, in mm.",
    "first_fret_thickness": (
        "The neck's whole thickness at the first fret, from the fretboard's "
        "playing surface to the back of the neck, in mm."
    ),
    "twelfth_fret_thickness": (
        "The neck's whole thickness at the twelfth fret, fretboard included, "
        "in mm; the back tapers evenly from the first fret to here."
    ),
    "heel_thickness": (
        "The neck's wood below the fretboard at the heel, in mm: how deep the "
        "body's neck pocket is cut for a bolt-on neck."
    ),
    "neck_profile_exponent": (
        "The shape of the neck's back in cross-section: 2 is a round C; "
        "larger values (3 to 4) a fuller, flatter D or U."
    ),
    "neck_angle": (
        "Tilts a bolt-on neck back by this many degrees, the headstock toward "
        "the player, for a tall bridge: the neck pocket's floor slopes. "
        "Empty: 2 degrees with a Tune-o-matic, else 0."
    ),
    "nut_style": (
        "How the nut is fitted: on the neck's shelf in front of the "
        "fretboard; Fender/Telecaster style in a slot at the fretboard's end; "
        "or behind a zero fret on the nut line, the nut then only guiding the "
        "strings."
    ),
    "locking_nut": (
        "A Floyd Rose locking nut screwed down from the top, which clamps the "
        "strings so a tremolo stays in tune: auto fits the R2 with a Floyd "
        "Rose bridge and a plain nut otherwise."
    ),
    "truss_rod_adjustment": (
        "Where the truss rod (the steel rod that sets the neck's bow) is "
        "adjusted: at the heel, or at the headstock behind the nut."
    ),
    "truss_rod_spoke_wheel": (
        "A spoke-wheel adjuster, turned with a rod through its holes: auto "
        "fits one at the heel and none at the headstock."
    ),
    "truss_rod_profile": (
        "standard: a two-way rod whose adjusting end steps down into a deeper "
        "pocket; low_profile: a slim rod in one straight 6.35 x 9.5 mm "
        "channel, for thin necks."
    ),
    "truss_rod_rod_length": (
        "The truss rod you have, its overall length in mm; the channel is cut "
        "for it. Empty: the longest stock length (300 to 600 mm in 20 mm "
        "steps) that fits the neck."
    ),
    # Fretboard
    "fretboard_radius": (
        "The fretboard's curve across the neck: its radius, in mm (184 = "
        "7.25 in vintage Fender, 241 = 9.5 in, 305 = 12 in Gibson; larger is "
        "flatter)."
    ),
    "fretboard_thickness": (
        "The fretboard's thickness at its centre, in mm; it is cut from its "
        "own blank and glued onto the neck."
    ),
    "fretboard_binding_width": (
        "Binding strips along the fretboard's long edges, this thick in mm "
        "(0: none); the board is cut narrower by as much, so board and "
        "binding keep the neck's width."
    ),
    "fretboard_end_extension": (
        "How far the fretboard runs on past the last fret, in mm."
    ),
    "fret_slot_width": "The fret slots' width, in mm, to suit the fret wire's tang.",
    "fret_slot_depth": (
        "How deep each fret slot is cut below the curved playing surface, in mm."
    ),
    "inlay_style": (
        "The position markers' shape, cut as pockets into the fretboard: "
        "barbed wire, dots, blocks, Les Paul trapezoids, Jackson sharktooth, "
        "parallelograms, diamonds or split blocks. All but dots are also cut "
        "from sheet to fit (Fretboard_inlay_pieces)."
    ),
    "inlay_single_marker_frets": "The frets that get one position marker.",
    "inlay_double_marker_frets": (
        "The frets that get two position markers (the octaves); block styles "
        "mark them like the others."
    ),
    "inlay_dot_diameter": "A dot marker's diameter, in mm.",
    # Heel
    "heel_mounting_length": (
        "The bolt-on neck's flat heel block that sits in the body's neck "
        "pocket, its length in mm (at least 40)."
    ),
    "heel_length": (
        "How far the neck runs on past the last fret to its heel end, in mm; "
        "the body's features are placed from that heel end."
    ),
    "heel_nose_radius": (
        "Rounds the heel block's front corner, its radius in mm (0: square)."
    ),
    "heel_block_overlap": (
        "How far the flat heel block overlaps the neck's rounded runout in the "
        "FreeCAD model, in mm, so the two join into one solid."
    ),
    "heel_root_length": (
        "Over how long the neck's rounded back eases into the flat heel block, in mm."
    ),
    "heel_scoop_depth": (
        "A slight hollow in that runout, in mm, so the heel reads as a "
        "shallow scoop rather than a straight ramp."
    ),
    "heel_root_center_extension": (
        "How much earlier the heel's runout starts on the neck's centre than "
        "at its sides, in mm, so it leads smoothly out of the neck."
    ),
    # Headstock and tuners
    "headstock_style": (
        "The tuners' layout: 3+3, six (or four, five, seven, eight) in line on "
        "the bass side, reverse on the treble side, 4+2 and so on; the "
        "headstock is shaped round them."
    ),
    "headstock_outline": (
        "drawn: the headstock's edges as drawn in the headstock editor (the "
        "fitted outline until they are); fitted: an outline fitted round the "
        "tuners."
    ),
    "headstock_length": (
        "The headstock's length past the nut, in mm; it grows when the tuners "
        "need more."
    ),
    "headstock_angle": (
        "How far the headstock's face tilts back from the neck, in degrees "
        "(Gibson 14 to 17, many 8 to 13; 0 for a flat, Fender style "
        "headstock), so the strings press down on the nut."
    ),
    "headstock_thickness": (
        "The headstock's thickness, face to back, in mm (14 to 16 suits most "
        "tuners' bushings)."
    ),
    "headstock_root_length": (
        "The headstock's root, from the nut to where its sides start tapering "
        "toward the tip, its length in mm."
    ),
    "headstock_shoulder_width": (
        "The headstock's width at the end of its root, in mm; empty: fitted "
        "round the tuners."
    ),
    "headstock_tip_width": (
        "The headstock's width at its tip, in mm; empty: fitted round the tuners."
    ),
    "headstock_shoulder_shift": (
        "Moves the headstock's centre at the end of its root toward the bass "
        "side (positive) or the treble side, in mm; empty: from the tuners."
    ),
    "headstock_tip_shift": (
        "Moves the headstock's centre at its tip toward the bass side "
        "(positive) or the treble side, in mm; empty: from the tuners."
    ),
    "headstock_bass_edge": (
        "The bass-side edge drawn in the headstock editor: (distance from the "
        "nut, half-width) points ending at the tip; empty uses the fitted edge."
    ),
    "headstock_treble_edge": (
        "The treble-side edge drawn in the headstock editor: (distance from "
        "the nut, half-width) points ending at the tip; empty uses the fitted "
        "edge."
    ),
    "headstock_volute_peak_fraction": (
        "Where along the headstock-to-neck transition its volute (the thicker "
        "ridge behind the nut) is fullest, as a fraction of its length."
    ),
    "headstock_root_swell": (
        "Extra depth of the continuous surface joining the headstock to the "
        "neck, in mm (0: a plain join)."
    ),
    "headstock_outer_d_profile_guide_extension": (
        "Construction lines only: how far the neck's outer profile guide "
        "lines run on onto the headstock's back in the FreeCAD model, in mm."
    ),
    "tuner_hole_diameter": (
        "The tuner post holes' diameter, in mm, to suit the tuners' bushings "
        "(10 mm for most); the G-code marks their centres to drill on a drill "
        "press."
    ),
    "tuner_tip_margin": (
        "Wood kept between the last tuner hole and the headstock's tip, in "
        "mm; the headstock grows when it needs it."
    ),
    "tuner_hole_clearance": (
        "The least wood kept between neighbouring tuner holes, in mm."
    ),
    "tuner_chamfer_depth": (
        "A small 45 degree chamfer round each tuner hole's top edge in the "
        "FreeCAD model, its depth in mm."
    ),
    "nut_end_u_trim_depth": (
        "How far the U-shaped curve where the neck's back meets the headstock "
        "reaches toward the heel at its centre, in mm (its corners stay at "
        "the nut line); the FreeCAD model only."
    ),
    "nut_end_u_side_fillet_radius": (
        "Rounds the two side walls of that U-shaped curve, the radius in mm."
    ),
    "joint_fillet_radius": (
        "Rounds the neck's joins to the heel and the headstock in the FreeCAD "
        "model, the radius in mm."
    ),
    "profile_sample_count": (
        "Points across each section of the neck's back surface (odd); more is "
        "smoother and slower."
    ),
    "segments_per_region": (
        "Sections between each pair of reference stations along the neck's "
        "back; more is smoother and slower."
    ),
    # Body
    "body_shape": (
        "The body's outline and the places of its electronics, drawn in the "
        "body editor."
    ),
    "body_thickness": (
        "The body's thickness, in mm (44.5 = 1.75 in on a Stratocaster; 50.8 "
        "on a Les Paul with a carved top)."
    ),
    "body_bridge": (
        "The bridge: a Kahler 7300, a Floyd Rose, a Tune-o-matic, a hardtail "
        "or a headless bridge, with the routes and holes each needs."
    ),
    "body_pickups": (
        "The pickups from neck to bridge: H = humbucker, S = single coil; on "
        "a bass P (Precision), J (Jazz), MM (Music Man), RR (Rickenbacker)."
    ),
    "body_neck_pickup_offset": (
        "How far the neck pickup's centre sits from the neck's heel end "
        "toward the bridge, in mm."
    ),
    "body_bridge_pickup_offset": (
        "How far the bridge pickup's centre sits ahead of the bridge's scale "
        "line, in mm; it moves further forward by itself when the bridge "
        "needs the room."
    ),
    "body_pickups_follow_fan": (
        "With fanned frets, whether the pickups turn with the frets: auto "
        "turns them, except with a Tune-o-matic."
    ),
    "body_bridge_follows_fan": (
        "With fanned frets, whether a hardtail bridge turns with them (a "
        "Tune-o-matic always does)."
    ),
    "body_controls": (
        "The controls: the cavity and its pots (volume and tone knobs) and "
        "the pickup selector's place, routed from the back, on a top plate "
        "or in the pickguard."
    ),
    "body_switch": (
        "The pickup selector: a 3-way toggle or a mini toggle, by its hole's size."
    ),
    "body_jack": (
        "The output jack: in from the body's side (a Les Paul plate or a "
        "barrel jack), a cup jack in a round counterbore, or a Stratocaster "
        "style plate on the top."
    ),
    "body_pickguard": (
        "A pickguard cut from sheet and shaped to the body, its screws "
        "spotted in the body."
    ),
    "body_pickguard_style": (
        "The automatic pickguard's shape: Stratocaster (beside the neck, a "
        "tail past the bridge) or superstrat (close round the pickups)."
    ),
    "body_top_edge_radius": "Rounds the top edge over, the radius in mm (0: square).",
    "body_back_edge_radius": "Rounds the back edge over, the radius in mm (0: square).",
    "body_top_binding_width": (
        "A channel round the top edge for a binding strip, this wide in mm "
        "(0: none); it takes a roundover's place there."
    ),
    "body_arm_contour_depth": (
        "An arm contour: the top's edge bevelled where the forearm rests, "
        "this deep in mm (0: none); its line can be drawn in the body editor."
    ),
    "body_belly_cut_depth": (
        "A belly cut: the back bevelled where the body meets the player, "
        "this deep in mm (0: none)."
    ),
    "body_battery_box": (
        "A 9 V battery box routed in the back (for active pickups or a "
        "preamp), with its own cover cut from sheet."
    ),
    "body_battery_count": "How many 9 V batteries the box holds: 1, or 2 side by side.",
    "body_engraving": "Engraves a decorative pattern into the top with a V-bit.",
    "body_engraving_pattern": (
        "The engraved pattern: Design by Jone's scrolls, EVH style stripes, "
        "flame, ripples or crackle."
    ),
    "body_engraving_seed": (
        "Lays the pattern out anew: each number gives a different layout."
    ),
    "body_pickup_route_depth": "How deep the pickup routes are cut, in mm.",
    "body_pickup_screw_recess_diameter": (
        "The round recesses at a pickup route's ends for its height screws, "
        "their diameter in mm."
    ),
    "body_pickup_screw_recess_extra_depth": (
        "How much deeper than the pickup route those screw recesses go, in mm."
    ),
    "body_battery_cavity_width": (
        "The battery box's width across its long side, in mm (a 9 V battery "
        "is 26.5 mm)."
    ),
    "body_pot_shaft_hole_diameter": (
        "The holes through the top for the pots' (volume and tone) shafts, "
        "their diameter in mm (10 mm for 3/8 in bushings)."
    ),
    "body_jack_diameter": "The output jack's bore, its diameter in mm.",
    "body_neck_bolt_spacing_y": (
        "The neck bolts' spacing across the neck, in mm (bolt-on neck)."
    ),
    "body_neck_ferrule_diameter": (
        "The counterbores in the body's back for the neck bolts' ferrules, "
        "their diameter in mm."
    ),
    "body_neck_ferrule_depth": "How deep those ferrule counterbores are, in mm.",
    "body_neck_bolt_hole_diameter": (
        "The neck bolts' holes through the body to the neck pocket, their "
        "diameter in mm."
    ),
    "body_carved_top": (
        "Arches the top, Les Paul style: flat round the pickups and the "
        "bridge, falling to a flat rim at the edge."
    ),
    "body_carve_depth": (
        "How far the carved top falls from its flat plateau to the rim, in "
        "mm (9.5 on a Les Paul)."
    ),
}
"""Each field's meaning, by name (``webapp._field_help`` prefers these)."""
