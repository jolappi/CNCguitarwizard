# Solid body

`cncguitarwizard.geometry.body` models a flat-slab solid body in the neck's
own nut-origin coordinate frame: X runs from the nut toward the tail, Y is
lateral from the centerline, and the body's top face is the same `Z = 0`
plane as the neck-back surface. The body is extruded downward, so a cavity
"cut from the top" removes material below `Z = 0` and a cavity "cut from
the back" removes material upward from `Z = -thickness`.

Seen from the front with the headstock to the left, +Y is up. Prototype001
is a **left-handed** instrument: its long upper horn and switch cavity lie at
-Y, its control cavity and jack at +Y. Mirroring every Y coordinate gives the
right-handed twin.

## Building blocks

| API | Purpose |
| --- | --- |
| `BodyOutline` | Parametric superstrat-style silhouette built from a few dimensions. |
| `TracedOutline` | A silhouette supplied as an explicit closed point loop, for example digitised from a drawing. |
| `RectangularCavity` | Rounded-corner rectangular pocket centred at a point. |
| `CircularCavity` | Round pocket sampled as a polygon. |
| `TracedCavity` | Pocket whose outline is supplied point by point. |
| `RearCavity` | A deep cavity plus a shallow cover-plate recess, both cut from the back face; optional deeper `steps` inside the cavity floor. |
| `DrilledHole` | Vertical round hole from the top face (pot/switch shafts, screw recesses). |
| `BridgeMounting` | Bridge reference line with optional pivot-stud holes and optional sustain-block cavity. |
| `JackHole` | Sideways cylindrical bore in from the edge. |
| `BodySolid` | The complete assembly; cross-validates every feature. |

All three cavity classes share one read interface — `name`, `depth`,
`outline`, `min_x`/`max_x`/`min_y`/`max_y` — so `BodySolid` and the FreeCAD
backend treat them identically.

```python
from cncguitarwizard.geometry.body import (
    BodyOutline,
    BodySolid,
    BridgeMounting,
    JackHole,
    RectangularCavity,
)

body = BodySolid(
    outline=BodyOutline(609.6, 407.2, 28.0),
    thickness=44.0,
    neck_pocket=RectangularCavity("Neck pocket", 434.2, 0.0, 54.0, 56.0, 20.0),
    bridge_pickup=RectangularCavity("Bridge pickup route", 570.0, 0.0, 38.1, 88.9, 22.0),
    neck_pickup=RectangularCavity("Neck pickup route", 500.0, 0.0, 38.1, 88.9, 22.0),
    bridge_mounting=BridgeMounting(609.6),
    jack_hole=JackHole(700.0, 140.0, 160.0),
)
```

## Validation rules

`BodySolid.__post_init__` raises `BodyGeometryError` when:

- any cavity is as deep as the slab, or a drilled hole deeper than it;
- any cavity outline point (inset 0.1 mm toward the cavity centre, to
  tolerate walls that run flush with the outline) lies outside the body
  outline — except the **neck pocket**, whose nut-ward end may open onto
  the horn gap as long as its tail-ward wall is in wood;
- a pivot hole or drilled hole is centred outside the outline;
- two top cavities overlap in plan, unless one is a *step* — a deeper
  cavity whose outline lies entirely inside a shallower one (a tremolo
  recess cut over its whole footprint, then deepened behind the studs) —
  or a through route inside its recess; a nested cavity that is not
  deeper is rejected;
- a rear cavity overlaps a top cavity in plan and their depths together
  reach the slab thickness (they would rout into each other);
- the jack bore would reach clean through the body.

`RearCavity` additionally requires its cover recess to be shallower than the
cavity and to enclose the cavity outline.

## Digitising a drawing

Prototype001's body is traced from the user's own
`assets/reference/omarunko.dxf` (millimetres, `$INSUNITS = 4`); the earlier
`examplebody.pdf` sits beside it for reference. The digitised point sets live in
`cncguitarwizard.presets._omarunko_outline`, already transformed into the
nut-origin frame:

- the outline is the chain of modelspace `ARC`/`LINE` entities (arcs sampled,
  segments chained by nearest endpoints);
- the two pickup routes are the drawing's own pickup block, inserted at its
  two recorded positions; the block's mounting-ear tabs are kept;
- the neck pocket is *not* traced: it is the neck's own tapered outline over
  the last `body_neck_pocket_length` (79.5 mm) before the heel end, widened
  by `body_neck_pocket_clearance` (0.15 mm) per side, so it always matches
  the neck it receives;
- the bridge baseplate cutout is the drawing's `LWPOLYLINE`;
- the almond control cavity and the round switch cavity are the drawing's
  pairs of concentric loops — the inner loop is the cavity, the outer loop the
  2 mm cover-plate recess — both cut from the back.

The frame is anchored on the drawing's own pickup placement: the neck
pickup's nut-ward edge sits 10 mm past the heel end, and the pickups' centre
line is `Y = 0`. Everything else in the drawing follows from that one offset.

## Body shapes

The silhouette is an interchangeable *spec* too (`presets.body_shapes`),
chosen with `Prototype001Parameters.body_shape`, sent from the web form
as a JSON object with a `kind` entry (`body_shape_from_dict` rebuilds it).
The web form always edits a drawn body; Python takes either:

| Spec | `kind` | Outline |
| --- | --- | --- |
| `YourDesignShape` (default) | `your_design` | A body the user draws: a closed Catmull-Rom spline (`geometry.primitives.closed_catmull_rom`, 8 samples per segment) through `control_points`, edited by dragging in the web app. The guitar's default is the Design by Jone template (`GUITAR_BODY`), the bass's the Jazz Bass style one (`BASS_BODY`); the bare class starts as a Stratocaster-inspired offset double cutaway (`YOUR_DESIGN_START_POINTS`) |
| `DesignByJoneShape` | `design_by_jone` | The user's own body traced from `assets/reference/omarunko.dxf` |

A shape carries the outline and the placements that belong to it — the
round switch cavity (centre, cover), the pot shaft holes and the jack bore —
all measured from the heel end, so the body rides with whatever neck it
receives. The almond control cavity and its cover ledge keep the DXF's
shapes on every body; `control_shift` moves them. Both shapes are
left-handed like the DXF: the long upper horn at -Y, controls at +Y. The
drawn body's starting loop closes across the horn gap about 52 mm ahead of
the pocket end so the neck pocket opens onto the gap as the DXF body's does.

`YOUR_DESIGN_TEMPLATES` offers five starting points for a drawn body, each
a complete `YourDesignShape` (outline and electronics placements):

| Key | Label | Outline |
| --- | --- | --- |
| `design_by_jone` | Design by Jone | The traced DXF outline resampled to 64 evenly spaced control points, with that body's own switch, pot and jack placements |
| `les_paul` | Les Paul style (mockup, not the original) | Single cutaway traced from a reference render and reshaped by hand — a genre mockup, not the original outline; its selector switch sits on the bass-side upper bout |
| `stratocaster` | Stratocaster style (mockup, not the original) | Offset double cutaway traced from a reference DXF drawing (aligned on its neck pocket) and reshaped by hand at both horns and the neck joint — a genre mockup, not the original outline; its neck bolts spread like the bass's, the front pair 63.5 mm ahead of the heel end near the body's edge and the rear pair at 7.5 mm, its ferrules wholly over the pocket |
| `jackson_rr` | Jackson RR style (mockup, not the original) | Offset V traced from a reference render and reshaped by hand at the neck joint, both wing tips and the V notch — a genre mockup, not the original outline; the switch on the bass wing, the pots, control cavity and jack on the treble wing; the neck bolts' front pair as far out as the narrow wings allow (50 mm ahead of the heel end on the bass side, 44 mm on the treble side), the rear pair at 7.5 mm |
| `jazz_bass` | Jazz Bass style (mockup, not the original) | Offset waist traced from a reference render (straightened on its centre stripe, scaled from its bridge pickup) and reshaped by hand at both horns and the treble cutaway — a genre mockup, not the original outline; its pots and control cavity on the lower bout behind the bridge pickup; the bass guitar's default body (`BASS_BODY`) |

The Les Paul, Stratocaster, Jackson RR and Jazz Bass ones are mockups:
traced and then reshaped by hand, so they are not the original outlines.

`Prototype001Parameters.body_layout()` returns the outline and every
feature (`BodyLayout`) without building the neck surfaces or validating
the body, in about a millisecond; the web app's editor uses it (through
`webapp.body_editor_layout`) to draw the fixed features under the outline
being drawn. The full `build()` then rejects an outline that leaves a
feature outside the wood.

## Pickups

`body_pickups` picks a named layout (`PICKUP_CONFIGURATIONS`) giving the
neck, middle and bridge types; `custom` takes them from `body_neck_pickup`,
`body_middle_pickup` and `body_bridge_pickup` instead:

| Layout | Neck | Middle | Bridge |
| --- | --- | --- | --- |
| `HH` (guitar default) | humbucker | — | humbucker |
| `HSH` | humbucker | single coil | humbucker |
| `HSS` | single coil | single coil | humbucker |
| `H` | — | — | humbucker |
| `SSS` | single coil | single coil | single coil |
| `SS` | single coil | — | single coil |
| `PJ` (bass default) | Precision Bass | — | Jazz Bass |
| `JJ` | Jazz Bass | — | Jazz Bass |
| `P` | Precision Bass | — | — |
| `MM` | — | — | bass soapbar |
| `RR` | Rickenbacker | — | Rickenbacker |

Every route sits on the centreline: the neck one `body_neck_pickup_offset`
past the heel end, the bridge one `body_bridge_pickup_offset` ahead of the
scale line, and the middle one `body_middle_pickup_offset` past the heel
end — or, left empty, in the middle of the gap between the neck and bridge
routes' facing edges, so a single coil between a single coil and a wider
humbucker still looks centred. A bridge single coil slants
`body_bridge_single_coil_angle` (10°), its treble end toward the bridge as
on a Strat; its screws turn with it. The middle route is one of the body's
extra top cavities. The route types:

| Type | Route | Height-screw recesses |
| --- | --- | --- |
| `humbucker` | The DXF's humbucker with mounting ears (41 × 85.9 mm) | two, `body_pickup_screw_spacing` apart |
| `single_coil` | 20 × 88 mm bar with round ends | two, 76 mm apart |
| `jazz_bass` | 96 × 20 mm bar (Warmoth's 3.75 × 0.79 in bridge rout; the neck pickup is 3-5/8 in) with two round recesses (R8) in each long side, 19.6 mm either side of the middle | four, one in each side recess, 12 mm out from the middle: through the ears on the pickup's sides, 2.9 mm clear of a 94.4 × 18.2 mm pickup (Seymour Duncan SJB-1b) |
| `precision_bass` | Two 58 × 28.5 mm coils one behind the other along the neck (57 mm, Warmoth's 2.28 in) and 23 mm over each other across the strings (93 mm, 3.678 in), the bass coil nut-ward on the bass side, each with a round mounting ear (R7) at both ends: four in all | two per coil, one in each ear, 1.2 mm inside the coil's end |
| `bass_soapbar` | 44 × 102 mm bar with R12 corners (MM style) | two, 90 mm apart |
| `rickenbacker` | 92 × 38 mm bar with R3 corners: a Rickenbacker style bass humbucker (a 4003's, or a Seymour Duncan SRB-1), a 90 × 36 mm block, with 1 mm round it | two, 82 mm apart, through the pickup's base |
| `none` | No route in that position | — |

The bass routes are labelled starting values; check them against the
pickups in hand. `BodySolid.neck_pickup` / `bridge_pickup` may be `None`.

## Neck bolts

A bolt-on neck is held by four bolts through the back of the body. Each
gets a ferrule counterbore (`body_neck_ferrule_diameter` 14 mm,
`body_neck_ferrule_depth` 5 mm) and, on from its floor, a bolt hole
(`body_neck_bolt_hole_diameter` 5 mm) through to the neck pocket — both in
`BodySolid.rear_holes`, drilled from the back. The body shape's
`neck_bolts` (X from the heel end, Y) place them along the neck; left empty
they form a rectangle `body_neck_bolt_spacing_x` (32 mm) by `_y` (40 mm)
with the tail pair as close to the pocket's end as
`body_neck_bolt_end_wall` (3 mm of wood between the hole and the neck's
heel end) allows (or centred `body_neck_bolt_center_offset` ahead of the
heel end). No bolt may come closer to the heel end than that wall; the
templates' own tail bolts sit right at it (5.5 mm ahead of the heel end),
since bolts spread further along the neck hold it better.

With `body_neck_bolts_outward` (the default) every bolt then moves out
across the neck, on its own side, as far from the truss rod as it can go:
until `body_neck_bolt_edge_wall` (5 mm) of wood is left between its hole
and the neck's edge (about ±20 mm on a 56 mm heel), or — beside a
cutaway — until its ferrule keeps `NECK_FERRULE_BODY_WALL` (1 mm) of wood
to the body's edge. A ferrule may run past the neck pocket but never out
of the body. Every bolt must leave that wall to the neck's edge, the end wall to the
heel end, at least
3 mm of wood to the truss-rod channel and a heel-adjusted rod's nut
pocket, and 1 mm between ferrules, or the build says which one to move.
The Design by Jone body's deep treble cutaway leaves room for ferrules
only near the heel end on that side, so its treble pair sits at x = -24
and -6 (y about 10 and 19). In the body editor the bolts can be dragged
along the neck like the cavities.

## Controls and cover plates

`body_controls` picks the electronics layout (`presets.controls`); each
layout is placed from the mean of the body shape's `pot_offsets`, so it
follows the shape and moves with the control group in the body editor.

| Layout | Label | Contents |
| --- | --- | --- |
| `almond_2` | Design by Jone almond | The DXF almond cavity and cover (default), 2 pots at the shape's `pot_offsets`, round switch cavity |
| `gibson_4` | Gibson style | 78 × 70 mm rear cavity (r 16) in a 90 × 82 mm cover recess, 4 pots at ±21 / ±17 mm, round switch cavity |
| `rear_3` | Rear cavity, 3 pots | 94 × 34 mm rear cavity in a 106 × 46 mm recess, 3 pots 30 mm apart in a row, round switch cavity |
| `tele` | Telecaster-style plate | A 160 × 32 mm plate recess (cover depth) routed into the **top**, with a 140 × 22 mm control cavity from its floor; the plate carries 2 pot holes, a 20 × 7 mm blade switch slot and 2 screws |
| `none` | No controls | No control or switch cavity, pots or covers |

The body shape's `control_angle_degrees` turns the whole layout about its
cavity's centre, counter-clockwise in the plan: the drawn almond and its
cover (its pots are the shape's own `pot_offsets`, which the body editor
turns with it), a Gibson or three-pot cavity with its cover and its own
pots, or the Tele plate with its cavity, pots, screws and blade slot. The
battery box turns with `battery_angle_degrees` and the jack with
`jack_direction_degrees`; round cavities only move. In the body editor a
Shift-drag turns them.

`control_stretch` makes the control cavity and its cover that much longer
(negative: shorter) along their long axis, from their centre: each end
moves out half of it and keeps its rounded shape, the width stays. A
Gibson or three-pot layout's end pots move out with the ends, as do the
Tele plate's screws, blade slot and rear pot; the drawn almond stretches
along its own long axis (its pots are its own). A cavity cannot shrink
past its rounded ends (`BodyGeometryError`). The body editor draws a
square handle at each end of the cover: dragging one stretches the
cavity from that end while the other end stays put.

`control_stretch_across` does the same square to the long axis: the
cavity and its cover get that much wider (negative: narrower) from their
centre. The Gibson layout's two rows of pots move apart with the sides;
the round-ended three-pot cavity and Tele plate keep half-circle ends at
any width. A cavity narrower than `MIN_CONTROL_CAVITY_WIDTH` (16 mm, a
mini pot's body) is refused. The editor's side handles, square to the
end handles, widen it from one side with the other held still.

The output jack (`body_jack`, `Prototype001Parameters._jack`) starts where
the shape's jack line — through `jack_offset` / `jack_y` along
`jack_direction_degrees` — enters the body, whatever outline is drawn, and
runs on into the control cavity, `JACK_CAVITY_OVERRUN` (3 mm) past its
wall; `body_jack_depth` fixes its length instead, and it is
`JACK_DEFAULT_DEPTH` (55 mm) when the line misses the cavity (the body
editor then says so). The housings:

| `body_jack` | Cut |
| --- | --- |
| `side` (default) | A Ø `body_jack_diameter` (12.5 mm) bore from the edge: a Les Paul style side plate or a barrel jack |
| `cup` | The bore with a 7/8 in (22.2 mm) counterbore 25 mm deep at the edge: a Telecaster cup jack or an Electrosocket (`JackHole.cup_diameter`, `cup_depth`) |
| `strat` | A Stratocaster style plate on the top: a Ø 25.4 × 32 mm cavity routed from the top 4 mm in from the edge (`Jack cavity`, cut with the top's pockets), the bore running on from its centre into the controls |

The jack's line can be dragged and turned (Shift-drag) in the body editor;
the bore follows the drawn outline and the cavity.

### Pickguard

`body_pickguard` puts on a pickguard (`presets.pickguard`), cut from
`body_pickguard_thickness` (2.5 mm) sheet in its own cover program
(`Cover_pickguard.nc`). Its outline is a closed Catmull-Rom spline through
control points (about 22 mm apart), like a drawn body. Left automatic it
lies `body_pickguard_margin` (6 mm) inside the body's outline, with a
notch the neck sits in, and:

- on the longer horn's side (the one reaching further toward the nut) it
  does not follow the horn: its edge runs `PICKUP_HUG` (8 mm) past the
  pickup routes (with none, `NECK_PASS`, 20 mm, past the pocket), from
  a little forward beside the neck to the bridge, flaring out toward the
  bridge as the style (`body_pickguard_style`, below) has it;
- when neither horn reaches further toward the nut, but they are wings
  reaching away from the neck past the bridge (a V's, the Jackson RR's),
  the longer wing's side counts as the longer horn's, and on the shorter
  wing's side the guard runs on past the bridge out along that wing,
  `WING_REACH` (100 mm) past the bridge's front, its inner edge along the
  V's and its end rounded off like a tail;
- on the shorter horn's side it follows the body's edge round the horn,
  when a cutaway parts the horn from the neck, and back down the cutaway
  to the notch; with no cutaway it reaches forward beside the neck, up to
  65 % of the pocket's length while there is wood there;
- on the bass side, if that is the shorter horn's, the edge curves in
  over 40 mm to run 8 mm past the pickups;
- along the neck it stops 1 mm short of the bridge (its routes, or for a
  hardtail or Tune-o-matic its holes and 15 mm ahead of the scale line),
  but always 3 mm past the last pickup, and runs on `BRIDGE_WRAP`
  (12 mm) past the bridge's front either side of it, 2 mm off it — on
  the shorter horn's side the style's tail, its end rounded off over
  `TAIL_ROUND` (30 mm).

`body_pickguard_style` (`PICKGUARD_STYLES`) picks how:

| Style | Beside the neck | Waist | Flare | Tail past the bridge |
|---|---|---|---|---|
| `stratocaster` (default) | 34 mm | none | 25 mm, from the first pickup's end to the last's centre | 55 mm |
| `superstrat` | 10 mm | 5 mm between the first and last pickups | 9 mm, from the last pickup's centre to the guard's end | 12 mm |

The Stratocaster style's numbers were measured off a Stratocaster's HH
guard; the superstrat's were drawn in the body editor.

The Stratocaster style template comes with that guard itself, drawn
(`pickguard_points`): traced from a photo, scaled to the body — its
notch on the neck pocket's end, its bass side stepping back clear of the
bridge. The Jazz Bass style template (the bass's default body) has the
same guard fitted to it: stretched along the neck from the pocket's end
to the bridge's front, widened for the bass's pickups (it covers every
bass pickup layout, four or five strings), clear of the bridge's screws,
and wherever it ran past the outline 6 mm in brought back onto that
line, its small horn then reshaped by hand. The Design by Jone template
(the guitar's default body) has it too, at the Stratocaster's scale,
following the outline 6 mm in round its horn and deep cutaway wherever
it would run past, then reshaped by hand: the horn's tip turned along
the body's edge and the edge kept off the pots' knobs. The Jackson RR
style template has one drawn in the body editor: a narrow strip past the
pickups on the longer wing's side, the shorter wing's side running out
along it toward its tip (its pots go through the guard); the Les Paul
style one too: round the cutaway's horn on the treble side, widening
toward the bridge on the bass side (the first pot goes through it). *Auto pickguard* swaps any of them for the automatic
one.

A bridge that covers more of the top than its routes — the Kahler
7300's plate reaches `plate_overhang` (5 mm) past its cutout all round
(`BridgeHardware.footprint`, drawn dashed in the body editor) — is kept
clear of by the guard as a whole: its footprint counts as part of the
bridge.

Every guard, automatic or drawn, is also stepped round a heel-adjusted
truss rod's access notch past the neck pocket (`clear_of_truss_rod`,
`TRUSS_ROD_CLEARANCE` 3.5 mm, which leaves at least 2 mm once the spline
rounds its corners), so the spoke wheel can be turned with the guard on.

A drawn guard is drawn for one bridge; whichever is fitted, it is
stepped round it (`clear_of_bridge`): where it runs into the box round
the bridge's routes and holes (`DRAWN_BRIDGE_CLEARANCE`, 3 mm, all round,
but starting no nearer the neck than 3 mm past the last pickup), it is
cut back along the box's edges — the way round that keeps the box out,
on to wherever the guard next comes out of it, so a guard that spans
the box's whole front is cut there too — points `DRAWN_BRIDGE_STEP` (8 mm) apart
so the spline keeps to them. A drawn guard
must cover a `pickguard` control layout's cavity, or the build is
refused (the traced HH guard has no room for one).

The shape's `pickguard_points` (dragged in the body editor,
where a click on its edge adds a point and Alt-click or right-click
removes one; its openings and holes are drawn cut out of it) replace it. It gets a rectangular opening for every pickup of the
chosen pickup layout — the pickup's own size, as a ring-less guard's are
(`presets.pickups.pickup_openings`; a Precision gets one per coil) — a hole for every pot and the selector's bushing
under it, and screws round its edge (4.5 mm in, about 60 mm apart, clear
of the openings), each with a 1 mm spot in the body. A guard off the body
is refused when the body is built.

`body_controls` `"pickguard"` mounts the controls in it, Stratocaster
style: three pots 30 mm apart and a 5-way blade switch's 5 × 22 mm slot
through the guard, over a 127 × 50 mm cavity routed from the top (no rear
control cavity); the automatic guard then runs on past the bridge on the
controls' side, leaving a notch for the bridge. It needs `body_pickguard`.

The rear layouts' pickup selector is chosen with `body_switch`: a 3-way
toggle (`toggle`, the default) through a 1/2 in (12.7 mm) hole, or a micro
(mini) toggle (`micro`) through a 1/4 in (6.35 mm) one
(`SWITCH_SHAFT_HOLE_DIAMETERS`); `body_switch_shaft_hole_diameter` sets the
hole by hand instead. The Tele plate carries its own blade switch.

Rear layouts spread their cover screws round the ledge between the cavity
and its recess (`geometry.body.cover_screw_points`: rays from the cover's
centre toward its corners, turned up to 30° where the ledge is narrower
than 5.2 mm) — 4 on the control cover, 3 on the switch cover. The screw
spots (Ø 3 mm, 1 mm into the ledge floor) are in
`BodySolid.control_back_marks`; a Tele plate's in `control_top_marks`, and
its recess and cavity in `control_top_cavities`.

A generated rear cavity (`gibson_4`, `rear_3`) that would rout into a
deep top route over it — a Floyd Rose's fine-tuner recess or a pickup,
leaving no wood between the floors — moves with its pots and cover to the
nearest place, out from the centreline and along the neck by up to
`CONTROL_CLEARANCE_SHIFT` (20 mm) in 1 mm steps, that clears them with
its cover in the body and off the spring-cavity and battery covers
(`Prototype001Parameters._placed_controls`). The drawn almond stays put.
The one combination still refused is a Gibson cavity with a Floyd Rose
and the battery box on the Jackson RR, whose narrow treble wing the
battery box already takes; drag the box aside.

Every cover is a `geometry.body.CoverPlate` (`Prototype001Geometry.covers`):
the recess outline, the recess depth as the sheet thickness, 3.2 mm screw
clearance holes, and for the Tele plate its pot holes and switch slot.

### Battery box

`body_battery_box` (off by default) adds a rear 9 V battery box with any
layout, `none` included (`controls.battery_features`):

| Parameter | Default | Meaning |
| --- | --- | --- |
| `body_battery_cavity_length` × `_width` | 56 × 30 mm | The box (r 5); a 9 V battery is 48.5 × 26.5 × 17.5 mm |
| `body_battery_cavity_depth` | 22 mm | Up from the back face; at most `body_thickness - body_rear_cavity_top_wall` |
| `body_battery_cover_margin` | 7 mm | The cover recess is this much wider all round (70 × 44 mm by default) |
| `body_battery_count` | 1 | 2 holds two batteries side by side (18 V): the box is `BATTERY_PITCH` (28 mm) wider, 56 × 58 mm in a 70 × 72 mm recess |

The body shape places it: `battery_offset` (X from the heel end),
`battery_y` and `battery_angle_degrees` (the box's long axis from the
neck's). Its cover (`Battery cavity cover`, `Cover_battery_cavity.nc`) is
held by two screws on the ledge at the box's ends. The battery lead's
channel to the control cavity is drilled by hand, so each shape and
template puts the box near its control cavity (18–32 mm between the
cavities), in a spot that clears every control
layout, bridge and pickup: beside the control cavity behind the bridge,
turned 15°, on the drawn bodies; behind the bridge next to the almond,
nearly across the neck (85°) with 10 mm of wood to the tail's edge, on
Design by Jone; along the treble wing behind the controls (60°)
on the Jackson RR; and between the pickups just ahead of the controls
(−15°) on the Jazz Bass, whose string-through holes take the space behind
the bridge. The body editor drags the box like the switch.

`BodySolid` rejects two rear cover recesses that overlap (their plates
would sit on each other) and any hole that would open into the battery
box: a top hole deep enough to reach its floor (a string-through hole) or
a hole from the back under its cover.

## Edge finishes and contours

Optional, and off by default (`geometry.body.edges`):

| Parameter | Effect |
| --- | --- |
| `body_top_edge_radius`, `body_back_edge_radius` | Roundover radius of each edge (`EdgeProfile.radius`) |
| `body_top_binding_width` / `_depth`, `body_back_binding_width` / `_depth` | A binding channel (rabbet) instead of a roundover; the default depth is 6 mm |
| `body_arm_contour_depth`, `_width`, `_length`, `_position` | A Strat-style arm contour on the top of the bass-side rear bout |
| `body_belly_cut_depth`, `_width`, `_length`, `_position` | A belly cut on the back of the bass-side upper bout |

A `ContourCut` follows `length` of the outline (resampled every 4 mm)
centred on its deepest point. Across the edge it is a straight ramp from
the face, `width` in, down to `depth` at the edge; along the edge width
and depth fade with a `cos²` taper, so it blends into the square edge at
both ends. Its deepest point is the outline point furthest out on the
bass side — for the arm contour from 120 mm behind the heel end, for the
belly cut from 40 mm ahead of it to 120 mm behind — or the one nearest
`_position` (X from the heel end). The defaults are 60 × 240 mm for the
arm contour and 70 × 260 mm for the belly cut.

Where the arm contour starts on the top can be drawn instead: the
shape's `arm_contour_points` are an open line's control points (X from
the heel end), its ends on the body's edge, drawn as an open Catmull-Rom
curve (`open_catmull_rom`). `ContourCut.along_line` takes the line's ends
onto the outline, runs the bevel along the stretch of edge between them
and, at each edge sample, in along the inward normal to the line
(`reaches`); its depth at the edge is `body_arm_contour_depth` where the
line is furthest in, scaled with the reach elsewhere, so a line that
meets the edge fades the bevel out there. In the body editor the line is
drawn in green with round handles while the arm contour is on: drag one,
click the line to add one, Alt-click or right-click to remove one (three
at least); *Auto arm contour* empties the points again.

`BodySolid` checks that each edge finish reaches less than half the
thickness less 2 mm; that a roundover lowers the rim of a cavity near the
edge (the neck pocket excepted) by no more than `EDGE_RIM_TOLERANCE`
(1 mm, hidden by a pickup ring or cover; `rim_drop`), the error naming
the largest radius that would fit (`max_radius_for`); that a binding
channel leaves 1 mm of wood before a cavity; that a contour stays under
half the thickness less 2 mm, and together with its face's roundover
(which runs on down from the contour's floor) within half the thickness,
the depth each face can be machined to; and that a contour cuts into no
cavity or hole on its own face and leaves 3 mm of wood over any cavity
routed from the other face.

## Decorative engraving

`body_engraving` engraves a scroll pattern into the top
(`presets.engraving`): Design by Jone's surface design
(`pintakuviodesignbyjone.dxf`), one motif of five arcs (radii 61.87,
29.12, 16.30, 31.85 and 81.47 mm: a broad swirl, a curl and a small tip
rolling out of it, a hook and a long sweep) scattered over the top.
Copies are placed at random from `body_engraving_seed` — the same seed
always gives the same pattern; the body editor's *New pattern* draws a new
seed — one per `body_engraving_spacing` (50 mm) squared of the top's
bounds, no two swirl centres nearer than half that, each turned one of the
drawing's two ways (`MOTIF_TURNS`, a quarter-turn apart, the drawing's
long side along the neck). Every arc is cut back to where the top may be
engraved (`EngravingArea`): `body_engraving_margin` (10 mm) in from the
edge and `body_engraving_clearance` (4 mm) clear of the neck pocket, the
truss rod's access, every pickup and bridge route, the bridge's plate,
the top control cavities and covers, the pickguard, the contours and
every hole — not the back's cavities, which leave the top whole, unless
one leaves less than `ENGRAVING_WALL` (3 mm) of wood under the engraving; pieces shorter than `MIN_LINE` (3 mm) are
dropped. A copy that would crowd more than `MAX_CLUSTER` (10) lines into
one block of three by three `CLUSTER_CELL` (10 mm) squares is passed over
for another, so no cluster gets too thick; and at the end lines that come
within `LONE_GAP` (10 mm) of each other are grouped, and a group of one
line, or of under `MIN_GROUP` (40 mm) of line all told, is dropped, so no
line stands alone as a stray mark. The default spacing gives about as much line on a body as the
drawing has over it.

It is cut `body_engraving_depth` (2 mm, less than half the body) deep in
its own program, `Body_top_engraving.nc`, with a V-bit
(`MachiningParameters.engraving_tool_angle`, 60°: a 2.31 mm wide groove).
In the FreeCAD model it is drawn as lines on the top face (object
`Body_engraving`), not cut, so the solid stays quick to build.

## Bridges

The bridge is an interchangeable *spec* (`geometry.body.bridges`). Each spec
is a small frozen dataclass of dimensions whose `hardware(scale_length,
body_thickness)` returns everything that bridge needs cut into the body,
all placed relative to the scale line:

| Spec | `kind` | Adds |
| --- | --- | --- |
| `KahlerBridgeSpec` (default) | `kahler_7300` | Rectangular baseplate cutout (the DXF's 55.45 × 65.04 × 25 mm); no studs, no rear cavity |
| `FloydRoseSpec` | `floyd_rose` | Floyd Rose Original recessed routing per the manufacturer's *Original Series Routing Diagrams*: two Ø 10 stud holes 73.91 mm apart, 11.9 mm ahead of the scale line (25.03 in on a 25.5 in scale); a 95.25 mm wide recess, 79.38 mm long, narrowing to 71.12 mm after 42.44 mm, cut 6.73 mm deep over its whole footprint (continuous walls) and deepened to 11.18 mm behind the front 15.88 mm stud shelf as a step inside it, with a 20.96 × 82.85 mm block route 29.59 mm deep through that floor that opens into the spring cavity only where the two overlap; a rear 123.19 × 56.64 × 16.13 mm spring cavity with a 28.19 mm deep block clearance pocket at its tail end and a 2 mm cover recess 8 mm wider all round (`cover_margin`), closed by a sheet cover with six screws on the ledge (`Floyd Rose spring cavity cover`, `Cover_floyd_rose_spring_cavity.nc`, made like the cavity covers by `controls.rear_cover`). The diagram is for a 1.75 in (44.45 mm) body, where the block route runs 1.27 mm into the spring cavity; in a thicker body the spring cavity and block pocket reach deeper by the difference (`FLOYD_ROSE_DRAWN_THICKNESS`), so the block route always opens into the back. The recess is 3.56 mm wider on the tremolo-arm (treble) side; `treble_side` picks that side (`"+y"` on the left-handed Prototype001 body) |
| `TuneOMaticSpec` | `tune_o_matic` | Two Ø 11.2 post holes 3 mm behind the scale line and two Ø 11.2 stop-bar stud holes 45 mm behind it |
| `HeadlessBridgeSpec` | `headless` | A headless bridge: saddles and tuners in one unit screwed flat to the top. Four Ø 3 × 12 mm pilot holes `screw_inset` (6 mm) in from the plate's corners; the plate, from `front_reach` (12 mm) ahead of the scale line, `length` (90 mm) long and `side_margin` (10 mm) past the outer strings (`string_count`, `string_spacing`), is the bridge's `footprint`, which must lie on the body and which the pickguard and the engraving keep clear of |
| `HardtailSpec` | `hardtail` | `string_count` (6) Ø 3 string-through holes 14 mm behind the scale line and five pilot holes for the baseplate screws; the bass uses four strings 19 mm apart, 30 mm behind the scale line |

`Prototype001Parameters.body_bridge` holds the spec; in the web form it is a
dropdown of bridge kinds with that kind's dimensions beneath it, sent back as
a JSON object with a `kind` entry (`bridge_spec_from_dict` rebuilds it).
Every dimension is a labelled starting value to be checked against the real
hardware. The bridge pickup keeps `body_bridge_pickup_offset` unless the
chosen bridge's routes reach further forward — a Floyd Rose recess starts
19.5 mm ahead of the scale line — in which case the route moves forward on
its own to leave `body_bridge_pickup_clearance` (3 mm) of wood; a larger
offset set by hand still wins. A Tune-o-matic on this flat body also wants a neck
angle or a recessed bridge, which the model does not provide.

Two new `BodySolid` fields carry bridge features: `through_cavities` (top
routes that open into a rear cavity or clean through the body, exempt from
the floor and break-through checks but required to reach the back face or a
rear cavity they overlap) and `extra_rear_cavities`.

## Two anchors

Longitudinal body placements are offsets, not absolute positions, so the
model stays consistent when the neck changes:

- **Heel-anchored** (`OMARUNKO_HEEL_END_X`): the outline, neck pocket, neck
  pickup, control and switch cavities, pot holes and jack all move with the
  neck's heel end (`last_fret_position + heel_length`).
- **Scale-anchored** (`OMARUNKO_SCALE_LENGTH`): the bridge baseplate cutout
  and the bridge pickup move with `scale_length`.

Changing the scale or the fret count therefore keeps the neck in its pocket
and the bridge on the scale; only the bridge's place on the body shifts by
the difference. `BodySolid` rejects the result if that shift makes two top
cavities overlap.

## Prototype001 body

| Feature | Value |
| --- | --- |
| Thickness | 44 mm flat slab (edges square unless finished, see *Edge finishes and contours*) |
| Neck pocket | Neck's own taper + 0.15 mm clearance, 79.5 mm long, ends at heel end (461.2), 20 mm deep, opens onto the horn gap |
| Pickup routes | DXF humbucker route with ears, 41 × 85.9 mm, 22 mm deep, centres 491.7 and 587.9 |
| Pickup screw recesses | Ø 6 mm, 8 mm below the route floor, at ±39.95 mm |
| Bridge | `KahlerBridgeSpec`: flat mount, no pivot studs, no sustain block; 55 × 65 mm baseplate cutout 25 mm deep (see *Bridges*) |
| Controls | `almond_2` (see *Controls and cover plates*) |
| Control cavity | DXF almond, rear, 36 mm deep (8 mm top wall), 2 mm cover recess |
| Switch cavity | DXF circle Ø 44 at the upper-horn root, rear, 36 mm deep, Ø 59.5 cover recess |
| Shaft holes | Ø 12.7 switch, 2 × Ø 10 pots at (642, 86) and (682, 87) |
| Jack | Ø 12.5 bore from (742, 107.5) at 202.5°, 55 mm, ending inside the control cavity |

Every value above is a `Prototype001Parameters` field (`body_*`), so any of
them can be changed with `dataclasses.replace`.
