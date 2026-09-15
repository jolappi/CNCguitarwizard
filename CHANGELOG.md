# Changelog

## Unreleased

Everything since v0.1.0-alpha2; no release tag has been cut yet.

### Added

- Geometry engine: neck centerline, longitudinal side profile, fretboard
  side and radius cross-sections, tapered 3D fretboard surface, loft-ready 3D
  neck-back surface with an exponent-2 elliptical profile, validated
  double-action truss-rod channel, tapered 8-degree headstock plan and
  solid, symmetric 3+3 tuner layout with edge-clearance validation.
- Neck heel: flat bolt-on mounting block (`heel_mounting_length`, default
  54 mm), 45 mm `heel_root_length` D-to-heel loft with rounded shoulders,
  `heel_root_center_extension`, 1.5 mm heel scoop, and lateral fillets on the
  heel and headstock joints.
- Headstock root: `headstock_root_length`, `headstock_root_side_extension`,
  `headstock_volute_length`/`_depth`, 5 mm fixed nut shelf, 12 mm U-shaped
  nut-end trim with 2 mm side fillets.
- Fretboard inlays: `InlayLayout`/`InlayMarker` with 2 mm barbed-wire
  markers at frets 3, 5, 7, 9, 15, 17, 19, 21 and double markers at 12 and 24.
- Solid body (`cncguitarwizard.geometry.body`): `BodySolid`, `BodyOutline`,
  `TracedOutline`, `RectangularCavity`, `CircularCavity`, `TracedCavity`,
  `RearCavity`, `DrilledHole`, `BridgeMounting`, `JackHole`, and
  `BodyGeometryError`; containment, depth, and rear-to-top break-through
  validation.
- Prototype001 body digitised from `assets/reference/omarunko.dxf`: outline,
  trapezoidal neck pocket ending at the heel and opening onto the horn gap,
  humbucker routes with mounting ears, Kahler 7300 baseplate cutout (25 mm),
  rear almond control cavity and round upper-horn switch cavity with 2 mm
  cover recesses, pot and switch shaft holes, pickup-screw recesses, and the
  jack bore into the control cavity. The instrument is left-handed.
- Geometry primitives: `Point3D`, `rounded_polygon_points`, `point_in_polygon`.
- FreeCAD backend: neck-back and fretboard loft scripts, `.FCStd` and STEP
  output, neck assembly export, truss-rod subtraction, radius-following fret
  slots, tuner holes with entry chamfers, headstock fusion, adaptive joint
  fillets, inlay pockets, and the body as a fourth `Part::Feature` with
  top-, rear-, and edge-cut cavities.
- `Prototype001Parameters` preset and `build-prototype001` one-command
  workflow producing `.FCMacro`, `.py`, `.FCStd`, `.step`, `build.json`, and
  `freecad.log`.
- Dependency-free 2.5D CAM (`cncguitarwizard.cam`): exact scanline clearance
  and pruned polygon offsets, pocket/drill/profile operations, holding tabs,
  a GRBL G-code writer, toolpath SVG plots, and a two-sided body plan on
  centerline index pins. `build-prototype001` now also writes
  `Body_index_pins.nc`, `Body_top.nc`, `Body_back.nc` and their previews,
  and reports stock size and time estimates in `build.json`.
- Browser app for GitHub Pages (`site/`): runs the package in Pyodide,
  generates its form from the parameter dataclasses, builds the FreeCAD
  script, body G-code, toolpath plots and report client-side, with a
  whole-instrument plan view (`render_plan_view_svg`). `tools/build_site.py`
  and a Pages workflow assemble and deploy it.
- `tools/inspect_step_reference.py` for reporting on reference STEP models.
- Documentation: solid-body guide, fretboard-surface and neck-back-surface
  guides, headstock guide, Prototype001 preset and workflow guides, FreeCAD
  backend guide, Finnish manufacturing specification (`SPECIFICATIONS.md`).

### Changed

- `first_fret_thickness` and `twelfth_fret_thickness` now include the 6 mm
  fretboard; generated neck-wood depths are 11 mm and 13 mm.
- The fretboard ends flush with the heel; the neck and heel are one
  uninterrupted loft ending 4 mm after fret 24.
- The first two tuner pairs sit 1 mm closer to the centerline to keep at least
  8 mm of side-edge wood in the longer headstock taper.
- `BridgeMounting` accepts `pivot_stud_spacing=None` (no stud holes) and
  `has_sustain_block=False` (no rear bridge cavity) for flat-mount bridges.
- README and documentation index link every current guide.
- Reference drawings moved from the repository root to `assets/reference/`.

### Fixed

- Joint fillet failures no longer abort the FreeCAD build; each rejected
  radius is logged and the base transition retained.
- The fused neck-to-heel seam is filleted.
- The fretboard taper continues through the mounting block.
- Tuner holes keep the required edge clearance.
- Ruff and mypy run clean across `src` and `tests`.

### Removed

- A stray Python 3.11 virtualenv (`bin/`, `lib/`, `include/`), compiled
  bytecode, and `egg-info` metadata that had been committed despite
  `.gitignore`; scratch STL/SVG/JSON analysis files in the repository root.

## v0.1.0-alpha2

### Added

- Project root dataclass
- Project metadata dataclass
- Initial project unit test
