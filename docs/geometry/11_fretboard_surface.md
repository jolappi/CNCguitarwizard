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

## Scallops

`FretboardScallops` (`geometry.fretboard.scallops`) hollows the surface
between the frets, as on a scalloped board: every fret space from
`from_fret` on to the last fret (0: from the nut) is `depth` deep at its
middle, a circular arc along the neck between the `land` left flat either
side of each fret line (the fret's foot sits on it), eased into the land
over `SCALLOP_EASE` (15 %) of it at either end so it meets the land with
no ridge, as deep right across the board, so the hollow follows the
radius. Slanted or fanned frets lean
their spaces with them. `depth_at(x, y)` is how far below the radiused
surface it lies (0 on the lands and outside the scalloped spaces);
`rows()` the surface's own rows (the nut, every fret, the board's end)
with `SCALLOP_ROWS` (16) spans of rows more across every scallop, each
point lowered by it.

It refuses a start outside the frets, a depth not finite and positive, a
land not finite and non-negative, a space no more than twice its depth
long between its lands, and a scallop leaving less than `SCALLOP_FLOOR`
(1.5 mm) of the board under it at its edge. Prototype001 makes one with
`fretboard_scalloped` (`fretboard_scallop_from_fret` 15,
`fretboard_scallop_depth` 2 mm, `fretboard_scallop_land` 1.5 mm). The
scallops are cut after the inlays are set, through them, so where a
marker lies under one every pocket is cut `SCALLOP_INLAY_KEEP` (1 mm)
deeper than the deepest scallop over a marker, if `inlay_depth` is not
already (3 mm under 2 mm scallops): one depth, the pieces still from one
sheet. FreeCAD lofts the board, and its binding, through the
hollowed rows; the fret slots still follow the frets' own rows.
