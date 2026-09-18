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

## Side reference

The headstock center plane drops at 8 degrees. With a 150 mm plan length, the
tip drop is:

```text
drop = length × tan(angle)
drop = 150 mm × tan(8°)
drop ≈ 21.081 mm
```

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
