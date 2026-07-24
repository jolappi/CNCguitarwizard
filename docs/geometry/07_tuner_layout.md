# Tuner-hole layout

Prototype001 uses six 10 mm tuner holes in a symmetric 3+3 arrangement.

| Position from nut | Centerline offset |
| ---: | ---: |
| 55 mm | ±16 mm |
| 85 mm | ±13 mm |
| 115 mm | ±10 mm |

The rows converge toward the tapered tip. The layout validates:

- nut and tip clearance;
- side-edge clearance;
- hole-to-hole clearance;
- station ordering;
- finite, positive dimensions.

Prototype001 requires at least approximately 8 mm of wood between each 10 mm
hole edge and the tapered side edge. The closest calculated clearance is
about 8.646 mm. Nut, tip, and hole-to-hole clearances remain validated
separately; the tuner-body footprint and washer diameter must still be checked
against the chosen hardware.

```python
from cncguitarwizard.geometry.neck import HeadstockPlan, TunerLayout

headstock = HeadstockPlan(150.0, 42.0, 30.0, 65.0, 40.0)
layout = TunerLayout(
    headstock,
    hole_diameter=10.0,
    station_distances=(55.0, 85.0, 115.0),
    side_offsets=(16.0, 13.0, 10.0),
    minimum_edge_clearance=8.0,
)
```
