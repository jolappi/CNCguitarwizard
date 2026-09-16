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

- the fretboard ending 4 mm after fret 24;
- a configurable `heel_mounting_length` for the complete flat, tapered
  bolt-on block; Prototype001 uses 54 mm (50 mm before fret 24 plus its
  4 mm end extension) and rejects a mounting block shorter than 40 mm;
- a configurable 45 mm `heel_root_length` multi-section D-to-heel loft with
  rounded shoulders; this runout ends before the complete flat mounting block;
- a 1.5 mm inward heel scoop with tangent endpoints;
- a 12 mm deep, backend-applied U-shaped neck-end trim: the two outer neck-end
  corners remain on the original end line while the centre of the back
  boundary moves smoothly 12 mm toward the heel. Its circular cutting arc
  passes exactly through those outer corners and does not change any D-profile
  section or add outward material. A 2 mm cylinder-side fillet rounds only
  the two vertical U side walls at the outer nut corners, rather than the
  central U arc;
- a fretboard that ends flush with the back of that heel;
- a fixed 5 mm nut shelf immediately before the fretboard; the scarf-root
  runout cannot alter this seat. Within that fixed shelf the center stays
  flat at the nut, while the two side shoulders transition progressively into
  the normal D profile before they reach the U-cylinder blend;
- a planar 20 mm heel underside after the rounded front;
- a rounded exponent-2 neck back beginning directly at the fretboard sides;
- the 430 mm radius fretboard;
- 24 radius-following fret slots;
- the 440 × 6 × 9 mm truss-rod channel;
- the 8-degree, 14–16 mm thick headstock;
- a configurable 45 mm `headstock_root_length` followed by a smooth taper to
  the tip, giving the plan-view sides a Strat-inspired triangular runout
  without adding volume below the thumb;
- a configurable 5–30 mm `headstock_volute_length`; Prototype001 uses a
  smooth 30 mm headstock-to-neck transition;
- a zero-depth `headstock_volute_depth` by default, leaving no outward swell
  below the thumb unless one is explicitly requested;
- a separate 15 mm `heel_root_center_extension`, which makes the center of
  the heel runout lead smoothly into the neck while the full 54 mm mounting
  block stays planar and intact;
- the six-hole 3+3 tuner layout with at least about 8 mm of side-edge wood;
- 2 mm deep barbed-wire position markers (`InlayLayout`) at frets 3, 5, 7, 9,
  15, 17, 19 and 21, with double markers at 12 and 24;
- a 44 mm flat-slab left-handed body (`BodySolid`) digitised from the user's
  `assets/reference/omarunko.dxf`: the drawing's own outline, a neck pocket
  derived from the neck's own taper, humbucker routes with mounting ears, an
  interchangeable bridge (`body_bridge`: Kahler 7300 by default, Floyd Rose,
  Tune-o-matic or hardtail), rear control and switch cavities with 2 mm cover recesses,
  pot and switch shaft holes, pickup-screw recesses, and the jack bore — see
  [Solid body](../geometry/12_body.md).

The FreeCAD convenience export applies all current manufacturing features and
joins the headstock to the neck by default. Core geometry remains independent
of FreeCAD.
