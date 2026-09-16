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
| `index_pin_diameter` / `index_pin_positions` | 6 mm, automatic | Dowels for the flip; `None` places them in the blank's waste on the centerline |
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
| `Body_index_pins.nc` | Top up | The two dowel holes, through the blank |
| `Body_top.nc` | Top up, on the dowels | Neck pocket, pickup routes, baseplate cutout, screw recesses, pot and switch shaft holes, outline to half depth + overlap |
| `Body_top_small_holes.nc` | Top up, on the dowels (only when needed) | Holes narrower than the main tool — a hardtail's string-through and pilot holes — with the `small_hole_tool_diameter` drill |
| `Body_back.nc` | Flipped, on the dowels | Cover recesses, control and switch cavities, any tremolo spring cavity and its deeper block clearance pocket, outline to half depth + overlap with tabs |

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
- Wire channels between cavities are not modelled.
- Arm and belly contours do not exist on the flat slab.
- Every `.nc` file should be run through a simulator or air-cut before the
  first real blank; the planner has been checked geometrically (every
  cutting move lies inside its own feature), not on a machine.

## Using the planner directly

```python
from cncguitarwizard.cam import GRBLWriter, MachiningParameters, plan_body_machining
from cncguitarwizard.presets import Prototype001Parameters

body = Prototype001Parameters().build().body
plan = plan_body_machining(body, MachiningParameters(feed_rate=800.0))
for setup in plan.setups:
    print(setup.name, round(setup.estimated_minutes(MachiningParameters()), 1), "min")
source = GRBLWriter().render(plan.top, MachiningParameters(feed_rate=800.0))
```

`pocket()`, `drill()` and `profile()` are also usable on their own with any
closed `Point2D` polygon in a machine frame.
