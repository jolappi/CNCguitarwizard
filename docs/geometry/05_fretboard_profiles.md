# Fretboard profiles

The separate fretboard is represented in two complementary directions.

## Longitudinal side profile

`FretboardSideProfile` describes the centerline thickness from the nut to the
final fret. Prototype001 uses a constant 6 mm center thickness.

## Radius cross-section

`FretboardCrossSection` describes the circular playing surface over a flat
underside. Prototype001 uses a 430 mm radius.

For a section width `w` and radius `r`, the surface drop from center to edge is:

```text
sagitta = r - sqrt(r² - (w / 2)²)
edge_thickness = center_thickness - sagitta
```

At the 56 mm-wide end of the board:

```text
radius             430.000 mm
center thickness     6.000 mm
edge thickness       5.087 mm
```

```python
from cncguitarwizard.geometry.fretboard import FretboardCrossSection

section = FretboardCrossSection(
    width=56.0,
    radius=430.0,
    center_thickness=6.0,
)
```

The sampled arc is a backend-independent approximation used for previews.
Future CAD backends can reconstruct an exact circular edge from the same
radius, width, and thickness values.
