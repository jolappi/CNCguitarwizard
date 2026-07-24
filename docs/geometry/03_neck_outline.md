# Neck outline

`NeckOutline` creates the backend-independent top view of the neck shaft and
bolt-on heel.

For Prototype001 the locked dimensions are:

| Parameter | Value |
| --- | ---: |
| Scale length | 609.6 mm |
| Frets | 24 |
| Nut width | 42 mm |
| Width at fret 24 | 56 mm |
| Heel width | 56 mm |
| Heel length | 63 mm |

The taper ends at the calculated position of the final fret. The heel then
continues at a constant width for the requested length.

```python
from cncguitarwizard.geometry.neck import NeckOutline

outline = NeckOutline(
    scale_length=609.6,
    fret_count=24,
    nut_width=42.0,
    last_fret_width=56.0,
    heel_width=56.0,
    heel_length=63.0,
)
```

The outline is a top-view manufacturing reference. Neck thickness, fretboard
radius, headstock angle, and back-profile surfaces are separate geometry
layers added later.
