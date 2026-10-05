# Solid body

`cncguitarwizard.geometry.body` models a flat-slab solid body in the neck's
own nut-origin coordinate frame: X runs from the nut toward the tail, Y is
lateral from the centerline, and the body's top face is the same `Z = 0`
plane as the neck-back surface. The body is extruded downward, so a cavity
"cut from the top" removes material below `Z = 0` and a cavity "cut from
the back" removes material upward from `Z = -thickness`.

Seen from the front with the headstock to the left, +Y is up. Prototype001
is a **right-handed** instrument as drawn: its bass side, long upper horn and
switch cavity lie at -Y, its control cavity and jack at +Y. Mirroring every Y
coordinate gives the left-handed twin, which `handedness = "left"` builds
(see *Left-handed* below).

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
| `WireHole` | A straight wire hole drilled by hand from one cavity into another (`plan_wiring`, see *Wire channels*). |
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
  the neck it receives; with a `neck_angle` its floor tilts (see *Neck
  angle* below);
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
right-handed like the DXF: the long upper horn at -Y, controls at +Y. The
drawn body's starting loop closes across the horn gap about 52 mm ahead of
the pocket end so the neck pocket opens onto the gap as the DXF body's does.

`YOUR_DESIGN_TEMPLATES` offers eleven starting points for a drawn body, each
a complete `YourDesignShape` (outline and electronics placements):

| Key | Label | Outline |
| --- | --- | --- |
| `design_by_jone` | Design by Jone | The traced DXF outline resampled to 64 evenly spaced control points, with that body's own switch, pot and jack placements |
| `les_paul` | Les Paul style (mockup, not the original) | Single cutaway traced from a reference render and reshaped by hand — a genre mockup, not the original outline; its selector switch sits on the bass-side upper bout |
| `stratocaster` | Stratocaster style (mockup, not the original) | Offset double cutaway traced from a reference DXF drawing (aligned on its neck pocket) and reshaped by hand at both horns and the neck joint — a genre mockup, not the original outline; its neck bolts spread like the bass's, the front pair 63.5 mm ahead of the heel end near the body's edge and the rear pair at 7.5 mm, its ferrules wholly over the pocket |
| `jackson_rr` | Jackson RR style (mockup, not the original) | Offset V traced from a reference render and reshaped by hand at the neck joint, both wing tips and the V notch — a genre mockup, not the original outline; the switch on the bass wing, the pots, control cavity and jack on the treble wing; the neck bolts' front pair as far out as the narrow wings allow (50 mm ahead of the heel end on the bass side, 44 mm on the treble side), the rear pair at 7.5 mm |
| `alexi_hexed` | ESP LTD Alexi Hexed style (mockup, not the original) | The Jackson RR style outline and placements (ESP's Alexi body is an offset V after Alexi Laiho's Jackson RRs), with no drawn guard; loading it in the body editor also sets the Hexed's look (`prototype001.BODY_TEMPLATE_VALUES`): one bridge humbucker (`body_pickups` "H") under one volume pot (`volume_1`, no selector), a Floyd Rose, and its graphic as a stepped top (*Stepped top*, below), its two steps drawn (`step_points`) where the original's pinstripes run: two nested arrows from the edge beside the neck pocket (where they converge) out into the wings, each tail a sharp V at the notch — the inner arrow, round the pickup and the bridge, at full height, the band between them 1.5 mm lower (only 4 mm wide at the notch), the rest out to the edge and the wing tips 3 mm lower. Its purple fade and pinstripes (on the back and sides too) are the painter's; it is neck-through with sawtooth inlays, left to choose (`neck_joint`, `inlay_style` "sharktooth") |
| `mockingbird` | Mockingbird style (mockup, not the original) | Traced from a straight-on product photo of a B.C. Rich Mockingbird (its edge as photographed, the strap button and the jack's rim left out), scaled from its 24 frets and placed with its 24th fret 4 mm ahead of the heel end, as the default neck's is, then reshaped by hand: the long curved horn on the treble side longer and sharper, the beak below it redrawn, the front of the bass side's deep scoop and its lower lobe drawn out; the notched short horn on the bass side. The switch a little in from the narrow treble waist, the jack in the lower treble edge and the battery box behind the bridge, square to the neck |
| `telecaster` | Telecaster style (mockup, not the original) | Single cutaway traced from a straight-on product photo, scaled from its frets (its 22nd fret 4 mm ahead of the heel end) — a genre mockup, not the original outline; the jack into the treble side nearest the control cavity |
| `sg` | SG style (mockup, not the original) | Double cutaway traced the same way — the horns meet the neck near its end, so the outline runs on along the neck's sides to hold a bolt-on neck's pocket |
| `explorer` | Explorer style (mockup, not the original) | Traced the same way, then reshaped by hand: the bass shoulder, the long bottom corner and the wing's tip sharper, the tip further forward; the long wing forward on the treble side, the long bottom corner back on the bass side |
| `flying_v` | Flying V style (mockup, not the original) | Traced the same way: two straight wings and a rounded notch; the switch behind the bridge, the control cavity turned 20 degrees along the treble wing (a Tele plate there too), the jack into the wing's outer edge and the battery box on past them toward its tip |
| `jazz_bass` | Jazz Bass style (mockup, not the original) | Offset waist traced from a reference render (straightened on its centre stripe, scaled from its bridge pickup) and reshaped by hand at both horns and the treble cutaway — a genre mockup, not the original outline; its pots and control cavity on the lower bout behind the bridge pickup; the bass guitar's default body (`BASS_BODY`) |

The Les Paul, Stratocaster, Jackson RR, Alexi Hexed and Jazz Bass ones are
mockups: traced and then reshaped by hand, so they are not the original
outlines. The Mockingbird, Telecaster, SG, Explorer and Flying V ones are
traced from straight-on product photos (the outline found against the
white background, scaled from the frets — a least-squares fit of the
fret positions to the scale length — and turned square to the neck,
hardware such as strap buttons left out), and their control points
chosen so the spline stays within 0.75 mm of the trace; the Mockingbird
and the Explorer were then reshaped by hand in the body editor. A template that sets more than its shape (the Alexi Hexed) says
which values in the editor's confirmation.

`Prototype001Parameters.body_layout()` returns the outline and every
feature (`BodyLayout`) without building the neck surfaces or validating
the body, in about a millisecond; the web app's editor uses it (through
`webapp.body_editor_layout`) to draw the fixed features under the outline
being drawn. The full `build()` then rejects an outline that leaves a
feature outside the wood.

## Left-handed

Every body template and the default neck are drawn right-handed.
`handedness = "left"` builds the instrument's mirror image across the
centreline while the design stays stored as drawn, so a saved design or
template serves both hands:

- the body shape (`mirrored_shape`): every placement's Y and every angle
  in the plan change sign — switch, pots, jack and its direction, almond
  shift, neck bolts, battery and its angle, the control layout's angle,
  a drawn pickguard (run the other way round), arm contour and belly cut
  — and its `mirrored` flag mirrors the traced constants (the Design by
  Jone outline, the almond cavity and cover);
- the bass side (`Prototype001Parameters.bass_sign`): pickups and their
  slant, the bridge (a Tune-o-matic's set-back bass post), a fan's long
  side, frets, inlays, the headstock's tuners, the automatic pickguard
  and contours all follow it;
- a Floyd Rose's `treble_side` (the arm and the recess's wider side);
- a drawn headstock tip (`built_tip_points`) and the lettering's place
  (`headstock_engraving_y`). The lettering is set again, never mirrored:
  it runs at 180 degrees less `headstock_engraving_angle`, so it lies
  where the right-handed text's mirror image would, its tops on the
  same side, and reads the right way round.

The body and headstock editors draw the design as drawn and show it
mirrored for a left-handed build (one SVG group turned over; dragging
reads points back through it); the lettering they show is the built one
mirrored back, so it reads right there too. A carved top's fall matches
its mirror within its grid's sampling (about 0.03 mm).

## Set neck

`neck_joint = "set"` glues the neck's heel into the pocket, Gibson style,
instead of bolting it: no neck bolts or ferrules, and the pocket only
`set_neck_glue_gap` (0.05 mm) a side round the heel for a tight glue
joint (a bolt-on pocket keeps `body_neck_pocket_clearance`, 0.15 mm). A
neck angle works as for a bolt-on neck (the pocket's floor slopes; a Les
Paul's 4 degrees, say). The neck never comes off, so a heel-adjusted
truss rod needs its spoke wheel, turned through the body's notch; the
neck's notes say to glue and clamp it in once it is finished and
fretted. A long tenon reaching under the neck pickup is not modelled.

## Neck-through

`neck_joint = "neck_through"` runs the neck blank on through the body
(`geometry.body.neck_through`): the body's outline between two glue lines
`Y = +-neck_through_width / 2` is the neck blank's **centre block**, the
outline beyond them the two **wings** (`Wing_bass`, `Wing_treble`), each
cut from its own blank and glued to the block's sides. An empty
`neck_through_width` makes the block wide enough for the pickup routes
and the bridge's routes and holes (and the neck's heel) with
`NECK_THROUGH_MARGIN` (3 mm) of wood beside them: 92 mm with two
humbuckers, 99 mm under a Tune-o-matic. `split_by_line` splits the outline
along a glue line into its pieces (a deep cutaway leaves two, not one
joined by a zero-width bridge); the block must be one piece.

The body has no neck pocket and no neck bolts; the pocket's outline stays
as where the neck passes, for the pickguard, carve and engraving
keep-outs. The neck's back keeps its D profile, then falls to the body's
thickness over `neck_through_heel_ramp` (40 mm), reaching it at
`front_x`, where the body first meets the neck's sides (the neck back's
own heel transition, its depth the body's). There is no neck angle (it
is refused; a Tune-o-matic's automatic 2 degrees is 0 here), and a
heel-adjusted truss rod needs a spoke wheel: a nut at the heel's end
would be buried in the block.

Each part is cut from a blank a little larger than it (`body_part`): it
carries every feature that reaches into it whole — a control cavity
across a glue line is cut in both parts, its far side in each one's
waste — a carve and contours whole, the engraving within reach, and its
edge finishes along `edge_outline`: the body's outline carried on
`NECK_THROUGH_EDGE_REACH` (12 mm) past the glue line into the waste, so a
roundover or binding runs right across the glue line and the glue face
stays square. The profile then trims the waste.

The FreeCAD model builds the body whole and splits it along the glue
lines: `Neck_block` (one piece of wood with the neck, its heel running
on into it; an object of its own, since a fuse fails on the neck loft's
faces lying in the block's top and bottom planes), `Wing_bass` and
`Wing_treble`. The plan view and the body editor draw the block a shade
darker; its long sides are the glue lines.

### One piece

`neck_joint = "one_piece"` cuts the neck and the whole body from one
blank: a neck-through whose block is the whole body (`neck_through` with
no width: `NeckThrough.one_piece`, no wings and no glue lines). Its
blank runs from the headstock tip to the tail and is as wide as the body
(995 × 364 × 44 mm for the default guitar, 1053 × 398 mm for the Les Paul
template); the neck blank's programs cut the body's features on their
own dowels (`Neck_body_...`) and its whole outline full depth. The
FreeCAD model shows the body as one object (`Body (one piece with the
neck)`). Everything a neck-through refuses it refuses too: a neck angle,
a buried heel adjuster, a headless neck.

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
| `superstrat` | Superstrat rear cavity | Ibanez RG / Jackson style: a 112 × 40 mm rear cavity (r 12) in a 124 × 52 mm recess holding a 5-way blade switch ahead of the volume and tone pots (26 mm apart), no round switch cavity. The switch sits in a 54 × 16 mm pocket deeper into the cavity, leaving `BLADE_SWITCH_TOP_WALL` (4 mm) of top so its lever stands out; its lever comes through a 27 × 6.5 mm slot routed from the top 1 mm into that pocket (a through route, cut in `Body_top` — wide enough for the 6 mm end mill), and its two #6-32 screws go through Ø 3.6 holes in the top into its tabs, 41.28 mm (1-5/8 in, Oak Grigsby / CRL) apart |
| `volume_1` | One volume pot | A 56 × 34 mm round-ended rear cavity with one pot and a three-screw cover; the round switch cavity only with two or more pickups (an EVH style single humbucker needs none) |
| `active_4` | Active bass, 4 pots | A 130 × 44 mm round-ended rear cavity (room for a preamp) in a 142 × 56 mm recess, 4 pots 28 mm apart in a row (volume, blend, bass, treble), a six-screw cover, no switch cavity; the 9 V battery goes in the battery box (`body_battery_box`) |
| `tele` | Telecaster-style plate | A 160 × 32 mm plate recess (cover depth) routed into the **top**, with a 140 × 22 mm control cavity from its floor; the plate carries 2 pot holes, a 20 × 7 mm blade switch slot and 2 screws |
| `jazz_bass` | Jazz Bass style plate | A 150 × 36 mm round-ended plate recess in the top (a real Jazz Bass plate is as long, gently curved) over a 112 × 26 mm cavity; 3 pots 32 mm apart (volume, volume, tone), two screws 124.5 mm (4.9 in) apart, and with `body_jack` "plate" the output jack's Ø 9.6 hole behind the pots (no bore from the edge), no switch cavity |
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
| `plate` | On the Jazz Bass control plate (`body_controls` "jazz_bass" only): a hole in the plate behind its pots, nothing bored from the edge (`BodySolid.jack_hole` is `None`) |

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
  but 3 mm past the last pickup (halfway between the two where they
  leave less room than that), and runs on `BRIDGE_WRAP`
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
or, where that leaves under 3 mm past the last pickup, halfway between
the bridge pickup and the bridge), it is
cut back along the box's edges — the way round that keeps the box out,
on to wherever the guard next comes out of it, so a guard that spans
the box's whole front is cut there too — points `DRAWN_BRIDGE_STEP` (8 mm) apart
so the spline keeps to them. A drawn guard that does not cover a
`pickguard` control layout's cavity — every template's is drawn for its
own rear cavities; the traced HH guard has no room for one — gives way to
the automatic guard, made round the controls (the body editor says so).

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
controls' side, leaving a notch for the bridge, and reaches out past the
controls along them (`CONTROLS_MARGIN`, 12 mm, as far as the body lets
it). The layout brings its guard with it, `body_pickguard` or not (the
web form ticks it). Where the shape's pots put the cavity too near the
edge for the guard to cover it — `body_pickguard_margin` +
`PICKGUARD_CONTROL_LAP` (6 + 6 mm) in — or within `PICKGUARD_CONTROL_GAP`
(3 mm) of the neck pocket, a pickup or the bridge, the controls move to the
nearest place that fits, up to `PICKGUARD_CONTROL_SHIFT` (40 mm) along and
across the neck, turned by up to 30° (`PICKGUARD_CONTROL_TURNS`) where
they do not fit square — along a Jackson RR's wing
(`Prototype001Parameters._guard_controls_placed`). They fit under the
guard on every template.

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

A generated rear cavity (`GENERATED_REAR_LAYOUTS`: `gibson_4`, `rear_3`,
`superstrat`, `volume_1`, `active_4`) that would rout into a
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
hole to the control cavity is drilled by hand (planned with the wiring,
*Wire channels* below), so each shape and template puts the box near its
control cavity (18–32 mm between the cavities), in a spot that clears every control
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

### Wire channels

`body_wire_channels` (on by default) wires the pickups, a separate switch
cavity and a battery box to the controls and grounds the bridge
(`geometry.body.wiring.plan_wiring`, laid out at build time, not in the
body editor). Each pickup route, and the round switch cavity of a rear
layout, joins whichever cavity already wired is nearest — the control
cavity (the rear one, or a pickguard's or plate's in the top), a pickup
route or the switch cavity wired before it — so pickups in a row chain to
the controls as on a Stratocaster or a Les Paul, and a Les Paul's toggle
switch joins by its neck pickup. A battery box's lead runs straight to
the control cavity (`Battery wire hole`); its old hand-drilling note in
`Body_back_controls` stays only when the wiring is off or finds no way.
The bridge's ground wire runs from the control cavity to a tremolo's
spring cavity (its claw) if a hole reaches it, or else to the nearest of
the bridge's routes and holes (a Kahler's baseplate cutout, a
Tune-o-matic's stud, a string-through hole). No controls (`none`), no
wiring.

A machine cutting from one face leaves any channel open on it, so a
channel is routed only where the pickguard hides it: between two top
routes (pickups, a pickguard's control cavity), `WIRE_CHANNEL_WIDTH`
(10 mm) wide and `WIRE_CHANNEL_DEPTH` (16 mm) deep at most, every part of
it outside the routes under the guard and off its openings (they may
reach `_OPENING_SLACK`, 1 mm, past a route), `WIRE_WALL` (2 mm) from every
other cavity and hole. It is one of the body's top cavities
(`BodySolid.wire_channels`), cut in `Body_top` and in the model; it may
open into the routes it joins.

Every other way is a straight hole drilled by hand with a long bit
(`BodySolid.wire_holes`, `WireHole`; `WIRE_HOLE_DIAMETER` 6 mm, the ground
`GROUND_HOLE_DIAMETER` 3 mm). The bit goes in through the open face of the
cavity it is drilled from — the top of a route, the back of a rear cavity
— clearing its far rim, and meets the wood on that cavity's wall; the hole
runs on down (or up) through the wood and breaks into the other cavity
through its wall. In plan it runs centre to centre, or between the
cavities' nearest points if that is shorter. Its height and slope are
found so that it

- opens into both cavities through their walls (a route above its floor,
  a rear cavity below its ceiling),
- leaves `WIRE_SKIN` (3 mm) under the top (lower over a carved or stepped
  top or an arm contour) and over the back (higher in a belly cut), and
  `WIRE_WALL` round every other cavity and hole (the jack's bore
  included) — it may pass under a route or over a rear cavity,
- stays within the body, `WIRE_WALL` from its edge, no steeper than
  `WIRE_STEEPEST` (60°), the bit's run from the rim no longer than
  `WIRE_DRILL_REACH` (300 mm).

Of the holes that fit, both ways round, the one that leaves (or reaches)
its route nearest the route's floor, where the leads lie, then the
shallowest; between two rear cavities simply the shallowest. Each is cut
in the model and drawn dashed red in the plan view, and `Body_top`'s
notes say how to drill it: the cavity it is drilled from and into, the
face the bit comes in through, its angle from level, where it starts
(with its height above the back) and where it aims, and its length. A way
no straight hole fits is left to the builder with a note
(`BodySolid.wire_notes`). A neck-through body's parts carry the channels
that reach them; the holes are drilled through the glued body.

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
at least); *Auto arm contour* empties the points again. The belly cut's
line is drawn the same way: `belly_cut_points` (seen from the top, as the
outline is) with `body_belly_cut_depth`, in blue on the editor, *Auto
belly cut* emptying them.

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

## Carved top

`body_carved_top` (beside the body editor too, with its depth
`body_carve_depth`) arches the top Les Paul style, on any body
(`geometry.body.carve.CarvedTop`): the top keeps its full
`body_thickness` over a flat plateau, falls `body_carve_depth` (9.5 mm)
toward the edge and lands on a flat rim `body_carve_rim` (8 mm) wide.
The plateau, where the fall starts, is drawn in straight lines and arcs
(`plateau_round`): the convex hull of circles round every feature point
— the neck pocket and the truss-rod access `CARVE_KEEP_MARGIN` (3 mm)
round, each pickup `PICKUP_RING_REACH` (12 mm) round, so its mounting
ring (a humbucker's is about 92 × 45 mm over its route) rests wholly on
the flat, the bridge (its routes, plate and post or stud holes)
`body_carve_margin` (15 mm) round — so straight sides tapering toward the
neck with arcs at the corners, and its tail end a half circle as wide as
the plateau. Where it comes nearer the edge than the rim and
`CARVE_MIN_FALL` (25 mm), the rim narrows (down to `edge_rim`) so the
fall keeps the room there is. How far down the fall a point lies starts
as its distance from the plateau against its distance from the rim's
inner edge (exact Euclidean distance transforms on a 2 mm grid), then is
relaxed toward a harmonic field (`RELAX_PASSES` over-relaxed passes, the
plateau and the rim held), which smooths away the creases the ratio
leaves where the nearest edge changes; a smoothstep of it is the drop,
so the fall leaves the plateau and meets the rim level with them, and
out from the plateau it only ever falls. It is read back by bilinear
interpolation (`drop_at`). The defaults follow a Les Paul's: a 5/8 in
maple cap over 1/4 in binding leaves a 3/8 in arch, the body 2 1/4 in in
the middle and 2 in at the edge (`body_thickness` 50.8 for one).

Some rim is kept all round however near the plateau comes: a top
binding's or roundover's width + 1 mm, 1 mm without one (`edge_rim`, a
grid cell wider so it reads level all across), round the neck pocket's
mouth too; nothing is held flat within `EDGE_FALL` (3 mm) of it, so a
binding's channel always lies on the rim's level. The plateau itself
keeps `PLATEAU_EDGE_FALL` (12 mm) clear of that strip, so where it runs
along the edge (a Les Paul's cutaway, beside the neck pocket, where it
left the top only a few mm to drop its whole height, a wall) the top has
room to fall; by the pocket's mouth the top falls round the pocket's
walls (its floor is unchanged; the neck stands above the arch at the
edge, as on a Les Paul). Only the `keep` areas, each pickup's ring
(`PICKUP_RING_KEEP`, 7 mm round its route: a humbucker's ring reaches
about 5 past it, where the plateau's 12 mm margin is generous) and the
bridge's parts, stay flat nearer than that; held 12 mm wide by a Les
Paul's cutaway, the neck pickup's left the top 5 mm to fall its whole
height, a wall by the binding. Past the edge the
rim's level carries on everywhere (the plateau's reach past it, round the
pocket's mouth, is waste).

The back's cavities keep `body_rear_cavity_top_wall` under the arch:
each is made shallower by as far as the top falls over it, and
`BodySolid` refuses a carve leaving less than `CARVE_WALL` (3 mm). An arm
contour does not go with a carved top. A top roundover or binding is cut
on the rim, the carve's height down; the engraving follows the arch.

`Body_top_carve.nc` runs right after the index pins. A flat end mill
(`carve_tool_diameter`, else the main tool) roughs the arch in
step-down layers, its last layer following the arch, and leaves it to
sand smooth by hand, as a carve routed by hand in steps is: each layer's
runs are taken nearest first (`raster_rough`'s `link_distance`, four
rows) and a short hop between them is fed across in the cut rather than
up at the safe height, so the passes no longer jump the plateau at every
row. The rim's level is cut past the body's edge only as far as the
tool needs, its radius and `CARVE_EDGE_REACH` (3 mm), within the `band`
(12 mm, which the index pins keep clear of). For a Les Paul with the
6 mm main tool that is about 92 minutes (315 with the old ball finish
everywhere), with a 10 mm roughing tool about 55 and 12 mm about 47.
`carve_finish` still finishes it with a ball nose as wide as the
roughing tool, in passes `CARVE_FINISH_STEP` (1 mm) apart. The FreeCAD
model cuts the top under a cubic B-spline surface whose control points
are the carve's heights every `CARVE_SURFACE_SPACING` (4 mm: held up
where the top falls sharply, by a Les Paul's cutaway, 6 mm left it up to
2 mm high there, 4 mm 0.7 and 3 mm 0.34, the carve's cut taking 6, 9 and
14 s; only the
heights are written to the script, on their regular grid), sharpened
once and held between the lowest and highest height round each
(`_carve_poles`): smooth and light, it follows the heights closely and,
unlike a cubic fitted through them, cannot ripple into the plateau at a
steep fall. Where the plateau comes near the edge (a Les Paul's neck
pickup by the cutaway) the top falls its whole depth in a few mm, sharper
than the cubic can turn, and smoothing it the model dipped under a corner
of the pickup's ring; so the control points are then raised
(`_carve_held_up`) until the surface lies on or above the carve at every
control point and quarter-way between them: the model is never cut
deeper than the top, only a little shallower at such a sharp fall (a few
mm over under 1 % of it). The strip the carve keeps at rim level all
round (`edge_rim`, a binding's or roundover's width and 1 mm) is cut to
rim level first, in a quick planar cut of its own, so the held-up
surface never leaves wood over a binding's channel by the neck pocket.
Over the plateau the surface stands `CARVE_PLATEAU_LIFT`
(0.3 mm) clear rather than a hair: a smoothstep starts level, so a
surface just above the top crossed it nearly tangent there, and that cut
failed quietly — the body back uncut, or even grown. The lift leaves the
fall's first 0.3 mm in the model (the G-code cuts it). It is cut last,
after the cavities and edges (which cut far quicker into the plain slab),
and checked: should a cut still fail, the script tries 0.001 and 0.01 mm
of fuzz, keeping the first valid result that took off about the wood the
carve should (`CARVE_REMOVED`, within 30 %), and stops with an error if
none did. Cutting the top as stepped terraces, as templates of falling
size rout it by hand, was tried and is far slower here: each step's wall
is hundreds of faces. The plan view and the body editor dash the
plateau's edge.

## Stepped top

`body_stepped_top` (beside the body editor too) lowers the top in bands
that follow the edge (`geometry.body.steps.SteppedTop`) — the ESP LTD
Alexi Hexed's graphic, its pinstripes nested along the edge, made into
levels. Each step has a boundary, a closed line on the top: inside the
innermost the top keeps its full height, and each band nearer the edge
lies `body_top_step_height` (1.5 mm) lower than the band inside it.

The boundaries are drawn (the shape's `step_points`: one closed line of
points per step, X from the heel end, the outermost first, straight lines
between the points, so a step can run straight across where the edge
curves), or, left empty, the outline taken in by each of
`body_top_step_insets` (12 and 40 mm): the band from 40 to 12 mm in 1.5 mm
down, the outermost 12 mm 3 mm down. Taken in from the edge, a boundary
follows the wings and horns as far as they are wide; where a horn is
narrower than twice an inset it leaves the horn out, and the horn lies
wholly in the lower band (the outline is first simplified,
`STEP_OUTLINE_TOLERANCE` 0.05 mm, which makes them about ten times
quicker to find). Drawn steps must each lie inside the one before without
crossing it (`SteppedTop.check_nested`) — except off the body, in the neck
pocket or within `STEP_EDGE_SLACK` (3 mm) of the edge, where lines may
converge (the sliver between them there is cut with the outer band; a
point outside several boundaries lies as deep as the deepest band whose
boundary it is outside). The Alexi Hexed template draws its two after the
original's pinstripes (drawn in the body editor): two nested arrows from
the edge beside the neck pocket out into the wings, each tail a sharp V at
the notch, the inner one's point 4 mm inside the outer's, so a narrow band
runs between them there as the pinstripes do; beside the neck they
converge on the edge, the bass horn's as drawn and the treble horn's its
mirror image, and their points in the neck pocket do not matter. The
editor puts the steps' handles on top of everything else (beside the
neck pocket they sit over its bolts and each other's lines).
The body editor draws each step's line in purple with diamond handles
(dashed while it is automatic, shown with handles simplified to within
`STEP_HANDLE_TOLERANCE`, 1.5 mm): dragging one, clicking a line to add a
point or Alt-clicking one to remove it writes every step's points;
*Auto steps* goes back to the insets.

The pickups and the bridge (its routes, plate and holes) must lie inside
the innermost boundary, on the top level, or the build is refused (the
body editor draws the steps wherever they fall; a smaller last inset
brings them in: on Design by Jone the pickups and the Kahler come within
9 mm of the edge, the Les Paul style 19, the Stratocaster 22, the
Jackson RR's two humbuckers 25). The back's cavities keep
`body_rear_cavity_top_wall` under the lowered bands, and `BodySolid`
refuses steps leaving less than `CARVE_WALL` (3 mm) over one, or coming
to a quarter of the body's thickness. A stepped top is not carved, and
takes no arm contour or pickguard (which would not lie flat). A top
roundover or binding is cut on the outermost band, all the steps down;
the engraving follows the levels. The plan view and the body editor draw
each step's wall.

`Body_top_steps.nc` runs right after the index pins, with the main tool.
The innermost step's band (everything outside its boundary) goes one step
down first, then each next band a step deeper. A band is cleared in passes
along the body's edge — the outline taken in by the tool's radius, then a
step-over (`raster_spacing`) further in each pass, each kept only where
the tool stays outside the step's boundary taken out by its radius —
until a pass lies wholly inside it; then that grown boundary runs round as
the step's wall, cut true. The clearing passes come from a coarser outline
(`STEP_CLEARING_TOLERANCE`, 0.25 mm), the walls from the boundary
simplified to within `STEP_WALL_TOLERANCE` (0.02 mm); each pass starts at
its end (or point) nearest where the last ended and is fed across when
that is within 1.5 step-overs (`STEP_LINK`), else the tool lifts. A band
the tool cannot cut anywhere is refused. The FreeCAD model cuts each step as a
ring: a slab of the step's depth over the whole body less the boundary's
prism.

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

### Other patterns

`body_engraving_pattern` picks the pattern (`ENGRAVING_PATTERNS`,
`pattern_lines`); every one is laid out from the same seed, scaled by
`body_engraving_spacing` and cut back to the same area, pieces shorter
than `MIN_PATTERN_LINE` (8 mm) left out (the cluster and lone-line rules
are the scroll's own):

| Pattern | Lines |
| --- | --- |
| `scroll` (default) | Design by Jone's scrolls, above |
| `evh_stripes` | Eddie Van Halen "Frankenstrat" style taped stripes: straight bands `STRIPE_WIDTHS` (6–16 mm) wide round `STRIPE_ANGLES` (every 30°, ± `STRIPE_SPREAD` 12°), one per twice the spacing squared of the area's bounds; both edges of each are engraved, and every later band covers the earlier ones as tape would |
| `flame` | Wavy lines across the body as in flamed maple, about a fifth of the spacing (at least 6 mm) apart, each drifting a little from the last so they never cross (`FLAME_WAVELENGTH`, `FLAME_AMPLITUDE`) |
| `ripples` | Groups of `RIPPLE_RINGS` (2–6) rings `RIPPLE_GAP` (8 mm) apart, one group per twice the spacing squared, each covering the groups laid before it |
| `crackle` | The cells of a random Voronoi pattern, as crazed lacquer, about the spacing across, each shared edge engraved once |
| `camo` | Woodland camouflage as a relief, not lines: closed shapes cleared flat to four levels (see *Camo relief*, below) |
| `pinstripe` | One stripe round the body `PINSTRIPE_INSET` (0.5 mm) inside the margin, following the edge as a painted pinstripe does (Jackson RR, ESP LTD Alexi Hexed), broken where a cavity, the bridge, the pickguard or a contour is in its way and where a horn narrows past twice the margin; neither the seed nor the spacing changes it — set its distance from the edge with `body_engraving_margin` and its width with `body_engraving_depth` (the V-bit's groove is about 1.15 × the depth wide) |

### Camo relief

`camo` (`pattern_pockets`, `RELIEF_PATTERNS`) is cut as a relief, not as
lines: `Engraving.pockets`, closed shapes (`EngravedPocket`) each cleared
flat to its own level with a flat end mill. Each is a lobed round
(`CAMO_LOBES`, five harmonics round it) with `CAMO_ARMS` (1–3) arms
reaching out of it (`CAMO_ARM_LENGTH` 0.35–0.8 × its size, tapering off
over `CAMO_ARM_WIDTH`, 0.25–0.5 rad), `CAMO_SIZE` (0.3–0.55 × the spacing,
at least `CAMO_SMALLEST` 12 mm) wide, stretched `CAMO_STRETCH` (up to
2.3 ×) along the pattern's direction (one per seed, each shape ±
`CAMO_TURN` 25°). Each gets one of `CAMO_LEVELS` (4) levels,
`body_engraving_depth` / 4 apart — 0.5, 1, 1.5 and 2 mm at the default
2 mm — at random, or one deeper than any shape its centre lies on. Up to
`CAMO_COVER` (2.5) per the spacing squared of the area's bounds are laid,
each wholly in the area, until `CAMO_GIVE_UP` (600) tries in a row lay
none.
Shapes at one level keep `CAMO_GAP` (3 mm) apart, so they never merge;
shapes at different levels may lie over one another — the deeper shows
where they overlap, as cutting each to its own depth leaves it — as long
as each keeps `CAMO_KEEP` (half) of its outline showing; two that do not
overlap keep `CAMO_GAP` apart too, so no thin wall stands between them. A
shape that does not fit is tried again with fewer arms (an arm is what
most often runs into something), then `CAMO_SHRINK` (0.75 ×) smaller and
rounder, down to the smallest, so the gaps fill — still at least 12 mm
across and armed or lobed. One started inside a shallower shape is shaped
after it (`CAMO_INNER` 0.4–0.6 × its size, one arm at most; `CAMO_NEST`, a
quarter of the tries, start inside a big one on purpose); one that lies
wholly inside it is cut from its floor (`within`).

A shape lies over a level face only (`EngravingArea.level`, the top's
drop): on a carved top its plateau, on a stepped top within one band,
its level measured from that band's face (`face_drop`).
`Body_top_relief.nc` clears each shape with `relief_tool_diameter` (3 mm)
in `engraving_step_down` passes, one inside another from that one's
floor; the FreeCAD model cuts them a level at a time, and the body
editor shades them darker the deeper they go, the deeper over the
shallower. A neck-through part keeps
the shapes that reach it, whole.

## Bridges

The bridge is an interchangeable *spec* (`geometry.body.bridges`). Each spec
is a small frozen dataclass of dimensions whose `hardware(scale_length,
body_thickness)` returns everything that bridge needs cut into the body,
all placed relative to the scale line:

| Spec | `kind` | Adds |
| --- | --- | --- |
| `KahlerBridgeSpec` (default) | `kahler_7300` | Rectangular baseplate cutout (the DXF's 55.45 × 65.04 × 25 mm); no studs, no rear cavity. `string_count` 6, 7 or 8: the seven- and eight-string units (7327, 7328) share a cutout 20.32 mm (0.800 in) wider, 85.36 mm — Kahler's 2300/7300 installation sheets route 3.400 in for them against 2.600 in for six, with the same length, depths and position (`KAHLER_BASEPLATE_WIDTHS`); `baseplate_width` left empty takes the string count's |
| `FloydRoseSpec` | `floyd_rose` | Floyd Rose Original recessed routing per the manufacturer's *Original Series Routing Diagrams*: two Ø 10 stud holes 73.91 mm apart, 11.9 mm ahead of the scale line (25.03 in on a 25.5 in scale); a 95.25 mm wide recess, 79.38 mm long, narrowing to 71.12 mm after 42.44 mm, cut 6.73 mm deep over its whole footprint (continuous walls) and deepened to 11.18 mm behind the front 15.88 mm stud shelf as a step inside it, with a 20.96 × 82.85 mm block route 29.59 mm deep through that floor that opens into the spring cavity only where the two overlap; a rear 123.19 × 56.64 × 16.13 mm spring cavity with a 28.19 mm deep block clearance pocket at its tail end and a 2 mm cover recess 8 mm wider all round (`cover_margin`), closed by a sheet cover with six screws on the ledge (`Floyd Rose spring cavity cover`, `Cover_floyd_rose_spring_cavity.nc`, made like the cavity covers by `controls.rear_cover`). The diagram is for a 1.75 in (44.45 mm) body, where the block route runs 1.27 mm into the spring cavity; in a thicker body the spring cavity and block pocket reach deeper by the difference (`FLOYD_ROSE_DRAWN_THICKNESS`), so the block route always opens into the back. The recess is 3.56 mm wider on the tremolo-arm (treble) side; `treble_side` picks that side (`"+y"` on the right-handed Prototype001 body; a left-handed build flips it). `string_count` 6, 7 or 8: every width across the body follows the studs' spacing by the same margins on Floyd Rose's six- and seven-string sheets (the walls 8.89 / 12.45 mm outside the studs, the block route 8.94 mm wider than the studs are apart, the fine-tuner part 2.79 mm narrower), so the widths left empty (`pivot_stud_spacing`, `recess_*_half_width`, `fine_tuner_width`, `block_route_width`; `FloydRoseSpec.widths()`) come from the string count's stud spacing — 73.91, 84.58 (the *FR 7-String Routing* sheet: a 105.92 mm recess narrowing to 81.79 mm, a 93.52 mm block route) or 95.5 mm (the FRT8's post spacing; Floyd Rose publishes no eight-string routing, so the eight-string is the seven-string sheet widened). Everything along the neck and every depth is the same on both sheets, except that the seven-string sheet routes no block pocket deeper than the spring cavity: seven and eight strings get none (`block_pocket_depth` left empty), the notes saying to deepen the cavity's tail by hand should the block touch on a deep dive |
| `TuneOMaticSpec` | `tune_o_matic` | Two Ø 11.2 post holes, the treble one `compensation` (1.6 mm, 1/16 in) behind the scale line and the bass one `bass_setback` (3.2 mm, 1/8 in) further back, so the bridge leans with the strings' compensation and every saddle starts mid-travel (mirrored onto a +Y bass side, `mirrored_hardware`); two Ø 11.2 stop-bar stud holes 45 mm behind the scale line |
| `HeadlessBridgeSpec` | `headless` | A headless bridge: saddles and tuners in one unit screwed flat to the top. Four Ø 3 × 12 mm pilot holes `screw_inset` (6 mm) in from the plate's corners; the plate, from `front_reach` (12 mm) ahead of the scale line, `length` (90 mm) long and `side_margin` (10 mm) past the outer strings (`string_count`, `string_spacing`), is the bridge's `footprint`, which must lie on the body and which the pickguard and the engraving keep clear of |
| `HardtailSpec` | `hardtail` | `string_count` (6) Ø 3 string-through holes 14 mm behind the scale line and five pilot holes for the baseplate screws; the bass uses four strings 19 mm apart, 30 mm behind the scale line. With `string_through` off the bridge is top-loaded (most bass bridges string either way): no string holes. Each string-through hole (a single-string bridge's too) gets its ferrule's counterbore from the back, `body_string_ferrule_diameter` × `body_string_ferrule_depth` (8 × 6 mm, 5/16 in; a bass 9.5 × 6.5 mm, 3/8 in; depth 0 leaves it to the builder), drilled in `Body_back` — the ferrule hides it |
| `SingleStringBridgeSpec` | `single_string` | A small bridge of its own for every string (`string_count`, `string_spacing`; ABM 3710-style bass singles by default: 60 × 15 mm, 19 mm apart): each unit reaches `front_reach` (15 mm) ahead of its string's scale point, two Ø 3 × 12 mm screw pilots on its centre line `screw_inset` (6 mm) in from its ends, and with `string_through` a Ø 4 string hole through the body 30 mm behind the scale point. On a multiscale each unit stands at its own string's scale on the fanned bridge line, still square to its string — the bridge follows the fan without turning (`hardware(..., lean)`), which is why fanned basses use them. Their footprint round all the units is kept clear like a plate; `unit_width` may not exceed the string spacing |

`Prototype001Parameters.body_bridge` holds the spec; in the web form it is a
dropdown of bridge kinds with that kind's dimensions beneath it, sent back as
a JSON object with a `kind` entry (`bridge_spec_from_dict` rebuilds it). A
kind takes only the string counts it is made for (`BRIDGE_MIN_STRINGS` /
`BRIDGE_MAX_STRINGS`: the Kahler and the Floyd Rose six to eight, the
Tune-o-matic up to six; the form hides the others), and a spec with a
`string_count` of its own must carry the instrument's — the form keeps it
in step. With a seven- or eight-string Floyd Rose, `locking_nut` "auto"
fits Floyd Rose's seven- or eight-string nut (`r7`, `r8`).
Every dimension is a labelled starting value to be checked against the real
hardware. The bridge pickup keeps `body_bridge_pickup_offset` unless the
chosen bridge reaches further forward, in which case the route moves forward
on its own to leave `body_bridge_pickup_clearance` (3 mm) of wood ahead of
the bridge's nearest route edge, or of each hole's edge across from it (a
hole is measured against the stretch of route between its own Y ± radius
plus clearance, so turned hardware on a multiscale is not over-counted): a
Floyd Rose recess starts 19.5 mm ahead of the scale line, a hardtail's Ø 3
baseplate screw pilots sit 10 mm ahead of it (the route ends 14.5 mm ahead),
a Tune-o-matic's Ø 11.2 treble post hole 1.6 mm behind it (the route ends
7.0 mm ahead). The route also never reaches past the saddle line, measured at each
point of the route against the line where the strings leave the saddles (it
fans on a multiscale; a slant alone leaves the bridge and pickups square);
the Kahler's route ends 1.2 mm ahead of it, as in the DXF. A larger offset
set by hand still wins. If the moved route would then overlap the next
pickup route (the middle, else the neck one), `body_layout` refuses with a
`BodyGeometryError` naming the bridge, rather than leaving the overlap for
`BodySolid` to report. A Tune-o-matic on this flat body also wants a neck
angle or a recessed bridge, which the model does not provide.

Two new `BodySolid` fields carry bridge features: `through_cavities` (top
routes that open into a rear cavity or clean through the body, exempt from
the floor and break-through checks but required to reach the back face or a
rear cavity they overlap) and `extra_rear_cavities`.

Every bridge's fitting notes (`BridgeHardware.notes`: its routing sheet,
what to check against the unit, what is left to the hand — a Floyd Rose's
trem-claw screw holes, drilled into the spring cavity's wall) are given in
`Body_top`'s notes (`BodySolid.bridge_notes`). A seven- or eight-string
Floyd Rose's sheet routes no block pocket deeper than the spring cavity;
should the block touch on a deep dive, `block_pocket_depth` 28.19 (the
six-string sheet's) cuts it at the cavity's tail end, under the cover.

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

## Neck angle

`Prototype001Parameters.neck_angle` tilts the neck back, its headstock
toward the player, so the strings rise toward a tall bridge: empty, it
is `NECK_ANGLE_TUNE_O_MATIC` (2°) with a Tune-o-matic, which stands too
tall for a flat neck on the flat top (2–2.5° is usual there; a carved Les
Paul top takes 3–5°), and 0° otherwise; at most `MAX_NECK_ANGLE` (6°).

The neck pocket's floor (`TracedCavity.floor_slope`, `depth_at`,
`deepest`) stays `heel_thickness` deep at the heel end and sinks toward
the mouth, `body_neck_pocket_length × tan(angle)` deeper there (22.8 mm
at 2°). The neck turns about that heel end of the floor
(`neck_pivot`, `neck_to_body`), its nut end going down, so its heel lies
on the tilted floor. The bridge moves with it (`bridge_scale_line`): the
saddles go where a point a scale from the nut along the fret tops lands
once the neck is tilted, so the scale — and the 12th fret halfway — holds
along the strings' tilted line (2° on a 24 in scale: 1.04 mm toward the
nut, the fret-top line 12.4 mm above the top at the saddles). The bridge
pickup keeps its clearance from the moved bridge.

`Body_top.nc` cuts the pocket at its heel-end depth, then steps the floor
down toward the mouth in `FLOOR_TERRACE_STEP` (0.1 mm) terraces, each
reaching as far as the floor is that deep: the steps stand at most 0.1 mm
proud of the slope and the neck rests on their edges (a terrace shorter
than the tool, at the very mouth, is left out). The FreeCAD script cuts
the tilted floor exactly and turns every neck-side object (neck,
fretboard, headstock, binding) about the pivot (`neck_tilt` in
`Prototype001Geometry`).

