"""What the web form's fields mean, where the code's own words fall short.

``webapp`` shows every field's meaning as its hint, taken from the code's
documentation (docstrings and the comments above the parameters); the
entries here come first. They cover every setting in plain words, a
sentence or two for someone new to guitar making: what it does on the
instrument, in what unit, and what leaving it empty does — not in the
code's own terms (the names of other settings, constants or modules).
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
        "fretboard ends fretboard_end_extension past the last one. On a "
        "microtonal neck count its own frets: 48 for two octaves of quarter "
        "tones."
    ),
    "frets_per_octave": (
        "Microtonal frets: how many equal steps each octave is divided into. "
        "12 is an ordinary guitar (semitones); 24 gives quarter tones, and "
        "19, 22 or 31 other microtonal tunings. The octave stays at half the "
        "scale; raise fret_count to match (48 for two octaves at 24). The "
        "markers stay at the usual pitches, on the nearest frets."
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
    "nut_string_spacing": (
        "The gap between neighbouring strings at the nut, centre to centre, "
        "in mm. With bridge_string_spacing it sets where each string runs "
        "(the tuner posts' lines, a multiscale's fanned frets)."
    ),
    "bridge_string_spacing": (
        "The gap between neighbouring strings at the bridge, centre to "
        "centre, in mm. With nut_string_spacing it sets where each string "
        "runs (the tuner posts' lines, a multiscale's fanned frets)."
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
        "Rose bridge (the 7- or 8-string nut on a seven- or eight-string) and "
        "a plain nut otherwise."
    ),
    "nut_jig": (
        "Adds a guide for filing the nut's string slots, cut from 3 mm sheet "
        "(program Jig_nut_slots): a comb that stands on the fretboard against "
        "the nut, with a slot as wide as each string where that string goes. "
        "Run each string's nut file through its slot to start the nut's slot "
        "in the right place, then finish it by hand."
    ),
    "nut_jig_thickness": (
        "The nut jig's sheet thickness, in mm: its length along the neck. No "
        "thicker than its cutter (nut_jig_tool_diameter) reaches through: 3 mm "
        "for the 0.6 mm fret-slot cutter, about 1.5 mm for a 0.3 mm one."
    ),
    "nut_jig_height": (
        "How high the nut jig's top stands above the fretboard, in mm: about "
        "the nut blank's own height. Its slots come down to the frets' height."
    ),
    "nut_jig_slot_play": (
        "How much wider than its string each of the nut jig's slots is, in "
        "mm, so the string's nut file slides through without wandering."
    ),
    "nut_jig_gauges": (
        "The strings' gauges for the jig's slots, one per string, in inches "
        "or thousandths ([10, 13, 17, 26, 36, 46]), in any order. Empty: a "
        "usual set (.010-.046 on a guitar, .045-.105 on a bass)."
    ),
    "truss_rod_adjustment": (
        "Where the truss rod (the steel rod that sets the neck's bow) is "
        "adjusted: at the heel, or at the headstock behind the nut."
    ),
    "truss_rod_install": (
        "How the truss rod goes in: from the neck's top under the "
        "fretboard, or the vintage Fender way, laid in from the back under "
        "a walnut strip and a teardrop plug (adjusted at the heel)."
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
    "fret_slot_end_inset": (
        "Blind fret slots: how far short of the fretboard's edges each slot "
        "stops, in mm (2 to 3 is usual; 0 cuts them out through the edges). "
        "No slot shows from the side; nip each fret's tang back as far at "
        "both ends, its crown running on to the edge. At most 4 mm."
    ),
    "fret_slot_depth": (
        "How deep each fret slot is cut below the curved playing surface, in mm."
    ),
    "fretboard_scalloped": (
        "A scalloped fretboard: the wood between the frets hollowed out from "
        "the fret below on, so the fingers press the strings without "
        "touching the board."
    ),
    "fretboard_scallop_from_fret": (
        "The fret the scallops start at: the space after it and every one on "
        "to the last fret are hollowed (0 from the nut, 15 for the top frets "
        "only)."
    ),
    "fretboard_scallop_depth": (
        "How deep each scallop is at its middle, in mm, right across the "
        "board; the inlays are cut 1 mm deeper than a scallop over them, so "
        "it leaves that much of each."
    ),
    "fretboard_scallop_land": (
        "How much of the board is left flat either side of each fret, in mm, "
        "for its foot to sit on."
    ),
    "inlay_style": (
        "The position markers' shape, cut as pockets into the fretboard: "
        "barbed wire, barbed wire 2 (a knot of barbed wire traced from a "
        "drawing, one piece at every marker fret), dots, blocks, Les Paul "
        "trapezoids, Jackson sharktooth, "
        "parallelograms, diamonds, split blocks, or your own drawn shape "
        "(custom, drawn in the Inlay design window). All but dots are also "
        "cut from sheet to fit (Fretboard_inlay_pieces)."
    ),
    "inlay_points": (
        "The custom marker's corners, drawn in the Inlay design window: "
        "[along, across] pairs, along 0 at the fret toward the nut and 1 at "
        "the marker's fret, across -1 to 1 the share of the board's "
        "half-width toward the bass edge. Every marker is this shape fitted "
        "to its own fret space; empty is a block."
    ),
    "inlay_single_marker_frets": (
        "The frets that get one position marker, counted in semitones: on a "
        "microtonal neck each goes on the fret nearest that pitch."
    ),
    "inlay_double_marker_frets": (
        "The frets that get two position markers (the octaves), counted in "
        "semitones as the single ones; block styles mark them like the "
        "others."
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
    "heel_root_style": (
        "How the neck's rounded back runs into the heel's block: smooth (the "
        "runout above), or drawn on Design › Neck as two lines across the "
        "back, where the block's flat begins and where the neck's own "
        "profile does, the back turning evenly from the one into the other. "
        "Drawing a line there makes it drawn."
    ),
    "heel_root_flat_points": (
        "A drawn heel: where its flat block begins (its rounding's shape), "
        "half of it seen from behind, [mm ahead of the block, mm across] "
        "from the centre line out to one side, mirrored. Empty: straight "
        "across at the block."
    ),
    "heel_root_neck_points": (
        "A drawn heel: where the neck's own profile begins, drawn as the flat "
        "line is. Empty: 45 mm ahead of the block at the sides, 60 mm down "
        "the middle."
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
    "headstock_pointed_volute": (
        "A volute carved into the back of the headstock behind the nut, "
        "where an angled headstock's short grain is weakest: seen from "
        "behind a rounded arrow whose nose reaches a little onto the neck, "
        "widening to the neck's width and fading into the headstock's back."
    ),
    "headstock_pointed_volute_depth": (
        "How much more wood the volute leaves than the plain back at its "
        "fullest, behind the nut, in mm: a drawn one's ridge height on its "
        "line (2 to 4 mm). More than 0 while the volute is on: turn it off "
        "for none."
    ),
    "headstock_pointed_volute_length": (
        "How far behind the nut the volute reaches into the headstock, in "
        "mm; its point reaches a third of that onto the neck."
    ),
    "headstock_volute_style": (
        "The volute's kind: drawn in the headstock editor as its crest and "
        "the lines where it ends in the headstock and in the neck, sharp on "
        "the crest and falling away on a logarithmic curve to each; or the "
        "rounded arrow."
    ),
    "headstock_volute_points": (
        "A drawn volute's crest, its highest line, as drawn in the headstock "
        "editor: half of it seen from behind, [mm behind the nut, mm across] "
        "from the centre line out to one side, mirrored. Empty: bulging 7 mm "
        "onto the neck down the middle."
    ),
    "headstock_volute_headstock_points": (
        "Where a drawn volute ends in the headstock's back, drawn as its crest "
        "is. Empty: about 30 mm behind the nut."
    ),
    "headstock_volute_neck_points": (
        "Where a drawn volute ends in the neck's back, drawn as its crest is. "
        "Empty: 13 to 22 mm past the nut."
    ),
    "headstock_root_style": (
        "How the neck's rounded back runs into the headstock's back: smooth, "
        "or drawn in the headstock editor (with the volute off) as two lines "
        "across the back, where the headstock's back begins and where the "
        "neck's own profile does, the back turning evenly from the one into "
        "the other, with no bump (that is the volute). Drawing a line there "
        "makes it drawn."
    ),
    "headstock_root_flat_points": (
        "A drawn root: where the headstock's back begins (the joint's "
        "rounding), half of it seen from behind, [mm behind the nut, mm "
        "across] from the centre line out to one side, mirrored. Empty: "
        "20 mm behind the nut, straight across."
    ),
    "headstock_root_neck_points": (
        "A drawn root: where the neck's own profile begins, drawn as the flat "
        "line is. Empty: 14 mm past the nut, straight across."
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
    "body_neck_pickup_angle": (
        "How far the neck pickup is turned about its centre, in degrees: "
        "positive swings its treble end toward the bridge (Shift-drag it in "
        "the body editor)."
    ),
    "body_middle_pickup_angle": (
        "How far the middle pickup is turned about its centre, in degrees: "
        "positive swings its treble end toward the bridge (Shift-drag it in "
        "the body editor)."
    ),
    "body_bridge_pickup_angle": (
        "How far the bridge pickup is turned about its centre, in degrees, "
        "on top of a single coil's slant: positive swings its treble end "
        "toward the bridge (Shift-drag it in the body editor); it still keeps "
        "its clearance to the bridge."
    ),
    "tuner_inline_offsets": (
        "Where a row of tuners' posts sit across the headstock, in mm from "
        "the centreline toward the row's side, one per tuner from the nut "
        "outward (negative past the centreline), so the row can run along "
        "a steep edge as on an Explorer; empty: each post on its own "
        "string's line, so no string bends at the nut."
    ),
    "tuner_hole_points": (
        "Where each tuner hole sits when it is not where the headstock style "
        "puts it: (distance from the nut, offset from the centreline toward "
        "its own side) in mm per hole. The headstock editor writes them when "
        "a hole is dragged, or when a dragged edge takes its holes along; "
        "empty: every hole where the style puts it."
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
        "The bridge: a Kahler 7300 or a Floyd Rose (six to eight strings), an "
        "Ibanez Lo-Pro Edge with a JEM777's Lion's Claw route behind it (six "
        "strings), a Tune-o-matic, a hardtail (strung through the body or "
        "top-loaded), a headless bridge or single-string bridges (one per "
        "string, each at its own scale on fanned frets), with the routes and "
        "holes each needs."
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
        "line, in mm; it moves further forward by itself to keep "
        "body_bridge_pickup_clearance of wood from the bridge's routes, plate "
        "and holes. Its route may reach past the saddle line toward a bridge "
        "set further back (a Kahler's plate), its centre never."
    ),
    "body_pickups_follow_fan": (
        "With fanned frets, whether the pickups turn with the frets: auto "
        "turns them, except with a Tune-o-matic."
    ),
    "body_bridge_follows_fan": (
        "With fanned frets, whether a hardtail bridge turns with them (a "
        "Tune-o-matic always does; single-string bridges each stand at their "
        "own string's scale anyway)."
    ),
    "body_controls": (
        "The controls: the cavity and its pots (volume and tone knobs) and "
        "the pickup selector's place, routed from the back, on a top plate "
        "or in the pickguard — among them a superstrat's rear cavity with "
        "the 5-way blade switch in it, a single volume pot, an active bass's "
        "four pots and a Jazz Bass plate."
    ),
    "body_switch": (
        "The pickup selector: a 3-way toggle or a mini toggle, by its hole's size."
    ),
    "body_jack": (
        "The output jack: in from the body's side (a Les Paul plate or a "
        "barrel jack), a cup jack in a round counterbore, a Stratocaster "
        "style plate on the top, on the Jazz Bass control plate, or in the "
        "top straight into the control cavity, as on an SG."
    ),
    "body_jack_plate": (
        "A Les Paul style jack plate over a side jack: a 34 mm square plastic "
        "plate cut from sheet, screwed onto the body's side with four screws, "
        "the jack through its middle."
    ),
    "body_stepped_top": (
        "Steps the top down in bands along the edge, as on an ESP LTD Alexi "
        "Hexed: the middle at full height, each band nearer the edge a step "
        "lower (body_top_step_insets, body_top_step_height)."
    ),
    "body_pickguard": (
        "A pickguard cut from sheet and shaped to the body, its screws "
        "spotted in the body; controls mounted in the guard bring it anyway."
    ),
    "body_pickguard_style": (
        "The automatic pickguard's shape: Stratocaster (beside the neck, a "
        "tail past the bridge) or superstrat (close round the pickups)."
    ),
    "body_pickup_frame": (
        "A frame round every humbucker, cut from plastic sheet in its own "
        "program: a plain ring, or horns or hook (traced from the builder's "
        "drawing), its opening the pickup's own, held by four screws, two "
        "past each of the pickup's ears, with holes to reach the pickup's "
        "height screws. One "
        "that does not fit is cut back round what is in its way; drag its "
        "points in the body editor to shape each pickup's frame."
    ),
    "body_pickup_frame_direction": (
        "Which way the frames' horns point: toward the neck, toward the "
        "bridge (turned round), or toward the neck where they fit and else "
        "turned round (auto)."
    ),
    "body_pickup_frame_thickness": "The frames' sheet thickness, in mm.",
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
    "body_top_bevel_width": (
        "A bevel all round the top's edge, as on an SG or a Mockingbird: "
        "how far in from the edge it reaches, in mm (0: none). It is left "
        "square beside the neck's pocket and where the body shape's round "
        "points leave the edge rounded over (an SG's tail), and narrows "
        "gently past routes, holes and narrow horns; a drawn pickguard is "
        "kept in off it."
    ),
    "body_back_bevel_width": (
        "The same bevel round the back's edge, in mm (0: none). With a "
        "set neck it runs on round the heel; beside a bolt-on neck's plate "
        "or a neck run through it is left square."
    ),
    "body_bevel_angle": (
        "How steep the bevels all round are, in degrees from the face: their "
        "depth at the edge is the width times its tangent (25 on an SG)."
    ),
    "body_leg_contour_depth": (
        "A leg contour: the back bevelled at the treble side's waist, where "
        "the body sits on the thigh when played seated, this deep in mm (0: "
        "none); its line can be drawn in the body editor."
    ),
    "body_heel_relief": (
        "A heel relief thins the back where the neck joins the body, so the "
        "hand reaches the top frets. Contour: a smooth slope, deepest at the "
        "body's edge. Notch: a flat step down. Bevel: a flat slope along the "
        "neck that a tilted neck plate can sit on (without a plate its sides "
        "slope too). None: a flat back."
    ),
    "body_heel_relief_depth": (
        "How deep the heel relief cuts into the back at its deepest, in mm "
        "(at the body's edge by the neck)."
    ),
    "body_heel_relief_reach": (
        "How far the heel relief's automatic line runs out past the neck "
        "pocket, in mm: behind the heel's end and on the treble side (across "
        "the corner: how far in from the edge it crosses the centreline)."
    ),
    "body_heel_relief_line": (
        "Where the heel relief's automatic line runs. Round the heel: a "
        "curve behind the heel's end. Along the neck pocket: its outline, "
        "the reach out. Either takes in the whole heel and reaches out past "
        "it on the treble side only. Across the treble corner: a straight "
        "45 degree line, clear of a neck plate. Draw your own line in the "
        "body editor; Auto heel relief comes back to this one."
    ),
    "body_wire_channels": (
        "Wires the pickups, a switch cavity and a battery box to the controls "
        "and grounds the bridge: a channel "
        "routed from the top where a pickguard hides it, else a straight hole "
        "drilled by hand from cavity to cavity, modelled, its angle in "
        "Body_top's notes."
    ),
    "body_battery_box": (
        "A 9 V battery box routed in the back (for active pickups or a "
        "preamp), with its own cover cut from sheet."
    ),
    "body_battery_count": "How many 9 V batteries the box holds: 1, or 2 side by side.",
    "body_engraving": "Engraves a decorative pattern into the top with a V-bit.",
    "body_engraving_pattern": (
        "The engraved pattern: Design by Jone's scrolls, EVH style stripes, "
        "flame, ripples, crackle, a woodland camo relief (closed shapes "
        "cleared to four levels down to body_engraving_depth), a pinstripe "
        "round the body just inside the margin (as on a Jackson RR or an ESP "
        "LTD Alexi Hexed), or lines drawn in another program (drawn: in the "
        "body editor's Export SVG template, its Pattern layer, read back with "
        "Import SVG)."
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
    "body_jack_plate_thickness": "The jack plate's sheet thickness, in mm.",
    "body_neck_bolt_spacing_y": (
        "The neck bolts' spacing across the neck, in mm (bolt-on neck)."
    ),
    "body_neck_ferrule_diameter": (
        "The counterbores in the body's back for the neck bolts' ferrules, "
        "their diameter in mm."
    ),
    "body_neck_ferrule_depth": "How deep those ferrule counterbores are, in mm.",
    "body_string_ferrule_diameter": (
        "A string-through bridge's string ferrules: the counterbore drilled "
        "from the back under each string's hole, in mm (5/16 in on a guitar, "
        "3/8 in on a bass)."
    ),
    "body_string_ferrule_depth": (
        "How deep the string ferrules' counterbores are, in mm (0: drilled by hand)."
    ),
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
    # Scale and fretboard (the rest)
    "fretboard_nut_corner_radius": (
        "Rounds the fretboard's two corners at the nut end, in mm (0: square corners)."
    ),
    "inlay_depth": (
        "How deep the position markers' pockets are cut into the fretboard, in mm."
    ),
    "inlay_block_length_fraction": (
        "For markers that fill a fret space (blocks, trapezoids, sharkteeth"
        " and the like): how much of the space between two frets each one "
        "covers, 0.6 being 60 %."
    ),
    "inlay_block_edge_margin": (
        "For those markers: how much fretboard is left between a marker and"
        " the board's edges, in mm."
    ),
    "inlay_runes": (
        "With rune markers: which runes, by name (fehu, uruz, thurisaz…), "
        "one per marker from the nut, starting over when there are more "
        "markers. Empty: the default set."
    ),
    "fret_height": (
        "How high the frets stand above the fretboard, in mm. A locking "
        "nut's shelf is set from the frets' tops."
    ),
    # Neck (the rest)
    "neck_through_width": (
        "On a neck-through guitar: how wide the neck's centre block running"
        " through the body is, in mm. Empty: just wide enough for the "
        "pickups, the bridge and their holes."
    ),
    "neck_through_heel_ramp": (
        "On a neck-through guitar: over how long the neck's back slopes "
        "down to the body's full thickness, ending where the body begins, "
        "in mm."
    ),
    "neck_heel_end": (
        "The shape of the neck's end: square across, as on a Telecaster, or"
        " round, as on a Stratocaster. The neck pocket (and a fretboard "
        "reaching the end) follows it. Not for a neck-through."
    ),
    "truss_rod_start": (
        "Where the truss rod's channel starts, measured from the nut toward"
        " the body, in mm."
    ),
    "truss_rod_stock_lengths": (
        "The truss rod lengths you can buy, in mm: unless you set a length,"
        " the longest one that fits the neck is used."
    ),
    "truss_rod_length": (
        "The truss rod channel's length, in mm. Empty: the longest stock rod that fits."
    ),
    "truss_rod_width": "How wide the truss rod's channel is, in mm: your rod's width.",
    "truss_rod_depth": "How deep the truss rod's channel is cut into the neck, in mm.",
    "truss_rod_step_length": (
        "At the adjusting end the channel steps wider and deeper for the "
        "rod's anchor: that step's length, in mm."
    ),
    "truss_rod_step_width": "That step's width, in mm.",
    "truss_rod_step_depth": "That step's depth, in mm.",
    "truss_rod_pocket_length": (
        "Past the step, a larger pocket for the adjusting nut: its length, in mm."
    ),
    "truss_rod_pocket_width": "That pocket's width, in mm.",
    "truss_rod_pocket_depth": "That pocket's depth, in mm.",
    "truss_rod_sleeve_length": (
        "With the rod adjusted at the heel: how far before the neck's end "
        "the channel stops, the adjuster's sleeve running on in a hole, in "
        "mm."
    ),
    "truss_rod_sleeve_diameter": (
        "The hole for the heel adjuster's sleeve: its diameter, in mm."
    ),
    "truss_rod_axis_depth": (
        "How deep below the neck's top the rod's centre lies, in mm; the "
        "heel adjuster's hole is centred on it."
    ),
    "truss_rod_nut_diameter": (
        "The heel adjuster's round head, the nut you turn: its diameter, in"
        " mm. The body gets a notch for it past the neck pocket."
    ),
    "truss_rod_nut_length": "That head's length along the neck, in mm.",
    "truss_rod_access_length": (
        "How long the opening is where you reach the adjuster: a notch in "
        "the body past the neck pocket (adjusted at the heel) or a trough "
        "in the headstock face (adjusted at the headstock), in mm. Empty: "
        "sized for the adjuster."
    ),
    "truss_rod_cover": (
        "Cuts a cover plate for the truss rod's trough in the headstock, "
        "from thin sheet, with its screw holes."
    ),
    "truss_rod_cover_style": (
        "The truss rod cover's shape: a Gibson bell, Ibanez / ESP style, a "
        "PRS teardrop, a rounded rectangle, or your own, drawn in the "
        "headstock editor."
    ),
    "truss_rod_cover_length": (
        "The truss rod cover's length, in mm. Empty: the style's own."
    ),
    "truss_rod_cover_width": (
        "The truss rod cover's width, in mm. Empty: the style's own."
    ),
    "truss_rod_cover_points": (
        "Your own truss rod cover's corners, as drawn in the headstock "
        "editor (in proportion to the cover's length and width)."
    ),
    "truss_rod_cover_screws": (
        "Your own truss rod cover's screws, as drawn in the headstock editor."
    ),
    "truss_rod_key_hole_diameter": (
        "With no cover, behind a slotted (Fender style) nut: how wide the "
        "notch is that your truss rod key goes through, in mm."
    ),
    "truss_rod_low_profile_width": (
        "A low-profile truss rod's straight channel: its width, in mm (1/4 in)."
    ),
    "truss_rod_low_profile_depth": "That channel's depth, in mm (3/8 in).",
    "truss_rod_sleeve_bore": (
        "Makes the hole for the heel adjuster's sleeve in the neck."
    ),
    "truss_rod_sleeve_routed": (
        "Routs that hole from the top as a slot, which the fretboard then "
        "covers (a router cannot drill along the neck); off, the hole is "
        "left for you to drill by hand."
    ),
    "truss_rod_trough": (
        "Routs the trough in the headstock face where you reach a headstock"
        " adjuster, and cuts its cover."
    ),
    "neck_carbon_rods": (
        "Adds two carbon fibre bars, glued into channels either side of the"
        " truss rod under the fretboard, to stiffen the neck against "
        "bending and twisting."
    ),
    "neck_carbon_rod_size": (
        "The carbon bars' size, width by height: 3.2 by 6.35 mm, 4 by 4 mm,"
        " 3.2 by 9.5 mm (it needs a thicker neck), or your own."
    ),
    "neck_carbon_rod_width": "Your own carbon bars' width, in mm.",
    "neck_carbon_rod_depth": "Your own carbon bars' height, in mm.",
    "neck_carbon_rod_start": (
        "Where the carbon bars start, measured from the nut toward the body, in mm."
    ),
    "neck_carbon_rod_length": (
        "How long the carbon bars are, in mm. Empty: to where the heel "
        "flattens, clear of the neck screws."
    ),
    "neck_carbon_rod_offset": (
        "How far out from the neck's centre line each carbon bar sits, in "
        "mm. Empty: right beside the truss rod, a little wood between."
    ),
    "nut_shelf_length": (
        "With the nut standing on a shelf: how long the flat seat it stands"
        " on is, in front of the fretboard's end, in mm."
    ),
    "nut_thickness": (
        "With a slotted (Fender style) nut: the slot's width, which is the "
        "nut's thickness, in mm."
    ),
    "nut_slot_depth": "How deep that slot is cut below the fretboard's top, in mm.",
    "nut_slot_lip": (
        "Behind the slot the fretboard carries on at full height this far "
        "before it slopes away, in mm."
    ),
    "nut_slot_taper": "Then it slopes down to the neck over this length, in mm.",
    "locking_nut_screw_diameter": (
        "A locking nut's two mounting screws: the diameter of their pilot "
        "holes, drilled by hand through the nut, in mm."
    ),
    "locking_nut_screw_depth": "How deep those pilot holes go, in mm.",
    # Headstock and tuners (the rest)
    "headstock_bass_side": (
        "Which side of the drawn headstock the bass strings' tuners are on."
        " Change it to swap the headstock's shape and tuners side for side."
    ),
    "headstock_tip_points": (
        "A drawn headstock's tip, shaped in the headstock editor. Empty: a "
        "straight cut across."
    ),
    "headstock_face_drop": (
        "How far the headstock's face is set down below the neck's top, in "
        "mm. Empty: 4 mm on a flat headstock, so the strings still press "
        "down on the nut; none on an angled one."
    ),
    "headstock_face_transition": (
        "Behind the nut, over how long the top curves down onto the "
        "headstock's face, in mm (0: a sharp step)."
    ),
    "headstock_engraving_text": (
        "Text engraved into the headstock's face: a name, or a logo's "
        "words. Empty: none."
    ),
    "headstock_engraving_font": (
        "The lettering's font: a plain single-line sans, a script or a gothic."
    ),
    "headstock_engraving_height": "How tall the lettering's capitals are, in mm.",
    "headstock_engraving_x": (
        "Where along the headstock the lettering is centred, in mm from the"
        " nut (negative: toward the tip). Empty: a little behind the nut."
    ),
    "headstock_engraving_y": (
        "How far across the headstock the lettering is centred from the middle, in mm."
    ),
    "headstock_engraving_angle": (
        "Which way the lettering runs, in degrees (90: across the "
        "headstock, read with its tip pointing up)."
    ),
    "headstock_engraving_depth": (
        "How deep the lettering and lines are engraved with the V-bit, in mm."
    ),
    "headstock_engraving_lines": (
        "Lines engraved on the headstock's face, drawn in another program "
        "and read back from the headstock editor's SVG template."
    ),
    "tuner_station_distances": (
        "On a three-a-side headstock: how far from the nut each pair of "
        "tuners sits, nearest first, in mm."
    ),
    "tuner_side_offsets": (
        "On a three-a-side headstock: how far out from the centre line each"
        " pair of tuners sits, nearest first, in mm."
    ),
    "tuner_inline_first_distance": (
        "On a six-in-line (or 4+2) headstock: how far from the nut the "
        "first tuner sits, in mm."
    ),
    "tuner_inline_spacing": "The spacing between tuners along the row, in mm.",
    "tuner_edge_offset": (
        "How far the headstock's edge stays out from the tuner holes, in mm."
    ),
    "tuner_post_diameter": (
        "The tuners' string posts' diameter, in mm: each string runs past "
        "its post's side, which places the holes in a row."
    ),
    "tuner_edge_clearance": (
        "The least wood left between a tuner hole and the headstock's edge, in mm."
    ),
    "headstock_volute_length": (
        "Behind the nut, over how long the neck's back eases into the headstock, in mm."
    ),
    "headstock_volute_depth": (
        "Extra wood left on the back where the neck meets the headstock, in"
        " mm (0: none). For a proper volute, turn on Headstock pointed "
        "volute."
    ),
    "headstock_root_side_extension": (
        "How far behind the nut the neck's sides keep their rounded shape "
        "before they flatten into the headstock, in mm."
    ),
    # Body (the rest)
    "body_neck_pocket_length": (
        "How long the neck pocket is, from the neck's end toward the nut, "
        "in mm. It always opens through the body's front edge."
    ),
    "body_neck_pocket_clearance": (
        "Extra room each side of the neck in its pocket, in mm (0.1 to 0.2 "
        "for a snug fit)."
    ),
    "body_bridge_pickup_clearance": (
        "The least wood kept between the bridge pickup's route and the "
        "bridge's routes and holes, in mm; the pickup moves forward if it "
        "must."
    ),
    "body_neck_pickup": "With your own pickup layout: the neck pickup's type, or none.",
    "body_middle_pickup": (
        "With your own pickup layout: the middle pickup's type, or none."
    ),
    "body_bridge_pickup": (
        "With your own pickup layout: the bridge pickup's type, or none."
    ),
    "body_middle_pickup_offset": (
        "Where the middle pickup's centre sits past the neck's end, in mm. "
        "Empty: halfway between the neck and bridge pickups."
    ),
    "body_bridge_single_coil_angle": (
        "How much a bridge single coil slants, its treble end toward the "
        "bridge, in degrees (10 on a Stratocaster)."
    ),
    "body_pickup_screw_spacing": (
        "How far apart each pickup's two height screws are, in mm: their "
        "tips get holes below the route."
    ),
    "body_widening": (
        "Widens the body along its middle for a wider neck, in mm: each "
        "half moves out by half of it. Empty: 12 mm for every string past "
        "six."
    ),
    "body_top_binding_depth": (
        "A binding channel round the top's edge: its depth, in mm."
    ),
    "body_back_binding_width": (
        "A binding channel round the back's edge: its width, in mm (0: none)."
    ),
    "body_back_binding_depth": "That binding channel's depth, in mm.",
    "body_arm_contour_width": (
        "The arm contour on the top: how far in from the edge it reaches, in mm."
    ),
    "body_arm_contour_length": "How long the arm contour runs along the edge, in mm.",
    "body_arm_contour_position": (
        "Where the arm contour is deepest, along the body from the neck's "
        "end, in mm. Empty: where the bout is widest."
    ),
    "body_belly_cut_width": (
        "The belly cut on the back: how far in from the edge it reaches, in mm."
    ),
    "body_belly_cut_length": "How long the belly cut runs along the edge, in mm.",
    "body_belly_cut_position": (
        "Where the belly cut is deepest, along the body from the neck's "
        "end, in mm. Empty: where the bout is widest."
    ),
    "body_leg_contour_width": (
        "The leg contour on the back of the treble side's waist, where the "
        "guitar rests on your leg: how far in it reaches, in mm."
    ),
    "body_leg_contour_length": "How long the leg contour runs along the edge, in mm.",
    "body_leg_contour_position": (
        "Where the leg contour is deepest, along the body from the neck's "
        "end, in mm. Empty: where the waist is narrowest."
    ),
    "body_epoxy_tray_depth": (
        "Routs the whole top this deep for an epoxy pour, leaving a wooden "
        "rim at the edge and walls round every opening, in mm (0: none)."
    ),
    "body_epoxy_tray_rim": "How wide the epoxy tray's wooden rim and walls are, in mm.",
    "body_rear_cavity_top_wall": (
        "How thick the top is left over the electronics cavities routed "
        "from the back, in mm: the pots and the switch go through it."
    ),
    "body_cover_recess_depth": (
        "How deep the ledges for the back's cover plates are, in mm: the "
        "plates' thickness."
    ),
    "body_pickguard_thickness": "The pickguard sheet's thickness, in mm.",
    "body_pickguard_margin": (
        "How far in from the body's edge an automatic pickguard stays, in mm."
    ),
    "body_neck_frame_points": (
        "The neck pickup's frame, as drawn in the body editor. Empty: the "
        "frame style's own shape."
    ),
    "body_middle_frame_points": (
        "The middle pickup's frame, as drawn in the body editor. Empty: the"
        " frame style's own shape."
    ),
    "body_bridge_frame_points": (
        "The bridge pickup's frame, as drawn in the body editor. Empty: the"
        " frame style's own shape."
    ),
    "body_carve_rim": "A carved top's flat rim round the edge: its width, in mm.",
    "body_carve_margin": (
        "How far the carved top's flat middle reaches round the pickups, "
        "the bridge and the neck pocket, in mm."
    ),
    "body_top_step_insets": (
        "A stepped top's bands: how far in from the edge each step is, in mm."
    ),
    "body_top_step_height": (
        "How much lower each band of a stepped top is than the one inside it, in mm."
    ),
    "body_engraving_depth": (
        "How deep the pattern on the top is engraved with the V-bit, in mm."
    ),
    "body_engraving_spacing": (
        "The engraved pattern's scale: about how far apart its repeats are, in mm."
    ),
    "body_engraving_margin": (
        "How far in from the body's edge the engraved pattern stays, in mm."
    ),
    "body_engraving_clearance": (
        "How far the engraved pattern stays from the cavities, holes, "
        "bridge and pickguard, in mm."
    ),
    "body_engraving_lines": (
        "The drawn pattern's lines, drawn in another program and read back "
        "with the body editor's Import SVG."
    ),
    "body_battery_cavity_length": (
        "The 9 V battery box's length, in mm (a battery is 48.5 mm long; "
        "the rest is room for its clip and wires)."
    ),
    "body_battery_cavity_depth": (
        "How deep the battery box is routed from the back, in mm (a battery"
        " is 17.5 mm thick)."
    ),
    "body_battery_cover_margin": (
        "How much larger than the battery box its cover plate is all round, in mm."
    ),
    "body_strap_guide": (
        "Adds a flame-shaped strap guide on the back: the strap runs under "
        "its bar, so the guitar hangs leaning toward you, as on the Design "
        "by Jone guitar."
    ),
    "body_strap_width": "Your strap's width, in mm: the guide's channel is 4 mm wider.",
    "body_strap_guide_gap": (
        "The room under the strap guide's bar for the strap, its thickness "
        "and a little play, in mm: the spacers' sheet thickness."
    ),
    "body_strap_guide_thickness": "The strap guide plate's sheet thickness, in mm.",
    "body_strap_guide_screw_diameter": (
        "The strap guide screws' pilot holes: their diameter, in mm."
    ),
    "body_strap_guide_screw_depth": "How deep those pilot holes go, in mm.",
    "body_switch_shaft_hole_diameter": (
        "The selector switch's hole through the top: its diameter, in mm. "
        "Empty: the switch's own size."
    ),
    "body_jack_depth": (
        "How long the output jack's hole is, in mm. Empty: through to the "
        "control cavity it aims at (55 mm when it aims at none)."
    ),
    "body_neck_bolt_spacing_x": (
        "The neck bolts' spacing along the neck, in mm (a bolt-on neck)."
    ),
    "body_neck_bolt_center_offset": (
        "How far ahead of the neck's end the bolts' pattern is centred, in "
        "mm. Empty: the rear bolts as close to the pocket's end as they can"
        " be."
    ),
    "body_neck_bolt_end_wall": (
        "The least wood between the rear bolts' holes and the neck's end, in mm."
    ),
    "body_neck_bolt_edge_wall": (
        "With the bolts moved outward: the least wood beside each bolt hole"
        " to the neck's edge, in mm."
    ),
    "body_neck_bolts_outward": (
        "Moves each neck bolt out across the neck, as far from the truss "
        "rod as the wood allows, for a firmer joint."
    ),
    "body_neck_plate": (
        "What the neck bolts pull against on the back: a ferrule each, a "
        "Fender style four-bolt plate, or that plate with one corner "
        "clipped, as on a contoured heel."
    ),
    "body_neck_plate_length": (
        "The neck plate's length along the neck, in mm (Fender's: 63.5)."
    ),
    "body_neck_plate_width": (
        "The neck plate's width across the neck, in mm (Fender's: 50.8)."
    ),
    "body_neck_plate_hole_inset": (
        "How far in from the neck plate's edges its holes are, in mm."
    ),
    "body_neck_plate_clip": (
        "With the clipped plate: how much of each edge its corner cut takes, in mm."
    ),
    # Other (the rest)
    "set_neck_glue_gap": (
        "With a glued (set) neck: the gap left each side round the heel in "
        "its pocket for the glue, in mm."
    ),
    "headless": (
        "A headless neck: no headstock and no tuners; the strings are tuned"
        " at the bridge and anchored at a short headpiece behind the nut."
    ),
    "headless_length": "How long a headless neck's headpiece is behind the nut, in mm.",
    "zero_fret_gap": (
        "With a zero fret: how far behind it the nut, only a string guide "
        "then, sits, in mm."
    ),
}
"""Each field's meaning, by name (``webapp._field_help`` prefers these)."""
