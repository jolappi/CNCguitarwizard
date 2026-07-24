## Geometry Engine

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

The three-dimensional neck-back surface now continues beyond fret 24 through
the complete 63 mm bolt-on heel. Heel width and wood depth remain constant at
56 mm and 20 mm, so FreeCAD exports no longer stop at the final fret.

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
