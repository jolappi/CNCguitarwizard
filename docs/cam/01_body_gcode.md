# Body G-code

`cncguitarwizard.cam` turns the `BodySolid` into GRBL G-code without any
external CAM package or FreeCAD. The body only needs the 2.5D planner —
pockets, holes and outside profiles with one end mill. The neck and
fretboard add 3D surfacing on top; see
[Neck and fretboard G-code](02_neck_and_fretboard_gcode.md).

## Machine and tooling assumptions

`MachiningParameters` carries everything the planner needs. Its defaults are
the Prototype001 manufacturing specification (TwoTrees H40, GRBL):

| Parameter | Default | Meaning |
| --- | --- | --- |
| `tool_diameter` | 6.0 mm | One flat end mill for every operation |
| `step_down` | 0: half the tool, 3 mm | Maximum axial depth per pass; 0 is half `tool_diameter` |
| `step_over` | 0.4 | Raster spacing as a fraction of the diameter |
| `finishing_allowance` | 0.30 mm | Wall stock left by roughing, removed by the contour pass |
| `feed_rate` / `plunge_rate` | 1000 / 300 mm/min | Starting values — tune to the wood |
| `spindle_speed` | 10 000 rpm | Emitted with `M3` |
| `safe_height` | 5 mm | Rapid traverse height above the stock top |
| `tab_count` / `tab_length` / `tab_height` | 6 / 8 mm / 4 mm | Holding tabs on the final profile passes |
| `index_pin_diameter` / `index_pin_positions` | automatic, automatic | Dowels for the flip. The holes are drilled with the main tool, so a dowel is never narrower than it: `None` (empty in the form) is 6 mm, or the tool's diameter where it is wider (an 8 mm end mill takes 8 mm dowels, a 1/4 in one 1/4 in dowels); dowels given narrower than the tool are refused. `None` positions place them in the blank's waste on the centerline |
| `index_pin_wall` / `stock_margin` / `stock_edge_margin` | 3 / 15 / 8 mm | Wood between a dowel and the nearest cut; waste around the outline; dowel distance from the blank edge |
| `small_hole_tool_diameter` / `small_hole_step_down` | 3 mm / 0: half, 1.5 mm | Drill for holes narrower than the main tool, in their own program, the end mill for routes the main tool fits nowhere in (*Narrow routes*, below), and the cover plates' cutter |
| `corner_cleanup` | `"none"` | Which pockets' inside corners the small end mill cuts after the main tool: `"none"`, `"neck_pocket"` or `"all"` (*Pocket corners*, below) |
| `ball_tool_diameter` / `ball_step_down` | 0: the main tool's / 0: half | The ball nose: the neck's back, the fretboard's radius and scallops, a body's edges |
| `profile_overlap` | 0.5 mm | How far each side's outline cut passes the mid-plane |

Feeds and speeds are deliberately conservative placeholders; nothing in the
planner depends on them except the time estimate.

Every cutter has its size and its depth per pass, and a depth of 0 is half
its diameter (`depth_per_pass`): the main flat end mill, the ball nose
(`ball_cutter`), the small end mill (`small_cutter`; the cover plates, in
sheet, never more than 1 mm a pass), the relief end mill
(`relief_cutter`, `relief_step_down`) and a carved top's roughing and
flat-parts cutters (`carve_cutter`, `carve_flat_cutter`,
`carve_step_down`, `carve_flat_step_down`). The tiny cutters keep a
shallow depth of their own, as they snap: the fret-slot cutter
(`fret_slot_tool_diameter` 0.6 mm, `fret_slot_step_down` 0.2) and the
inlay cutter (`inlay_tool_diameter` 1 mm, `inlay_step_down` 0.2). The
neck's and the fretboard's programs are cut with the same cutters, their
sizes, depths and speeds (`with_cutter`, `with_form_settings`); their own
blanks stay theirs. The web app sets them all on a page of their own,
*Build › Cutters and depths*.

## Coordinate frame and the flip

The body is machined from both faces. Two 6 mm dowels on the neck
centerline locate the blank in both setups, and both sit in the **waste**,
never in the finished body: pin 1 in the horn gap ahead of the neck pocket,
pin 2 in the tail notch behind the body. By default the planner places
them itself — it scans the centerline across the blank for runs where a
dowel fits with the tool diameter plus `index_pin_wall` of wood to every
cut (outline profile and every top cavity, the neck pocket included, since
it reaches into the horn gap) and `stock_edge_margin` from the blank's
edge, then takes the middle of the nut-ward-most and tail-ward-most runs.
Explicit `index_pin_positions` are accepted but checked the same way.
`build.json` records the positions in model and machine coordinates.

Because the dowels are in the waste frame, the holding tabs on the final
profile passes are what keep the body located until the very end.
Because the flip is about the centerline, a model point `(x, y)` becomes
`(x, -y)` on the back and the dowels stay where they were. Every program
therefore shares one work zero:

- **X/Y zero** at index pin 1 (in the neck-pocket floor; the model
  coordinates are in `build.json`);
- **Z zero** on the stock top of the current setup.

Three programs are written, in running order:

| File | Setup | Contents |
| --- | --- | --- |
| `Body_index_pins.nc` | Top up | The two dowel holes, through the blank (a body with no tail notch on the centerline, such as the drawn body's starting shape, gets a blank lengthened so the tail pin sits in waste; likewise a body whose neck pocket runs out past its face, such as the Jackson RR and Les Paul style templates, gets a blank long enough for pin 1 ahead of the pocket — a dowel plus the tool's and `index_pin_wall`'s clearance and `stock_edge_margin`) |
| `Body_top_steps.nc` | Top up, on the dowels (only with `body_stepped_top`), before `Body_top` | A stepped top's bands, each a step deeper than the band inside it, in passes along the edge, each step's wall cut true by the last (see *Stepped top* in the body docs) |
| `Body_top.nc` | Top up, on the dowels | An epoxy tray first, over the whole top round the walls it leaves (`body_epoxy_tray_depth`), then the neck pocket (with a `neck_angle`, its floor then stepped down toward the mouth in 0.1 mm terraces), pickup routes, baseplate cutout, screw recesses, pot and switch shaft holes, a superstrat cavity's blade switch slot (through the top into its pocket), the wire channels routed under a pickguard, outline to half depth + overlap; the notes say how to drill each wire hole by hand |
| `Body_top_small_holes.nc` | Top up, on the dowels (only when needed) | Holes narrower than the main tool — a hardtail's string-through and pilot holes, a superstrat cavity's blade switch screws, the pickguard's and humbucker frames' screw pilots — with the `small_hole_tool_diameter` drill; first, any route the main tool fits nowhere in, with it as an end mill (*Narrow routes*, below), then the pockets' corners with `corner_cleanup` (*Pocket corners*) |
| `Body_top_controls.nc` | Top up, on the dowels (Tele or Jazz Bass plate only) | The control plate recess, then the control cavity from its floor |
| `Body_back.nc` | Flipped, on the dowels | Any tremolo spring cavity with its cover recess and deeper block clearance pocket, the neck-bolt ferrules (none with a neck plate), a string-through bridge's string ferrules (the outline's lower half is cut last, in `Body_back_outline`) |
| `Body_back_controls.nc` | Back up, on the dowels (rear control layouts or a battery box) | The control, switch and battery cover recesses and cavities, and a superstrat cavity's deeper blade switch pocket (the battery lead's and the switch's holes are drilled by hand, as `Body_top`'s notes say) |
| `Body_top_edges.nc` | Top up, on the dowels (only with an arm contour, a top roundover or scooped grooves) | The arm contour (roughed in step-down layers, then finished with 1 mm passes), a Lion's Claw's scoops (where its grooves lift out of the wood past their full-depth part, which `Body_top` pockets: sampled every 0.5 mm, roughed in layers and finished in passes along the neck 1 mm apart) and the top roundover, with a ball nose the main tool's size |
| `Body_top_relief.nc` | Top up, on the dowels (only with the `camo` engraving) | The camo relief's shapes, each cleared flat to its level (0.5, 1, 1.5 or 2 mm at the default depth) with a flat end mill (`relief_tool_diameter`, 3 mm) in `engraving_step_down` passes, one inside another on from that one's floor; run it before a top roundover |
| `Body_top_engraving.nc` | Top up, on the dowels (only with `body_engraving`) | The decorative engraving with a V-bit (`engraving_tool_angle`, 60°), each line in `engraving_step_down` (1 mm) passes back and forth to `body_engraving_depth` (2 mm), the nearest line next; run it before a top roundover, while the top is flat |
| `Body_back_small_holes.nc` | Back up, on the dowels | The neck-bolt holes (narrower than the main tool) with the `small_hole_tool_diameter` drill, from each ferrule's floor (with a neck plate, from the back face) into the neck pocket — with a plate on a heel bevel only a centre mark on the bevel each, the notes saying how to drill them by hand square to it — the cover-screw spots on the recess ledges and a strap guide's screw pilots; first, any rear pocket the main tool fits nowhere in (*Narrow routes*), then the rear pockets' corners with `corner_cleanup` `"all"` (*Pocket corners*) |
| `Body_back_edges.nc` | Back up, on the dowels (only with a belly cut, a heel relief or back roundover) | The belly cut, the heel relief and the back roundover, with the ball nose |
| `Body_back_outline.nc` | Back up, on the dowels, last of all | The outline's lower half, to half depth + overlap, with its tabs: the cut that frees the body, always after every other program (`back_release`) |
| `Cover_<name>.nc` | A sheet on a spoilboard | One program per cover plate (below) |

The electronics are in their own programs so the body can be cut with or
without them and the cavities re-run on their own. The Tele plate's screw
spots go in `Body_top_small_holes.nc`.

### Narrow routes

A route the main tool fits nowhere in is cut with the small end mill
(`small_hole_tool_diameter`) instead, in the face's small-drill program:
from the top in `Body_top_small_holes`, from the back in
`Body_back_small_holes`, the routes first and then the holes (a hole in a
route starts at its floor). Under the default 6 mm end mill every route
fits; under a wider one for quicker roughing (12 mm at 6 mm a pass) the
pickups' wire channels and the truss rod's access at the heel do not.
`Body_top`'s (or `Body_back`'s) notes name each route moved, and the
small program's description and notes then say *end mill*:

```text
Too narrow for the 12 mm end mill, cut in Body_top_small_holes with the 3 mm one: Truss rod access.
```

A route the main tool fits in somewhere is still the main tool's, which
leaves its radius in the inside corners (6 mm under a 12 mm end mill;
*Pocket corners*, below). The neck's truss-rod route goes the same way
(*Neck_top_small_holes*, in the neck's G-code).

### Pocket corners

The main tool leaves its own radius in every inside corner: 3 mm under
the default 6 mm end mill, 6 mm under a 12 mm one. Most routes do not
mind (a pickup's ring, a cavity's cover or the pickguard hides them), but
a square heel, or a set neck's tenon, will not sit right down in its
pocket. `corner_cleanup` has the small end mill cut those corners down to
its own radius (1.5 mm under the default 3 mm one), in the face's
small-drill program after the narrow routes and before the holes:

- `"none"` (the default): the corners stay as the main tool leaves them;
- `"neck_pocket"`: the neck pocket's corners only;
- `"all"`: every route's: the pickups', the electronics' and their cover
  recesses', from the top and from the back, and a separate top's core
  routes (in `Body_core_small_routes`, before the top goes on). Scooped
  grooves are left out: their ends lift out of the wood.

The small end mill follows its own finishing contour, but only along the
stretches where it reaches wood the main tool left (more than
`CORNER_TOLERANCE`, 0.05 mm), each from a point where the wall is already
clean to the next. It goes back and forth along a stretch, one pass
deeper each way, so it never lifts in a corner, and comes down at the
stretch's clean end, in the pocket already cut. On an angled neck's
tilted floor each stretch goes as deep as the terraces let it all along
it, never below them. `Body_top`'s (or `Body_back`'s) notes name the
pockets:

```text
The 12 mm end mill leaves its radius in the corners; Body_top_small_holes cuts them down to the 3 mm one's: Neck pocket corners.
```

A neck pocket's four corners under a 12 mm end mill take the 3 mm end mill
about 640 mm of cutting, a minute and a quarter in the time estimate (under
the default 6 mm end mill, under a minute); `"all"` adds some 5 to 9
minutes to a body under a 12 mm end mill, 1 to 4 under a 6 mm one.

### Edge finishes

All optional and off by default (`cam.body_edges`):

- **Roundover** (`body_top_edge_radius`, `body_back_edge_radius`): the ball's
  centre sweeps a quarter circle `radius + ball radius` about the fillet's
  own centre, one loop of the outline per 1 mm of that arc, from the face
  down into the outline's slot. Offsets come from the outline resampled
  every 1.5 mm and pushed along smoothed normals; where a sample would come
  too close to a pointed horn or a tight cutaway the pass lifts over it.
  Inside an arm contour or belly cut the passes follow the bevel down.
- **Arm contour / belly cut / heel relief**: the bevel's depth map is
  sampled on a 1 mm grid over its area plus the outline's slot, offset for
  the ball (drop-cutter), roughed in step-down layers and finished with
  passes 1 mm apart that run only where the surface is below the face; the
  waste past the slot is left alone. A heel relief's notch comes out flat
  with a wall rounded at its foot by the ball; the neck-bolt ferrules
  drilled under a relief are that much deeper from the back face, so they
  come out right whichever program runs first.
- **Binding channel** (`body_top_binding_width` / `_depth`, and the back's):
  a profile with the main end mill, `binding_width` inside the outline,
  after the outline pass of the same face.

The top face's edge work goes no deeper than the upper outline's slot; the
back's stays 0.5 mm above the outline's holding tabs, so near the deepest
point of a belly cut the roundover may leave a small lip to sand off.

### Cover plates

Every cover (`Prototype001Geometry.covers`) gets its own
`Cover_<name>.nc`, planned by `cam.plan_cover_machining`, to cut from
plexiglass, pickguard plastic or thin plywood as thick as the cover recess
(2 mm by default). The small tool cuts everything (`cam.cover_tool`:
`small_hole_tool_diameter`, feed ≤ 600, plunge ≤ 150, 1 mm steps): the
screw and pot holes, any slot, then the outline with four 4 mm tabs no
higher than half the sheet, all 0.5 mm through. The outline is cut
0.2 mm inside the recess (`COVER_FIT_CLEARANCE`) so the plate drops in.
The work zero is the centre of the cover's bounding box on the sheet top
(the header says so instead of naming index pin 1), and a back cover is
mirrored so its visible face is up. A part screwed onto a face rather
than into a recess is cut to its own outline, and its notes say where it
goes: a pickup frame, the strap guide's plate and spacers, a truss-rod
cover, and a Les Paul style jack plate (`Cover_jack_plate.nc`) on the
body's side over the jack's bore, its screws' pilots drilled by hand
through it.

Every program first rapids to `X0 Y0` at the safe height — parked over
index pin 1 — then over dowel 2 and back, all before the spindle starts,
so the work zero and the fixture can be checked by eye; it returns to pin 1
after the last cut. Each `.nc` file starts with
operator notes as comments, the first after the version always
`REVIEW REQUIRED: simulate and air-cut this program, checking the work
zero, tool, clamps and machine travel, before cutting stock`
(`cam.gcode.REVIEW_REQUIRED_NOTE`): a program is never ready to cut on
its own word, and the operator starts the machine. Its name is the program's and then the tool
it is cut with (`cam.program_stem`), so the file says which cutter to
fit: `Body_top_6mm_flathead.nc`, `Body_back_small_holes_3mm_flathead.nc`,
`Body_top_edges_6mm_ballnose.nc`, `Body_top_engraving_60deg_vbit.nc` (a
V-bit by its angle); the tables here name the programs alone. A matching
`.svg`, named the same,
plots every move (rapids dashed, cuts coloured blue → red by depth) over the
outline in that setup's own frame, so the flipped setup is drawn mirrored.

### A separate top: the core first

A body glued up from a core and a separate top (`BodySolid.cap_thickness`)
with routes under the top (wire channels, chambers) starts with two
programs of its own, run on the core alone before the top is glued on:

- `Body_core_index_pins` drills the two dowel holes through the core, at
  the same places as `Body_index_pins` (the blank: the core's thickness,
  the top's blank as large and the cap's thickness);
- `Body_core_top` pockets the core's routes from its top, the core on its
  dowels, each to its depth below the core's top (its own Z zero);
- `Body_core_small_routes` (only when needed) cuts the core's routes the
  main tool fits nowhere in with the small end mill, after
  `Body_core_top` (a Les Paul's wire channels under a 12 mm end mill: then
  they are all of its routes, and there is no `Body_core_top`), and the
  corners of the others with `corner_cleanup` `"all"`.

Then the top is glued on with the core still on its dowels, the glue kept
out of the routes and the dowel holes; once it has set, `Body_index_pins`
drills on through the top into the core's dowel holes, and every other
program follows as for a body of one piece. Without routes under the top
there are no core programs: `Body_index_pins` says to glue the top on
first.

## Operations

**Pocket.** For every depth pass the planner rasters the region where the
tool fits with the finishing allowance still on the walls, then runs one
finishing contour at the exact tool-radius offset. Rows are linked in the
cut where the link stays clear and by a retract otherwise. Plunges are
straight, at the plunge rate. The raster region is computed exactly per
scanline (the disc-fits test against every edge's stadium), and the contour
is a normal offset pruned by the same disc-fits test, with arc samples placed
on the circumscribed polygon so the chords never gouge the wall. Inside
corners are left at the tool radius, as an end mill must.

**Hole.** Pivot-stud holes (a Floyd Rose) are drilled with the shaft and
recess holes; holes narrower than the main tool get their own program with
the small drill. A tool-sized hole is peck-plunged. A larger hole is first pecked
at its centre, so no pillar survives, then bored with a sampled helix whose
pitch is the step-down, finishing with one full circle on the floor. Pot
and switch shaft holes only break through the 8 mm top wall into the rear
cavity below them; pickup-screw recesses start at the route floor.

**Profile.** The tool centre follows the outward offset counter-clockwise
(part on the tool's left → climb milling). Each face cuts half the thickness
plus the overlap, so no pass exceeds the flute length needed for a 22 mm
cut. The back's half, its final passes lifting over evenly spaced tabs, is
a program of its own, `Body_back_outline`, run after every other back
program (the electronics, the small holes, the edges' ball nose): the cut
that frees a part always runs last, as the neck's and the fretboard's
outlines do. The roundover's ball nose, run before it, cuts its own way
down outside the edge, a little deeper each loop.

## What the G-code does not cover

- The jack bore enters from the edge and needs a drill jig.
- The wire holes between cavities (where no pickguard hides a routed
  channel) are drilled by hand with a long bit, as `Body_top`'s notes
  say (see *Wire channels* in the body docs).
- Every `.nc` file should be run through a simulator or air-cut before the
  first real blank; the planner has been checked geometrically (every
  cutting move lies inside its own feature), not on a machine.

## G-code dialects

`MachiningParameters.post_processor` picks the dialect every program is
written in (`cam.GCodeWriter`; `GRBLWriter` is its GRBL default). Every
dialect carries the same `G0`/`G1` moves — arcs are already lines, so no
controller needs arc support — and differs only around them:

| `post_processor` | For | Differences |
| --- | --- | --- |
| `grbl` (default) | GRBL, grblHAL, FluidNC, Carbide Motion, UGS, Candle | `( )` comments, `G21 G90 G17 G94`, `M3 S…`, `M2` |
| `linuxcnc` | LinuxCNC | as GRBL |
| `mach3` | Mach3 / Mach4 / UCCNC | as GRBL, but `M30` at the end |
| `marlin` | Marlin | `;` comments (Marlin skips `( )` unless built for them), only `G21 G90`, no end code |
| `fanuc` | Fanuc-style industrial controls | `%` around the program, `O1000`, upper-case comments, `G54` and `T1 M6`, `S… M3`, `M30` |
| `kosy` | KOSY / nccad | `.knc` files: two `_` lines and `G90` to start, `;` comments, two decimals, feeds in nccad's units (mm/min ÷ 6, capped at F200 = 1200 mm/min with a note), the spindle on relay 6 (`M10 O6.1` / `M10 O6.0`, no speed), `G99` at the end |

`spindle_dwell` (seconds, 0 by default) waits after the spindle starts, for
a spindle that needs time to reach speed, written in each dialect's own
units: `G4 P` seconds for GRBL and LinuxCNC, `G4 P` milliseconds for Mach
(its default setting) and Marlin, `G4 X` seconds for Fanuc, `M30 P` in
1/18 s for KOSY. The files keep the `.nc` extension (KOSY: `.knc`); rename
them if your control wants another (`.ngc`, `.tap`, `.gcode`) — the
content is plain text. The KOSY dialect follows the KOSY post processor
for Autodesk Fusion as adapted for nccad; its spindle relay and feed
units are those of that setup, so run the first program in nccad's own
simulation. KinetiC-NC (CNC-STEP)
reads the GRBL dialect as it is.

`z_lift_rate` (mm/min, 0 by default) slows the cutter's moves straight up
and down outside the cut: every lift to the safe height, every move back
down to just above the work and the program's first and last move to the
safe height are written as `G1 Z… F…` at that feed instead of `G0`, so the
Z axis never runs at the machine's top speed. A Z motor too weak for a
heavy spindle at that speed stalls lifting and loses steps without a
word, and every cut after it goes that much deeper: a pocket routed
−22 mm comes out −30 mm. The moves across at the safe height stay rapids,
and the time estimate counts the lifts at their feed. Set it to what the
Z axis lifts the spindle reliably at (500–1000 mm/min on a hobby machine),
or lower the machine's own Z top speed (GRBL `$112`, `$122`) instead.

## Eco mode

`eco_mode` (off by default) builds the programs to cut as little air as
they can, every part's — the body's, the neck's, the fretboard's, the
covers' and the inlay pieces':

* **Fast down to the last floor.** A pocket's passes after its first, and
  a hole's pecks after its first, come down as rapids to 1 mm over the
  floor that cut's own last pass left there, not to 1 mm over the stock
  top, and feed down only from there, as a pecking cycle (`G83`) does. The
  first pass still starts over the stock top: nothing but the cut itself
  vouches for the wood being gone (an outline profile's start depth, the
  neck's skin cut, is only roughly so). With a Z lift speed, these moves
  down are fed at it too.
* **Each pass from where the last ended.** A pocket's raster runs the
  other way round on every other pass, and its finishing wall starts at
  its point nearest where the raster ended, so the tool never feeds back
  across the pocket it has just cut: a truss-rod channel's 372 mm back to
  its start, every pass, and the same again to start the next.
* **A ball nose only where there is wood.** A ball nose finishing a
  surface an end mill roughed — a neck's back (`Neck_back_finish`), a
  carved top's arch — runs only where the end mill left wood
  (`raster_finish`'s `rest`): not over the waste beside the neck, cut flat
  to the skin, nor over a carved top's plateau and rim. Its runs are taken
  nearest first, and a hop to the next within two tool diameters
  (`ECO_LINK_DIAMETERS`) is fed straight across 0.5 mm over the surface
  and the wood left (`LINK_CLEARANCE`), not up at the safe height and
  over; the ball nose alone (`neck_back_cut` "ball") links its finishing
  runs so too.

On Prototype001 the neck's back finish goes from 63 to 48 minutes (81 to
51 with a 300 mm/min Z lift speed), a truss-rod channel and every pocket
and hole a little each. The header of every program planned so says
`Eco mode: rapids come down to 1 mm over the floor the last pass cut, not
to the stock top` (`ECO_MODE_NOTE`): air-cut it first like any other.

## Programs run as one

Each part's setups are written one program each, so any of them can be
run, or run again, on its own. With `MachiningParameters.combine_programs`
on, programs that run one after another with the same tool, the same
fixture and the same work zero are joined into one
(`cam.combined_setups`): nothing is done at the machine between them, so
it is loaded and started once. Each setup names how it holds the stock
(`Setup.fixture`): the body's top-face programs share one, its back's
another once the blank is flipped; anything done by hand between two
programs — the dowels put in after `Body_index_pins`, the inlays glued in
before `Fretboard_scallops` — gives the later one its own, as does a
program with its own work zero.

With the default tools, `Body_back` and `Body_back_controls` become
`Body_back_and_controls`; a stepped top's `Body_top_steps`, `Body_top`
and `Body_top_controls` run as one too. A program for another tool (the
small drill, the ball nose, a V-bit) still stands alone. The joined
program is named after the first, then by the words each later one's
name adds (`_and_controls`); its notes are the first's, then each later
one's under its own name, and its preview is drawn on the first one's
face.

## The machine's travel

Every part is planned lying along the machine's X — sideways, its length
across the operator — and by default stays that way.
`MachiningParameters.machine_x_travel` and `machine_y_travel` give how
far the machine reaches (its width and length; empty limits nothing).
A part whose programs do not fit that way but do along Y has all of them
turned a quarter counter-clockwise about the work zero
(`cam.fitted_to_machine`): its X along the machine's Y, its Y along the
machine's −X, the dowels with it, so the stock is turned the same way on
the table and nothing else changes. On a 750 × 1000 mm machine a 650 mm
neck blank still runs sideways and an 850 mm bass neck along Y. What
counts is how far the tool travels (`cam.program_span`): every position
the part's programs visit, the work zero and the dowels included. Each
turned program's notes start by saying so; a part too big either way
stays sideways, its notes saying how much travel it needs. The build
report gives each blank's `machine_turned`, `machine_span_mm` and
`fits_machine`, and its dowels' machine positions as they lie; the web
app's summary says which blanks are turned.

## One feature on its own

A feature left out of a body already cut — a battery box, say — can be
cut on its own (`cam.plan_feature_machining`): only its pockets and holes
(chosen by name), with the work zero at the centre of the feature rather
than at index pin 1, so the machine is zeroed on the spot marked on the
body. A feature on the top face gets `Feature_<name>_top` (and
`_top_small_holes`), one on the back `Feature_<name>_back` (and
`_back_small_holes`), cut with the body flipped about its centerline as
`Body_back` is; its cover plates get their usual sheet programs. In the
web app, drag the feature onto *Create NC file* in the body editor
(`webapp.feature_programs`). The jack's bore enters from the edge and is
drilled by hand.

## Using the planner directly

```python
from cncguitarwizard.cam import GCodeWriter, MachiningParameters, plan_body_machining
from cncguitarwizard.presets import Prototype001Parameters

body = Prototype001Parameters().build().body
plan = plan_body_machining(body, MachiningParameters(feed_rate=800.0))
for setup in plan.setups:
    print(setup.name, round(setup.estimated_minutes(MachiningParameters()), 1), "min")
source = GCodeWriter("linuxcnc").render(plan.top, MachiningParameters(feed_rate=800.0))
```

`pocket()`, `drill()` and `profile()` are also usable on their own with any
closed `Point2D` polygon in a machine frame.
