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

## Current limitations

- The generated loft uses sampled polygon sections rather than exact B-spline
  or circular wires.
- Neck-to-headstock and neck-to-heel transition surfaces are not included.
- Truss-rod subtraction and fret-slot cuts are not yet applied.
- Scripts must be visually inspected in FreeCAD before any CAM work.
