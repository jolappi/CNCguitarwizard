# Parameter sheet

Every build writes a parameter sheet: the design's key dimensions on one
page, with units, where each value came from, a few values worked out
from the built geometry, and checks of that geometry. It is for a person
to review the design before anything is cut.

It is written twice, with the same content:

- `Prototype001_parameters.csv`, beside the other build files, for a
  spreadsheet (in the web app it is among *Model and report* in the
  downloads);
- `build.json`, under `parameter_sheet`.

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

## CSV columns

One row a value: `group`, `name`, `value`, `unit`, `source`, `expected`,
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
