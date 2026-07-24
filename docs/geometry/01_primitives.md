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
fret number `n`, the remaining scale length is `S / 2^(n / 12)` and the fret
distance from the nut is `S - S / 2^(n / 12)`.

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

## Why geometry objects are immutable

All geometry objects are frozen dataclasses with slots. Once created, their
coordinates and endpoints cannot change. This makes a geometric value safe to
reuse across neck calculations without one operation silently changing another
operation's input. Immutability also makes equality predictable, prevents
accidental mutation of shared reference geometry, and keeps calculations easy
to reason about when later CAD or CAM stages consume the same objects.
