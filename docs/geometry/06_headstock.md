# Headstock reference geometry

Prototype001 uses a symmetric 3+3 headstock with a modern tapered outline.
It is Gibson-inspired in layout but does not reproduce an identifiable
manufacturer outline.

## Plan view

| Parameter | Value |
| --- | ---: |
| Length | 150 mm |
| Nut width | 42 mm |
| Shoulder distance | 30 mm |
| Shoulder width | 65 mm |
| Tip width | 40 mm |

The outline widens after the nut and then tapers toward the tip.

## Side reference

The headstock center plane drops at 8 degrees. With a 150 mm plan length, the
tip drop is:

```text
drop = length × tan(angle)
drop = 150 mm × tan(8°)
drop ≈ 21.081 mm
```

```python
from cncguitarwizard.geometry.neck import (
    HeadstockAngleReference,
    HeadstockPlan,
)

plan = HeadstockPlan(150.0, 42.0, 30.0, 65.0, 40.0)
angle = HeadstockAngleReference(150.0, 8.0)
```

These are reference geometries. Headstock thickness, transition curves, and
six 10 mm tuner holes are separate manufacturing features.
