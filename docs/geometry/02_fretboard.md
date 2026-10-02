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

## Binding

`Prototype001Parameters.fretboard_binding_width` (0 = none, at most
`MAX_FRETBOARD_BINDING`, 3 mm) binds the fretboard's two long edges. The
board itself — its `FretboardSurface` and `Fretboard`, so its outline,
radius, slots and inlays — is built that much narrower each side, and
strips that thick are glued on, so board and binding together keep
`nut_width` and `final_fret_width`; the neck under them keeps those
widths too. The fret slots run out through the narrowed board's edges as
usual, and each fret's tang is nipped back over the binding before it is
pressed in. `Fretboard_outline.nc` and `Fretboard_slots.nc` say so in
their notes. In the FreeCAD model the strips are their own object,
`FretboardBinding`: two solids from the nut to the board's end, as tall
as the board's edge, outside it.

## Position markers

`InlayLayout` (`Prototype001Parameters.inlay_style`, `inlay_depth` 2 mm)
places the markers as flat-bottomed pockets in the playing surface, in
one of `INLAY_STYLES`:

| Style | Markers |
| --- | --- |
| `barbed_wire` (default) | A barbed-wire ribbon across the board; two at the double-marker frets (12, 24) |
| `dot` | Round dots (`inlay_dot_diameter`, 6 mm); two at 12 and 24 |
| `block` | Gibson blocks |
| `trapezoid` | Les Paul trapezoids: long at the bass edge, the treble edge `TRAPEZOID_SHORT_SIDE` (55 %) of it |
| `sharktooth` | Jackson sharktooth: a triangle across the board at its bridge-side end and along the bass edge, its point at the treble edge |
| `parallelogram` | Leaning blocks, the treble edge `PARALLELOGRAM_LEAN` (35 % of the length) toward the nut |
| `diamond` | A diamond, its points on the centreline and at the edges' margin |
| `split_block` | Gibson split blocks: a block split along its diagonal (treble front corner to bass back corner) into two pieces `SPLIT_BLOCK_GAP` (1.5 mm) apart |

Every style but barbed wire and dots spans the board between its frets
(`BOARD_STYLES`): one per listed fret, `inlay_block_length_fraction`
(60 %) of the fret spacing long, `inlay_block_edge_margin` (5 mm) inside
each board edge with the board's taper, its corners rounded 1 mm. The
bass side comes from `headstock_bass_side` (`bass_sign`). With slanted or
fanned frets these lean point by point with the frets; barbed wire turns
to their angle and dots move onto the line between them. Every style but
dots gets the sheet program for its pieces (`Fretboard_inlay_pieces.nc`).
