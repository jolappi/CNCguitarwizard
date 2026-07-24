# Fret layout

`FretLayout` combines three existing pieces of the geometry engine:

1. equal-temperament fret positions;
2. the neck centerline;
3. the tapered fretboard outline.

The result is a tuple of immutable `Line2D` slot segments. Each segment is
perpendicular to the centerline and ends at the fretboard edges, making it a
useful input for drawings, renderers, and later CAM operations.

## Position

The distance from the nut to fret `n` is:

```text
distance = scale_length - scale_length / 2^(n / 12)
```

## Width

The fretboard width is interpolated linearly at the fret position:

```text
fraction = distance / scale_length
width = nut_width + (bridge_width - nut_width) * fraction
```

The slot extends half of that width to each side of the centerline.

## Example

```python
from cncguitarwizard.geometry.fretboard import Fretboard, FretLayout
from cncguitarwizard.geometry.neck import Centerline

scale_length = 609.6
fretboard = Fretboard(
    scale_length=scale_length,
    nut_width=42.0,
    bridge_width=63.0,
    centerline=Centerline(scale_length),
)
layout = FretLayout(fretboard, fret_count=24)

assert len(layout.slots) == 24
```

The geometry describes slot centerlines only. Cutter diameter, slot depth,
stepdown, and feeds belong to the later manufacturing layer.

## SVG preview

`SVGRenderer` accepts a complete `FretLayout`. It renders the tapered outline
and every bounded slot inside a group:

```python
from cncguitarwizard.render.svg import SVGRenderer

svg = SVGRenderer().render(layout)
```

The output uses `fret-layout`, `fretboard-outline`, and `fret-slot` CSS class
names so downstream documentation and preview tools can style the geometry
without changing the geometry engine.

The renderer calculates its SVG `viewBox` from the geometry. Long and short
scale lengths therefore fit the same viewport automatically. The default
model-space margin is 10 mm and can be changed without touching the geometry:

```python
svg = SVGRenderer(width=1200, height=400, padding=15.0).render(layout)
```
