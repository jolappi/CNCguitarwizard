## Geometry Engine

Prototype001 now has a planar bolt-on heel underside. A 35 mm smooth profile
transition changes the neck D profile into the rectangular heel, while a
30 mm volute blends the angled headstock thickness into the first-fret neck.
Its fretboard now ends flush with the heel, and the neck wood includes a
6 mm horizontal nut shelf before the fretboard without moving the scale.
The playing-section back now uses a rounded exponent-2 elliptical profile
that begins directly at the fretboard sides instead of the flatter D shape.

Generated FreeCAD scripts can optionally save an editable `.FCStd` document
and export their solid as `.step` or `.stp`. Output suffixes are validated
before source generation.

The FreeCAD backend can now generate a single neck assembly document. The
neck back and fretboard remain separate solids, while an optional STEP export
contains both objects for fit inspection.

The assembly exporter can optionally subtract the validated rectangular
truss-rod channel from the neck solid. It rejects mismatched outlines and
channels that would consume the full neck depth.

The fretboard solid can now receive all 24 validated fret-slot cuts. Their
0.6 mm wide, 2.7 mm deep cutting geometry follows the sampled 430 mm playing
surface radius and preserves material beneath every slot.

The fretboard ends 4 mm after fret 24. The flat bolt-on heel begins 50 mm
toward the headstock from fret 24 and ends with the fretboard, making an exact
54 × 20 mm tapered mounting solid that reaches 56 mm at its end. It is fused
to the shaped neck separately, preventing spline-loft ripples on its flat
mounting faces.
Both major joints are continuous laterally as well: the heel follows the
neck/fretboard taper, and the headstock shoulder uses a sampled curved outline.
FreeCAD output additionally applies configurable 3 mm side-joint fillets at
the heel and headstock connections so no sharp lateral corner remains.

The tapered headstock now has backend-independent solid geometry with a
configurable, validated thickness from 14 to 16 mm. Prototype001 uses 16 mm,
and FreeCAD assemblies can export it as a separate angled solid.

FreeCAD headstock exports can now subtract the validated 3+3 tuner layout.
All six 10 mm bores pass completely through the solid along the normal of the
8-degree face.

Tuner holes now receive a configurable 45-degree face chamfer. Prototype001
uses the previously agreed 0.2 mm depth, while zero disables the feature.

The FreeCAD assembly exporter can optionally fuse the angled headstock into
the neck back for manufacturing output. Separate-object inspection remains
available, and incompatible nut widths are rejected before source generation.

The Prototype001 preset now provides one immutable parameter source for the
complete neck. It builds every current geometry component and feeds them to a
one-call FreeCAD export without coupling the core model to a CAD backend.

Prototype001 now has a one-command build workflow. It creates matching
FreeCAD macro and Python scripts plus a JSON report containing the complete
parameter set, version, timestamp, target files, and script checksum.

The normal build now executes FreeCAD and verifies that both `.FCStd` and
`.step` exist before reporting success. Script-only generation is explicit,
and failed or incomplete FreeCAD runs produce a build workflow error.

FreeCAD execution now always records its command, exit code, stdout, and
stderr in `freecad.log`. The JSON report persists `pending`, `failed`, or
`complete` state, so an interrupted build cannot resemble a successful one.

Neck loft sections no longer repeat their existing `Z = 0` edge points.
Removing those zero-length polygon edges fixes FreeCAD's initial `Null shape`
failure. Generated scripts now validate and identify every loft and boolean
result.

Radius-following fret slots now use one continuous cutter solid per fret.
This removes the internal coplanar seams that caused FreeCAD to report an
invalid shape during the first fret-slot boolean operation.

Fret-slot cutters now cross the playing surface and both fretboard edges with
small controlled overcuts. This avoids coincident OpenCASCADE boolean faces,
and diagnostics identify the exact fret number if a cut still fails.

Prototype001 now interprets the 17 mm and 19 mm neck dimensions correctly as
totals including the 6 mm fretboard. Its neck-wood depths are 11 mm and 13 mm,
while the heel remains the specified 20 mm of wood plus fretboard. Builds also
remove stale FCStd and STEP targets before FreeCAD execution.

Prototype001 tuner stations moved to 55, 85, and 115 mm with 16, 13, and
10 mm centerline offsets. This leaves at least 8.646 mm of wood between every
10 mm hole edge and the tapered headstock side.

The geometry package was introduced as the backend-independent foundation for
instrument geometry.

- Added immutable `Point2D`, `Vector2D`, and `Line2D` primitives.
- Introduced the guitar neck `Centerline` model.
- Added finite, positive scale-length validation for centerline geometry.
- Added `distance`, `midpoint`, and `interpolate` geometry utilities.
- Extended `Vector2D` with dot, cross, angle, and perpendicular operations.
- Added immutable point translation, rotation, and mirror transformations.
- Added equal-temperament fret positions and centerline-derived fret lines.
- Added tapered fretboard outlines from centerline and endpoint widths.
- Added dependency-free SVG rendering with geometry snapshots.
- Added an immutable neck model and fluent neck builder.
- Added unit tests for primitive behavior, validation, and centerline geometry.

## Fretboard Generator

Fret positions were combined with the tapered fretboard outline for the first
time. The engine now produces bounded slot segments whose lengths follow the
fretboard taper, providing a backend-independent foundation for drawings and
future CAM operations.

The SVG backend was then extended to render the complete fretboard and its
bounded slots together. This created the first combined visual preview of the
fretboard geometry.

SVG previews now derive their view box from the rendered geometry. Models of
different dimensions fit the viewport automatically while retaining a
configurable model-space margin.

## Neck Generator

The first top-view neck outline was generated from the locked Prototype001
dimensions. It combines a 42 mm nut, a 56 mm width at fret 24, and a 63 mm
parallel bolt-on heel without manual CAD sketching.

The longitudinal wood profile followed next, introducing the 17 mm first-fret,
19 mm twelfth-fret, and 20 mm heel thickness references while keeping the
fretboard as a separate future geometry layer.

The separate fretboard geometry was then added with a 6 mm center thickness
and a true 430 mm circular cross-section. The model now exposes the calculated
surface sagitta and remaining edge thickness for manufacturing checks.

The modern 3+3 headstock reference followed with a 150 mm tapered plan and an
8-degree side angle. The shape widens through a 65 mm shoulder and narrows to
a 40 mm tip without copying a manufacturer-specific outline.

Six 10 mm tuner holes were added in a symmetric 3+3 layout. Automated checks
now protect the headstock edges, nut, tip, and neighboring holes before the
layout can proceed to a manufacturing backend.

The centered 440 × 6 × 9 mm double-action truss-rod channel was added with a
heel-side adjustment reference. Its fit is checked against the complete neck
outline before geometry is accepted.

Wizard-inspired D-profile cross-sections were introduced at frets 1 and 12.
The backend-independent superellipse keeps the shape symmetric and makes its
shoulder fullness adjustable for the future physical test block.

The cross-sections were then joined into the first backend-independent 3D neck
surface. A deterministic quad mesh now follows the nut, first-fret,
twelfth-fret, and final-fret thickness references and is ready for a future
FreeCAD loft backend.

The 430 mm fretboard radius was extended into a three-dimensional tapered
playing surface. Cross-section rows now coincide with the nut and every fret,
providing exact longitudinal references for CAD lofting and future fret-slot
operations.

## FreeCAD Backend

The first CAD backend was introduced without coupling FreeCAD to the geometry
engine. Deterministic standalone scripts can now loft the sampled neck-back
and fretboard sections into FreeCAD solids for visual inspection.

## Documentation

- Added public package reference with API tables, examples, and diagrams.
- Updated README, roadmap, and architecture documentation.

## Continuous Integration

- Added cached Python 3.12 GitHub Actions checks for pytest, Ruff, and mypy.
- Configured pytest warnings to fail the CI build.

## Step 2

The first core object was implemented.

Every future module will attach to the Project object,
forming the backbone of CNCguitarwizard.

2026-07-18 – Lift Off

The first runnable version of CNCguitarwizard was created. The project's architecture, philosophy and development principles were established before geometry generation began.
──────────────────────────────

History

Introduced:
v0.1.0

Related commits:

feat(geometry): add centerline

Related modules:

geometry/centerline.py

Tests:

tests/geometry/test_centerline.py

──────────────────────────────

## Internal Project Lore

The term "Digidust" was coined during the development of the first geometry modules.

Just like sawdust appears when wood is shaped,
Digidust appears when mathematics becomes geometry.

It reminds us that every tiny calculation is part of building a real instrument.
