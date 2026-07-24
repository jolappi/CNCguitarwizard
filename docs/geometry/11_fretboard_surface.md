# Three-dimensional fretboard surface

`FretboardSurface` creates the backend-independent 3D playing surface for the
separate fretboard.

A radius row is generated at the nut and every fret position. For
Prototype001 this produces 25 cross-sections:

- nut width: 42 mm;
- fret 24 width: 56 mm;
- constant radius: 430 mm;
- center thickness: 6 mm.

```python
from cncguitarwizard.geometry.fretboard import FretboardSurface

surface = FretboardSurface(
    scale_length=609.6,
    fret_count=24,
    nut_width=42.0,
    last_fret_width=56.0,
    radius=430.0,
    center_thickness=6.0,
)
```

The output is an immutable quad mesh. Its rows can be converted to exact
circular wires and lofted by a future CAD backend. The flat underside and end
walls remain separate construction steps so the geometry layers stay
individually testable.
