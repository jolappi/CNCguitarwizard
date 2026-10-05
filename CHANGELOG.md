# Changelog

## Unreleased

### Added

- The battery box and the controls are placed together, so neither
  blocks the other: where the box as drawn keeps the controls from their
  clear place or sits in their way, the controls take the place they
  would have without it and the box moves the least that clears them
  and everything else — nearby first (turning a little if need be),
  else anywhere in the body. A Jackson RR now takes a Gibson cavity, a
  Floyd Rose and a battery box (and a superstrat or active bass layout
  with one), which were refused.
- Telling two outlines apart is quicker: those whose bounding boxes are
  apart are not compared edge by edge.
- Each pickup turns about its own centre: Shift-drag it in the body
  editor, as the control cavity, the battery box and the jack already
  turn (`body_neck_pickup_angle`, `body_middle_pickup_angle`,
  `body_bridge_pickup_angle`, up to 45 degrees either way, a positive
  angle swinging the treble end toward the bridge, on top of a single
  coil's slant and a fan). The route, its screw recesses and a
  pickguard's opening turn with it; a turned bridge pickup still keeps
  its clearance to the bridge.
- Five more body templates traced from straight-on product photos
  (scaled from the frets, the last fret 4 mm ahead of the heel end, as
  the default neck's is; strap buttons and jack rims left out):
  - "Mockingbird style": traced from a B.C. Rich Mockingbird and then
    reshaped by hand in the body editor (the long horn longer and
    sharper, the beak, the bass scoop's front and lower lobe).
  - "Telecaster style", "SG style", "Explorer style" (reshaped by hand
    at its shoulder, bottom corner and wing tip) and "Flying V style"
    mockups; the Flying V's switch, control cavity (turned along
    the wing), jack and battery box all on its treble wing.
- Five more neck templates for the headstock editor's *Start from*,
  mockups traced from the same kind of photos:
  - Stratocaster: flat six-in-line on a slotted nut, the posts 22.5 mm
    apart, the tuner edge redrawn along them.
  - Gibson style: a 17 degree "open book" three-a-side.
  - Flying V: a 17 degree three-a-side narrowing to a rounded point.
  - Explorer: a 17 degree six-in-line "hockey stick", its tip hooked
    over to the treble side (drawn fuller by hand), the original's row of
    posts along its steep tuner edge.
- `tuner_inline_offsets`: a row of tuners' posts where they are given
  (one per tuner, across the headstock from the centreline) instead of
  on the strings' lines, so the row can run along a steep drawn edge; the
  strings then bend at the nut toward their posts.
  - Mockingbird: the B.C. Rich three-a-side, its top rising to a point
    (drawn higher by hand).
- DXF export: every build writes `Prototype001_plan.dxf`, the whole
  instrument's plan outlines (body, neck, headstock, fretboard, nut, fret
  slots, inlays, tuner holes, cavities, holes, wire holes, carve, steps,
  contours, engraving, plates), a layer a kind, and
  `Prototype001_covers.dxf`, the sheet plates side by side for cutting
  with their holes, slots and labels. R12 ASCII DXF in millimetres,
  written without a library; listed in the web app's downloads and the
  command line's output.
- String ferrules: every hole a string passes through the body by (a
  hardtail's, single-string bridges') gets its ferrule's counterbore from
  the back, drilled in `Body_back` where the ferrule hides it
  (`body_string_ferrule_diameter` × `_depth`, 8 × 6 mm on a guitar,
  9.5 × 6.5 mm on a bass; 0 deep leaves them to the builder).
- The bridge's fitting notes (its routing sheet, what to check, what is
  left to the hand) are given in `Body_top`'s notes; a seven- or
  eight-string Floyd Rose's note says how to have the deep-dive pocket cut
  under the spring cover.
- Pointed headstocks: drawn edges whose tip corners meet make a sharp
  point (a Jackson style tip) instead of a tip line.
  - In the headstock editor a tip corner dragged within 3 mm of the
    other snaps onto it; the point then moves as one, and Shift-drag
    parts the corners again.
  - The edges may narrow to the point over their last run; a pinch or a
    crossing anywhere else is still refused.
  - The neck's outline program cuts the point, and the FreeCAD model is
    lofted wide and cut back to it.
- A `camo` engraving pattern, cut as a relief:
  - Closed, lobed woodland shapes with one to three arms, stretched one
    way and laid densely; a shape that does not fit is tried with fewer
    arms, then smaller and rounder, so the gaps fill — the smallest still
    12 mm across.
  - Shapes at different levels lie over one another (the deeper shows
    where they overlap, each keeping half its outline showing); shapes at
    one level, and any two side by side, keep 3 mm apart.
  - Each is cleared flat to one of four levels, a quarter of
    `body_engraving_depth` apart (0.5, 1, 1.5 and 2 mm by default); one
    wholly inside another is cut on from its floor.
  - `Body_top_relief.nc` cuts them with a flat end mill
    (`relief_tool_diameter`, 3 mm); the FreeCAD model cuts them and the
    body editor shades them by depth.
  - On a carved or stepped top they keep to a level face.
- Wire channels between the cavities (`body_wire_channels`, on by
  default):
  - Every pickup route is wired to the controls, nearest first, so a row
    of pickups chains to them; a separate switch cavity joins the chain
    the same way (a Les Paul's toggle by its neck pickup), and a battery
    box's lead runs straight to the controls.
  - The bridge's ground wire runs from the controls to a tremolo's spring
    cavity, or else the nearest bridge route or hole.
  - Under a pickguard the channel is routed from the top (10 mm wide, up
    to 16 mm deep) in `Body_top`.
  - Every other way is a straight hole drilled by hand (6 mm, the ground
    3 mm). Its height and angle are found so the bit gets in through the
    cavity's open face, the hole keeps 3 mm under the top and over the
    back and 2 mm from other cavities, and it opens into both cavities.
  - Each hole is modelled in FreeCAD, drawn dashed in the plan view and
    given in `Body_top`'s notes (from where, the angle, the aim, the
    length).
  - A way no straight hole fits is left to the builder with a note.
- An inlay editor in the web app (*Inlay design*, under the headstock
  editor):
  - It draws the first fret marker's space on the board with the chosen
    style's marker in it, and the whole board below with every marker.
  - Dragging a corner, adding one (click a side) or removing one
    (Alt-click or right-click) draws your own marker: the new `custom`
    inlay style, its corners in `inlay_points`.
  - Every marker is that shape fitted to its own fret space and the
    board's width there.
  - A dashed line shows where the shape fits every marker (1 mm from the
    frets and the edges); a drag stops at it, and the panel names the fret
    a shape does not fit.
  - *Start over* goes back to a block.
  - Drawn markers are cut, sheet-cut as pieces and modelled like the other
    styles, with slanted and fanned frets too.
- An ESP LTD Alexi Hexed style body template (mockup, not the original):
  - The Jackson RR style outline (ESP's Alexi body is an offset V after
    Alexi Laiho's Jackson RRs).
  - Loading it in the body editor also sets the Hexed's look
    (`BODY_TEMPLATE_VALUES`): one bridge humbucker under one volume pot,
    a Floyd Rose, and its graphic as a stepped top.
- A stepped top (`body_stepped_top`, `body_top_step_height` 1.5 mm): the
  top lowered in bands along the edge, the middle at full height and each
  band nearer the edge a step lower.
  - Each step's line is drawn (the shape's `step_points`, straight lines
    between points, edited with diamond handles in the body editor), or
    taken in from the edge by `body_top_step_insets` (12 and 40 mm;
    *Auto steps*).
  - The Alexi Hexed template draws its steps where the original's
    pinstripes run: two nested arrows from the edge beside the neck pocket
    into the wings, each tail a sharp V at the notch.
  - Drawn lines may meet off the body, in the neck pocket or by the edge;
    the editor keeps the steps' handles on top.
  - `Body_top_steps.nc` cuts the bands in passes along the edge, each
    step's wall true.
  - The FreeCAD model cuts the steps as rings.
  - The back's cavities keep their top wall under the bands.
  - The plan view and the body editor draw the step walls.
- A `pinstripe` engraving pattern: one stripe round the body just inside
  the engraving's margin, following the edge as a painted pinstripe does,
  broken where something is in its way.
- Body templates can set other values besides their shape; the editor's
  confirmation names them.

- More control layouts (`body_controls`):
  - `superstrat`: an Ibanez RG / Jackson style rear cavity with the 5-way
    blade switch in it beside the volume and tone pots. The switch sits in a
    deeper pocket under a 4 mm top; its lever's slot is routed from the top
    into that pocket, and its two screws go through the top 1-5/8 in apart.
  - `volume_1`: one volume pot; the round switch cavity only with two or
    more pickups.
  - `active_4`: an active bass's four pots in a row in a cavity with room
    for the preamp.
  - `jazz_bass`: a Jazz Bass style plate in the top (three pots, two screws
    4.9 in apart).
- `body_jack` "plate": the jack on the Jazz Bass plate, nothing bored from
  the edge (`BodySolid.jack_hole` may be `None`).

- The Floyd Rose and the Kahler for seven and eight strings
  (`string_count` on `FloydRoseSpec` and `KahlerBridgeSpec`). The Floyd
  Rose's widths follow its stud spacing by the margins on Floyd Rose's
  six- and seven-string routing sheets (`FloydRoseSpec.widths()`): the
  seven-string's 84.58 mm studs, 105.92 mm recess and 93.52 mm block
  route, no block pocket deeper than the spring cavity, as drawn; the
  eight-string (no published routing) widened to the FRT8's 95.5 mm
  studs. The Kahler 7327/7328 cutout is 20.32 mm wider, as Kahler's
  installation sheets have it. Widths left empty come from the string
  count.
- Floyd Rose's seven- and eight-string locking nuts (`locking_nut`
  "r7" 47.6 mm, "r8" 53.8 mm with three screws, `LockingNutSpec.screw_count`);
  "auto" fits them with a seven- or eight-string Floyd Rose.
- Single-string bridges (`SingleStringBridgeSpec`, `kind`
  "single_string"): a unit per string, two screws and an optional string
  hole each; on a multiscale each unit stands at its own string's scale,
  square to its string — for fanned basses above all.
- A top-loaded hardtail (`HardtailSpec.string_through` off): no string
  holes through the body, as most bass bridges allow.

- A set neck (`neck_joint` "set", `set_neck_glue_gap` 0.05 mm): the heel
  glued into a tight pocket, Gibson style — no bolts or ferrules, a neck
  angle as for a bolt-on neck, a heel-adjusted truss rod only with its
  spoke wheel; the neck's notes say how to glue it in.
- A one-piece instrument (`neck_joint` "one_piece"): the neck and the
  whole body cut from one blank, as a neck-through whose block is the
  whole body — no wings, no glue lines; its body programs are
  `Neck_body_...` on the neck blank's dowels, and the FreeCAD model shows
  the body as one object.
- Carbon fibre neck reinforcement (`neck_carbon_rods`; the bars'
  `neck_carbon_rod_size` 3.2 x 6.35 mm, 4 x 4 mm, 3.2 x 9.5 mm or custom;
  their start, length and offset): two bars in channels beside
  the truss rod, under the fretboard, checked to leave 2 mm of wood under
  them and beside the rod and the neck's sides; `Neck_carbon_rods.nc`
  cuts the channels with a 3 mm end mill, the FreeCAD model cuts them and
  shows the bars, the plan view dashes them.
- Every field in the web form explains itself on hover (its name
  underlined dotted): taken from the code's own documentation
  (`webapp._field_help`: docstrings and the comments above the
  parameters), with plain words for the settings shown up front
  (`field_help.FIELD_HELP`).
- A zero fret (`nut_style` "zero_fret", `zero_fret_gap` 3 mm): a fret on
  the nut line, the nut a string guide in a slot behind it on the board's
  run-on (`FretLayout.zero_fret_slot`, `LockingNutSpec.set_back`); its
  slot is cut first in `Fretboard_slots.nc` and in the FreeCAD model, and
  drawn in the plan view.
- The headstock editor offers the nut's style in its own pane (shelf,
  Fender slot, zero fret) and draws the nut, the board running on past
  the nut line and a zero fret.
- The web app names the guitar (*Guitar name*, saved with the design and
  naming its file) and downloads every NC program in one ZIP named for it
  (*Download all NC files (.zip)*, `webapp.nc_archive`): a folder a part,
  each program numbered in running order, and a README listing them with
  their tools and run times.
- A neck-through construction (`neck_joint` "neck_through",
  `neck_through_width`, `neck_through_heel_ramp`): the neck blank runs on
  through the body as its centre block (wide enough for the pickup and
  bridge routes by default), the two wings cut from their own blanks and
  glued to its sides. No neck pocket or bolts; the neck's back falls to
  the body's thickness where the body begins. The neck blank's programs
  cut the block's features on its own dowels (`Neck_block_...`) and its
  whole outline full depth; each wing gets the body's programs
  (`Wing_bass_...`, `Wing_treble_...`), every feature reaching it cut
  whole and its edge finishes run on past the glue line so the glue faces
  stay square. The FreeCAD model splits the body into `Neck_block` and
  the wings; the plan view and body editor show the block.
- A left-handed option (`handedness`, "right" or "left", first in the
  form): the instrument built as its mirror image across the centreline
  while the design stays stored as drawn. The body shape and its
  electronics, pickguard and contours (`mirrored_shape`, a `mirrored`
  flag for the traced outline and almond cavity), the bass side
  (`bass_sign`: pickups, bridge, fan, frets, inlays, tuners), a Floyd
  Rose's arm side and a drawn headstock tip flip; the headstock lettering
  is set again so it still reads (its angle 180 degrees less). The body
  and headstock editors show the design mirrored.
- A carved top, Les Paul style, for any body (`body_carved_top` and its
  depth `body_carve_depth`, 9.5 mm, both beside the body editor too,
  `body_carve_rim` 8 mm, `body_carve_margin`
  15 mm; `CarvedTop`): flat over a plateau drawn in straight lines and
  arcs round the neck pocket, the pickups (12 mm, for their mounting
  rings) and the bridge, its tail end a half circle, falling smoothly
  (exact distance transforms, relaxed: no creases or bumps) to a flat rim
  at the edge, the plateau keeping 12 mm clear of the edge so the top has
  room to fall beside the neck pocket and along a cutaway (only the
  pickups' rings, 7 mm round their routes, and the bridge stay flat
  nearer), the rim narrowing
  where the plateau comes near but always
  keeping a top binding's channel on its level. The back's cavities keep
  their top wall under it; `Body_top_carve.nc` roughs it first, to sand
  smooth by hand (its runs linked in the cut; `carve_tool_diameter` for a
  bigger roughing tool, `carve_finish` for a ball-nose finish; about 92
  minutes on a Les Paul with the 6 mm tool, 55 with a 10 mm one); a top
  roundover or binding is cut on the rim and the engraving
  follows the arch. The FreeCAD model cuts it last, under a cubic
  surface with the heights every 4 mm as its control points, light and
  unable to ripple into the plateau, its control points raised where the
  top falls too sharply to follow (by a Les Paul's neck pickup at the
  cutaway it dipped under a corner of the pickup's ring; the rim's strip
  is cut to its level on its own, so no wood is left over the binding by
  the neck pocket), standing 0.3 mm
  clear over the
  plateau so it crosses the top cleanly (a surface a hair above it met it
  nearly tangent, and the cut could leave the body quietly uncut), and
  checks the cut took off the carve's wood.
- More body engraving patterns (`body_engraving_pattern`, beside the
  body editor too): Eddie Van Halen style taped `evh_stripes`, `flame`,
  `ripples` and `crackle`, all laid out from the seed like the scrolls
  (`pattern_lines`).
- More fretboard markers (`inlay_style`): Les Paul `trapezoid`, Jackson
  `sharktooth`, `parallelogram`, `diamond` and Gibson `split_block`,
  each spanning the board between its frets like the blocks, sized to
  its taper, leaning with slanted frets and cut from sheet as pieces;
  the bass side follows `headstock_bass_side`.
- A neck angle (`neck_angle`, degrees; empty: 2° with a Tune-o-matic,
  0° otherwise): the neck pocket's floor sinks toward its mouth
  (`TracedCavity.floor_slope`), cut in 0.1 mm terraces after the pocket in
  `Body_top.nc`; the neck turns about the floor's heel end in the FreeCAD
  model; and the bridge moves so the scale, and the 12th fret halfway,
  hold along the tilted strings (`bridge_scale_line`, `neck_to_body`).
- A low-profile truss rod (`truss_rod_profile` "low_profile"): one
  straight 6.35 × 9.5 mm channel with no step or pocket, as StewMac's and
  Hosco's Hot Rod Low-profile (1/4 × 3/8 in, 4 mm hex key), which fits
  the thin neck by the nut without thickening it; no spoke wheel by
  default.
- A choice of spoke wheel for the truss rod (`truss_rod_spoke_wheel`:
  auto, yes, no; auto fits one at the heel and none at the headstock).
  Without one at the heel the route runs out through the heel's end, the
  adjuster nut at its end face, so no bore or body notch is needed. At
  the headstock a wheel sits in an open trough behind the nut; without
  one, behind a slotted nut, the router cuts only the open start of the
  key's hole, a notch `truss_rod_key_hole_diameter` (8 mm) wide.
- A Telecaster neck: the nut can sit in a slot in the fretboard, Fender
  style (`nut_style` "slot", `nut_thickness`, `nut_slot_depth`): the
  board runs on past the nut line, the slot milled into it
  (`Nut slot` in `Fretboard_inlays.nc`), then carries on at full height
  behind the nut (`nut_slot_lip`, 3 mm) and slopes down to the glue face
  (`nut_slot_taper`, 3 mm; stepped in `Fretboard_outline.nc`), the nut
  glued in. A headstock-adjusted truss rod is then reached without a
  cover (see the spoke wheel). The headstock
  editor's *Start from* loads a whole Telecaster neck (`NECK_TEMPLATES`):
  the slotted nut, a flat six-in-line headstock drawn as a Telecaster's
  and a truss rod adjusted at the heel (or, chosen after, behind the nut).
- The plan view draws the nut on its seat (bone white, or dark for a
  locking nut), and a fretboard that runs on under it (a slotted nut's,
  an R2's) reaches under it and on behind it, with a line where a slotted
  nut's board starts sloping down.
- The fretboard's marker inlays can be cut from sheet: barbed-wire and
  block markers get `Fretboard_inlay_pieces.nc` (part `Inlays`,
  `plan_inlay_machining`), every piece nested in fret order on a sheet as
  thick as the pockets are deep and cut with the inlay end mill, 0.1 mm
  smaller all round than its pocket. Round dots get no program.
- Headless guitar and headless bass instruments (`headless`): no
  headstock or tuners, the neck ending in a 35 mm flat headpiece for the
  string anchor (`headless_length`), and a headless bridge with the tuners
  (`HeadlessBridgeSpec`, `kind` "headless"): a plate screwed to the top at
  its four corners, its footprint kept clear by the pickguard and
  engraving and required to lie on the body.
- Lettering engraved into the headstock face (`headstock_engraving_text`):
  in a single-stroke font (`geometry.lettering`: a plain sans, or Hershey
  Script or Hershey Gothic English converted from Inkscape's SVG fonts by
  `tools/import_svg_font.py`, with ä ö å), placed, sized and turned
  in the headstock editor (drag it there), kept clear of the edge, the
  nut's seat and the tuner holes, cut 1 mm deep with a V-bit following the
  angled face in `Headstock_engraving.nc`; drawn as lines in the FreeCAD
  model. Text parameters are plain text fields in the web app's form.
- Fretboard binding (`fretboard_binding_width`): the board is cut that much
  narrower each side and strips glued along its long edges keep the
  nominal widths; the outline and slot programs say so, and the FreeCAD
  model shows the strips (`FretboardBinding`).
- A decorative engraving on the top (`body_engraving`): Design by Jone's
  scroll motif scattered at random from `body_engraving_seed` (*New
  pattern* in the body editor draws a new one), never more than ten lines
  crowded together nor a line standing alone, kept clear of every top
  cavity, the bridge, the pickguard, the contours and the holes (the
  back's cavities only when one would leave under 3 mm of wood), cut 2 mm
  deep with a V-bit in `Body_top_engraving.nc` (`presets.engraving`,
  `cam.engraving`, `engraving_tool_angle`); drawn blue in the body
  editor and as lines in the FreeCAD model.
- Every pickguard, automatic or drawn, steps round a heel-adjusted truss
  rod's access notch (at least 2 mm clear), so the spoke wheel can be
  turned with the guard on (`clear_of_truss_rod`).
- The bridge is chosen in the body editor's own pane too, beside the
  pickups (its sizes stay in the form).
- The arm contour's starting line can be drawn in the body editor
  (`arm_contour_points`): a green line with round handles, its ends on
  the body's edge, shown while `body_arm_contour_depth` is on; the bevel
  reaches in to it, deepest where it is furthest in
  (`ContourCut.along_line`, `open_catmull_rom`). *Auto arm contour* goes
  back to the automatic one.
- The belly cut's starting line can be drawn the same way
  (`belly_cut_points`): a blue line on the back, seen from the top as the
  outline is, shown while `body_belly_cut_depth` (now beside the editor
  too) is on; *Auto belly cut* goes back to the automatic one.
- A pickguard (`body_pickguard`): shaped to the body (the outline 6 mm in,
  reaching forward beside the neck with a notch for it as a
  Stratocaster's does, on to the bridge, past every pickup, round the
  shorter horn, but on the longer horn's side 8 mm past the pickups,
  flaring out toward the bridge, and on past the bridge's front either
  side of it; `body_pickguard_style` draws it as a Stratocaster's —
  a tongue beside the neck, a rounded tail past the bridge — or a
  superstrat's, close round the pickups; on a V (the Jackson RR) it runs
  100 mm out along the shorter wing; the Stratocaster style template
  comes with a guard traced from a Stratocaster's HH guard, and the Jazz
  Bass style and Design by Jone ones with the same guard fitted to them,
  the Jackson RR style and Les Paul style ones with guards drawn for
  them;
  a drawn guard steps round whichever bridge is fitted, and every guard
  clears the Kahler 7300's plate, 5 mm bigger all round than its cutout
  (`plate_overhang`, drawn dashed in the body editor)) or drawn with
  its own handles in the body editor (`pickguard_points`; a click on its
  edge adds a point, Alt- or right-click removes one, dragging the edge
  moves the whole guard or, onto *Create NC file*, makes its own
  programs, *Auto pickguard* goes back; its openings and holes show cut out of it), with rectangular openings the size of the
  chosen pickup layout's pickups, holes for the pots and selector under it and screws round its
  edge, cut from sheet in `Cover_pickguard.nc` (`presets.pickguard`).
  The control layout `pickguard` mounts three pots and a 5-way blade
  switch in it, Stratocaster style, over a cavity routed from the top;
  the guard then runs on past the bridge on the controls' side; a drawn
  guard that does not cover them is refused.
- Output jack housings (`body_jack`): a side jack (`side`, the default: a
  Les Paul style plate or a barrel jack), a cup jack or Electrosocket
  (`cup`, a 7/8 in counterbore at the edge) or a Stratocaster style top
  plate (`strat`, a 1 in cavity routed from the top). The jack's bore
  now starts where its line meets the drawn outline, whatever the body,
  and runs on into the control cavity (`body_jack_depth`, now optional,
  fixes its length); the body editor warns when it misses the cavity.
  The Jackson RR style template's jack moved to the treble wing's edge by
  its control cavity, aimed at it.
- A five-string bass (`five_string_bass`, "5-string bass" in the web
  app), as the seven- and eight-string guitars are: the four-string's
  values with a 47 mm nut, 18 mm at the bridge, a 77 mm heel, a 4+1
  headstock (Fender Jazz V style) and a five-string hardtail, its Jazz
  Bass route Warmoth's 4-1/8 in five-string one (104 mm). New headstock
  styles 4+1, 1+4, 3+2, 2+3, 5_inline and 5_inline_reverse; a lone tuner
  on one side now gets its edge `tuner_edge_offset` out, and a row's
  fitted edge moves out when its end tuners would sit more than 0.5 mm
  too near it.
- One feature on its own: dragged onto *Create NC file* in the body
  editor, a feature (a battery box forgotten in the first build, say)
  gets its own NC programs with the work zero at its centre instead of
  the index pins, its cover plates included (`cam.plan_feature_machining`,
  `webapp.feature_programs`); each file has a *Simulate* button too.
- The body editor asks to remove a feature dropped wholly outside the
  body: a pickup (the layout turns "custom" with that position empty),
  the controls, the battery box, or one of several pots or neck bolts;
  declined, it goes back. The schema lists each pickup layout's types
  (`pickup_configurations`).
- Rickenbacker style bass humbuckers: the pickup type `rickenbacker` (a
  4003's, or a Seymour Duncan SRB-1: a 90 x 36 mm block, routed 92 x
  38 mm, screwed 82 mm apart) and the bass layout `RR`, one at the neck
  and one at the bridge.
- A drawn headstock's tip can be shaped: one click on the tip in the
  headstock editor adds a handle (`headstock_tip_points`, how far past
  the tip line and Y), dragged out for a pointed or rounded tip or in for
  a notch. Edges and tip are rounded curves through their handles (the
  edges a `SmoothCurve` that may swing past them, the tip a Catmull–Rom
  curve leaving each corner along its edge), so a Stratocaster or
  Schecter style headstock can be drawn; the FreeCAD model,
  the neck's outline program and blank, the plan view and the tuner
  holes' tip clearance all follow it (`HeadstockPlan.tip_points`,
  `reach`, `tip_outline`, `tip_clearance`). A drawn headstock's edges
  were monotone curves that never bulged past their handles: saved
  drawn headstocks now round a little more through theirs.
- A top-mounted Floyd Rose locking nut (`locking_nut`): "auto" (the
  default) takes the Floyd Rose Original R2 with a Floyd Rose bridge,
  "none", "r2" or "r3" choose outright. Its seat runs 16 mm behind the nut
  line (the headstock face and a headstock-adjusted truss rod's pocket
  start behind it), its shelf sits from the frets' tops (`fret_height`):
  the R2's on the fretboard, which runs on under the nut and is milled
  down to it in `Fretboard_outline.nc`, the R3's on the neck on a shim.
  The FreeCAD model drills its two screws' pilot holes; `Neck_top.nc`'s
  notes say how to fit it (`geometry.neck.locking_nut`). In the web form
  `nut_width` now sits in the Neck group beside it, and choosing a nut
  wider than the neck (the R3) widens `nut_width` to it (43 mm).
- The control layout can be turned: the body shape's
  `control_angle_degrees` turns the cavity, its cover and its pots (or the
  Tele plate with its screws and blade slot) about the cavity's centre. In
  the body editor a Shift-drag turns the control cavity, the battery box
  or the jack; round cavities only move. One click on the outline now
  adds a handle there (it took a double-click, which also caught the body
  inside it).
- The control cavity stretches: the body shape's `control_stretch` makes
  the cavity and its cover longer (or shorter) along their long axis from
  their centre, moving a generated layout's end pots (the Tele plate's
  screws, slot and rear pot) out with the ends; `control_stretch_across`
  makes them wider (or narrower), the Gibson layout's pot rows moving
  apart, down to 16 mm wide. The body editor has a square handle at each
  end and each side of the cover to drag.
- A battery box for two 9 V batteries side by side
  (`body_battery_count` 2): 28 mm wider, 56 × 58 mm in a 70 × 72 mm cover
  recess. A basic field in the web form.
- A laminated neck blank (`neck_blank` / `NeckMachiningParameters.blank`
  = `"laminated"`): the neck is cut from its own 20 mm plank first, then a
  block as thick as the plank is glued under the headstock end, and the
  headstock gets programs of its own (`Headstock_top`,
  `Headstock_back_rough`, `Headstock_back_finish`) before the whole
  outline (`Neck_back_outline`).
- The pickup selector can be a micro (mini) toggle: `body_switch`
  chooses a 3-way toggle (1/2 in, 12.7 mm hole, the default) or a micro
  toggle (1/4 in, 6.35 mm); `body_switch_shaft_hole_diameter` now only
  overrides the hole. A basic choice in the web form.
- G-code dialects: `MachiningParameters.post_processor` writes every
  program for GRBL (default), LinuxCNC, Mach3/4 / UCCNC, Marlin or a
  Fanuc-style control, or as KOSY / nccad `.knc` programs (feeds in
  nccad's units, spindle on relay 6, `G99` end) (`cam.GCodeWriter`;
  `GRBLWriter` stays the GRBL default), and `spindle_dwell` waits for the
  spindle in each dialect's own units. Both are basic fields in the web
  app's machining form.
- A Floyd Rose's spring cavity gets its sheet cover: six screws spotted
  on the ledge and `Cover_floyd_rose_spring_cavity.nc`, like the cavity
  covers (`controls.rear_cover`). Its cover recess is 8 mm wider all
  round (was 5 mm, too narrow for the screws).

### Changed

- The fretboard programs' notes say where to re-touch Z: on the blank's
  untouched top beside the board, not on the radiused surface (1 mm lower
  at the crown, so every cut, the fret slots' first included, would go
  that much too deep); the slot program also says how each slot starts.
- The fret slots are cut at 30 000 rpm, at most 0.2 mm a pass (they were
  12 000 rpm, 0.9 mm), so the 0.6 mm cutter does not snap; both are
  settings in the machining form (`fret_slot_spindle_speed`,
  `fret_slot_step_down`). The 1 mm inlay cutter likewise (it was
  12 000 rpm, 1 mm a pass), for the inlay pockets, a slotted nut's slot
  and the inlay pieces (`inlay_spindle_speed`, `inlay_step_down`).
- A closed engraving line the area cuts (a ripple ring, the pinstripe) is
  turned to start at the cut, so its pieces are no longer split again at
  its seam.
- The web app's build button reads *Build 3D and CNC files* (it was
  *Build Prototype001*).
- A bridge kind takes only the string counts it is made for
  (`BRIDGE_MIN_STRINGS` / `BRIDGE_MAX_STRINGS`), refused before anything
  else is built; a bridge with a string count of its own must carry the
  instrument's, and the web form keeps it in step when the kind changes.
- The six-string Floyd Rose recess is 45.845 / 49.405 mm from the
  centreline (8.89 + 73.91 / 2 and 12.45 + 73.91 / 2, as drawn; it was
  rounded to 45.85 / 49.4).
- Empty optional number fields in the web form say *auto*.
- The FreeCAD script writes its coordinate data to 0.1 micron
  (`SERIAL_DECIMALS`) instead of full floats: a far shorter macro.
- The Tune-o-matic's bass post sits `bass_setback` (3.2 mm, 1/8 in)
  behind the treble one, which is now `compensation` 1.6 mm (1/16 in)
  behind the scale line (was 3 mm, both square): the bridge leans with the
  strings' compensation so every saddle starts mid-travel. A neck with
  its bass side on +Y gets the bridge mirrored (`mirrored_hardware`).
- The neck's notes no longer ask for a filler over the truss rod's route
  under a nut the fretboard runs on under (a Floyd Rose R2's or a slotted
  one): the board covers it there.
- The fretboard's inlay pockets follow the marker outline rounded both
  ways by the inlay end mill's radius (`inlay_fit_outline`), their inner
  corners cut round, so a piece cut from sheet fits them.
- The web app shows the settings that shape an editor's drawing in that
  editor's pane: the pickup layout, controls, pickup selector and
  battery box beside the body drawing, the tuner layout beside the
  headstock's (their rows leave the form; saving and loading are as
  before).
- The bass pickup routes follow Warmoth's rout diagrams: the Jazz Bass
  route is 96 x 20 mm with two round recesses (R8) in each long side
  (it was a plain 100 x 21 mm bar), a screw in each recess outside the
  pickup's sides (a 94.4 x 18.2 mm SJB-1b fits between them); the
  Precision Bass route's two coils are 58 x 28.5 mm (57 mm along the
  neck over both, was 42 mm) and 23 mm over each other, each with a
  round ear (R7) at both ends that its screws go through.
- The headstock is drawn by default (`headstock_outline` "drawn"), so the
  web app's headstock editor is open from the start. Until a handle is
  moved the edges stay empty and follow the fitted outline (a changed
  style redraws them), so the form starts unchanged; *Start over* goes
  back to that. One click on an edge now adds a handle (it took a
  double-click).
- The bass's neck bolts are 56 mm apart along the neck with 5 mm to the
  pocket's end (`body_neck_bolt_spacing_x`, `body_neck_bolt_end_wall` in
  its defaults): the pair at the neck pocket's mouth moves 26 mm out,
  near the body's edge, and the rear pair 2 mm in, its ferrules wholly
  over the pocket. The Stratocaster style template takes the same
  pattern, and the Jackson RR style one moves its front pair out as far
  as its narrow wings allow (50 / 44 mm ahead of the heel end).
- The web app's intro ("What this page does") heads the left column.
  On a narrow screen it comes first, then the buttons
  and the instrument choice with the body and headstock editors and the
  results right under them, and the long form last. The body editor's
  template row wraps instead of running off a phone's screen.
- The body is always drawn: the web form has no body shape dropdown, and
  the default body is the Design by Jone template (`GUITAR_BODY`, a
  `YourDesignShape`) on a guitar and the Jazz Bass style one on a bass.
  `DesignByJoneShape` (the traced DXF) remains in Python; a saved design
  that names it loads as the template.
- The plan view stands upright, headstock at the top (the side view
  turned a quarter turn clockwise, not mirrored), and the web app fits it
  to the window.
- The neck blank is as thick as the neck and headstock need, not a fixed
  40 mm (`NeckMachiningParameters.blank_thickness` now defaults to none):
  a flat headstock's neck comes from a 20 mm plank. The index-pin notes,
  `build.json` (`stock.Neck`) and the web summary give the blank. The needless 2 mm skin
  under the headstock's lowest point is gone.
- A Floyd Rose's spring cavity and block pocket reach deeper in a body
  thicker than the routing diagram's 1.75 in, so the block route still
  opens into the back (bodies over 45.7 mm were refused).

### Fixed

- The neck heel's mounting block is a true rectangle: its sides are
  square from the glue face down to the full depth and its bottom flat
  right out to them. They sloped in 1.75 mm at the bottom (the squarish
  section's last points fell away to the edge), so the heel met the
  pocket's square walls only at the top; the lead-in from the D profile
  now squares up toward it.
- A zero fret (`nut_style` "zero_fret") is no longer dropped without a
  word under a locking nut (a Floyd Rose's, `locking_nut` "auto"): the
  zero fret's slot is cut and the locking nut stands `zero_fret_gap`
  behind it, its top a little below the frets' tops, the board running on
  at full height under the zero fret before the nut's shelf. A nut too
  tall to stand on the board behind a zero fret is refused with the
  remedy.
- Fanned (multiscale) and slanted frets build in FreeCAD again: since the
  script's coordinates were rounded to 4 decimals, every leaning
  fretboard section came out a hair off its plane, so the fretboard loft
  was invalid ("loft produced an invalid shape") and the fret slots' faces
  failed. The script now puts each section, slot profile and the board's
  run-on behind a slotted nut back onto its plane first. This affected
  fanned basses and guitars alike.

- Choosing the Stratocaster controls in the pickguard (`body_controls`
  "pickguard") no longer fails with "The pickguard does not cover its
  controls" (or "need a pickguard"):
  - The layout brings its guard with it, and the web form ticks
    `body_pickguard`.
  - A drawn guard that does not cover the controls (every template's is
    drawn for its own rear cavities) gives way to the automatic guard.
  - The automatic guard reaches out over the controls, and the body
    editor says so.
  - Where the cavity sits too near the edge or another route to be
    covered, the controls move (and turn, along a Jackson RR's wing) to
    the nearest place that fits.
  - They now fit on every template.

- The Les Paul style template's outline had a bump on the bass side by
  the neck pocket (two control points too close together); one point
  moved, as drawn in the body editor.
- The web form's body shape showed a dropdown of its one kind ("Your
  design"), its hidden row shown by the field style; it is gone, and the
  shape's fields fold away under *body_shape — Advanced*.
- The default instrument and every body template were called left-handed
  in the code and docs; they are right-handed (seen from the front with
  the headstock to the left, the bass side and long horn at -Y).
- A truss rod adjusted at the headstock no longer breaks through the back
  of the neck: its 11 mm pocket and 10.5 mm step lie in the neck by the
  nut, which thins to the first fret's wood (11 mm on the default neck).
  The neck is now made thick enough at the first fret to leave 1 mm under
  them at their edges, where the D profile curves up
  (`first_fret_thickness_needed`, 18.3 mm instead of 17; a thicker
  `first_fret_thickness` is kept), the rod staying wholly on the neck's
  side as before. Its 15.5 mm adjuster trough also broke through an
  angled headstock's root by the nut: without a spoke wheel only the
  key's 8 mm notch is routed now (11.5 mm deep, covered behind a shelf
  nut), and a wheel there needs a flat or thicker headstock.
- Inward tool offsets (`offset_polygon`) no longer cut straight across
  a round corner sampled in edges shorter than the sample spacing: the
  point where the shifted edges cross is kept, so small pocket corners
  (inlay blocks, dots) are cut out to the tool's reach.
- The web app's yes/no questions (*Start from* → *Load*, removing a
  dragged-off feature, switching instrument, loading a design, resetting
  the headstock) are asked in the page's own dialog: some embedded
  browsers answered `window.confirm` unseen, so *Load* did nothing.
- The bridge pickup sat in the same place whatever the bridge, so a
  hardtail's baseplate screw pilots fell inside its route and a
  Tune-o-matic's post holes cut within 4 mm behind it. It now keeps
  `body_bridge_pickup_clearance` (3 mm) of wood ahead of the bridge's
  holes as well as its routes, moving forward on its own (13.3 mm for
  the hardtail, 4.4 mm for the Tune-o-matic on the default guitar), and
  never reaches past the saddle line, fanned on a multiscale (the bass
  soapbar on a guitar used to end 0.27 mm past it); the Kahler and
  Floyd Rose placements are unchanged. A route that would then overlap
  the next pickup is refused with a `BodyGeometryError`.
- The FreeCAD model's headstock top sank in wedges either side of the
  nut's seat and the transition behind it: the loft held its top edge to
  the nut's width there, so the top beside it fell away down the rounded
  edge. The edge now keeps to the headstock's outline all the way to the
  nut (plain to see behind a locking nut's 16 mm seat, slight before).
- The body editor's *Start from* list always showed the Stratocaster
  style template; it now shows the template the drawing is (Design by
  Jone on a guitar, Jazz Bass style on a bass), or "Your own drawing"
  once the outline has been changed.
- The Jackson RR and Les Paul style body templates failed their body
  CAM: their neck pocket runs out past the body's face almost to the
  blank's edge, leaving no room for index pin 1. When the pins do not
  fit, the blank now grows past the furthest of the part and its cuts by
  a dowel plus its clearances — at the end that needs it, front first,
  and at both only when neither alone will do (`cam.fixturing`).
- Loading a saved design shows its drawn body in the body editor. The
  editor used to keep the start shape it showed while the form was being
  filled in, so the loaded outline seemed lost and the next drag wrote the
  start shape over it.
- A 0 degree (flat, Fender-style) headstock is accepted (it was refused
  with "Headstock angle must be between zero and 90 degrees"). It stays 16
  mm thick and is set down: its face is milled 4 mm below the glue face
  behind the nut shelf (`headstock_face_drop`, empty = 4 mm when flat), so
  the headstock ends 20 mm below the fretboard and the strings break over
  the nut toward the tuners.
- The nut's seat on the neck is only as long as the nut (5 mm), level
  with the glue face, and follows a slanted or fanned nut line as a strip
  of even length; the headstock face starts right behind it. A fanned
  nut's seat used to be a square shelf lengthened to reach behind the
  whole nut, leaving up to 20 mm of flat glue face on the treble side.
- Behind the nut's seat the neck eases onto the headstock face over
  `headstock_face_transition` (12 mm) instead of a vertical step or sharp
  corner: a smooth curve for an angled face, a Stratocaster style concave
  cove down to a flat headstock's set-down face. An
  angled face now falls from the seat's back edge (so the tip sits 0.7 mm
  higher and the neck blank is 0.7 mm thinner at 8 degrees), and stays
  square to the neck behind a fanned nut, where only the transition turns.

## v1.0.0-beta1 - 2026-09-27

### Added

- A Gibson or three-pot rear cavity that would rout into a deep top
  route (a Floyd Rose's fine-tuner recess) moves, pots and cover with it,
  to the nearest clear place up to 20 mm out and along the neck, so the
  Gibson layout now works with a Floyd Rose on every template.
- A headstock-adjusted truss rod's route opens the middle of the nut
  seat; `Neck_top.nc`'s notes now ask for a wooden filler over the fitted
  rod, flush with the seat (its width and the seat's length given), before
  the nut is glued. At the heel the seat is whole.
- Neck bolts keep `body_neck_bolt_end_wall` (3 mm, was a fixed 4 mm) of
  wood between their holes and the neck's heel end, now checked for every
  bolt; the default rectangle's tail pair and the Design by Jone and Les
  Paul tail bolts sit right at it, 5.5 mm ahead of the heel end, so the
  bolts spread further along the neck and hold it better.
- The web app credits its author after the motto and links the GitHub
  repository there and in a new footer.
- The truss rod's adjuster openings can be left out: `truss_rod_sleeve_bore`
  (the heel sleeve's hand-drilled bore) and `truss_rod_trough` (the
  headstock trough and its cover), both on by default.
- The neck G-code runs the truss rod's channel, step and pocket each a
  tool radius on over its neighbour, and the pocket toward the adjuster,
  so the round cutter leaves no corner standing into the rod's square
  step and block.
- The web app's downloads come in one list per part (model and report,
  body, neck, fretboard, covers), each program numbered in the order it
  is run with its plot beneath it; `build.json` gives each program's
  `step`, and the summary numbers them too.
- Stock truss-rod lengths: rods are sold by overall length in 20 mm steps
  (`truss_rod_stock_lengths`, 300–600 mm), only the thin part growing.
  With no `truss_rod_rod_length` the neck is routed for the longest stock
  rod that fits (440 mm on the default guitar, 480 mm on the seven-string,
  600 mm on the bass); a given rod is checked, and one too long is
  rejected naming the longest stock rod that fits. The adjusting end
  stays put and the anchor end moves. `Prototype001Parameters.truss_rod_fit`
  returns a `TrussRodFit`; `build.json` (`truss_rod`) and the web app's
  summary report the rod, its route, the longest the neck takes and the
  recommendation.
- An optional rear 9 V battery box (`body_battery_box`, off by default):
  a 56 × 30 mm box (r 5) routed 22 mm up from the back in a 70 × 44 mm
  cover recess (`body_battery_cavity_length`, `_width`, `_depth`,
  `body_battery_cover_margin`), cut in `Body_back_controls.nc`, with a
  two-screw cover cut from sheet in `Cover_battery_cavity.nc`. The body
  shape's `battery_offset`, `battery_y` and `battery_angle_degrees` place
  it; every shape and template puts it as near its control cavity as the
  two covers allow (the lead's channel is drilled by hand), in a spot
  that clears every control layout, bridge and pickup, and the body
  editor drags it.
  `BodySolid` now rejects overlapping rear cover recesses and any hole
  that would open into the battery box.
- Interchangeable bridges (`geometry.body.bridges`): `KahlerBridgeSpec`
  (default), `FloydRoseSpec` (studs, recess, through block route, rear
  spring cavity with cover), `TuneOMaticSpec` (posts and stop-bar studs)
  and `HardtailSpec` (string-through and pilot holes), selected with
  `Prototype001Parameters.body_bridge`; the web form shows it as a
  dropdown of kinds with the chosen kind's dimensions beneath it. `BodySolid` gained `through_cavities` and `extra_rear_cavities`.
  The body CAM drills pivot studs, cuts through routes and puts holes
  narrower than the main tool in a separate `Body_top_small_holes.nc`.

- `FloydRoseSpec` now follows Floyd Rose's own *Original Series Routing
  Diagrams*: stud shelf, 29.59 mm block route opening into the spring
  cavity, and fine-tuner clearance at their drawn sizes and depths, the asymmetric 95.25 mm recess with a
  `treble_side` switch, studs 11.9 mm ahead of the scale line, and a rear
  spring cavity with a deeper block clearance pocket (`RearCavity.steps`).
- Inlay styles: `inlay_style` chooses barbed wire, round dots
  (`inlay_dot_diameter`) or Gibson-style tapered blocks
  (`inlay_block_length_fraction`, `inlay_block_edge_margin`); `Literal`
  parameters appear as dropdowns in the web form.
- `BodySolid` accepts stepped top cavities: a deeper cavity nested inside
  a shallower one is cut from that floor down (the body CAM starts it at
  the enclosing floor), so a two-level recess keeps continuous walls.
- Headstock styles (`headstock_style`): 3+3, six in line on either side
  and 4+2 / 2+4. `HeadstockPlan` can shift its shoulder and tip sideways
  (per-side widths flow through the FreeCAD loft, CAM and plan view) and
  `TunerLayout` places stations on named sides. A tuner row lengthens the
  headstock automatically. In the row styles every post sits on its own
  string's straight line past the nut (a six-in-line row crosses the
  centreline, a 4+2 row converges Music Man-style), and
  every edge with tuners is fitted through its holes `tuner_edge_offset`
  out, so holes sit the same distance from the edge — outside a per-style
  wood reserve (`HEADSTOCK_RESERVES`) that keeps a six-in-line blank big
  enough for a Strat outline and a 4+2 blank for a Music Man one; a
  headstock edge may cross the centreline and the tip may be wider than
  the shoulder. `headstock_bass_side` (default `-y`, the
  left-handed body) makes "bass" the physical bass side in the tuner
  layout and headstock plan. The default 3+3 outline is now 61.7 mm at
  the shoulder and 42.5 mm at the tip, following its holes.
- Body shapes (`Prototype001Parameters.body_shape`, a dropdown in the web
  form): `DesignByJoneShape` (the traced DXF, default) and `YourDesignShape`,
  a body drawn as a closed Catmull-Rom spline through movable control
  points. In the web app "Your design" opens an editor: drag handles to
  shape the outline (double-click to add, Alt-click to remove) and drag
  the control cavity (with its pots), single pots, the switch cavity and
  the jack, and slide the pickup routes along the neck; the neck, pocket
  and bridge stay put. A live check lists any feature left outside.
- Bolt-on neck: four neck-bolt ferrule counterbores (14 mm, 5 mm deep)
  and bolt holes (5 mm) through to the neck pocket, drilled from the back
  (`BodySolid.rear_holes`, a new `Body_back_small_holes.nc` for the
  narrow bolt holes). The body shape's `neck_bolts` place them (a
  trapezoid on the Design by Jone body, whose treble cutaway is deep),
  else a 32 × 40 mm rectangle near the heel end; ferrules must sit in
  wood. The body editor drags the bolts too.
- The Les Paul style body template is a new mockup, labelled "Les Paul
  style (mockup, not the original)": traced from a reference render (60
  control points, 442 × 328 mm) and reshaped by hand at the neck joint and
  treble horn, with its selector switch on the bass-side upper bout.
- The Stratocaster style body template is a new mockup too, labelled
  "Stratocaster style (mockup, not the original)": traced from a reference
  DXF drawing's outermost edge (76 control points, 459 × 323 mm, aligned
  on its neck pocket) and reshaped by hand at both horns and the neck
  joint. A new drawing still starts from the original 42-point outline.
- The Jackson RR style body template is a new mockup too, labelled
  "Jackson RR style (mockup, not the original)": traced from a reference
  render (64 control points, 549 × 415 mm, scaled from its humbucker covers
  and placed from its neck pickup) and reshaped by hand at the neck joint,
  both wing tips and the V notch. Its selector switch sits on the bass
  wing, the pots and control cavity forward on the treble wing and the
  jack in the treble wing's outer edge.
- A Jazz Bass style body template (`jazz_bass`) is new, also a mockup:
  "Jazz Bass style (mockup, not the original)", traced from a reference
  render (76 control points, about 510 × 333 mm, straightened on the
  body's centre stripe and scaled from its bridge pickup) and reshaped by
  hand at both horns and the treble cutaway. It replaces the offset bass
  (the Stratocaster-style outline stretched) as the bass guitar's default
  body, which is gone from the template menu.
- Neck bolts move out toward the neck's edge (`body_neck_bolts_outward`)
  until 5 mm of wood is left beside the hole (`body_neck_bolt_edge_wall`)
  or, by a cutaway, until the ferrule keeps 1 mm of wood to the body's
  edge; they must keep 3 mm of wood to the truss rod and 1 mm between
  ferrules, and a ferrule may run past the neck pocket but not out of the
  body. The Design by Jone treble pair moves to x = -24 and -6, clear of
  the rod.
- Web app: **Save design** downloads every setting — the instrument and
  the drawn body and headstock included — as a JSON file, and **Load
  design** restores it into the form and editors, skipping and listing
  settings the running version does not know.
- Truss rod adjusting end (`truss_rod_adjustment`: heel or headstock) and
  its hardware: the channel (now 6 × 7.5 mm) steps down to a 7.5 × 10.5 ×
  14 mm step and a 9 × 11 × 32 mm pocket at the adjusting end
  (`TrussRodChannel.pockets`). At the heel the adjuster's 12 mm sleeve bore
  (drilled by hand; in the model and the neck program's notes) runs on to
  the heel end on the rod's axis (7.5 mm below the glue face,
  `truss_rod_axis_depth`) and its Ø 15 × 6 mm head sits in a `Truss rod access`
  notch in the body; at the headstock the route starts under the nut and
  the adjuster sits in a trough in the headstock face, with a sheet-cut
  truss-rod cover (`Cover_truss_rod.nc`). Every size is a parameter, and
  the route is fitted to the neck by default (`truss_rod_length` empty).
- Slanted frets (`fret_slant_angle`, 0° by default): every fret, the
  fretboard's nut end and far end tilt about the centerline (`slant` on
  `FretLayout`, `Fretboard` and `FretboardSurface`), block inlays follow
  them, and the fretboard program cuts each slot along its own line. The
  fret spacing stays exact on the centerline; the neck, bridge and
  pickups are unchanged.
- Multiscale (fanned) frets: `bass_scale_length` (with `scale_length` as
  the treble scale) and `perpendicular_fret`. Every fret is straight and
  exact on every string (`FretSkew`, replacing the plain slant on
  `FretLayout`, `Fretboard` and `FretboardSurface`), the centerline gets
  the mean scale, and the pickups turn to the frets at their centres
  (`body_pickups_follow_fan`: auto, yes or no; auto keeps them square
  with a Tune-o-matic). Any bridge can be used, square at the centerline
  scale with its saddles set per string — except a Tune-o-matic, whose
  posts always turn to the fanned bridge line as its saddles have too
  little travel (the stop-bar studs stay); a hardtail can turn its
  string-through holes the same way (`body_bridge_follows_fan`,
  `turned_hardware`). A
  leaning nut end lengthens the neck's nut shelf so the nut keeps 5 mm.
  Inlays follow slanted and fanned frets: blocks lean with them, barbed
  wire turns to their angle and dots move onto their lines.
- The FreeCAD neck has a flat nut seat as long as the nut shelf (as the
  neck G-code already cut it); before, the modelled top tilted from the
  nut itself. The seat is built into the neck loft and the headstock face
  is cut down to its true plane from the end of the shelf, so `NeckBack`
  stays one solid.
  `BodySolid` now tests cavities' real outlines, not just their bounding
  boxes, for overlap.
- Edge finishes, all optional: a roundover on the top and back edges
  (`body_top_edge_radius`, `body_back_edge_radius`), a binding channel
  instead (`body_*_binding_width` / `_depth`), a Strat-style arm contour
  on the top (`body_arm_contour_*`) and a belly cut on the back
  (`body_belly_cut_*`), tapering along the bass-side bouts
  (`EdgeProfile`, `ContourCut`). New ball-nose programs
  `Body_top_edges.nc` / `Body_back_edges.nc` rough and finish the
  contours and sweep the roundovers; the binding channel is cut with the
  outline. The FreeCAD model terraces them in 1 mm layers, the plan view
  and body editor show the contours, and `BodySolid` checks them against
  the cavities: a roundover may lower a nearby cavity's rim by up to
  1 mm, and a contour plus its face's roundover must stay within half
  the body.
- Seven- and eight-string guitars (`for_instrument("seven_string_guitar")`,
  `"eight_string_guitar"`, both in the web form's instrument menu): 25.5-
  and 27-inch scales, wider nuts and heels, a hardtail with a hole per
  string, and new headstock styles 7 / 8 in line (either side), 4+3, 3+4
  and 4+4. Guitar pickups stretch 12 mm per extra string, and
  `body_widening` opens the body along its centreline (12 mm per extra
  string by default) so the wider neck and pickups fit every body shape;
  the drawn-body editor shows the widened outline. Bridges drawn for six
  strings (`BRIDGE_MAX_STRINGS`: Kahler 7300, Floyd Rose, Tune-o-matic)
  are refused for more and hidden in the form.
- Control layouts (`body_controls`, a dropdown in the web form): the
  Design by Jone almond with 2 pots (default), a Gibson-style cavity with
  4 pots, a rear cavity with 3 pots in a row, a Telecaster-style control
  plate routed into the top, or none. The electronics are cut in their own
  `Body_back_controls.nc` / `Body_top_controls.nc`; cover-screw spots sit
  on the recess ledges (`cover_screw_points`) and go in the small-drill
  programs. Every cover and control plate (`CoverPlate`,
  `Prototype001Geometry.covers`) gets its own `Cover_<name>.nc`
  (`cam.plan_cover_machining`) to cut from plexiglass or plastic sheet,
  with its own work zero (`Setup.work_zero`).
- Pickup layouts (`body_pickups`): HH, HSH, HSS, H, SSS and SS for a
  guitar, PJ, JJ, P and MM for a bass, or `custom` with each position's
  own type. New middle pickup position (`body_middle_pickup`,
  `body_middle_pickup_offset`; when empty it sits in the middle of the
  gap between the neck and bridge routes) and a guitar `single_coil`
  route (20 × 88 mm, round ends). A bridge single coil slants
  `body_bridge_single_coil_angle` (10°), its treble end toward the bridge.
  The body editor drags the middle pickup along the neck too.
- Drawn headstocks: `headstock_outline = "drawn"` takes the two edges from
  `headstock_bass_edge` / `headstock_treble_edge` (distance, half-width
  points to the tip, joined by the new `geometry.primitives.MonotoneCurve`)
  and checks that every tuner hole of the chosen style stays at least
  `tuner_edge_offset` from them. The web app opens a headstock editor for
  it: drag the edge handles and the tip, over fixed tuner holes with their
  keep-out circles. New: `HeadstockPlan(bass_edge, treble_edge)`,
  `Prototype001Parameters.headstock_design()` / `tuner_centres()`,
  `webapp.headstock_editor_layout()`.
- Electric guitar or bass guitar: the web form's first control picks the
  instrument and reloads its defaults (`Prototype001Parameters.for_instrument`,
  `INSTRUMENT_OVERRIDES`). The bass is a four-string, 34-inch, 21-fret
  neck (38 mm nut, 62 mm heel, 12-inch radius) with four in-line 19 mm
  tuner holes, Precision + Jazz pickups, a four-string hardtail and an
  offset bass body. New parameters `string_count`, `body_neck_pickup` and
  `body_bridge_pickup` (humbucker, Jazz Bass, Precision Bass, bass
  soapbar or none, `presets.pickups`); headstock styles `2+2`,
  `4_inline`, `4_inline_reverse`; `HardtailSpec.string_count`;
  `BodySolid` pickups may be `None`.
- The drawn body can start from a template (`YOUR_DESIGN_TEMPLATES`):
  Design by Jone (the traced DXF resampled to 64 control points, with its
  own cavity placements), Les Paul, Stratocaster or Jackson RR style. The switch cavity, pot and
  jack placements moved from `body_switch_*` / `body_pot_offsets` /
  `body_jack_offset` parameters into the shape spec. New:
  `geometry.primitives.closed_catmull_rom`,
  `Prototype001Parameters.body_layout()` and `webapp.body_editor_layout`.
- Every `.nc` download row has a *Simulate* button that copies the
  program to the clipboard and opens ncviewer.com in a panel below, ready
  for pasting into its editor (the viewer offers no URL or message API).
- The web form shows only the commonly changed fields of each group and
  folds the rest behind an "Advanced" toggle (`advanced` in the schema),
  with a page-wide checkbox to open them all.
- Toolpath previews shade every cut with the tool's full width, so pockets
  that share a wall are seen to meet instead of showing a tool-centre gap.
- The bridge pickup moves forward automatically when the chosen bridge's
  routes reach ahead of the scale line (a recessed Floyd Rose), keeping
  `body_bridge_pickup_clearance` of wood.

### Changed

- Prototype001's fretboard meets the nut with square corners
  (`fretboard_nut_corner_radius = 0`); the 8 mm rounding is available by
  setting the parameter.

- The build workflow is stepwise (`workflows.Prototype001Build`), and the
  web app shows a spinner and a stage-by-stage progress bar while building.

### Fixed

- The web app versions its script and wheel URLs by build id, so a cached
  `app.js` can no longer run against a newer wheel after a rebuild.
- The joined neck loft no longer self-intersects at the headstock tip
  (FreeCAD's `check(True)` reported it): the rounded headstock edge's
  outermost sample sat 0.06 mm from the edge point, leaving a sliver face
  the length of the loft.
- The FreeCAD truss-rod channel is cut 5 mm above the neck's top instead
  of stopping exactly at it; a headstock-adjusted rod's channel runs over
  the nut shelf, where that left the neck self-intersecting.
- The FreeCAD truss-rod nut pocket or trough is cut as a row of boxes at
  most 5 mm long, so the neck passes `check(True)` (one long box left
  C0 edges where its walls cross the neck's top).

## v0.2.0-alpha1 - 2026-09-16

Everything since v0.1.0-alpha2.

### Added

- Geometry engine: neck centerline, longitudinal side profile, fretboard
  side and radius cross-sections, tapered 3D fretboard surface, loft-ready 3D
  neck-back surface with an exponent-2 elliptical profile, validated
  double-action truss-rod channel, tapered 8-degree headstock plan and
  solid, symmetric 3+3 tuner layout with edge-clearance validation.
- Neck heel: flat bolt-on mounting block (`heel_mounting_length`, default
  54 mm), 45 mm `heel_root_length` D-to-heel loft with rounded shoulders,
  `heel_root_center_extension`, 1.5 mm heel scoop, and lateral fillets on the
  heel and headstock joints.
- Headstock root: `headstock_root_length`, `headstock_root_side_extension`,
  `headstock_volute_length`/`_depth`, 5 mm fixed nut shelf, 12 mm U-shaped
  nut-end trim with 2 mm side fillets.
- Fretboard inlays: `InlayLayout`/`InlayMarker` with 2 mm barbed-wire
  markers at frets 3, 5, 7, 9, 15, 17, 19, 21 and double markers at 12 and 24.
- Solid body (`cncguitarwizard.geometry.body`): `BodySolid`, `BodyOutline`,
  `TracedOutline`, `RectangularCavity`, `CircularCavity`, `TracedCavity`,
  `RearCavity`, `DrilledHole`, `BridgeMounting`, `JackHole`, and
  `BodyGeometryError`; containment, depth, and rear-to-top break-through
  validation.
- Prototype001 body digitised from `assets/reference/omarunko.dxf`: outline,
  trapezoidal neck pocket ending at the heel and opening onto the horn gap,
  humbucker routes with mounting ears, Kahler 7300 baseplate cutout (25 mm),
  rear almond control cavity and round upper-horn switch cavity with 2 mm
  cover recesses, pot and switch shaft holes, pickup-screw recesses, and the
  jack bore into the control cavity. The instrument is left-handed.
- Geometry primitives: `Point3D`, `rounded_polygon_points`, `point_in_polygon`.
- FreeCAD backend: neck-back and fretboard loft scripts, `.FCStd` and STEP
  output, neck assembly export, truss-rod subtraction, radius-following fret
  slots, tuner holes with entry chamfers, headstock fusion, adaptive joint
  fillets, inlay pockets, and the body as a fourth `Part::Feature` with
  top-, rear-, and edge-cut cavities.
- `Prototype001Parameters` preset and `build-prototype001` one-command
  workflow producing `.FCMacro`, `.py`, `.FCStd`, `.step`, `build.json`, and
  `freecad.log`.
- 3D surfacing in the CAM (`cam.surfacing`): drop-cutter offset grids for
  flat and ball-nosed tools, Z-limited roughing and finishing rasters;
  `plan_neck_machining` (truss rod, angled headstock face, tuner centre
  marks, back roughing/finishing, tabbed outline over a holding skin) and
  `plan_fretboard_machining` (radius, inlay pockets, radius-following fret
  slots, tabbed outline). `build-prototype001` now writes thirteen `.nc`
  programs with previews and per-part stock/pin data in `build.json`.
- Dependency-free 2.5D CAM (`cncguitarwizard.cam`): exact scanline clearance
  and pruned polygon offsets, pocket/drill/profile operations, holding tabs,
  a GRBL G-code writer, toolpath SVG plots, and a two-sided body plan on
  centerline index pins. `build-prototype001` now also writes
  `Body_index_pins.nc`, `Body_top.nc`, `Body_back.nc` and their previews,
  and reports stock size and time estimates in `build.json`.
- Browser app for GitHub Pages (`site/`): runs the package in Pyodide,
  generates its form from the parameter dataclasses, builds the FreeCAD
  script, body G-code, toolpath plots and report client-side, with a
  whole-instrument plan view (`render_plan_view_svg`). `tools/build_site.py`
  and a Pages workflow assemble and deploy it.
- Body placements are anchored: outline, pocket, neck pickup, electronics
  and jack ride with the neck's heel end, bridge features with the scale
  length; the neck pocket is derived from the neck's own tapered outline
  with a clearance; index pins are placed automatically in the blank's
  waste on the centerline (horn gap and tail notch), never in the finished
  body, and every program checks both dowels before the spindle starts;
  overlapping top cavities are rejected; inlay markers beyond the last
  fret are skipped.
- `tools/inspect_step_reference.py` for reporting on reference STEP models.
- Documentation: solid-body guide, fretboard-surface and neck-back-surface
  guides, headstock guide, Prototype001 preset and workflow guides, FreeCAD
  backend guide, Finnish manufacturing specification (`SPECIFICATIONS.md`).

### Changed

- `first_fret_thickness` and `twelfth_fret_thickness` now include the 6 mm
  fretboard; generated neck-wood depths are 11 mm and 13 mm.
- The fretboard ends flush with the heel; the neck and heel are one
  uninterrupted loft ending 4 mm after fret 24.
- The first two tuner pairs sit 1 mm closer to the centerline to keep at least
  8 mm of side-edge wood in the longer headstock taper.
- `BridgeMounting` accepts `pivot_stud_spacing=None` (no stud holes) and
  `has_sustain_block=False` (no rear bridge cavity) for flat-mount bridges.
- README and documentation index link every current guide.
- Reference drawings moved from the repository root to `assets/reference/`.

### Fixed

- Joint fillet failures no longer abort the FreeCAD build; each rejected
  radius is logged and the base transition retained.
- The fused neck-to-heel seam is filleted.
- The fretboard taper continues through the mounting block.
- Tuner holes keep the required edge clearance.
- Ruff and mypy run clean across `src` and `tests`.

### Removed

- A stray Python 3.11 virtualenv (`bin/`, `lib/`, `include/`), compiled
  bytecode, and `egg-info` metadata that had been committed despite
  `.gitignore`; scratch STL/SVG/JSON analysis files in the repository root.

## v0.1.0-alpha2

### Added

- Project root dataclass
- Project metadata dataclass
- Initial project unit test
