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

## Current limitations

- The generated loft uses sampled polygon sections rather than exact B-spline
  or circular wires.
- Neck-to-headstock and neck-to-heel transition surfaces are not included.
- Fret slots follow the sampled polygon surface rather than an exact circular
  sweep.
- Scripts must be visually inspected in FreeCAD before any CAM work.
