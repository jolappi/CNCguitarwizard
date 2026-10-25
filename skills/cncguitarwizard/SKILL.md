---
name: cncguitarwizard
description: Design an electric guitar or bass with CNCguitarwizard from a description in plain words - start a design file from an instrument or a style, find and change its settings, check it, and build its FreeCAD model, G-code and parameter sheet. Use when the user wants to design, change, check or build a guitar or bass with CNCguitarwizard, or to work on a design file saved from its web app.
---

# Designing a guitar with CNCguitarwizard

You steer CNCguitarwizard through its command line. You choose settings;
the program computes every dimension and checks every change. A design is
one JSON file, the same one the web app's *Save design* writes and its
*Load design* opens, so the user can move between you and the web app
at any time.

## Before you start

Check that the command works:

```bash
cncguitarwizard settings --search "scale length"
```

In a checkout of the repository, use `python -m cncguitarwizard` instead.
If neither works, install it (Python 3.12 or newer):

```bash
python -m pip install git+https://github.com/jolappi/CNCguitarwizard
```

## Rules

1. **Never work out a dimension yourself.** Fret positions, the bridge's
   place, the neck pocket, pickup routes and every other shape come from
   the program. You only choose settings.
2. **Never edit the design file by hand.** Change it with `set`, which
   reads each value as its setting's type and refuses what does not fit.
3. **Units:** lengths are millimetres. Give inches with their unit
   (`scale_length=25.5in`) and the program converts them. Angles are
   degrees.
4. **Do not guess what the user has not said** when it shapes the
   instrument: the bridge, the neck joint, the neck angle, the scale. Ask
   once, or keep the instrument's or style's default and say that you
   assumed it.
5. **A bridge brings more than itself.** It can tilt the neck (an empty
   `neck_angle` means the bridge's own: a Tune-o-matic's is 2 degrees)
   and bring its own hardware (a Tune-o-matic's stop tailpiece instead of
   strings through the body). After changing the bridge, look at
   `settings --design ... --search "neck angle"` and at the bridge's own
   fields, and tell the user what came with it.
6. **Change related settings together**, in one `set` command (a pickup
   layout and its pickups, a bridge and its string count).
7. **Never call a design or a program ready to cut.** At best a design is
   `READY FOR HUMAN REVIEW`. Every G-code program says `REVIEW REQUIRED`:
   the user simulates it, air-cuts it and starts the machine. Never start
   a machine yourself.

## Workflow

1. **Understand the request.** The instrument: `electric_guitar`,
   `seven_string_guitar`, `eight_string_guitar`, `bass_guitar`,
   `five_string_bass`, `headless_guitar` or `headless_bass`. A style
   close to what the user wants is the quickest start;
   `cncguitarwizard new-design --help` lists the styles and the
   instruments each is offered for.
2. **Start a design**, or use the file the user gives you:

   ```bash
   cncguitarwizard new-design --instrument electric_guitar --style telecaster --name "My Tele" --output my_tele.json
   ```

3. **Find the settings** by words in their names or meanings:

   ```bash
   cncguitarwizard settings --design my_tele.json --search "neck pickup" --json
   ```

   Each setting has its `name`, `type`, `value`, `default`, `help`, the
   `options` of a choice and the `kinds` of a bridge or body shape.
   `"applies": false` means it does nothing in this design;
   `applies_when` says what it needs.
4. **Change them:**

   ```bash
   cncguitarwizard set --design my_tele.json --json handedness=left body_pickups=custom body_neck_pickup=humbucker body_bridge_pickup=single_coil
   ```

5. **Read the answer** (see below) and go on until the design is what the
   user asked for and `check` says it is OK:

   ```bash
   cncguitarwizard check --design my_tele.json --json
   ```

6. **Tell the user** what you changed (the `changes` of your `set`
   commands), what you assumed and what is still open.
   `settings --design my_tele.json --changed` lists every setting that
   differs from the instrument's defaults, a style's own settings
   included.
7. **Build when asked**, into a folder of the user's (beside the design
   file, not inside the program's own repository):

   ```bash
   cncguitarwizard build-prototype001 --design my_tele.json --output my_tele_build
   ```

   Without FreeCAD, add `--scripts-only`: the G-code programs (`.nc`,
   each with an `.svg` toolpath preview), the DXF outlines, the parameter
   sheet (`Prototype001_parameters.csv`) and the FreeCAD script are still
   made; the FreeCAD model (`.FCStd`, `.step`) needs FreeCAD. Report:
   - the sheet's status, printed as `Sheet: ... (READY FOR HUMAN REVIEW)`,
     and its `to_confirm` items in `build.json` (`parameter_sheet`),
     which the user must check by hand;
   - when FreeCAD ran, the model check (`Check:`, `model_check` in
     `build.json`).

   `build.json`'s own `status` (`scripts_only`, `complete`) is the
   build's, not a review status.
8. **Point the user to the web app,**
   https://jounilappi.hopto.org/CNCguitarwizard/ : *Load design* with the
   file shows the drawings and every setting, and *Save design* gives a
   file you can go on with.

## Values

| Type | Write it as |
| --- | --- |
| Number (`float`) | `647.7`, `647.7mm`, `25.5in` (lengths only), `25,5` |
| Whole number (`int`) | `22` |
| Optional number (`optional_float`) | a number, or `none` |
| Yes or no (`bool`) | `true`/`false`, `yes`/`no` |
| Choice (`choice`) | one of its `options`, exactly |
| List (`json`) | JSON: `inlay_single_marker_frets=[3,5,7,9]` |
| Bridge or body shape (`variant`) | one of its `kinds`, written whole with its defaults: `body_bridge=tune_o_matic`; one field of it: `body_bridge.string_count=7` |

Quote an assignment with spaces or brackets for the shell:
`"headstock_engraving_text=My Tele"`.

## Reading the answers

- `set` keeps a change only when the design still builds and checks, or
  an unfinished design gets no worse: then `"keep": true` and `saved`
  names the file written. Otherwise the file stays as it was
  (`"keep": false`, `"saved": null`, exit code 1).
  - `changes`: each setting's old and new value (a bridge or body shape
    whole).
  - `unchanged`: settings that already had the value given.
  - `not_applied`: settings that do nothing beside the others, with
    `applies_when`, the values they need. Set what they need, or ask.
  - `rejected`: values that did not read, each with its reason. Fix the
    value and try again.
  - `check`: the changed design's check, as below.
- `check` (exit code 0 when OK, else 1):
  - `error`: why the design does not build. Fix the setting it names.
  - `problems`: what the web app's editors would show in red.
  - `skipped`: settings in the file this version does not know.
  - `sheet`: the parameter sheet's status and its checks (the octave
    fret at half the scale, every fret where it belongs).
  - `changed`: every setting changed from the instrument's defaults.
- Exit code 2 is a command that could not run (no such file, no such
  instrument or style): the message says why.
