# SVG Rendering

`SVGRenderer` converts a single supported geometry object into a standalone,
well-formed SVG document without external dependencies.

Supported types are `Point2D`, `Line2D`, `Centerline`, and `Fretboard`.
Points are rendered as circles, lines and centerlines as SVG `line` elements,
and fretboard outlines as an SVG `polygon`.

```python
from cncguitarwizard.geometry.neck import Centerline
from cncguitarwizard.render.svg import SVGRenderer

svg = SVGRenderer().render(Centerline(609.6))
assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
```

The renderer emits direct geometry coordinates. It does not transform, scale,
or mutate the input geometry.
