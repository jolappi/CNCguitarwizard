# Changelog

## Unreleased

### Added

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
