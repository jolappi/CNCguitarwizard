"""FreeCAD's ``FreeCAD`` and ``Part`` modules, as much of them as the build's
FreeCAD script uses, on OpenCascade compiled for the browser
(replicad-opencascadejs): the script runs as it is, in Pyodide, and makes
the same model FreeCAD makes (FreeCAD's own geometry is OpenCascade's).

``connect`` takes OpenCascade's bindings (``Engine``) and puts the two
modules where ``import FreeCAD`` and ``import Part`` find them. Only what
the scripts use is here (``tests/backends/occt`` runs the scripts of every
kind of design against a stand-in engine to keep it so); there is no
window, so ``FreeCAD.GuiUp`` is false.
"""

from __future__ import annotations

import math
import sys
import types
from collections.abc import Iterable, Sequence
from typing import Any


class OCCError(Exception):
    """An OpenCascade operation that failed (FreeCAD's ``Part.OCCError``)."""


class Engine:
    """OpenCascade's bindings: classes made with ``new``, static methods
    called on their class, enumerations' values looked up by name.

    Args:
        oc: The initialised replicad-opencascadejs module (a JavaScript
            object in Pyodide), or a stand-in with the same names.
    """

    def __init__(self, oc: Any) -> None:
        self.oc = oc

    def new(self, name: str, *args: Any) -> Any:
        """Return a new ``name``, its constructor chosen by ``args``."""
        return getattr(self.oc, name).new(*args)

    def call(self, owner: str, method: str, *args: Any) -> Any:
        """Return the static method ``owner.method`` called with ``args``."""
        return getattr(getattr(self.oc, owner), method)(*args)

    def enum(self, owner: str, value: str) -> Any:
        """Return the enumeration ``owner``'s ``value``."""
        return getattr(getattr(self.oc, owner), value)


_ENGINE: Engine | None = None


def engine() -> Engine:
    """Return the connected engine.

    Raises:
        OCCError: Before ``connect``.
    """
    if _ENGINE is None:
        raise OCCError("OpenCascade is not connected: call connect() first.")
    return _ENGINE


# --- FreeCAD -------------------------------------------------------------


class Vector:
    """A point or direction in mm (``FreeCAD.Vector``)."""

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        self.x, self.y, self.z = float(x), float(y), float(z)

    def __add__(self, other: Vector) -> Vector:
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector) -> Vector:
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __neg__(self) -> Vector:
        return Vector(-self.x, -self.y, -self.z)

    def __mul__(self, other: Any) -> Any:
        # FreeCAD: a vector times a vector is their dot product.
        if isinstance(other, Vector):
            return self.dot(other)
        return Vector(self.x * other, self.y * other, self.z * other)

    __rmul__ = __mul__

    def __truediv__(self, factor: float) -> Vector:
        return Vector(self.x / factor, self.y / factor, self.z / factor)

    def __iter__(self) -> Any:
        return iter((self.x, self.y, self.z))

    def __getitem__(self, index: int) -> float:
        return (self.x, self.y, self.z)[index]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Vector) and tuple(self) == tuple(other)

    def __hash__(self) -> int:
        return hash((self.x, self.y, self.z))

    def __repr__(self) -> str:
        return f"Vector ({self.x}, {self.y}, {self.z})"

    @property
    def Length(self) -> float:  # noqa: N802 - FreeCAD's name
        return math.sqrt(self.dot(self))

    def dot(self, other: Vector) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector) -> Vector:
        return Vector(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def normalize(self) -> Vector:
        """Make it one long (in place, as FreeCAD's) and return it."""
        length = self.Length
        if length == 0.0:
            raise OCCError("Cannot normalize a null vector.")
        self.x, self.y, self.z = self.x / length, self.y / length, self.z / length
        return self

    def multiply(self, factor: float) -> Vector:
        """Scale it (in place) and return it."""
        self.x, self.y, self.z = self.x * factor, self.y * factor, self.z * factor
        return self

    def add(self, other: Vector) -> Vector:
        return self + other

    def sub(self, other: Vector) -> Vector:
        return self - other

    def pnt(self) -> Any:
        """Return OpenCascade's point."""
        return engine().new("gp_Pnt", self.x, self.y, self.z)

    def vec(self) -> Any:
        """Return OpenCascade's vector."""
        return engine().new("gp_Vec", self.x, self.y, self.z)

    def dir(self) -> Any:
        """Return OpenCascade's (unit) direction."""
        return engine().new("gp_Dir", self.x, self.y, self.z)


class Rotation:
    """A turn about an axis through the origin, in degrees
    (``FreeCAD.Rotation(axis, angle)``)."""

    def __init__(self, axis: Vector | None = None, angle: float = 0.0) -> None:
        axis = Vector(0.0, 0.0, 1.0) if axis is None else axis
        length = axis.Length or 1.0
        ux, uy, uz = axis.x / length, axis.y / length, axis.z / length
        c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        t = 1.0 - c
        # Rodrigues' rotation matrix.
        self.matrix = (
            (t * ux * ux + c, t * ux * uy - s * uz, t * ux * uz + s * uy),
            (t * ux * uy + s * uz, t * uy * uy + c, t * uy * uz - s * ux),
            (t * ux * uz - s * uy, t * uy * uz + s * ux, t * uz * uz + c),
        )


class Placement:
    """Where a part is put (``FreeCAD.Placement(base, rotation, centre)``):
    turned about ``centre``, then moved by ``base``."""

    def __init__(
        self,
        base: Vector | None = None,
        rotation: Rotation | None = None,
        centre: Vector | None = None,
    ) -> None:
        r = (rotation or Rotation()).matrix
        b, o = base or Vector(), centre or Vector()
        # x' = R (x - o) + o + b, as a 3 x 4 matrix.
        self.matrix = tuple(
            (
                r[i][0],
                r[i][1],
                r[i][2],
                tuple(b)[i]
                + tuple(o)[i]
                - sum(r[i][k] * tuple(o)[k] for k in range(3)),
            )
            for i in range(3)
        )

    def multiply(self, other: Placement) -> Placement:
        """Return this placement after ``other`` (FreeCAD's order)."""
        a, b = self.matrix, other.matrix
        result = Placement()
        result.matrix = tuple(
            (
                *(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)),
                sum(a[i][k] * b[k][3] for k in range(3)) + a[i][3],
            )
            for i in range(3)
        )
        return result

    @property
    def is_identity(self) -> bool:
        identity = ((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0))
        return all(
            abs(value - expected) < 1e-12
            for row, rows in zip(self.matrix, identity, strict=True)
            for value, expected in zip(row, rows, strict=True)
        )

    def apply(self, shape: Shape) -> Shape:
        """Return ``shape`` moved by it."""
        if self.is_identity:
            return shape
        trsf = engine().new("gp_Trsf")
        trsf.SetValues(*(value for row in self.matrix for value in row))
        return Shape(
            engine().new("BRepBuilderAPI_Transform", shape.shape, trsf, True).Shape()
        )


class Feature:
    """A part in the document (``Part::Feature``): its shape, name and
    placement."""

    def __init__(self, name: str) -> None:
        self.Name = name
        self.Label = name
        self.Shape = Shape()
        self.Visibility = True
        self.Placement = Placement()

    def isDerivedFrom(self, kind: str) -> bool:  # noqa: N802 - FreeCAD's name
        return kind == "Part::Feature"


class Sheet:
    """A spreadsheet (``Spreadsheet::Sheet``), as the build's parameter
    sheet makes one: its cells and their names kept, nothing more. It is
    no part, so the model takes none of it."""

    def __init__(self, name: str) -> None:
        self.Name = name
        self.Label = name
        self.cells: dict[str, str] = {}
        self.aliases: dict[str, str] = {}

    def set(self, cell: str, content: str) -> None:
        self.cells[cell] = content

    def setAlias(self, cell: str, alias: str) -> None:  # noqa: N802
        self.aliases[cell] = alias


class Document:
    """A FreeCAD document: the parts the script makes."""

    def __init__(self, name: str) -> None:
        self.Name = name
        self.FileName = ""
        self.Objects: list[Feature] = []

    def addObject(self, kind: str, name: str) -> Feature | Sheet:  # noqa: N802
        """Return a new part; a spreadsheet is made but kept out of
        ``Objects``, the parts."""
        if kind == "Spreadsheet::Sheet":
            return Sheet(name)
        if kind != "Part::Feature":
            raise OCCError(f"Only Part::Feature objects are made here, not {kind}.")
        feature = Feature(name)
        self.Objects.append(feature)
        return feature

    def recompute(self) -> None:
        """Nothing to recompute: each shape is set as it is made."""

    def saveAs(self, path: str) -> None:  # noqa: N802
        """Remember the name; the model is written by ``model.export``."""
        self.FileName = path

    def getObject(self, name: str) -> Feature | None:  # noqa: N802
        return next((f for f in self.Objects if f.Name == name), None)


DOCUMENTS: list[Document] = []
"""The documents made since ``connect``, the last the script's."""


def newDocument(name: str = "Unnamed") -> Document:  # noqa: N802
    document = Document(name)
    DOCUMENTS.append(document)
    return document


# --- Part ----------------------------------------------------------------


class BoundBox:
    """A shape's box (``Shape.BoundBox``), its gap left out as FreeCAD's."""

    def __init__(self, low: Sequence[float], high: Sequence[float]) -> None:
        self.XMin, self.YMin, self.ZMin = low
        self.XMax, self.YMax, self.ZMax = high

    @property
    def XLength(self) -> float:  # noqa: N802
        return self.XMax - self.XMin

    @property
    def YLength(self) -> float:  # noqa: N802
        return self.YMax - self.YMin

    @property
    def ZLength(self) -> float:  # noqa: N802
        return self.ZMax - self.ZMin

    @property
    def Center(self) -> Vector:  # noqa: N802
        return Vector(
            (self.XMin + self.XMax) / 2.0,
            (self.YMin + self.YMax) / 2.0,
            (self.ZMin + self.ZMax) / 2.0,
        )


class Shape:
    """A shape (``Part.Shape``): OpenCascade's ``TopoDS_Shape``, or none.

    A compound made here (``makeCompound``) keeps its ``members``: a cut,
    fuse or common takes them as tools of their own (``_tools``).
    """

    def __init__(self, shape: Any = None, members: Sequence[Shape] = ()) -> None:
        self.shape = shape
        self.members = tuple(members)

    # Its state.
    def isNull(self) -> bool:  # noqa: N802
        return self.shape is None or bool(self.shape.IsNull())

    def isValid(self) -> bool:  # noqa: N802
        if self.isNull():
            return False
        return bool(
            engine().new("BRepCheck_Analyzer", self.shape, True, False).IsValid()
        )

    @property
    def Volume(self) -> float:  # noqa: N802
        if self.isNull():
            return 0.0
        props = engine().new("GProp_GProps")
        engine().call(
            "BRepGProp", "VolumeProperties", self.shape, props, False, False, False
        )
        return float(props.Mass())

    @property
    def Area(self) -> float:  # noqa: N802
        if self.isNull():
            return 0.0
        props = engine().new("GProp_GProps")
        engine().call("BRepGProp", "SurfaceProperties", self.shape, props, False, False)
        return float(props.Mass())

    @property
    def BoundBox(self) -> BoundBox:  # noqa: N802
        box = engine().new("Bnd_Box")
        engine().call("BRepBndLib", "Add", self.shape, box, True)
        box.SetGap(0.0)
        if box.IsVoid():
            return BoundBox((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        low, high = box.CornerMin(), box.CornerMax()
        return BoundBox((low.X(), low.Y(), low.Z()), (high.X(), high.Y(), high.Z()))

    # Its parts, each once.
    def _parts(self, kind: str, cast: str) -> list[Shape]:
        """Return its sub-shapes of ``kind``, each once (FreeCAD's order:
        as first met), shared ones (an edge of two faces) not twice. The
        browser's OpenCascade has no shape map, so they are told apart
        by their boxes, those alike by ``IsSame``."""
        if self.isNull():
            return []
        e = engine()
        explorer = e.new(
            "TopExp_Explorer",
            self.shape,
            e.enum("TopAbs_ShapeEnum", kind),
            e.enum("TopAbs_ShapeEnum", "TopAbs_SHAPE"),
        )
        alike: dict[tuple[float, ...], list[Any]] = {}
        found: list[Shape] = []
        while explorer.More():
            current = e.call("TopoDS", cast, explorer.Current())
            bucket = alike.setdefault(_box_key(current), [])
            if not any(other.IsSame(current) for other in bucket):
                bucket.append(current)
                found.append(Shape(current))
            explorer.Next()
        return found

    @property
    def Solids(self) -> list[Shape]:  # noqa: N802
        return self._parts("TopAbs_SOLID", "Solid")

    @property
    def Faces(self) -> list[Shape]:  # noqa: N802
        return self._parts("TopAbs_FACE", "Face")

    @property
    def Wires(self) -> list[Shape]:  # noqa: N802
        return self._parts("TopAbs_WIRE", "Wire")

    @property
    def Edges(self) -> list[Shape]:  # noqa: N802
        return self._parts("TopAbs_EDGE", "Edge")

    @property
    def Vertexes(self) -> list[Shape]:  # noqa: N802
        return self._parts("TopAbs_VERTEX", "Vertex")

    @property
    def Point(self) -> Vector:  # noqa: N802 - a vertex's
        point = engine().call("BRep_Tool", "Pnt", self.shape)
        return Vector(point.X(), point.Y(), point.Z())

    # New shapes from it.
    def _tools(self) -> list[Shape]:
        """Return it as a boolean's tools: a compound's members, each one's
        own. OpenCascade takes a tool's parts as never overlapping, and a
        compound's may (an epoxy tray's walls round two routes side by
        side); as tools of their own they may overlap (FreeCAD's newer
        OpenCascade copes with either, this one not with the first)."""
        if not self.members:
            return [self]
        return [tool for member in self.members for tool in member._tools()]

    def _boolean(self, kind: str, tools: Any, fuzz: float = 0.0) -> Shape:
        tools = list(tools) if isinstance(tools, (list, tuple)) else [tools]
        e = engine()
        arguments = e.new("NCollection_List_TopoDS_Shape")
        arguments.Append(self.shape)
        others = e.new("NCollection_List_TopoDS_Shape")
        for tool in tools:
            for part in tool._tools():
                others.Append(part.shape)
        operation = e.new(f"BRepAlgoAPI_{kind}")
        operation.SetArguments(arguments)
        operation.SetTools(others)
        if fuzz:
            operation.SetFuzzyValue(fuzz)
        operation.Build(e.new("Message_ProgressRange"))
        if not operation.IsDone() or operation.HasErrors():
            raise OCCError(f"The {kind.lower()} failed.")
        _count_boolean()
        return Shape(operation.Shape())

    def cut(self, tools: Any, fuzz: float = 0.0) -> Shape:
        return self._boolean("Cut", tools, fuzz)

    def fuse(self, tools: Any, fuzz: float = 0.0) -> Shape:
        return self._boolean("Fuse", tools, fuzz)

    def common(self, tools: Any, fuzz: float = 0.0) -> Shape:
        return self._boolean("Common", tools, fuzz)

    def removeSplitter(self) -> Shape:  # noqa: N802
        unify = engine().new(
            "ShapeUpgrade_UnifySameDomain", self.shape, True, True, False
        )
        unify.Build()
        return Shape(unify.Shape())

    def extrude(self, direction: Vector) -> Shape:
        prism = engine().new(
            "BRepPrimAPI_MakePrism", self.shape, direction.vec(), False, True
        )
        return Shape(prism.Shape())

    def translate(self, offset: Vector) -> Shape:
        """Move it (in place, as FreeCAD's) and return it."""
        trsf = engine().new("gp_Trsf")
        trsf.SetTranslation(offset.vec())
        self.shape = (
            engine().new("BRepBuilderAPI_Transform", self.shape, trsf, True).Shape()
        )
        # Its members move with it (copies: the shapes it was made of stay).
        self.members = tuple(
            Shape(m.shape, m.members).translate(offset) for m in self.members
        )
        return self

    def copy(self) -> Shape:
        # This OpenCascade has no BRepBuilderAPI_Copy: a transform that
        # moves nothing, told to copy, copies.
        identity = engine().new("gp_Trsf")
        return Shape(
            engine()
            .new("BRepBuilderAPI_Transform", self.shape, identity, True)
            .Shape(),
            self.members,
        )

    def makeFillet(self, radius: float, edges: Iterable[Shape]) -> Shape:  # noqa: N802
        e = engine()
        fillet = e.new(
            "BRepFilletAPI_MakeFillet",
            self.shape,
            e.enum("ChFi3d_FilletShape", "ChFi3d_Rational"),
        )
        for edge in edges:
            fillet.Add(radius, e.call("TopoDS", "Edge", edge.shape))
        fillet.Build(e.new("Message_ProgressRange"))
        if not fillet.IsDone():
            raise OCCError("The fillet failed.")
        return Shape(fillet.Shape())

    def makeOffset2D(  # noqa: N802
        self,
        offset: float,
        join: int = 0,
        fill: bool = False,
        openResult: bool = False,  # noqa: N803 - FreeCAD's name
        intersection: bool = False,
    ) -> Shape:
        """Return its faces (or wires) grown by ``offset`` in their plane,
        round at the corners (``join`` 0) or sharp (2); faces stay faces,
        several fused into one shape (FreeCAD's ``intersection`` False)."""
        e = engine()
        kinds = {0: "GeomAbs_Arc", 1: "GeomAbs_Tangent", 2: "GeomAbs_Intersection"}
        join_type = e.enum("GeomAbs_JoinType", kinds.get(join, "GeomAbs_Arc"))
        faces = self.Faces
        spines = faces or self.Wires
        results: list[Shape] = []
        for spine in spines:
            maker = e.new(
                "BRepOffsetAPI_MakeOffset", spine.shape, join_type, openResult
            )
            maker.Perform(offset, 0.0)
            if not maker.IsDone():
                raise OCCError("The 2D offset failed.")
            grown = Shape(maker.Shape())
            results.append(_faces_from_wires(grown.Wires) if faces else grown)
        if not results:
            raise OCCError("Nothing to offset.")
        if len(results) == 1:
            return results[0]
        return results[0].fuse(results[1:]).removeSplitter()

    def toShape(self) -> Shape:  # noqa: N802
        return self


BOOLEANS_A_REPORT = 25
"""How many cuts, fuses and commons between one progress line and the next:
a big model's build takes minutes, and the script itself says little."""

_booleans = 0


def _count_boolean() -> None:
    """Count a boolean operation done, and say how many every
    ``BOOLEANS_A_REPORT``."""
    global _booleans
    _booleans += 1
    if _booleans % BOOLEANS_A_REPORT == 0:
        print(f"Building the 3D model: {_booleans} cuts and joins done…", flush=True)


def _box_key(shape: Any) -> tuple[float, ...]:
    """Return a sub-shape's box, rounded: the same shape always gets the
    same, two different ones nearly always different."""
    box = engine().new("Bnd_Box")
    engine().call("BRepBndLib", "Add", shape, box, False)
    if box.IsVoid():
        return ()
    low, high = box.CornerMin(), box.CornerMax()
    return tuple(
        round(value, 4)
        for value in (low.X(), low.Y(), low.Z(), high.X(), high.Y(), high.Z())
    )


def _faces_from_wires(wires: Sequence[Shape]) -> Shape:
    """Return a face bounded by the largest of ``wires``, the rest holes."""
    if not wires:
        raise OCCError("An offset left no outline.")
    ordered = sorted(wires, key=lambda w: -(w.BoundBox.XLength * w.BoundBox.YLength))
    e = engine()
    face = e.new(
        "BRepBuilderAPI_MakeFace", e.call("TopoDS", "Wire", ordered[0].shape), True
    )
    for hole in ordered[1:]:
        hole_wire = e.call("TopoDS", "Wire", hole.shape)
        face = e.new("BRepBuilderAPI_MakeFace", face.Face(), hole_wire)
    return Shape(face.Face())


def makePolygon(points: Sequence[Vector], closed: bool = False) -> Shape:  # noqa: N802
    """Return the wire through ``points`` (closed when its last is its first)."""
    e = engine()
    wire = e.new("BRepBuilderAPI_MakeWire")
    path = list(points)
    if closed and path and path[0] != path[-1]:
        path.append(path[0])
    for a, b in zip(path, path[1:], strict=False):
        if (a - b).Length > 1e-9:
            wire.Add(e.new("BRepBuilderAPI_MakeEdge", a.pnt(), b.pnt()).Edge())
    return Shape(wire.Wire())


def Face(wires: Any) -> Shape:  # noqa: N802
    """Return the planar face a wire bounds (a list: the first, the rest
    holes in it)."""
    wires = list(wires) if isinstance(wires, (list, tuple)) else [wires]
    e = engine()
    face = e.new(
        "BRepBuilderAPI_MakeFace", e.call("TopoDS", "Wire", wires[0].shape), True
    )
    for hole in wires[1:]:
        face = e.new(
            "BRepBuilderAPI_MakeFace", face.Face(), e.call("TopoDS", "Wire", hole.shape)
        )
    if not face.IsDone():
        raise OCCError("The face could not be made.")
    return Shape(face.Face())


def Wire(edges: Sequence[Shape]) -> Shape:  # noqa: N802
    e = engine()
    wire = e.new("BRepBuilderAPI_MakeWire")
    for edge in edges:
        wire.Add(e.call("TopoDS", "Edge", edge.shape))
    return Shape(wire.Wire())


class LineSegment:
    """A straight edge between two points (``Part.LineSegment``)."""

    def __init__(self, start: Vector, end: Vector) -> None:
        self.start, self.end = start, end

    def toShape(self) -> Shape:  # noqa: N802
        return Shape(
            engine()
            .new("BRepBuilderAPI_MakeEdge", self.start.pnt(), self.end.pnt())
            .Edge()
        )


class Arc:
    """A circle's arc through three points (``Part.Arc``)."""

    def __init__(self, start: Vector, middle: Vector, end: Vector) -> None:
        self.points = (start, middle, end)

    def toShape(self) -> Shape:  # noqa: N802
        e = engine()
        arc = e.new("GC_MakeArcOfCircle", *(p.pnt() for p in self.points)).Value()
        return Shape(e.new("BRepBuilderAPI_MakeEdge", arc).Edge())


class BSplineSurface:
    """A B-spline surface from its poles, knots and multiplicities
    (``Part.BSplineSurface``, ``buildFromPolesMultsKnots``)."""

    def __init__(self) -> None:
        self.surface: Any = None

    def buildFromPolesMultsKnots(  # noqa: N802
        self,
        poles: Sequence[Sequence[Vector]],
        umults: Sequence[int],
        vmults: Sequence[int],
        uknots: Sequence[float],
        vknots: Sequence[float],
        uperiodic: bool,
        vperiodic: bool,
        udegree: int,
        vdegree: int,
    ) -> None:
        e = engine()
        grid = e.new("NCollection_Array2_gp_Pnt", 1, len(poles), 1, len(poles[0]))
        for i, row in enumerate(poles, 1):
            for j, pole in enumerate(row, 1):
                grid.SetValue(i, j, pole.pnt())

        def array(kind: str, values: Sequence[float]) -> Any:
            result = e.new(f"NCollection_Array1_{kind}", 1, len(values))
            for index, value in enumerate(values, 1):
                result.SetValue(index, value)
            return result

        self.surface = e.new(
            "Geom_BSplineSurface",
            grid,
            array("double", uknots),
            array("double", vknots),
            array("int", umults),
            array("int", vmults),
            udegree,
            vdegree,
            uperiodic,
            vperiodic,
        )

    def toShape(self) -> Shape:  # noqa: N802
        return Shape(engine().new("BRepBuilderAPI_MakeFace", self.surface, 1e-6).Face())


def makeBox(  # noqa: N802
    length: float, width: float, height: float, base: Vector | None = None
) -> Shape:
    corner = (base or Vector()).pnt()
    return Shape(
        engine().new("BRepPrimAPI_MakeBox", corner, length, width, height).Shape()
    )


def makeCylinder(  # noqa: N802
    radius: float, height: float, base: Vector | None = None, axis: Vector | None = None
) -> Shape:
    e = engine()
    frame = e.new("gp_Ax2", (base or Vector()).pnt(), (axis or Vector(0, 0, 1)).dir())
    return Shape(e.new("BRepPrimAPI_MakeCylinder", frame, radius, height).Shape())


def makeCone(  # noqa: N802
    radius1: float,
    radius2: float,
    height: float,
    base: Vector | None = None,
    axis: Vector | None = None,
) -> Shape:
    """Return a cone (or its frustum) as a ruled loft of its two ends."""
    e = engine()
    base = base or Vector()
    axis = Vector(*(axis or Vector(0, 0, 1))).normalize()
    loft = e.new("BRepOffsetAPI_ThruSections", True, True, 1e-6)
    for radius, centre in ((radius1, base), (radius2, base + axis * height)):
        if radius <= 0.0:
            loft.AddVertex(e.new("BRepBuilderAPI_MakeVertex", centre.pnt()).Vertex())
            continue
        circle = e.new("gp_Circ", e.new("gp_Ax2", centre.pnt(), axis.dir()), radius)
        edge = e.new("BRepBuilderAPI_MakeEdge", circle).Edge()
        loft.AddWire(e.new("BRepBuilderAPI_MakeWire", edge).Wire())
    loft.Build(e.new("Message_ProgressRange"))
    if not loft.IsDone():
        raise OCCError("The cone could not be made.")
    return Shape(loft.Shape())


def makeLoft(  # noqa: N802
    sections: Sequence[Shape],
    solid: bool = False,
    ruled: bool = False,
    closed: bool = False,
) -> Shape:
    e = engine()
    loft = e.new("BRepOffsetAPI_ThruSections", solid, ruled, 1e-6)
    for section in sections:
        loft.AddWire(e.call("TopoDS", "Wire", section.shape))
    loft.Build(e.new("Message_ProgressRange"))
    if not loft.IsDone():
        raise OCCError("The loft failed.")
    return Shape(loft.Shape())


def makeCompound(shapes: Iterable[Shape]) -> Shape:  # noqa: N802
    e = engine()
    compound = e.new("TopoDS_Compound")
    builder = e.new("TopoDS_Builder")
    builder.MakeCompound(compound)
    members = [shape for shape in shapes if not shape.isNull()]
    for shape in members:
        builder.Add(compound, shape.shape)
    return Shape(compound, members)


def Compound(shapes: Iterable[Shape]) -> Shape:  # noqa: N802
    return makeCompound(shapes)


def export(objects: Sequence[Feature], path: str) -> None:
    """Remember what the script asks for; ``model.export`` writes files."""
    EXPORTED.append((list(objects), path))


EXPORTED: list[tuple[list[Feature], str]] = []
"""The script's own ``Part.export`` calls, in turn."""


def connect(oc: Any) -> None:
    """Use ``oc`` (OpenCascade's bindings) and make ``import FreeCAD`` and
    ``import Part`` find these modules; forget earlier documents."""
    global _ENGINE
    _ENGINE = oc if isinstance(oc, Engine) else Engine(oc)
    DOCUMENTS.clear()
    EXPORTED.clear()
    freecad = types.ModuleType("FreeCAD")
    for name, value in {
        "Vector": Vector,
        "Rotation": Rotation,
        "Placement": Placement,
        "newDocument": newDocument,
        "GuiUp": False,
    }.items():
        setattr(freecad, name, value)
    part = types.ModuleType("Part")
    for name, value in {
        "Shape": Shape,
        "OCCError": OCCError,
        "makePolygon": makePolygon,
        "Face": Face,
        "Wire": Wire,
        "LineSegment": LineSegment,
        "Arc": Arc,
        "BSplineSurface": BSplineSurface,
        "makeBox": makeBox,
        "makeCylinder": makeCylinder,
        "makeCone": makeCone,
        "makeLoft": makeLoft,
        "makeCompound": makeCompound,
        "Compound": Compound,
        "export": export,
    }.items():
        setattr(part, name, value)
    sys.modules["FreeCAD"] = freecad
    sys.modules["Part"] = part
