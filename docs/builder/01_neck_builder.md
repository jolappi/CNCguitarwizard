# Neck Builder

`NeckBuilder` collects the three required neck dimensions and creates an
immutable `Neck` model. The resulting model includes a `Centerline` and a
`Fretboard` created from the same dimensions.

```python
from cncguitarwizard.builder import NeckBuilder

neck = (
    NeckBuilder()
    .scale_length(609.6)
    .nut_width(42.0)
    .bridge_width(63.0)
    .build()
)

assert neck.centerline.length == 609.6
assert neck.fretboard.nut_line.length == 42.0
assert neck.fretboard.bridge_line.length == 63.0
```

All dimensions are required and must be greater than zero. `build()` raises
`BuilderError` when a required dimension is missing or invalid.
