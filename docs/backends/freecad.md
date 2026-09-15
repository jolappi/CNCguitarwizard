# FreeCAD backend

The first FreeCAD backend produces deterministic standalone Python source.
CNCguitarwizard itself does not import FreeCAD, so geometry and tests remain
usable on systems without a FreeCAD installation.

```python
from pathlib import Path

from cncguitarwizard.backends.freecad import FreeCADScriptExporter

exporter = FreeCADScriptExporter()
source = exporter.render_neck_back(neck_surface)
exporter.write_script(Path("Prototype001_Neck.FCMacro"), source)
```

Optional output paths make the generated script save the editable FreeCAD
document and export the resulting solid as STEP:

```python
source = exporter.render_neck_back(
    neck_surface,
    fcstd_path=Path("/output/Prototype001_Neck.FCStd"),
    step_path=Path("/output/Prototype001_Neck.step"),
)
```

Use absolute output paths when the script may be launched from different
working directories. The exporter validates `.FCStd`, `.step`, and `.stp`
suffixes before generating the script.

Run the generated file inside FreeCAD. It:

1. creates closed polygon wires from every 3D profile row;
2. lofts the wires as a solid with `Part.makeLoft`;
3. places the result in a `Part::Feature`;
4. recomputes the document.

Every loft and boolean operation is checked with FreeCAD's `isNull()` and
`isValid()` methods. A failed operation reports its stage, such as
`truss-rod cut`, `fret-slot cut`, or `headstock-to-neck fusion`.

The fretboard exporter follows the same process, closing every radiused
section against its flat underside.

## Neck assembly

`render_neck_assembly()` places the neck back and fretboard in one FreeCAD
document as separate `Part::Feature` objects:

```python
source = exporter.render_neck_assembly(
    neck_surface,
    fretboard_surface,
    fcstd_path=Path("/output/Prototype001.FCStd"),
    step_path=Path("/output/Prototype001.step"),
)
```

The editable FreeCAD document preserves both objects separately. A requested
STEP file exports both solids together, without applying a boolean union.
This makes the joint at the shared `Z = 0` plane easy to inspect before later
manufacturing operations are introduced.

The fretboard's nut-end corners receive the same symmetric R8 mm rounding as
the two-dimensional outline. The generated FreeCAD script selects the two
vertical nut-corner edges immediately after lofting the fretboard and applies
the fillet before any fret-slot cuts. `nut_corner_radius` defaults to 8 mm and
is validated against half the nut width.

The neck and heel are created by one uninterrupted loft ending 4 mm after
fret 24. Its 54 mm heel region is 20 mm deep, and its sides continue the
fretboard taper to the 56 mm end width. No separate heel prism is fused to
the neck, so FreeCAD has no intermediate face boundary to display.

The neck-to-heel transition is part of the backend-independent 3D geometry,
not a FreeCAD edge fillet or separate rounded solid. Prototype001 uses
multiple superelliptical sections through a 35 mm loft. The sections widen,
deepen and flatten into the heel rows without a linear bevel or boolean
boundary. The generated script applies an adaptive 3 mm fillet to the
remaining transverse heel-transition edge, removing its sharp visible corner
while retaining one continuous lofted neck solid.
For neck-end inspection, the backend can cut a U-shaped boundary immediately
after lofting the neck: both outer neck-end corners remain on the original end
line and the middle retracts toward the heel. This changes only the boundary; the sampled
D-profile rows and the fixed 5 mm nut shelf remain exactly as generated. A
vertical circular cutter passes through the two outer corners and the chosen
centre depth, avoiding the invalid BREP created by a tangent U-prism.
After refining that cut, a 2 mm cylindrical fillet rounds only the two lateral
U arcs where the D profile rises into the cylinder. The U nose and both outer
endpoints deliberately remain unmodified; the fixed 5 mm nut shelf remains
unchanged.

OpenCASCADE can reject a radius on a particular BREP edge. The generated
script therefore tries 100%, 75%, 50%, and 25% of each requested radius and
retains the tangent base transition if none is valid. Every failed attempt
and the applied radius are written to `freecad.log`; a rejected optional
fillet does not abort FCStd or STEP generation.

Passing a `HeadstockSolid` adds the modern tapered headstock as a third
`Part::Feature`. Its configurable 14–16 mm thickness is extruded normal to
the 8-degree face, and the optional STEP output includes all three solids.

Passing the matching `TunerLayout` cuts all six 10 mm holes through the
headstock:

```python
source = exporter.render_neck_assembly(
    neck_surface,
    fretboard_surface,
    headstock=headstock,
    tuner_layout=tuner_layout,
)
```

The cutters follow the headstock normal rather than the global Z axis, so the
finished bores remain perpendicular to the 8-degree face. Each cutter extends
1 mm beyond both faces to make the boolean operation unambiguous.

Each hole also receives a 45-degree entry chamfer on the headstock face.
`tuner_chamfer_depth` defaults to 0.2 mm, accepts other safe values, and can
be set to zero to disable the chamfer.

For manufacturing output, `join_headstock_to_neck=True` fuses the angled
headstock into the neck-back solid after tuner-hole cutting. The editable
inspection mode remains the default and keeps the two objects separate.
Fusion requires matching nut widths, and STEP output contains only the fused
wood solid plus the separate fretboard.

An existing `TrussRodChannel` can be applied as a rectangular subtraction
from the neck solid:

```python
source = exporter.render_neck_assembly(
    neck_surface,
    fretboard_surface,
    truss_rod_channel=channel,
)
```

The backend verifies that the channel and neck use the same outline and that
the requested depth leaves wood below the channel floor. The current
subtraction models the specified 440 × 6 × 9 mm straight channel; a separate
spokewheel access pocket will follow once its hardware dimensions are known.

An aligned `FretLayout` enables the 24 fret-slot cuts:

```python
source = exporter.render_neck_assembly(
    neck_surface,
    fretboard_surface,
    fret_layout=fret_layout,
    fret_slot_width=0.6,
    fret_slot_depth=2.7,
)
```

Each slot follows the sampled 430 mm playing-surface radius instead of using
a single flat-bottomed box. The backend validates scale length, fret count,
slot positions, and remaining material below the 2.7 mm slot floor.
Each cut uses one continuous closed profile across the fretboard, avoiding
the invalid internal seams produced by fusing many small cutter prisms.
The cutter extends 0.2 mm above the playing surface and 1 mm beyond both
fretboard edges. These overcuts avoid coincident boolean faces without
changing the requested 2.7 mm finished slot depth.

## Fretboard inlays

Passing an `InlayLayout` cuts each position marker as a flat-bottomed pocket
into the radiused playing surface. Every marker outline is extruded from
above the surface down to its floor, so the pocket depth is measured from the
crown of the fretboard at the marker's own position. The backend checks that
the layout belongs to the same `FretboardSurface` and that every marker stays
inside the fretboard outline.

## Solid body

Passing a `BodySolid` adds the body as a fourth `Part::Feature`, `Body` by
default:

```python
source = exporter.render_neck_assembly(
    neck_surface,
    fretboard_surface,
    body=body,
    body_object_name="Body",
)
```

The outline is extruded from `Z = 0` down by the slab thickness, so the body's
top face meets the neck-back surface's own `Z = 0` plane and the neck heel
sits in the neck-pocket cavity. The script then cuts, in order:

1. the neck pocket, both pickup routes, the optional sustain-block cavity, and
   every extra cavity straight down from the top face;
2. the control, switch and battery cavities (when present) upward from the
   back face, each followed by its shallow cover recess;
3. pivot-stud holes (when the bridge has any) and every `DrilledHole` as
   vertical cylinders from the top face — a hole as deep as the slab is
   overcut at both ends so it breaks out cleanly;
4. the jack bore as a horizontal cylinder at half the slab thickness.

Every cavity profile is overcut by 0.6 mm above its entry face so no boolean
operation meets a coincident face. A requested STEP file includes the body.

## Current limitations

- The generated loft uses sampled polygon sections rather than exact B-spline
  or circular wires.
- The headstock root replaces a trimmed section of the angled headstock with a
  sampled, tangent-continuous loft; visually inspect it in FreeCAD before CAM
  work.
- Fret slots follow the sampled polygon surface rather than an exact circular
  sweep.
- The body is a flat slab: arm and belly contours, edge round-overs, and the
  cover plates themselves are not modelled.
- Scripts must be visually inspected in FreeCAD before any CAM work.
