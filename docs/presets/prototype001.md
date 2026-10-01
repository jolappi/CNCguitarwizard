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

## Electric guitar, extended-range guitar or bass

`Prototype001Parameters.for_instrument("electric_guitar")` is the plain
default; `"seven_string_guitar"`, `"eight_string_guitar"` and
`"bass_guitar"` apply `INSTRUMENT_OVERRIDES`:

| Setting | Electric guitar | 7-string | 8-string | Bass guitar |
| --- | --- | --- | --- | --- |
| Strings (`string_count`) | 6 | 7 | 8 | 4 |
| Scale / frets | 609.6 mm / 24 | 647.7 mm (25.5 in) / 24 | 685.8 mm (27 in) / 24 | 863.6 mm (34 in) / 21 |
| Nut / heel width | 42 / 56 mm | 48 / 66 mm | 55 / 76 mm | 38 / 62 mm |
| 1st / 12th fret thickness, heel | 17 / 19 / 20 mm | 17 / 19 / 20 mm | 17 / 19 / 20 mm | 21 / 23 / 22 mm |
| Fretboard radius | 430 mm | 400 mm | 400 mm | 305 mm |
| String spacing nut / bridge | 7 / 10.5 mm | 7 / 10.5 mm | 7 / 10.5 mm | 10 / 19 mm |
| Headstock | 3+3, 10 mm holes | 7 in line (or 4+3 / 3+4) | 8 in line (or 4+4) | 4 in line, 19 mm holes 38 mm apart, 20 mm from the edge |
| Pickups | humbucker + humbucker | stretched 12 mm | stretched 24 mm | Precision Bass (neck) + Jazz Bass (bridge) |
| Bridge | Kahler 7300 | seven-string hardtail | eight-string hardtail (6 screws) | four-string string-through hardtail |
| Body | Design by Jone | opened 12 mm | opened 24 mm | Jazz Bass style body (a drawn mockup) |

The Kahler 7300, Floyd Rose and Tune-o-matic specs are drawn for six
strings (`BRIDGE_MAX_STRINGS`): the build refuses them for more, and the
web form hides them. A hardtail must have a hole per string.

A guitar humbucker or single coil for more than six strings is the
six-string route stretched across the strings by 12 mm per extra string
(`pickups.pickup_stretch`), with its screws spread by the same amount.
The body shapes are drawn for a six-string neck, so `body_widening`
(empty: 12 mm per string past six, `BODY_WIDENING_PER_STRING`) opens the
body along its centreline: each half, with its cavities, pots, switch,
battery box and jack, moves out by half of it (`body_shapes.widened_shape`); the web
editor draws a drawn body the same way. A row headstock opposite three or
four tuners (4+3) stretches `tuner_inline_spacing` in 0.5 mm steps until
every pair of holes keeps `tuner_hole_clearance`.

The bass's long neck pocket takes its four neck bolts 56 mm apart along
the neck (`body_neck_bolt_spacing_x`, 32 mm on a guitar) with 5 mm of
wood to the pocket's end (`body_neck_bolt_end_wall`, 3 mm on a guitar):
the pair at the pocket's mouth sits 63.5 mm ahead of the heel end, near
the body's edge, and the rear pair at 7.5 mm, its ferrules wholly over
the pocket.

Every value stays editable; the bass numbers are labelled starting points
for a common four-string bass. `instrument` records which defaults a set
started from; `string_count` is what the tuners, the hardtail bridge and
the pickups follow. The web form's first control picks the instrument and
reloads the form with its defaults.

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
- the tuner layout chosen by `headstock_style` — 3+3 by default, or a
  6-in-line row (either side) or 4+2 / 2+4 — with at least about 8 mm of
  side-edge wood; a row of tuners lengthens the headstock as needed, every
  post sits on its string's own line, and each edge follows its holes (see
  [Tuner-hole layout](../geometry/07_tuner_layout.md));
- 2 mm deep position markers (`InlayLayout`) at frets 3, 5, 7, 9, 15, 17, 19
  and 21, doubled at 12 and 24: barbed wire by default, or round dots
  (`inlay_style="dot"`, `inlay_dot_diameter`) or Gibson-style tapered blocks
  (`inlay_style="block"`, one per fret, `inlay_block_length_fraction`,
  `inlay_block_edge_margin`);
- a 44 mm flat-slab left-handed body (`BodySolid`) whose silhouette is
  chosen by `body_shape` — a drawn body (spline control points), by
  default the Design by Jone template: the user's own outline digitised
  from `assets/reference/omarunko.dxf` and resampled (the traced outline
  itself is `DesignByJoneShape`) — with the drawing's own cavities: a neck pocket
  derived from the neck's own taper, humbucker routes with mounting ears, an
  interchangeable bridge (`body_bridge`: Kahler 7300 by default, Floyd Rose,
  Tune-o-matic or hardtail), rear control and switch cavities with 2 mm cover recesses,
  an optional rear 9 V battery box with its own cover (`body_battery_box`,
  one battery or two side by side with `body_battery_count`),
  pot and switch shaft holes, pickup-screw recesses, and the jack bore — see
  [Solid body](../geometry/12_body.md).

The FreeCAD convenience export applies all current manufacturing features and
joins the headstock to the neck by default. Core geometry remains independent
of FreeCAD.
