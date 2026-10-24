"""Triangle meshes written as STL, OBJ, 3MF and GLB files, in mm.

A ``Mesh`` is one part's triangles: its points and, three to a triangle,
the indices of their corners, counter-clockwise seen from outside. Each
writer takes the parts in turn and writes them all into one file.
"""

from __future__ import annotations

import io
import json
import math
import struct
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Mesh:
    """One part's triangles.

    Args:
        name: The part's name (``Body``, ``NeckBack``...).
        points: Its corners, ``(x, y, z)`` in mm.
        triangles: Three indices into ``points`` a triangle,
            counter-clockwise seen from outside.
        colour: Its colour, ``(red, green, blue)`` from 0 to 1, for the
            formats that keep one.
    """

    name: str
    points: tuple[tuple[float, float, float], ...]
    triangles: tuple[tuple[int, int, int], ...]
    colour: tuple[float, float, float] = (0.8, 0.7, 0.55)


def _normal(
    a: Sequence[float], b: Sequence[float], c: Sequence[float]
) -> tuple[float, float, float]:
    """Return a triangle's unit normal (none for a sliver)."""
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length == 0.0:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)


def stl(meshes: Sequence[Mesh]) -> bytes:
    """Return a binary STL of every part's triangles."""
    count = sum(len(mesh.triangles) for mesh in meshes)
    out = io.BytesIO()
    header = b"CNCguitarwizard, mm"
    out.write(header.ljust(80, b" "))
    out.write(struct.pack("<I", count))
    for mesh in meshes:
        for i, j, k in mesh.triangles:
            a, b, c = mesh.points[i], mesh.points[j], mesh.points[k]
            out.write(struct.pack("<12fH", *_normal(a, b, c), *a, *b, *c, 0))
    return out.getvalue()


def obj(meshes: Sequence[Mesh]) -> bytes:
    """Return a Wavefront OBJ, each part an object of its own."""
    lines = ["# CNCguitarwizard, mm"]
    offset = 1
    for mesh in meshes:
        lines.append(f"o {mesh.name}")
        lines.extend(f"v {x:.6g} {y:.6g} {z:.6g}" for x, y, z in mesh.points)
        lines.extend(
            f"f {i + offset} {j + offset} {k + offset}" for i, j, k in mesh.triangles
        )
        offset += len(mesh.points)
    return ("\n".join(lines) + "\n").encode("utf-8")


def three_mf(meshes: Sequence[Mesh]) -> bytes:
    """Return a 3MF package (in mm), each part an object of its own."""
    objects, items = [], []
    for number, mesh in enumerate(meshes, 1):
        vertices = "".join(
            f'<vertex x="{x:.6g}" y="{y:.6g}" z="{z:.6g}"/>' for x, y, z in mesh.points
        )
        triangles = "".join(
            f'<triangle v1="{i}" v2="{j}" v3="{k}"/>' for i, j, k in mesh.triangles
        )
        objects.append(
            f'<object id="{number}" name="{_xml(mesh.name)}" type="model"><mesh>'
            f"<vertices>{vertices}</vertices><triangles>{triangles}</triangles>"
            "</mesh></object>"
        )
        items.append(f'<item objectid="{number}"/>')
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        f"<resources>{''.join(objects)}</resources><build>{''.join(items)}</build>"
        "</model>"
    )
    types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" '
        'ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
        "</Relationships>"
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", types)
        package.writestr("_rels/.rels", rels)
        package.writestr("3D/3dmodel.model", model)
    return out.getvalue()


def glb(meshes: Sequence[Mesh]) -> bytes:
    """Return a binary glTF 2.0 (in metres, as glTF's are), each part a
    node of its own in its colour."""
    blob = bytearray()
    buffer_views, accessors, gltf_meshes, materials, nodes = [], [], [], [], []
    for index, mesh in enumerate(meshes):
        metres = [(x / 1000.0, y / 1000.0, z / 1000.0) for x, y, z in mesh.points]
        positions = b"".join(struct.pack("<3f", *p) for p in metres)
        indices = b"".join(struct.pack("<3I", *t) for t in mesh.triangles)
        for data, target in ((positions, 34962), (indices, 34963)):
            while len(blob) % 4:
                blob.append(0)
            buffer_views.append(
                {
                    "buffer": 0,
                    "byteOffset": len(blob),
                    "byteLength": len(data),
                    "target": target,
                }
            )
            blob.extend(data)
        lows = (
            [min(p[axis] for p in metres) for axis in range(3)] if metres else [0.0] * 3
        )
        highs = (
            [max(p[axis] for p in metres) for axis in range(3)] if metres else [0.0] * 3
        )
        accessors.append(
            {
                "bufferView": 2 * index,
                "componentType": 5126,
                "count": len(metres),
                "type": "VEC3",
                "min": lows,
                "max": highs,
            }
        )
        accessors.append(
            {
                "bufferView": 2 * index + 1,
                "componentType": 5125,
                "count": 3 * len(mesh.triangles),
                "type": "SCALAR",
            }
        )
        materials.append(
            {
                "name": mesh.name,
                "pbrMetallicRoughness": {
                    "baseColorFactor": [*mesh.colour, 1.0],
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.8,
                },
            }
        )
        gltf_meshes.append(
            {
                "name": mesh.name,
                "primitives": [
                    {
                        "attributes": {"POSITION": 2 * index},
                        "indices": 2 * index + 1,
                        "material": index,
                    }
                ],
            }
        )
        nodes.append({"name": mesh.name, "mesh": index})
    document = {
        "asset": {"version": "2.0", "generator": "CNCguitarwizard"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": gltf_meshes,
        "materials": materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(blob)}],
    }
    text = json.dumps(document, separators=(",", ":")).encode("utf-8")
    text += b" " * (-len(text) % 4)
    blob.extend(b"\0" * (-len(blob) % 4))
    chunks = (
        struct.pack("<II", len(text), 0x4E4F534A)
        + text
        + struct.pack("<II", len(blob), 0x004E4942)
        + bytes(blob)
    )
    return struct.pack("<III", 0x46546C67, 2, 12 + len(chunks)) + chunks


def _xml(text: str) -> str:
    """Return ``text`` safe inside an XML attribute."""
    return (
        text.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


WRITERS = {"stl": stl, "obj": obj, "3mf": three_mf, "glb": glb}
"""The mesh formats, by file extension, and each one's writer."""
