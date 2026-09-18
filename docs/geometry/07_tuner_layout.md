# Tuner-hole layout

Prototype001 uses six 10 mm tuner holes in a symmetric 3+3 arrangement by
default. `headstock_style` chooses the arrangement:

| `headstock_style` | Bass side | Treble side | Layout |
| --- | ---: | ---: | --- |
| `3+3` | 3 | 3 | the given stations and offsets, mirrored |
| `6_inline` | 6 | 0 | a row on the bass side, every post on its string's line, the edge 15 mm outside it |
| `6_inline_reverse` | 0 | 6 | the same row on the treble side |
| `4+2` | 4 | 2 | a row of four on the bass edge, the pair at the root on the treble edge (Music Man-like) |
| `2+4` | 2 | 4 | the same, mirrored |

**Stations.** A row is spaced `tuner_inline_spacing` (25.4 mm) apart from
`tuner_inline_first_distance` (50 mm); a 4+2 pair sits at the root on the
other edge, staggered half a station opposite the row's first two. The
headstock grows past `headstock_length` whenever the last tuner plus its
clearance and `tuner_tip_margin` needs it (195 mm for six in line; 4+2
fits the 150 mm default).

**Straight strings.** In the row styles every post sits on its own
string's straight continuation past the nut — the bridge-to-nut line from
`bridge_string_spacing` (10.5 mm) and `nut_string_spacing` (7 mm) — with
the post (`tuner_post_diameter` 6 mm) its radius outboard of the string, so
no string bends at the nut. The row takes its side's strings nearest first
(low E to the first bass post) and the pair the other side's outermost
strings, outermost nearest the nut. A six-in-line row therefore runs
diagonally across the centreline (unlike a Strat's, whose far strings bend
at the nut), and a 4+2 row converges toward it with the G post almost on
it. A 3+3 keeps `tuner_side_offsets`: with both rows at the same stations,
straight strings would put the D and G posts too close together.

**Edges follow the holes, outside a wood reserve.** Each headstock edge
that carries tuners is the straight line fitted through those holes
`tuner_edge_offset` (15 mm) further out, from the shoulder to the tip, so
on a 3+3 every hole sits the same distance from its edge (within about
0.3 mm; its holes are not quite collinear). The row styles keep more wood
than that so a traditional outline can still be carved from the blank
(`HEADSTOCK_RESERVES`, least half-widths at the shoulder and tip):

| Style | Row side | Other side | Room for |
| --- | --- | --- | --- |
| `6_inline` / `_reverse` | 36 / 0 mm (the edge follows the row) | 35 / 60 mm | a Strat's treble lobe beside the diagonal row |
| `4+2` / `2+4` | 36 / 15 mm | 40 / 30 mm | a Music Man's root lobe and narrow tip |

Either edge's tip end is then pushed out if a post of the other row has
crossed the centreline toward it, keeping `tuner_edge_clearance` outside
every hole. `headstock_shoulder_width`, `headstock_shoulder_shift`,
`headstock_tip_width` and `headstock_tip_shift`, when set, override the
resolved ends. `TunerLayout` accepts a `sides` tuple naming each station's
side (an offset may then be negative for a post past the centreline);
without it every station is mirrored onto both sides.

`headstock_bass_side` says which side of the centreline carries the low E:
`-y` on the left-handed Prototype001 body (the long-horn side), `+y` for a
right-handed one; `HeadstockPlan.bass_sign` and every `TunerHole.side`
follow it, so "bass" always means the physical bass side.

## 3+3 layout

| Position from nut | Centerline offset |
| ---: | ---: |
| 55 mm | ±16 mm |
| 85 mm | ±13 mm |
| 110 mm | ±10 mm |

The rows converge toward the tapered tip. The layout validates:

- nut and tip clearance;
- side-edge clearance;
- hole-to-hole clearance;
- station ordering;
- finite, positive dimensions.

Prototype001 requires at least approximately 8 mm of wood between each 10 mm
hole edge and the tapered side edge. The closest calculated clearance is
about 8.771 mm. Nut, tip, and hole-to-hole clearances remain validated
separately; the tuner-body footprint and washer diameter must still be checked
against the chosen hardware.

```python
from cncguitarwizard.geometry.neck import HeadstockPlan, TunerLayout

headstock = HeadstockPlan(150.0, 42.0, 30.0, 65.0, 40.0)
layout = TunerLayout(
    headstock,
    hole_diameter=10.0,
    station_distances=(55.0, 85.0, 110.0),
    side_offsets=(16.0, 13.0, 10.0),
    minimum_edge_clearance=8.0,
)
```
