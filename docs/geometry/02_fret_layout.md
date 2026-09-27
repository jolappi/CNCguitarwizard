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

## Slanted and fanned frets

`FretLayout(fretboard, fret_count, skew)`, `Fretboard(..., skew=...)` and
`FretboardSurface(..., skew=...)` take a `FretSkew`: the lean `at(x)`
(`dx/dy`) of the fret line through centerline station `x`. Every point `y`
off the centerline moves `at(x) * y` along the neck, so each slot's
midpoint (and every `station_positions` entry) stays on the
equal-temperament position on the centerline and each slot still ends on
the tapered edges; the nut end and board end lean like the frets there.
Inlays follow the frets around them: a block leans point by point, so its
front and back stay parallel to the frets either side; barbed wire turns
about its own centre to the frets' angle there; a dot keeps its shape and
moves onto the line between its two frets (so a double dot's pair lies
along the frets).

**Slanted frets** — `Prototype001Parameters.fret_slant_angle` (degrees,
0 by default, at most `MAX_FRET_SLANT_ANGLE` = 10°): a constant lean; a
positive angle moves each fret's treble end toward the bridge, whichever
side `headstock_bass_side` puts the bass on (`fret_slant`). The bridge and
pickups are unchanged, so only the centerline string keeps its exact
scale; the others are set at the saddles.

**Multiscale** — with `bass_scale_length` set, `scale_length` is the treble
(outermost string's) scale and `bass_scale_length` the bass one (longer,
at most `MAX_MULTISCALE_RATIO` = 1.15 times). `perpendicular_fret` (7 by
default, 0 for the nut) is square to the neck. Each fret is the straight
line through its exact positions on the two outer strings, which run from
`(n - 1) / 2 × nut_string_spacing` off the centerline at the nut to
`(n - 1) / 2 × bridge_string_spacing` at the bridge; since the strings fan
evenly, every string between gets its exact fret positions too. The
centerline takes the mean scale (`centre_scale`), which the neck, the
heel and the body's scale line follow. Any bridge can be used: it stays
square at the centerline scale and each saddle is set to its string's
scale, so the bridge's saddle travel must cover half the fan either way
(±19 mm for a 38 mm fan) plus the usual compensation. The exception is
the Tune-o-matic, whose saddles have too little travel: its posts (where
the strings rest) always turn about the centerline bridge point to the
fanned bridge line, while its stop-bar studs stay square
(`turned_hardware`, `bridge_follows_fan`). A hardtail turns its
string-through holes the same way when `body_bridge_follows_fan` is set.
`body_pickups_follow_fan` (`"auto"`, `"yes"` or `"no"`) decides whether
the pickups turn; `"auto"` turns them unless the bridge is a
Tune-o-matic. A turned pickup takes the lean of the frets at its centre
and moves back by its extra reach, so its near edge keeps the straight
pickup's gap to the neck pocket or bridge. A slant adds to the fan on
the fretboard only.

A leaning nut end reaches back into the nut shelf; the neck's shelf is
lengthened by that reach (`nut_shelf_reach`), so the nut keeps its full
5 mm where the nut end leans furthest back and the shelf is longer on the
other side.

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
