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

The shaped neck loft ends 50 mm before fret 24 and is fused to an exact
rectangular heel block that ends 4 mm after fret 24. The resulting mounting
block is 54 mm long and 20 mm deep. Its sides continue the fretboard taper
to the 56 mm end width rather than forming a rectangle. The fretboard ends
separately 4 mm after fret 24. Keeping the heel block out of the spline loft
prevents ripples on its flat mounting faces.

Prototype001 applies a configurable 3 mm fillet to the lateral joint edges
where the shaped neck meets the heel and angled headstock. These fillets
remove the remaining sharp side-view corners without rounding the heel's
flat mounting underside.

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

## Current limitations

- The generated loft uses sampled polygon sections rather than exact B-spline
  or circular wires.
- Neck-to-headstock and neck-to-heel transition surfaces are not included.
- Fret slots follow the sampled polygon surface rather than an exact circular
  sweep.
- Scripts must be visually inspected in FreeCAD before any CAM work.
