# Three-dimensional neck-back surface

`NeckBackSurface` is the first backend-independent 3D geometry in
CNCguitarwizard.

The surface is sampled through five exact longitudinal references:

1. nut;
2. fret 1 at 17 mm wood depth;
3. fret 12 at 19 mm wood depth;
4. fret 24 at 20 mm wood depth;
5. the end of the 63 mm heel at the same 20 mm depth.

Each station uses the same Wizard-inspired superellipse while its width and
depth change along the neck. Adjacent station rows are connected with
immutable quad faces. After fret 24, the heel remains parallel at 56 mm wide
and retains its constant 20 mm wood depth.

```python
from cncguitarwizard.geometry.neck import NeckBackSurface, NeckOutline

outline = NeckOutline(609.6, 24, 42.0, 56.0, 56.0, 63.0)
surface = NeckBackSurface(
    neck_outline=outline,
    first_fret_thickness=17.0,
    twelfth_fret_thickness=19.0,
    final_fret_thickness=20.0,
)
```

`NeckBackSurface` itself describes wood below the fretboard. The
Prototype001 preset converts the requested total 17 mm and 19 mm dimensions
to 11 mm and 13 mm wood depths by subtracting its 6 mm fretboard. The heel
remains 20 mm of wood as originally specified.

Prototype001 uses a compact 12 mm headstock-root transition. At the nut, its
center remains at the rectangular headstock reference while the broad
D-profile shoulders extend 12 mm toward the headstock. The default local back
swell is zero; an optional swell can be added only when needed. At the body end,
Prototype001 uses a
45 mm tangent-controlled blend from the D profile to the heel section. The
D-shaped sections widen, deepen, and flatten through several superelliptical
intermediate profiles until they enter the straight heel. The heel starts
50 mm before fret 24 and ends 4 mm after fret 24, producing a 54 mm long
mounting region with a 20 mm center depth.
In plan view, the heel continues the fretboard taper from its local starting
width to the 56 mm end width instead of forming a rectangle.

The shaped neck does not meet the heel through a separate nose, fillet, or
triangular bevel. Cubic Hermite depth interpolation controls the centerline
depth, while quintic longitudinal blending progressively changes each
cross-section from the playing D into a rounded lead-in for the heel. The
remaining 54 mm heel mounting region retains the same sampled loft topology required by
FreeCAD: its central mounting area is flat in the longitudinal direction and
almost flat across its width, with only small rounded relief at the outer side
edges. The transition and heel belong to one loft, so no separate heel solid,
boolean seam, or overlap step is introduced.
Prototype001 adds a 1.5 mm inward longitudinal scoop. The scoop is zero with
zero slope at both transition ends, so it reverses the visible hump without
introducing a kink at the playing neck or heel. Its magnitude is scaled by the
remaining depth to the heel plane; it therefore never reaches that plane early
or creates a flat segment before the transition ends.

The two root regions are also tapered laterally. At the headstock, the outer
shoulders retain the D profile for an additional configurable distance toward
the headstock, while the center remains at the nut. The FreeCAD exporter
replaces that part of the headstock with a matching transition loft, so these
are physical surfaces rather than hidden overlap. At the heel, the center of the rounded runout starts earlier than
the side edges, creating the broad Strat-inspired root ahead of the flat
mounting block. Both controls only reshape the runout; neither one creates a
second solid or reduces the flat bolt-on area.

The neck wood begins 5 mm before the fretboard at the headstock side. This
horizontal shelf provides the reserved space for the nut while keeping the
scale origin and all fret locations at the fretboard start.

The nut transition uses cubic smoothstep interpolation. The heel root profile uses
quintic smootherstep interpolation so both its slope and curvature approach
zero at the adjoining reference sections.

The Prototype001 playing section uses exponent `2.0`, producing an elliptical
profile instead of the earlier flat-backed `3.5` D profile. The back curve
therefore begins directly at each fretboard side and remains continuously
rounded through the centerline.

The default mesh contains eight longitudinal segments in each reference
region and 33 points across every D-profile section. It is intended as a
deterministic interchange surface. The FreeCAD backend uses these rows as
loft sections to create the complete neck-and-heel BREP solid.
