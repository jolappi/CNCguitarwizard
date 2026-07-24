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

The default mesh contains eight longitudinal segments in each reference
region and 33 points across every D-profile section. It is intended as a
deterministic interchange surface. The FreeCAD backend uses these rows as
loft sections to create the complete neck-and-heel BREP solid.
