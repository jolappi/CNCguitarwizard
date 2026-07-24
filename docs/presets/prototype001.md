# Prototype001 preset

`Prototype001Parameters` is the single source of dimensions for the first
complete CNCguitarwizard neck. Its defaults reproduce the locked 24-inch,
24-fret design, while individual fields remain configurable through
`dataclasses.replace`.

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
- the 430 mm radius fretboard;
- 24 radius-following fret slots;
- the 440 × 6 × 9 mm truss-rod channel;
- the 8-degree, 14–16 mm thick headstock;
- the six-hole 3+3 tuner layout.

The FreeCAD convenience export applies all current manufacturing features and
joins the headstock to the neck by default. Core geometry remains independent
of FreeCAD.
