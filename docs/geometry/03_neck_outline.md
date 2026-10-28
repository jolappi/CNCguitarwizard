# Neck outline

`NeckOutline` creates the backend-independent top view of the neck shaft and
bolt-on heel.

For Prototype001 the locked dimensions are:

| Parameter | Value |
| --- | ---: |
| Scale length | 609.6 mm |
| Frets | 24 |
| Nut width | 42 mm |
| Width at fret 24 | 56 mm |
| Heel width | 56 mm |
| Heel length | 63 mm |

The taper ends at the calculated position of the final fret. The heel then
continues at a constant width for the requested length.

## A heel wider than the taper

A `heel_width` wider than the taper reaches at the heel end, given
`heel_flare_length`, flares the neck out to it over that length ahead of
the heel end (`heel_flare`, a `HeelFlare`): the extra width grows as the
square of the way along, from nothing where it begins (so the side has no
kink there) to all of it at the heel end, and the outline's sides follow
it (`HEEL_FLARE_SAMPLES` points each). `half_width_at(x)` gives the
neck's half-width anywhere along it, flare and all; the neck's back, its
truss rod's clearance, its side profile, the neck pocket and the neck
bolts' walls all take it from there. The fretboard flares with it, flush
with the neck's sides (`FretboardSurface(heel_flare=...)`,
`half_width_at`): its rows, its plan outline (through the rows along the
flare, `outline_rows`), its binding, its slots (`FretLayout(heel_flare=...)`),
its markers and scallops. The Prototype001 preset flares over the heel's
mounting block (`heel_mounting_length`, 54 mm); a heel as wide as the
final fret (every instrument's default) does not flare at all.

```python
outline = NeckOutline(609.6, 22, 42.0, 56.0, 58.0, 4.0, heel_flare_length=54.0)
assert round(2 * outline.half_width_at(outline.heel_end_position), 6) == 58.0
assert outline.heel_flare.start == outline.heel_end_position - 54.0
```

## A round heel end

The heel ends square across the neck (a Telecaster's), or round as a
Stratocaster's does: given `heel_end_radius` (and `heel_corner_radius`),
its end is an arc of that radius across it, through the end on the
centre, blended into each side by a fillet (`heel_end_curve`). The
Prototype001 preset's `neck_heel_end="round"` uses Fender's: a 127 mm
(5 in) arc and 6.35 mm (1/4 in) corners, so the end lies about 8.3 mm
short at the corners and 1.4 mm at a neck bolt 19 mm off the centre
(`heel_end_inset`). The outline is the square one cut back to it
(`clip_to_heel_end`, the end being convex), so on a short heel the round
cuts into the taper's end too; `trimmed` cuts a fretboard back the same
way where it reaches the heel's end.

```python
outline = NeckOutline(609.6, 24, 42.0, 56.0, 56.0, 4.0, 127.0, 6.35)
end = outline.last_fret_position + outline.heel_length
assert max(p.x for p in outline.boundary) == end
assert round(outline.heel_end_inset(28.0), 2) == 8.31
```

The neck pocket follows it its clearance out (the arc and the corners'
radii that much larger, its end still touching the heel's on the
centre), and the neck bolts keep their end wall to the heel's end beside
them. In FreeCAD the neck, the fretboard and its binding are cut by a
prism of what lies past the end, set `HEEL_TRIM_SLACK` (0.02 mm) out past
the heel's sides and its curve as far in from the neck's end, so its faces
cross the neck's rather than touch them (a curve out past the end left
slivers of the loft's flat end by its apex, which a later boolean there
failed on).

```python
from cncguitarwizard.geometry.neck import NeckOutline

outline = NeckOutline(
    scale_length=609.6,
    fret_count=24,
    nut_width=42.0,
    last_fret_width=56.0,
    heel_width=56.0,
    heel_length=63.0,
)
```

The outline is a top-view manufacturing reference. Neck thickness, fretboard
radius, headstock angle, and back-profile surfaces are separate geometry
layers added later.
