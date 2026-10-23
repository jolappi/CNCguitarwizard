# Geometry Primitives

The geometry package provides the small, backend-independent building blocks
used to describe guitar geometry. Coordinates and lengths are measured in
millimetres.

## Point2D

`Point2D` represents a location in two-dimensional space. It stores an `x`
coordinate and a `y` coordinate.

```python
from cncguitarwizard.geometry import Point2D

nut = Point2D(0.0, 0.0)
bridge_side = Point2D(609.6, 0.0)
```

## Vector2D

`Vector2D` represents a two-dimensional displacement. Its `length` property
returns the Euclidean magnitude, and `normalized()` returns a unit vector in
the same direction.

```python
from cncguitarwizard.geometry import Vector2D

direction = Vector2D(3.0, 4.0)
assert direction.length == 5.0
assert direction.normalized() == Vector2D(0.6, 0.8)
```

Vectors also support dot and two-dimensional cross products, an unsigned
angle in radians, and a 90-degree counter-clockwise perpendicular vector.

```python
import math

right = Vector2D(1.0, 0.0)
up = Vector2D(0.0, 1.0)

assert right.dot(up) == 0.0
assert right.cross(up) == 1.0
assert right.angle_to(up) == math.pi / 2.0
assert right.perpendicular() == up
```

Normalizing `Vector2D(0.0, 0.0)` is undefined and raises
`ZeroLengthVectorError`.

```python
from cncguitarwizard.geometry import ZeroLengthVectorError

try:
    Vector2D(0.0, 0.0).normalized()
except ZeroLengthVectorError:
    print("A zero-length vector has no direction.")
```

## Line2D

`Line2D` represents a line segment with a `start` point and an `end` point.
The `length` property returns the Euclidean distance between its endpoints.

```python
from cncguitarwizard.geometry import Line2D, Point2D

segment = Line2D(Point2D(0.0, 0.0), Point2D(3.0, 4.0))
assert segment.length == 5.0
```

## Centerline

`Centerline` is neck-specific geometry. Given a positive scale length, it
builds a segment from the nut at `Point2D(0.0, 0.0)` to the bridge position at
`Point2D(scale_length, 0.0)`.

```python
from cncguitarwizard.geometry.neck import Centerline

centerline = Centerline(609.6)
assert centerline.line.start.x == 0.0
assert centerline.line.end.x == 609.6
assert centerline.length == 609.6
```

The scale length must be finite and greater than zero. Zero, negative,
infinite, and not-a-number values raise `GeometryException`.

## Utility functions

`cncguitarwizard.geometry.utils` provides small functions that operate on
immutable `Point2D` values. `distance()` delegates segment measurement to
`Line2D`; `midpoint()` and `interpolate()` return new points without changing
their inputs.

```python
from cncguitarwizard.geometry import Line2D, Point2D
from cncguitarwizard.geometry.utils import distance, interpolate, midpoint

start = Point2D(0.0, 0.0)
end = Point2D(8.0, 4.0)

assert distance(start, end) == Line2D(start, end).length
assert midpoint(start, end) == Point2D(4.0, 2.0)
assert interpolate(start, end, 0.25) == Point2D(2.0, 1.0)
```

## Point transformations

`cncguitarwizard.geometry.transforms` returns new immutable `Point2D` values
for translations, rotations about the origin, and reflections. Scaling is
intentionally not provided.

The formulas are:

- Translation by vector `(dx, dy)`: `(x + dx, y + dy)`
- Rotation by angle `a` radians: `(x cos(a) - y sin(a), x sin(a) + y cos(a))`
- Mirror across the x-axis: `(x, -y)`
- Mirror across the y-axis: `(-x, y)`

```python
import math

from cncguitarwizard.geometry import Point2D, Vector2D
from cncguitarwizard.geometry.transforms import mirror_x, rotate, translate

point = Point2D(2.0, 3.0)

assert translate(point, Vector2D(-1.0, 4.0)) == Point2D(1.0, 7.0)
assert rotate(point, math.pi / 2.0) == Point2D(-3.0, 2.0)
assert mirror_x(point) == Point2D(2.0, -3.0)
```

## Fret geometry

`FretCalculator` uses equal temperament. For a scale length `S` and one-based
fret number `n`, the remaining scale length is `S / 2^(n / N)` and the fret
distance from the nut is `S - S / 2^(n / N)`, `N` the frets per octave: 12,
or more on a microtonal neck (`frets_per_octave`; see
[Fret calculation](../math/fret_calculation.md)). `nearest_fret(s, N)` is
the fret nearest `s` semitones up, where a marker listed for semitone `s`
goes.

`FretLine` places that distance along a `Centerline`. Its direction is the
normalized perpendicular of the centerline direction `(dx, dy)`, namely
`(-dy, dx) / sqrt(dx^2 + dy^2)`. The line is infinite because fretboard width
is not yet part of the geometry model.

```python
from cncguitarwizard.geometry.fret import FretCalculator, FretLine
from cncguitarwizard.geometry.neck import Centerline

centerline = Centerline(609.6)
first_position = FretCalculator.calculate(centerline.length, 1)[0]
first_fret = FretLine(centerline, first_position)

assert first_fret.location.x == first_position.distance_from_nut
assert first_fret.direction.dot(first_fret.direction) == 1.0
```

## Closed splines

`closed_catmull_rom(control_points, samples_per_segment=8)` returns a
smooth closed outline that passes through every control point: each
segment is a uniform Catmull-Rom cubic, tangent-continuous with its
neighbours. A drawn body (`YourDesignShape`) is such a loop.

```python
from cncguitarwizard.geometry.primitives import Point2D, closed_catmull_rom

square = (Point2D(0, 0), Point2D(10, 0), Point2D(10, 10), Point2D(0, 10))
outline = closed_catmull_rom(square, samples_per_segment=4)
assert outline[0::4] == square
```

`open_catmull_rom` is the same curve from the first point to the last,
not joined back. Either takes `corners`, one mark a point: a sharp corner
leaves toward its next point and comes in from the one before (its
tangent each way half its own segment's chord), so the curve runs
straight between two. A drawn point carries the mark as a third item,
`(x, y, "corner")` (`CORNER`); `drawn_points(points)` returns the points
and their marks and refuses anything else, and `moved(point, x, y)` puts
a drawn point elsewhere with its mark kept. Without marks the curve is
exactly as before.

```python
from cncguitarwizard.geometry.primitives import CORNER, drawn_points

points, corners = drawn_points(((0, 0), (10, 0, CORNER), (10, 10, CORNER), (0, 10)))
outline = closed_catmull_rom(points, 8, corners)
assert all(p.x == 10.0 for p in outline[8:17])  # straight between the corners
```

A drawn polygon is the other way round: straight between its points,
but rounded through one marked `(x, y, "round")` (`ROUND`, read with
`drawn_points(points, ROUND)`). `drawn_polygon(points, rounds)` is the
closed loop through them with every other point a corner, its straight
sides kept as their two ends, and with no point round the points
themselves: a stepped top's drawn lines, a drawn truss-rod cover and a
drawn inlay marker.

## Monotone curves

`MonotoneCurve(points)` is a smooth `y(x)` through points with increasing
`x` (a Fritsch–Carlson piecewise cubic): between two neighbouring points
it stays within their `y` values, its first slope is zero, and a peak or
dip gets a flat slope. A drawn headstock edge is such a curve.

```python
from cncguitarwizard.geometry.primitives import MonotoneCurve

edge = MonotoneCurve(((0.0, 21.0), (45.0, 33.0), (150.0, 20.0)))
assert edge.value_at(45.0) == 33.0
```

`SmoothCurve(points, corners=())` rounds through its points instead (each
one's slope its neighbours' chord), as a drawn headstock edge does; at a
point marked a corner it takes each side's own chord (`slopes` leaving a
point, `slopes_in` arriving), so it runs straight between two.

## Bézier spans

The smooth curves are cubics, so each converts exactly to cubic Bézier
spans, as an SVG path draws them, with a node at every control point:
`closed_catmull_rom_spans(points, corners=())` (one span a point of the
closed loop, sharp at its corners), `smooth_curve_spans(curve)` (a
`SmoothCurve` y(x), a span between its points) and `hermite_spans(points,
tangents, arriving=())` (a headstock's shaped tip; `arriving` the
tangents arriving at each point where they differ from those leaving it,
at a sharp tip point).
`bezier_point(span, t)` evaluates a span and `flatten_span(span,
tolerance)` turns it into points never further than `tolerance` from it.

```python
from cncguitarwizard.geometry.primitives import (
    Point2D, bezier_point, closed_catmull_rom, closed_catmull_rom_spans,
)

square = (Point2D(0, 0), Point2D(10, 0), Point2D(10, 10), Point2D(0, 10))
spans = closed_catmull_rom_spans(square)
assert bezier_point(spans[1], 0.5) == closed_catmull_rom(square, 2)[3]
```

## Why geometry objects are immutable

All geometry objects are frozen dataclasses with slots. Once created, their
coordinates and endpoints cannot change. This makes a geometric value safe to
reuse across neck calculations without one operation silently changing another
operation's input. Immutability also makes equality predictable, prevents
accidental mutation of shared reference geometry, and keeps calculations easy
to reason about when later CAD or CAM stages consume the same objects.
