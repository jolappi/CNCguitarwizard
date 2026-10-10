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
| `step_down` | 3.0 mm | Maximum axial depth per pass |
| `step_over` | 0.4 | Raster spacing as a fraction of the diameter |
| `finishing_allowance` | 0.30 mm | Wall stock left by roughing, removed by the contour pass |
| `feed_rate` / `plunge_rate` | 1000 / 300 mm/min | Starting values — tune to the wood |
| `spindle_speed` | 10 000 rpm | Emitted with `M3` |
| `safe_height` | 5 mm | Rapid traverse height above the stock top |
| `tab_count` / `tab_length` / `tab_height` | 6 / 8 mm / 4 mm | Holding tabs on the final profile passes |
| `index_pin_diameter` / `index_pin_positions` | automatic, automatic | Dowels for the flip. The holes are drilled with the main tool, so a dowel is never narrower than it: `None` (empty in the form) is 6 mm, or the tool's diameter where it is wider (an 8 mm end mill takes 8 mm dowels, a 1/4 in one 1/4 in dowels); dowels given narrower than the tool are refused. `None` positions place them in the blank's waste on the centerline |
| `index_pin_wall` / `stock_margin` / `stock_edge_margin` | 3 / 15 / 8 mm | Wood between a dowel and the nearest cut; waste around the outline; dowel distance from the blank edge |
| `small_hole_tool_diameter` | 3 mm | Drill for holes narrower than the main tool, in their own program |
| `profile_overlap` | 0.5 mm | How far each side's outline cut passes the mid-plane |

Feeds and speeds are deliberately conservative placeholders; nothing in the
planner depends on them except the time estimate.

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
| `Body_top.nc` | Top up, on the dowels | Neck pocket (with a `neck_angle`, its floor then stepped down toward the mouth in 0.1 mm terraces), pickup routes, baseplate cutout, screw recesses, pot and switch shaft holes, a superstrat cavity's blade switch slot (through the top into its pocket), the wire channels routed under a pickguard, outline to half depth + overlap; the notes say how to drill each wire hole by hand |
| `Body_top_small_holes.nc` | Top up, on the dowels (only when needed) | Holes narrower than the main tool — a hardtail's string-through and pilot holes, a superstrat cavity's blade switch screws, the pickguard's and humbucker frames' screw pilots — with the `small_hole_tool_diameter` drill |
| `Body_top_controls.nc` | Top up, on the dowels (Tele or Jazz Bass plate only) | The control plate recess, then the control cavity from its floor |
| `Body_back.nc` | Flipped, on the dowels | Any tremolo spring cavity with its cover recess and deeper block clearance pocket, the neck-bolt ferrules (none with a neck plate), a string-through bridge's string ferrules, outline to half depth + overlap with tabs |
| `Body_back_controls.nc` | Back up, on the dowels (rear control layouts or a battery box) | The control, switch and battery cover recesses and cavities, and a superstrat cavity's deeper blade switch pocket (the battery lead's and the switch's holes are drilled by hand, as `Body_top`'s notes say) |
| `Body_top_edges.nc` | Top up, on the dowels (only with an arm contour or top roundover) | The arm contour (roughed in step-down layers, then finished with 1 mm passes) and the top roundover, with a ball nose the main tool's size |
| `Body_top_relief.nc` | Top up, on the dowels (only with the `camo` engraving) | The camo relief's shapes, each cleared flat to its level (0.5, 1, 1.5 or 2 mm at the default depth) with a flat end mill (`relief_tool_diameter`, 3 mm) in `engraving_step_down` passes, one inside another on from that one's floor; run it before a top roundover |
| `Body_top_engraving.nc` | Top up, on the dowels (only with `body_engraving`) | The decorative engraving with a V-bit (`engraving_tool_angle`, 60°), each line in `engraving_step_down` (1 mm) passes back and forth to `body_engraving_depth` (2 mm), the nearest line next; run it before a top roundover, while the top is flat |
| `Body_back_small_holes.nc` | Back up, on the dowels | The neck-bolt holes (narrower than the main tool) with the `small_hole_tool_diameter` drill, from each ferrule's floor (with a neck plate, from the back face) into the neck pocket, and the cover-screw spots on the recess ledges |
| `Body_back_edges.nc` | Back up, on the dowels (only with a belly cut, a heel relief or back roundover) | The belly cut, the heel relief and the back roundover, with the ball nose |
| `Cover_<name>.nc` | A sheet on a spoilboard | One program per cover plate (below) |

The electronics are in their own programs so the body can be cut with or
without them and the cavities re-run on their own. The Tele plate's screw
spots go in `Body_top_small_holes.nc`.

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
mirrored so its visible face is up.

Every program first rapids to `X0 Y0` at the safe height — parked over
index pin 1 — then over dowel 2 and back, all before the spindle starts,
so the work zero and the fixture can be checked by eye; it returns to pin 1
after the last cut. Each `.nc` file starts with
operator notes as comments. A matching `.svg`
plots every move (rapids dashed, cuts coloured blue → red by depth) over the
outline in that setup's own frame, so the flipped setup is drawn mirrored.

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
cut, and the back setup's final passes lift over evenly spaced tabs.

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
