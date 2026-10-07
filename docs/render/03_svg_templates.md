# Outline templates for other drawing programs

The body and headstock editors' *Export SVG* and *Import SVG* take an
outline to another drawing program and back (`cncguitarwizard.drawings`,
called by `webapp.outline_template()` and `webapp.import_outline()`).

## The template

`template_svg(title, frame, outline, references, notes)` writes the SVG,
1:1 in millimetres (`width`/`height` in mm, the viewBox in the model's
millimetres), in two Inkscape layers that other programs read as groups:

| Layer | What it holds |
| --- | --- |
| *Reference* (`cgwReference`, locked) | What the outline is drawn round (`ReferenceShape`s: polygons, lines and circles, each titled), the notes, and three red registration marks `cgwMarkA`, `cgwMarkB`, `cgwMarkC` |
| *Outline* (`cgwOutlineLayer`) | The outline, one closed path `cgwOutline` of cubic Bézier spans |

`TemplateFrame(marks, mirrored)` places the model on the page: X as it
is, Y up (down when `mirrored`, a left-handed design as the editor shows
it), and the marks at three model points not in a line — the body's at
(0, 0), (100, 0) and (0, 100) from the heel end, the headstock's at the
nut's centre, 100 mm past it and 50 mm beside it.

The body's outline is its Catmull-Rom loop as Bézier spans
(`closed_catmull_rom_spans`, widened for a seven- or eight-string body as
drawn); the headstock's, `outlines.headstock_spans(plan)`: the bass edge
from the nut, the tip, the treble edge back and the nut line. Either way
every editor handle is a node of the path.

## Reading it back

`read_svg_shapes(text)` reads any SVG drawing into `SvgShape`s, each a
list of polylines in the document's millimetres with its id, its
Inkscape label or Illustrator `data-name`, the groups (layers) it sits
in, whether it is hidden and which points are its own nodes: paths
(every command, relative and absolute, arcs split into quarter-turn
cubics), rects (rounded too), circles, ellipses, lines, polylines and
polygons, inside groups with any `transform`, the document sized in any
unit (px at 96 to the inch, pt, pc, in, cm, mm) with its viewBox (fitted
in, centred). `defs`, text, images and the like are left out.

`read_template_outline(text, frame)` finds the three marks (their
centres) and maps the drawing onto the model with the affine map that
takes them home, so the program may have scaled, moved or flipped the
whole drawing; `ReadOutline.scale` says by how much it was scaled. The
outline is the path still named `cgwOutline`, else the largest closed
shape outside the reference layer (its ends up to 3 mm apart); other
closed shapes are counted in `ignored`. A missing mark, or no closed
outline, is a `DrawingError` saying what to keep or draw.

## Fitting the editor's handles

`fit_closed_spline(outline, nodes)` gives a body's control points: the
drawing's nodes first (a polyline's, closer than 8 mm on average, are
not), else 16 evenly spread; every span straying more than 0.25 mm from
the outline is halved, and its neighbours too when they would be left
more than 2.5 times as long, up to 240 points. Every point lies on the
drawn line; an outline read back unchanged gives the same points.

`fit_headstock(outline, nut_half_width, bass_sign, nodes)` gives the
drawn edges and tip points. From the point furthest from the nut it
walks both sides back to the nut; both edges end at one distance, the
tip line, which is the first of these that fits within 0.25 mm (else the
closest): a pair of nodes at one distance on the two sides (furthest
first; the template's own corners fit well within it), where each side
turns to run more across than along it, and back from the far end a
millimetre at a time. Corners that meet make a pointed tip. Each edge is
a `SmoothCurve` from the nut's half-width through its nodes and the
points where it strays most; the tip a Hermite curve through its nodes
and the like (`tip_tangents`, as `HeadstockPlan.tip_outline`). An edge
turning back toward the nut, or a tip turning back across the headstock
(a hook), cannot be drawn and is refused.
