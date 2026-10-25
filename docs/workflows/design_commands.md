# Designing from the command line, or with Claude

Four commands describe, start, change and check a design file, the same
JSON the web app's *Save design* writes and its *Load design* opens
(`cncguitarwizard.design_tools`). They let a person, a script or an AI
assistant such as Claude design an instrument without the browser. The
[CNCguitarwizard skill](../../skills/cncguitarwizard/SKILL.md) teaches
Claude to use them.

Every change goes through the web app's own reading and checking: a
setting this version does not know, a value of the wrong type or a
choice it does not offer is refused, and a design is checked by building
its geometry, the editors' problems and its
[parameter sheet](parameter_sheet.md). Nothing computes a dimension of
its own.

Each command prints a short summary, or JSON with `--json`. The exit
code is 0 when all is well, 1 when a design is not OK or a change was not
kept, and 2 when the command could not run (no such file, instrument or
style).

## `settings`

```bash
python -m cncguitarwizard settings --design my_tele.json --search "neck pickup"
```

Lists the settings, each with its type, default and meaning (the web
app's hover text), the options of a choice and the kinds of a bridge or
body shape. With `--design`, each setting's value in that design and
whether it does anything there (`setting_conditions.applies`): a setting
that does nothing says what it needs (`applies_when`, *it needs
body_pickups custom*).

| Option | Lists |
| --- | --- |
| `--search WORDS` | The settings with every word in their name or meaning, underscores read as spaces, as the web app's *Find a setting*. |
| `--group TITLE` | One form group's settings: *Instrument*, *Scale and fretboard*, *Neck*, *Heel*, *Headstock and tuners*, *Body*, *Fillets and sampling*, *Other*, *Machining*. |
| `--changed` | With `--design`: the settings the design changed from its instrument's defaults. |

## `new-design`

```bash
python -m cncguitarwizard new-design --instrument electric_guitar --style telecaster --name "My Tele" --output my_tele.json
```

Starts a design file from an instrument's defaults or, with `--style`,
from one of its styles (the web app's *Style*: every setting the
instrument's default, then the style's own). It refuses a style not
offered for the instrument, naming those that are, and a file already
there unless `--force` is given. It prints the new design's check.

## `set`

```bash
python -m cncguitarwizard set --design my_tele.json handedness=left scale_length=25.5in body_bridge=tune_o_matic
```

Changes settings, `name=value` each, in order. A bridge's or body
shape's own field is `name.field=value` (`body_bridge.string_count=7`);
`body_bridge=floyd_rose` chooses another kind, written whole with its
defaults (as the web app saves it). Values
are read as their setting's type:

| Type | Written as |
| --- | --- |
| Number | `647.7`, `647.7mm`, `25,5`; a length in inches `25.5in` or `25.5"` (25.4 mm an inch). Angles, fractions, the profile exponent, speeds, feed rates, the dwell and the step-over take no inches. |
| Whole number | `22` |
| Optional number | a number, or `none` |
| Yes or no | `true`, `false`, `yes`, `no`, `on`, `off`, `1`, `0` |
| Choice | one of its options |
| List | JSON, `[3, 5, 7, 9]` |

The instrument itself is not set: it decides every default, so another
instrument is a new design.

The changed design is checked (`check`). It is written (over `--design`,
or to `--output`) only when nothing was refused and it is OK, or when an
unfinished design it started from gets no worse: its error, editor
problems and a sheet not ready for review, counted. Otherwise the file is
left as it was and the command ends with code 1. The result lists
`changes` (each setting's old and new value), `unchanged` (given the
value it had), `not_applied` (doing nothing beside the other settings,
with what it needs), `rejected` (each with its reason) and the `check`.

## `check`

```bash
python -m cncguitarwizard check --design my_tele.json
```

Reads the design as the web app loads it, builds its geometry, finds the
editors' problems and checks its parameter sheet. It is OK when the
geometry builds, no editor shows a problem and the sheet is
`READY FOR HUMAN REVIEW`. It also lists the settings the file has that
this version does not know (`skipped`) and every setting changed from the
instrument's defaults (`changed`). The machining is planned only by a
build (`build-prototype001 --design`).

## The skill

`skills/cncguitarwizard/SKILL.md` teaches Claude to design with these
commands: start from an instrument or style, find settings by words,
change related ones together, read every answer (refused values,
settings that do nothing, the check), ask instead of guessing what
shapes the instrument, and never call a design or a program ready to
cut. To use it in Claude Code, copy or link the folder into your skills:

```bash
mkdir -p ~/.claude/skills && cp -R skills/cncguitarwizard ~/.claude/skills/
```

(`.claude/skills/` in a project folder makes it that project's only.) It
needs the `cncguitarwizard` command where Claude runs: a checkout with
the package installed (`python -m pip install -e .`), or
`python -m pip install git+https://github.com/jolappi/CNCguitarwizard`.
