# Headstock reference geometry

Prototype001 uses a symmetric 3+3 headstock with a modern tapered outline by
default; the same plan can be shifted sideways for an in-line or 4+2 tuner
row (see [Tuner-hole layout](07_tuner_layout.md)).
The first 45 mm uses a sampled smoothstep side curve from the 42 mm nut width
to the 65 mm shoulder. This rounds the neck-to-headstock joint in plan view
instead of connecting it with two straight diagonal edges.
It is Gibson-inspired in layout but does not reproduce an identifiable
manufacturer outline.

## Plan view

| Parameter | Value |
| --- | ---: |
| Length | 150 mm |
| Nut width | 42 mm |
| Root length / shoulder distance | 45 mm |
| Shoulder width | 61.7 mm on the default 3+3 (follows the holes; `headstock_shoulder_width` overrides) |
| Tip width | 42.5 mm on the default 3+3 (follows the holes; `headstock_tip_width` overrides) |

The outline widens after the nut and then runs straight to the tip, which
may be narrower or — for a Strat-style six-in-line blank — wider than the
shoulder. Edges that carry tuners are fitted through the holes 15 mm out,
never inside the style's wood reserve (see
[Tuner-hole layout](07_tuner_layout.md)), so the widths above are what
Prototype001's 3+3 stations produce, not fixed inputs.

`HeadstockPlan` takes optional `shoulder_shift` and `tip_shift` values
(positive toward the bass side) that move the outline's centre at the
shoulder and at the tip while the nut stays centred on the neck, and a
`bass_sign` (-1 with the bass side at -Y, the right-handed default; +1
left-handed) saying which way the bass
side lies. `half_width_at(distance, side)` gives each side's own signed
edge distance — negative should that edge cross the centreline —
`edge_y(distance, y_sign)` the
edge's Y coordinate, and `width_at_distance` the total; the FreeCAD
headstock loft, the plan view and the CAM outline all run between the two
signed edges.

## Drawn edges

`headstock_outline = "drawn"` (the default) replaces the fitted outline
with two drawn edges — while they are empty it is the fitted outline — `headstock_bass_edge` and `headstock_treble_edge`: lists of
`(distance from the nut, half-width)` points, each ending at the tip. Each
edge is a `SmoothCurve` from the nut's half-width through its points: it
leaves the nut parallel to the neck and rounds through its points (each
one's slope is its neighbours' chord), swinging past them into round
bulges and hollows as a hand-drawn Stratocaster or Schecter outline does.
Without tip points the tip is a straight cut at `distance == length`, the
last point's distance, so the FreeCAD headstock loft, the CAM outline and the
plan view take a drawn headstock exactly as a fitted one
(`HeadstockPlan(bass_edge=..., treble_edge=...)`).

`headstock_tip_points` shape a drawn headstock's tip: `(how far past the
tip line, y)` points across it from −Y to +Y, strictly between the two
edges' tip corners. The tip is then a Catmull–Rom curve from corner to
corner through them (`HeadstockPlan.tip_outline`), leaving each corner
along its edge so a round end meets its sides without a corner; points
past the tip line make a pointed or round end, one short of it a notch,
and `HeadstockPlan.reach` is how far the headstock then reaches. Tuner
holes keep their clearance to the tip measured straight to its curve
(`tip_clearance`); a FreeCAD loft past the tip line is as wide as the tip
bulges (`envelope_y`). Being
measured from the tip line, they move with it when the tip handles change
the length. The FreeCAD loft runs 1 mm past the furthest point and a
prism cuts it back to the tip (`_render_headstock_tip_cut`); the neck's
outline program, its blank and the tuner holes' tip clearance follow the
shaped tip. A fitted headstock ignores them.

A sharp point (a Jackson style headstock) is the two edges meeting: drawn
edges whose tip corners end less than `TIP_POINT_WIDTH` (1 mm) apart meet
in one point between them (`HeadstockPlan.pointed`, `tip_point`), with no
tip line and no tip points (refused with one). The edges may narrow to it
under 1 mm wide over their last run, narrowing all the way; anywhere else
they must stay 1 mm apart (a pinch, or edges crossing before the tip, is
still "the drawn edges meet or cross"). The outline runs down one edge to
the point and back up the other, so the neck's outline program cuts the
point. The FreeCAD loft keeps `POINT_LOFT_WIDTH` (12 mm) wide over that
last run under it (`point_start`, `envelope_y`) and a prism cuts it back to
the two edges and the point from 1 mm before (`_render_headstock_tip_cut`).
In the headstock editor, a tip corner dragged within 3 mm of the other
snaps onto it; the point then drags as one, and Shift-dragging a corner
parts them again.

The tuner holes still come from `headstock_style`. `headstock_design()`
checks every hole against the drawn outline — across the neck to each
edge at the hole's own distance from the nut and along it to the tip, as
the fitted outline is laid out; the nut is not an edge — and rejects one
closer than `tuner_edge_offset` (less 0.5 mm).
Empty edges fall back to the fitted outline. In the web app, choosing
"drawn" opens an editor that starts from the fitted edges (ten handles a
side: halfway to the shoulder, the shoulder, seven along the taper and the
tip) and draws each hole's keep-out circle.

## Side reference

The headstock center plane drops at 8 degrees. With a 150 mm plan length, the
tip drop is:

```text
drop = length × tan(angle)
drop = 150 mm × tan(8°)
drop ≈ 21.081 mm
```

`headstock_angle` takes any angle from 0 up to (not including) 90 degrees.
The headstock is always `headstock_thickness` (16 mm) thick, measured normal
to its face. The nut is glued both to the fretboard's end and to the neck,
so the neck keeps a flat seat for it, level with the glue face and only as
long as the nut: `nut_shelf_length` (5 mm) behind the nut line, as a strip
of even length along a slanted or fanned nut (`HeadstockSolid.nut_lean`,
`nut_seat_length`, `face_start_x`).

### Locking nut

A Floyd Rose locking nut is screwed down from the top instead
(`geometry.neck.locking_nut`, `Prototype001Parameters.locking_nut`):
`"auto"` (the default) takes the Floyd Rose Original R2 with a Floyd Rose
bridge — the seven- or eight-string nut with a seven- or eight-string
Floyd Rose (`FLOYD_ROSE_NUTS`) — and a plain nut otherwise; `"none"`,
`"r2"`, `"r3"`, `"r7"` and `"r8"` choose outright. Each needs `nut_width`
at least its own width.

| Nut | Width | Height | Depth | Screws |
| --- | --- | --- | --- | --- |
| R2 (`LOCKING_NUT_SPECS["r2"]`) | 41.3 mm | 5.85 mm | 15 mm | two, 13.59 mm apart |
| R3 | 42.85 mm | 7.10 mm | 15 mm | two, 13.59 mm apart |
| 7-string (`"r7"`) | 47.6 mm | 6.30 mm | 15.5 mm | two, 18.6 mm apart |
| 8-string (`"r8"`) | 53.8 mm | 6.30 mm | 15.7 mm | three, 13.3 mm apart |

The R2, R3 and seven-string heights are Floyd Rose's nut chart's (at the D
string); the seven-string nut's depth is Schaller's (which makes it), the
eight-string's size and its three screws the FRT8's dimension sheet's.
Floyd Rose lists no height for the eight-string nut (it takes the
seven-string's) and draws no screws for the seven-string one, whose two
are taken between its clamping pads; the screws are drilled through the
nut's own holes anyway.

Its front face stands on the nut line and the seat runs its depth + 1 mm
(16 mm) behind it, so the headstock face, its transition and a
headstock-adjusted truss rod's pocket all start that much further back.
Floyd Rose puts the nut's top 0.38 mm (0.015 in) above the frets' tops
(`NUT_ABOVE_FRETS`), so its shelf sits at `fretboard_thickness +
fret_height − height + 0.38` above the glue face: 1.73 mm for the R2 on a
6 mm board with 1.2 mm frets. A shelf at least `MIN_BOARD_SHELF` (1 mm)
high is the fretboard itself, which runs on under the nut and is milled
down to it; a lower one (the R3's 0.48 mm) leaves the board ending at the
nut line, the nut standing on the neck's seat on a shim of that
thickness. The mounting screws' pilot holes
(`locking_nut_screw_diameter` 2.5 mm, `locking_nut_screw_depth` 8 mm into
the neck) are spread evenly over `screw_spacing` (`screw_count`, two or
three), half the nut's depth behind the nut line; they are drilled by hand
through the nut. A shelf below the glue
face, or a nut wider than the neck, is refused (`NeckGeometryError`).

### Slotted nut (Fender / Telecaster)

`nut_style = "slot"` seats a plain nut the Fender way
(`LockingNut.slotted`, the same placement without screws): the fretboard
runs on past the nut line, a slot `nut_thickness` (3.5 mm) wide milled
`nut_slot_depth` (3 mm) below its crown there, and the nut is glued into
it, front face on the nut line. Behind the slot the board carries on at
full height for `nut_slot_lip` (3 mm), then slopes down to the glue face
over `nut_slot_taper` (3 mm), where it ends: 9.5 mm behind the nut line.
The neck's flat seat runs as far, then the headstock face's transition
starts. The slot must
leave at least `MIN_BOARD_SHELF` (1 mm) of board under the nut. A locking
nut takes the nut's place whichever style is set.

### Zero fret

`nut_style = "zero_fret"` stands a fret on the nut line itself (the scale
starts there; `FretLayout(zero_fret=True).zero_fret_slot`, apart from the
`slots` of fret 1 on) and sets the nut, now only a string guide filed a
little below the fret's top, `zero_fret_gap` (3 mm) behind it: the
slotted nut's placement with its slot set back (`LockingNutSpec.set_back`,
`LockingNut.zero_fret`, `front`), so the board runs on past the nut line
to hold both — the gap, the slot, the lip and the taper, 12.5 mm. The
zero fret's slot is cut first in `Fretboard_slots.nc` (`Zero fret slot`)
and in the FreeCAD model (on the board's nut-end row); the plan view and
the headstock editor draw it.

The headstock editor's own pane offers the nut's style (`nut_style`)
beside the tuner layout, and draws the nut: a plain one on its shelf, a
slotted or zero-fret nut with the board running on behind the nut line,
a zero fret's line, a locking nut dark (`webapp._nut_drawing`).

A headstock-adjusted truss rod is then reached Fender style too, with no
cover: a spoke wheel in an open trough behind the board, or without one a
notch for the key (see [Truss rod](08_truss_rod.md#spoke-wheel-or-not)).

`NECK_TEMPLATES["telecaster"]` (`TELECASTER_NECK`, *Start from* in the
web app's headstock editor) sets a whole Telecaster neck: the slotted
nut, a flat (0°) six-in-line headstock drawn as a Telecaster's (the tuner
edge straight along the posts and flaring out from the nut, the other
edge sweeping out to a rounded treble point, the end wrapping round the
last tuner; 204 mm long round the default row) and the truss rod
adjusted at the heel, vintage style; `truss_rod_adjustment = "headstock"`
gives the modern one. The plan view draws the nut in its slot, the board
running on behind it with a line where it starts sloping down.

Behind the seat the top eases onto the face over
`headstock_face_transition` (12 mm), meeting it at its own slope, so there
is no step (`HeadstockSolid.top_z`): an angled face is eased in with a
smooth curve (`smoothstep`, level at the seat as well), and a face set
down (a flat headstock's 4 mm) is reached through a Stratocaster style
cove, a concave cup that leaves the seat's edge falling at about 34
degrees and flattens onto the face. The face itself is a plane
square to the neck that falls at the angle from the seat's front-most end
(`face_pivot_x`), so an angled headstock starts to fall right behind a
square seat, and a fanned nut only turns the transition, never the
headstock. At 0 degrees the headstock is flat, Fender style, and set down:
its face lies `headstock_face_drop` below the glue face — empty, 4 mm for
a flat headstock (`FLAT_HEADSTOCK_FACE_DROP`: its 16 mm in the bottom of a
20 mm blank below the fretboard) and nothing for an angled one — so the
strings still break over the nut toward the tuners; the tuner centre marks
are drilled straight through. A flat headstock with
`headstock_face_drop=0` keeps the glue face as its face: the FreeCAD loft
is flush with it and nothing is milled; the strings then need a string
tree.

The FreeCAD script lofts the neck flat over the seat and the transition
and a little proud of the face, then cuts the transition and face with one
ruled loft between two side profiles (`HEADSTOCK_FACE_CUT_PROFILES`); the
neck G-code mills the same surface.

Prototype001 uses a true joined root transition: a smooth longitudinal curve
blends the fixed 5 mm nut shelf into the normal D profile, and the outer
shoulders continue farther into the headstock root than the center does. The
default manufacturing build therefore replaces the first part of the angled
headstock with a transition loft instead of relying on a visible post-fuse
edge fillet. This makes the neck-back curve continue into the headstock root
without a noticeable seam.

```python
from cncguitarwizard.geometry.neck import (
    HeadstockAngleReference,
    HeadstockPlan,
)

plan = HeadstockPlan(150.0, 42.0, 45.0, 65.0, 40.0)
angle = HeadstockAngleReference(150.0, 8.0)
```

These are reference geometries. Headstock thickness, transition curves, and
six 10 mm tuner holes are separate manufacturing features.

## Thickness and solid

`HeadstockSolid` turns the plan and angle reference into a three-dimensional
blank. Thickness is configurable from 14 to 16 mm and is measured normal to
the angled face. Prototype001 defaults to 16 mm:

```python
from cncguitarwizard.geometry.neck import HeadstockSolid

solid = HeadstockSolid(plan, angle, thickness=16.0)
```

Values below 14 mm or above 16 mm are rejected before CAD export.

## Lettering

`headstock_engraving_text` engraves lettering into the headstock face in
one of `geometry.lettering`'s single-stroke fonts (`FONTS`,
`headstock_engraving_font`) — each letter a few centre lines a V-bit
follows:

- `sans` (the default), drawn here: a plain geometric sans with capitals
  10 units tall, lowercase on a 7 unit x-height with 3 unit descenders,
  digits and a little punctuation (`GLYPHS`);
- `script`, Hershey Script (medium), a joined handwriting;
- `gothic`, Hershey Gothic English, a blackletter.

The last two are converted from Inkscape's single-stroke SVG fonts by
`tools/import_svg_font.py` into `geometry.fonts` (curves sampled to lines,
printable ASCII and ä ö å ü é), carrying the Hershey Fonts' required
acknowledgement: they were originally created by Dr. A. V. Hershey at the
U. S. National Bureau of Standards, in a data format originally created
by James Hurt, Cognition, Inc. `text_lines` sets a string in any of them
at any height (the capital H's), centre and angle. The capitals are
`headstock_engraving_height` (6 mm) tall, centred on
`headstock_engraving_x` / `_y` (by default `HEADSTOCK_ENGRAVING_SETBACK`,
20 mm, behind the nut's seat, on the centreline), running along
`headstock_engraving_angle` degrees from +X with the letters' tops to its
left: 90° (the default) runs across the headstock, read with it pointing
up. `Prototype001Parameters.headstock_lettering` refuses lettering the
font has no glyph for, and lettering that comes within
`HEADSTOCK_ENGRAVING_CLEARANCE` (2 mm) of the face's edge, the nut's
seat, a tuner hole or a headstock truss rod adjuster's trough; the
headstock editor draws it in blue, drags it (writing `_x` / `_y`) and
shows why it does not fit. It is cut `headstock_engraving_depth` (1 mm)
deep into the finished face in `Headstock_engraving.nc`, and drawn as
lines on the face in the FreeCAD model (`HeadstockLettering`).

## Headless

`Prototype001Parameters.headless` (the `headless_guitar` and
`headless_bass` instruments) has no headstock and no tuners: the neck ends
`headless_length` (35 mm, 25–80 mm, `MIN_HEADLESS_LENGTH` for the neck's
nut-end blend) behind the nut in a flat headpiece as wide as the nut, its
top level with the glue face (angle 0, `headstock_face_drop` 0), where
the string anchor screws on. `headstock_design` then returns that plan and
an empty `TunerLayout` (no stations), `headstock_style` and the tuner
values are not used, and the strings are tuned at the bridge
(`HeadlessBridgeSpec`, see the body's bridges). The FreeCAD loft, the neck
programs (no face raster, no tuner marks) and the web app (no headstock
editor) all take the headpiece as a short headstock; the loft drops tip
sections crowding within `MIN_SECTION_GAP` (0.2 mm) of the next, which a
head this short otherwise produces.
