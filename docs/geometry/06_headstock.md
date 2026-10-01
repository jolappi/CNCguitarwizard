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
`bass_sign` (+1 right-handed, -1 left-handed) saying which way the bass
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
bridge and a plain nut otherwise; `"none"`, `"r2"` and `"r3"` choose
outright.

| Nut | Width | Height | Depth | Screws apart |
| --- | --- | --- | --- | --- |
| R2 (`LOCKING_NUT_SPECS["r2"]`) | 41.3 mm | 5.85 mm | 15 mm | 13.59 mm |
| R3 | 42.85 mm (needs `nut_width` at least that) | 7.10 mm | 15 mm | 13.59 mm |

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
thickness. The two mounting screws' pilot holes
(`locking_nut_screw_diameter` 2.5 mm, `locking_nut_screw_depth` 8 mm into
the neck) sit `screw_spacing` apart, half the nut's depth behind the nut
line; they are drilled by hand through the nut. A shelf below the glue
face, or a nut wider than the neck, is refused (`NeckGeometryError`).

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
