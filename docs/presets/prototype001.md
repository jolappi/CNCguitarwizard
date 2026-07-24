# Prototype001 preset

`Prototype001Parameters` is the single source of dimensions for the first
complete CNCguitarwizard neck. Its defaults reproduce the locked 24-inch,
24-fret design, while individual fields remain configurable through
`dataclasses.replace`.

`first_fret_thickness=17.0` and `twelfth_fret_thickness=19.0` are complete
centerline thicknesses including the 6 mm fretboard. The generated neck-wood
depths are therefore 11 mm and 13 mm. `heel_thickness=20.0` remains a wood
dimension below the fretboard, giving 26 mm total center thickness at the
heel.

```python
from dataclasses import replace
from pathlib import Path

from cncguitarwizard.backends.freecad import FreeCADScriptExporter
from cncguitarwizard.presets import Prototype001Parameters

parameters = replace(
    Prototype001Parameters(),
    headstock_thickness=15.0,
)
geometry = parameters.build()

source = FreeCADScriptExporter().render_prototype001(
    geometry,
    fcstd_path=Path("/output/Prototype001.FCStd"),
    step_path=Path("/output/Prototype001.step"),
)
```

Building the preset creates and cross-validates:

- the full neck and 63 mm heel;
- a fretboard that ends flush with the back of that heel;
- a 6 mm nut shelf immediately before the fretboard;
- a planar 20 mm heel underside with a 35 mm neck-to-heel transition;
- a rounded exponent-2 neck back beginning directly at the fretboard sides;
- the 430 mm radius fretboard;
- 24 radius-following fret slots;
- the 440 × 6 × 9 mm truss-rod channel;
- the 8-degree, 14–16 mm thick headstock;
- a 30 mm headstock-to-neck volute matched to that headstock thickness;
- the six-hole 3+3 tuner layout with at least about 8 mm of side-edge wood.

The FreeCAD convenience export applies all current manufacturing features and
joins the headstock to the neck by default. Core geometry remains independent
of FreeCAD.
