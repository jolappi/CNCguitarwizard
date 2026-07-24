# Tuner-hole layout

Prototype001 uses six 10 mm tuner holes in a symmetric 3+3 arrangement.

| Position from nut | Centerline offset |
| ---: | ---: |
| 60 mm | ±21 mm |
| 95 mm | ±18 mm |
| 130 mm | ±15 mm |

The rows converge toward the tapered tip. The layout validates:

- nut and tip clearance;
- side-edge clearance;
- hole-to-hole clearance;
- station ordering;
- finite, positive dimensions.

The current minimum material outside each hole is 2 mm. This is a geometric
starting point; the tuner-body footprint and washer diameter must be added
before manufacturing approval.

```python
from cncguitarwizard.geometry.neck import HeadstockPlan, TunerLayout

headstock = HeadstockPlan(150.0, 42.0, 30.0, 65.0, 40.0)
layout = TunerLayout(headstock, hole_diameter=10.0)
```
