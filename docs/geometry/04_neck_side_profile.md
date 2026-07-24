# Neck side profile

`NeckSideProfile` describes the neck wood below the separately modelled
fretboard.

Prototype001 uses these locked thicknesses:

| Reference | Wood thickness |
| --- | ---: |
| Fret 1 | 17 mm |
| Fret 12 | 19 mm |
| Heel | 20 mm |

The profile stays at 17 mm between the nut and first fret, interpolates through
the twelfth-fret reference, reaches 20 mm at the final fret, and remains
parallel through the 63 mm heel.

```python
from cncguitarwizard.geometry.neck import NeckSideProfile

profile = NeckSideProfile(
    scale_length=609.6,
    fret_count=24,
    first_fret_thickness=17.0,
    twelfth_fret_thickness=19.0,
    heel_thickness=20.0,
    heel_length=63.0,
)
```

The 6 mm fretboard is intentionally absent from this geometry. Keeping it
separate preserves the distinction between the neck blank and the glued
fretboard for later CAD and CAM operations.
