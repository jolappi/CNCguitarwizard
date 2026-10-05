# DXF plan outlines

Every build writes the plan outlines as DXF for other CAD, CAM and laser
programs (`render.dxf`, the build's *Writing the DXF outlines* stage):

| File | What it holds |
| --- | --- |
| `Prototype001_plan.dxf` | The whole instrument as the model lays it out: millimetres, X from the nut toward the tail, Y across the neck (left-handed builds already mirrored) |
| `Prototype001_covers.dxf` | The sheet plates — cavity covers, control plates, the pickguard, a truss-rod cover — side by side for cutting, each with its holes, slots and a label; only when there are plates |

Both are AutoCAD R12 (AC1009) ASCII DXF, the version almost every program
reads, written without any library (`DxfDocument`): closed (or open)
`POLYLINE`s, `CIRCLE`s, `LINE`s and `TEXT`, every entity on a named layer
with its own colour. `$INSUNITS` says millimetres for the programs that
read it; pick millimetres on import otherwise.

## The plan's layers

| Layer | Entities |
| --- | --- |
| `BODY_OUTLINE`, `NECK_OUTLINE`, `HEADSTOCK_OUTLINE`, `FRETBOARD_OUTLINE` | The outlines (the fretboard's reaching under a nut it runs on under) |
| `NECK_THROUGH_BLOCK` | A neck-through's centre block, its sides the glue lines |
| `NUT` | The nut in plan, behind a zero fret where there is one |
| `FRET_SLOTS` | A line per fret slot, the zero fret's first |
| `INLAYS` | Every marker's outline |
| `TUNER_HOLES` | The tuner holes |
| `TRUSS_ROD_ACCESS`, `CARBON_RODS` | A headstock-adjusted rod's trough, the carbon bars' channels |
| `TOP_CARVE_PLATEAU`, `TOP_STEPS`, `TOP_CONTOURS`, `BACK_CONTOURS` | A carved top's plateau, a stepped top's step walls, the arm contour and belly cut |
| `BODY_TOP_CAVITIES` | Every cavity routed from the top (wire channels included) |
| `BODY_REAR_CAVITIES` | Every rear cavity and its cover recess |
| `BODY_HOLES_TOP`, `BODY_HOLES_BACK` | Holes drilled from the top (pivot studs, pots, screws, string holes, screw spots) and from the back (neck-bolt and string ferrules, cover screw spots) |
| `JACK` | The jack's bore where it meets the edge |
| `WIRE_HOLES` | Each wire hole's line in plan, from cavity to cavity |
| `SIDE_HOLES` | Each hole drilled sideways by hand into a cavity's wall (a Floyd Rose's trem-claw screws), its line in plan |
| `ENGRAVING` | The engraving's lines, or a relief's shapes |
| `COVERS`, `COVER_HOLES` | The plates where they are fitted, their holes and slots |
| `CENTERLINE` | The neck's centreline |

## The plates

`render_covers_dxf` lays each plate out in plan as it is fitted (seen
from above), left to right `COVER_GAP` (10 mm) apart from X = 0, its
lowest point on Y = 0: the outline on `COVER_OUTLINES`, its holes and
slots on `COVER_HOLES`, and its name and sheet thickness below it on
`COVER_LABELS` (hide that layer before cutting).

```python
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.render.dxf import render_covers_dxf, render_plan_dxf

geometry = Prototype001Parameters().build()
plan = render_plan_dxf(geometry)
covers = render_covers_dxf(geometry.covers)  # None without plates
```
