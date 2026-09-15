# Fretboard Outline Geometry

`Fretboard` creates a tapered four-edge outline from a centerline, a scale
length, and widths at the nut and bridge. All dimensions are millimetres.

The centerline direction is normalized to `(dx, dy)`. Its left-facing
perpendicular is `(-dy, dx)`. At each end of the fretboard, half the local
width is added to and subtracted from the center point along that perpendicular:

```text
left  = center + perpendicular * width / 2
right = center - perpendicular * width / 2
```

The resulting `nut_line`, `bridge_line`, `left_edge`, and `right_edge` form
the `outline` tuple. No scaling transform or additional outline type is added.

The nut's two corners are symmetrically rounded with an 8 mm radius by
default. The radius starts from the nut end and is rendered as two SVG circular
arc segments. It can be overridden with `nut_corner_radius` when constructing
a `Fretboard`.

```python
from cncguitarwizard.geometry.fretboard import Fretboard
from cncguitarwizard.geometry.neck import Centerline

fretboard = Fretboard(
    scale_length=609.6,
    nut_width=42.0,
    bridge_width=63.0,
    centerline=Centerline(609.6),
    nut_corner_radius=8.0,
)

assert fretboard.nut_line.length == 42.0
assert fretboard.bridge_line.length == 63.0
assert len(fretboard.outline) == 4
```
