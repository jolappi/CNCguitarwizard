# Parameter sheet

Every build writes a parameter sheet: the design's key dimensions on one
page, with units, where each value came from, a few values worked out
from the built geometry, and checks of that geometry. It is for a person
to review the design before anything is cut.

It is written three times, with the same content:

- `Prototype001_parameters.csv`, beside the other build files, for a
  spreadsheet (in the web app it is among *Model and report* in the
  downloads);
- `build.json`, under `parameter_sheet`;
- the FreeCAD model, as its `Parameters` spreadsheet, each value's cell
  named for it (`Parameters.scale_length`). It records the design and
  drives no solid: see
  [Parameters spreadsheet](../backends/freecad.md#parameters-spreadsheet).

All dimensions are millimetres (`mm`), all angles degrees (`deg`).
Positions are measured along the neck's centreline from the nut line
(X = 0).

## Status

The sheet's status is either:

- `READY FOR HUMAN REVIEW`: every check passed. A person must still
  review the design and confirm the items under *To confirm*. The sheet
  never says a design is ready to cut.
- `REVIEW REQUIRED`: a check failed; its row says which, by how much.

## Settings

The settings that decide the instrument's size (`SHEET_FIELDS` in
`cncguitarwizard.workflows.parameter_sheet`), grouped as *Instrument*,
*Scale and frets*, *Neck*, *Strings*, *Fretboard* and *Body*. A bridge
or body shape shows its kind (`kahler_7300`, `your_design`); an empty
value is a setting left unset (`bass_scale_length` on a neck that is not
multiscale, `neck_angle` taken from the bridge).

Each setting's `source` says where its value came from:

| Source | Meaning |
| --- | --- |
| `default` | The plain Prototype001 default. |
| `instrument` | The chosen instrument's default (a bass's 34-inch scale). |
| `design` | Changed in the design: by hand, or by a style. |

## Derived values

Worked out from the built geometry (`source` `derived`):

| Name | Meaning |
| --- | --- |
| `centre_scale` | The scale on the centreline: the mean of a multiscale's two. |
| `last_fret_position` | Where the last fret crosses the centreline. |
| `fretboard_end_position` | Where the fretboard ends on the centreline. |
| `saddle_line_position` | The nominal saddle line on the body, the saddles at the middle of their travel; carried with a tilted neck. |
| `neck_angle_degrees` | The neck's tilt as built: `neck_angle`, or the bridge's own. |
| `body_length`, `body_width` | The body outline's overall size. |

The saddle line is nominal: saddle compensation is set on the finished
instrument.

## Checks

Each check compares the built fret slots with the equal-tempered
formula, independently of how they were made, within 0.01 mm
(`FRET_TOLERANCE`):

| Name | Expected |
| --- | --- |
| `octave_fret_at_half_scale` | Fret `frets_per_octave` (fret 12 on an ordinary neck) crosses the centreline at half of `centre_scale`. Left out of a neck with fewer frets than an octave. |
| `frets_follow_equal_temperament` | Every fret `n` lies at `centre_scale * (1 - 2 ** (-n / frets_per_octave))` from the nut: the largest distance from it is 0. |

A slanted or fanned fret is measured where its line crosses the
centreline. The checks hold for multiscale, slanted, left-handed and
microtonal necks alike.

## To confirm

Whatever the checks say, the sheet lists what a person must still
confirm (`TO_CONFIRM`): the hardware footprints against the parts in
hand, the intonation on the finished instrument, and each program's
units, work zero, tool and machine travel, with a simulation and an air
cut before cutting stock.

## Model check

A build that runs FreeCAD then checks the model FreeCAD made against the
design (`workflows.model_check`). Its stage, *Checking the FreeCAD
model*, runs `Prototype001_check.py` in FreeCAD (see
[Measuring the finished model](../backends/freecad.md#measuring-the-finished-model)),
its output in `freecad_check.log`, and checks what it measured:

| Name | Expected |
| --- | --- |
| `model_holds_its_parts` | `NeckBack`, `Fretboard` and, unless the neck runs through the body, `Body` are in the model. |
| `model_parts_are_valid` | Every solid part is a valid shape. |
| `step_is_valid` | The STEP, read back, is a valid shape. |
| `step_holds_the_model_solids` | The STEP holds as many solids as the model's parts. |
| `model_holds_its_parameters` | The model holds its `Parameters` spreadsheet. |
| `step_lies_where_the_model_does` | The STEP's box and the model's differ by at most 0.01 mm: nothing moved or scaled on export. |
| `body_length_in_model`, `body_width_in_model` | The body solid's length and width are the sheet's `body_length` and `body_width`, within 0.01 mm (`MODEL_TOLERANCE`). |
| `body_back_at_thickness` | The body's back lies `body_thickness` below its top (Z = 0); a carved top rises above it. |

The three body checks are made for a bolt-on or set neck only: a neck
run through the body has a block and wings instead of one body solid.

The result goes into `build.json` as `model_check`: its status
(`READY FOR HUMAN REVIEW` when every check passed, else
`REVIEW REQUIRED`), the checks, what was measured, and the script's and
log's names. The command line prints the status (`Check:`). A check that
cannot be made (FreeCAD fails on the script, or prints nothing that
reads) leaves the model built and the check `REVIEW REQUIRED`, its
reason under `error`. A build made with `--scripts-only`, and the web
app's, run no FreeCAD and have no model check.

## CSV columns

The CSV and the FreeCAD spreadsheet share one layout
(`ParameterSheet.as_table`). One row a value: `group`, `name`, `value`, `unit`, `source`, `expected`,
`tolerance`, `result`. The status comes first (group `Status`), then the
settings, the derived values (group `Derived`), the checks (group
`Check`, `source` `check`, `value` the actual value, `result` `passed` or
`failed`) and the items to confirm (group `To confirm`).

## From Python

```python
from cncguitarwizard.presets import Prototype001Parameters
from cncguitarwizard.workflows import parameter_sheet

parameters = Prototype001Parameters()
sheet = parameter_sheet(parameters, parameters.build())
print(sheet.status)
print(sheet.as_csv())
```
