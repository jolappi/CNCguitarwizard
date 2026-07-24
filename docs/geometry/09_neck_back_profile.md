# Neck-back D profile

The first Wizard-inspired neck-back profile uses a superellipse rather than a
semicircle. This produces a flatter center and fuller shoulders associated
with a thin D shape.

```text
(|x| / half_width)^n + (|depth| / center_depth)^n = 1
```

Prototype001 starts with an exponent of `3.5`. This is deliberately a
parameter, not a claim to duplicate a proprietary Ibanez profile.

The neck taper determines the local widths:

| Station | Width | Wood depth |
| --- | ---: | ---: |
| Fret 1 | approximately 43.047 mm | 17 mm |
| Fret 12 | approximately 51.333 mm | 19 mm |

```python
from cncguitarwizard.geometry.neck import (
    NeckOutline,
    NeckProfileStations,
)

outline = NeckOutline(609.6, 24, 42.0, 56.0, 56.0, 63.0)
stations = NeckProfileStations(outline, 17.0, 19.0, exponent=3.5)
```

The physical test block should be used to adjust the exponent and shoulder
feel before the value is approved for a complete neck.
