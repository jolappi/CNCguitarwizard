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
| `RearCavity` | A deep cavity plus a shallow cover-plate recess, both cut from the back face. |
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
- the neck pocket is the drawing's trapezoidal `neckpocket` block, placed so
  its tail-ward wall is exactly where the neck's real heel ends and widened
  laterally so every wall is at least `heel_width / 2` from the centerline;
- the bridge baseplate cutout is the drawing's `LWPOLYLINE`;
- the almond control cavity and the round switch cavity are the drawing's
  pairs of concentric loops — the inner loop is the cavity, the outer loop the
  2 mm cover-plate recess — both cut from the back.

The frame is anchored on the drawing's own pickup placement: the neck
pickup's nut-ward edge sits 10 mm past the heel end, and the pickups' centre
line is `Y = 0`. Everything else in the drawing follows from that one offset.

## Prototype001 body

| Feature | Value |
| --- | --- |
| Thickness | 44 mm flat slab |
| Neck pocket | DXF trapezoid, 79.5 mm long, ends at heel end (461.2), 20 mm deep, opens onto the horn gap |
| Pickup routes | DXF humbucker route with ears, 41 × 85.9 mm, 22 mm deep, centres 491.7 and 587.9 |
| Pickup screw recesses | Ø 6 mm, 8 mm below the route floor, at ±39.95 mm |
| Bridge | Kahler 7300, flat mount: no pivot studs, no sustain block; 55 × 65 mm baseplate cutout 25 mm deep |
| Control cavity | DXF almond, rear, 36 mm deep (8 mm top wall), 2 mm cover recess |
| Switch cavity | DXF circle Ø 44 at the upper-horn root, rear, 36 mm deep, Ø 59.5 cover recess |
| Shaft holes | Ø 12.7 switch, 2 × Ø 10 pots at (642, 86) and (682, 87) |
| Jack | Ø 12.5 bore from (742, 107.5) at 202.5°, 55 mm, ending inside the control cavity |

Every value above is a `Prototype001Parameters` field (`body_*`), so any of
them can be changed with `dataclasses.replace`.
