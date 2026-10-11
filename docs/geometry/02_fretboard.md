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
| `barbed_wire_2` | A knot of barbed wire across the board — two twisted strands, three coils, four barbs — traced from the builder's drawing as one piece (`BARBED_WIRE_2_OUTLINE`, see below); one at every marker fret, 12 and 24 too |
| `dot` | Round dots (`inlay_dot_diameter`, 6 mm); two at 12 and 24 |
| `block` | Gibson blocks |
| `trapezoid` | Les Paul trapezoids: long at the bass edge, the treble edge `TRAPEZOID_SHORT_SIDE` (55 %) of it |
| `sharktooth` | Jackson sharktooth: a triangle across the board at its bridge-side end and along the bass edge, its point at the treble edge |
| `parallelogram` | Leaning blocks, the treble edge `PARALLELOGRAM_LEAN` (35 % of the length) toward the nut |
| `diamond` | A diamond, its points on the centreline and at the edges' margin |
| `split_block` | Gibson split blocks: a block split along its diagonal (treble front corner to bass back corner) into two pieces `SPLIT_BLOCK_GAP` (1.5 mm) apart |
| `runes` | A rune of the Elder Futhark at every marker fret, chosen for each (`inlay_runes`) — see below |
| `cross` | Latin crosses, upright as the guitar is played (as a rune stands): the long arm across the board, its head toward the bass edge |
| `iron_cross` | Iron crosses (cross pattée): four arms flaring from a narrow waist |
| `custom` | Your own shape (`inlay_points`), drawn once and fitted to every fret space — see below |

`barbed_wire_2` spans `BARBED_WIRE_2_SPAN` (80 %) of the board's width at
its fret, centred, its barbs reaching along the neck; where the fret
space is too short for that (the last frets) the knot is drawn smaller,
its barbs `BARBED_WIRE_2_FRET_CLEARANCE` (1.5 mm) from the frets either
side. Its outline (`geometry.fretboard.barbed_wire_2`) was traced once
from the drawing `barbedwiretrue.dxf` (85 × 25 mm, 13 pieces): the
pieces joined into one so it is one piece to cut and glue, thickened,
a backbone run along the wire and the slits and spurs a 1 mm end mill
cannot cut taken off, so at these sizes the 1 mm inlay cutter cuts each
knot whole. The inlay editor starts from a coarser copy of it (43
corners, `BARBED_WIRE_2_EDITOR_OUTLINE`).

The symbol styles (`SYMBOL_STYLES`: `runes`, `cross`,
`iron_cross`) set one symbol in every marker fret's space, 12 and 24
too, as large as it fits: at most `SYMBOL_SPAN` (60 %) of the board's
width across it and `CUSTOM_CLEARANCE` (1 mm) from the frets either side.
Its thinnest part (a rune's stroke, a cross's arm or waist) must stay
`SYMBOL_THINNEST` (1.1 mm) wide for the 1 mm inlay cutter; a fret space
too short for that is refused. The crosses' corners are rounded 1 mm as
the blocks' are. With slanted or fanned frets a symbol turns to their
angle, as barbed wire does. The inlay editor starts from the first
marker's symbol shrunk whole inside the limits a drawn shape keeps (its
shape kept).

### Runes

`runes` sets a rune of the Elder Futhark (`geometry.fretboard.runes`) in
every marker fret: `inlay_runes` names them nut first, starting over when
there are more frets; empty, the default set (`DEFAULT_RUNES`:
fehu, uruz, thurisaz, ansuz, algiz, sowilo, tiwaz, ehwaz, mannaz, othala). In the inlay editor each marker fret has
its own choice, each rune with what it stands for. Each rune is drawn as
a few straight strokes (its stave and branches) with a round pen
`RUNE_STROKE` (12 %) of its height wide: the strokes' outline is traced
where the distance to them is half that (`stroke_outlines`, marching
squares on a grid `RUNE_CELL` of the height apart, thinned within
`RUNE_TOLERANCE`). An area a rune closes in (Thurisaz's thorn,
Berkano's and Dagaz's triangles, Ingwaz's diamond) is filled, as an
inlay piece cannot hold an island of wood; Jera's two hooks are two
pieces. A rune stands with its top toward the bass edge, read from the
front with the guitar played (its nut on the right of a right-handed
guitar): turned half round by the bass side, never mirrored, so in the
inlay editor and the drawings (the nut on the left) it is upside down.

| Rune | Name | Stands for |
| --- | --- | --- |
| ᚠ | `fehu` | wealth, cattle |
| ᚢ | `uruz` | strength, the aurochs |
| ᚦ | `thurisaz` | the thorn, protection, a giant |
| ᚨ | `ansuz` | Odin, wisdom, the spoken word |
| ᚱ | `raidho` | the journey, the ride |
| ᚲ | `kaunan` | the torch, knowledge |
| ᚷ | `gebo` | a gift, partnership |
| ᚹ | `wunjo` | joy, harmony |
| ᚺ | `hagalaz` | hail, a sudden change |
| ᚾ | `naudiz` | need, endurance |
| ᛁ | `isa` | ice, stillness |
| ᛃ | `jera` | the year, the harvest |
| ᛇ | `eihwaz` | the yew, defence, endurance |
| ᛈ | `perthro` | fate, mystery |
| ᛉ | `algiz` | protection, the elk |
| ᛊ | `sowilo` | the sun, victory, success |
| ᛏ | `tiwaz` | Tyr, victory, honour |
| ᛒ | `berkano` | the birch, growth, new beginnings |
| ᛖ | `ehwaz` | the horse, movement, trust |
| ᛗ | `mannaz` | mankind, the self |
| ᛚ | `laguz` | water, the flow of life |
| ᛜ | `ingwaz` | Ing, fertility, completion |
| ᛞ | `dagaz` | the day, dawn, breakthrough |
| ᛟ | `othala` | heritage, home, ancestry |

Every style but the barbed wires, dots and symbols spans the board between its frets
(`BOARD_STYLES`): one per listed fret, `inlay_block_length_fraction`
(60 %) of the fret spacing long, `inlay_block_edge_margin` (5 mm) inside
each board edge with the board's taper, its corners rounded 1 mm. The
bass side comes from `headstock_bass_side` (`bass_sign`). With slanted or
fanned frets these lean point by point with the frets; barbed wire turns
to their angle and dots move onto the line between them. Every style but
dots gets the sheet program for its pieces (`Fretboard_inlay_pieces.nc`).

### A drawn marker

The `custom` style's shape is drawn once, on the first marker's fret
space, as corners (`inlay_points`, `InlayLayout.custom_points`) joined by
straight lines and rounded 1 mm — but curving through a corner marked
`[along, across, "round"]` (`drawn_polygon`, its sides there sampled,
`CUSTOM_ROUND_SAMPLES`), every point of the curve kept clear as the
corners are: `[along, across]`, `along` 0 at the fret
toward the nut and 1 at the marker's own fret, `across` the share of the
board's half-width there, toward the bass edge (−1 the treble edge, +1
the bass edge). Every listed fret gets one marker, that shape fitted to
its own fret space and to the board's width along it, so the markers
shorten toward the body and widen with the board. Empty, it is a block
(`DEFAULT_CUSTOM_POINTS`). At least three corners, inside the fret space
and the board, sides that do not cross; every corner of every marker must
keep `CUSTOM_CLEARANCE` (1 mm) from the fret slots and the board's edges,
or the build says at which fret it does not. `custom_limits()` gives the
range that fits every marker (the shortest fret space and the narrowest
board decide it), and `InlayLayout.editable_points()` any style's first
marker as such points, held inside that range, so the web app's inlay
editor can start from any style.
