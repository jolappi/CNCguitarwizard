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

Prototype001 adds a 30 mm headstock volute. At the nut, its rectangular
underside matches the selected 14–16 mm headstock thickness, then changes
smoothly into the first-fret D profile. At the body end, a 35 mm transition
changes the D profile into a rectangular heel. Its flat section begins 50 mm
before fret 24 and ends 4 mm after it, producing a 54 mm long mounting block
with a planar 20 mm underside for reliable seating in a bolt-on neck pocket.
During the preceding 35 mm transition, the side width also curves smoothly
out to the full 56 mm heel width. The block therefore has no lateral step.

The neck wood begins 6 mm before the fretboard at the headstock side. This
horizontal shelf provides the reserved space for the nut while keeping the
scale origin and all fret locations at the fretboard start.

Both transitions use cubic smoothstep interpolation. Their slopes reach zero
at the adjoining reference sections instead of producing abrupt thickness or
profile changes.

The Prototype001 playing section uses exponent `2.0`, producing an elliptical
profile instead of the earlier flat-backed `3.5` D profile. The back curve
therefore begins directly at each fretboard side and remains continuously
rounded through the centerline.

The default mesh contains eight longitudinal segments in each reference
region and 33 points across every D-profile section. It is intended as a
deterministic interchange surface. The FreeCAD backend uses these rows as
loft sections to create the complete neck-and-heel BREP solid.
