"""Tests for the mesh formats written in the browser (``backends.occt.meshes``)."""

import io
import json
import struct
import zipfile
from xml.etree import ElementTree

from cncguitarwizard.backends.occt.meshes import Mesh, glb, obj, stl, three_mf

# A tetrahedron (a cube's corner cut off), its triangles facing out.
TETRA = Mesh(
    "Body",
    ((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 10.0, 0.0), (0.0, 0.0, 10.0)),
    ((0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)),
)
NECK = Mesh(
    "NeckBack",
    ((0.0, 0.0, 20.0), (5.0, 0.0, 20.0), (0.0, 5.0, 20.0)),
    ((0, 1, 2),),
    colour=(0.9, 0.7, 0.5),
)


def test_an_stl_holds_every_triangle_with_its_normal() -> None:
    data = stl([TETRA, NECK])

    (count,) = struct.unpack_from("<I", data, 80)
    assert count == 5
    assert len(data) == 84 + 50 * count
    # The bottom (z = 0) triangle faces down.
    normal = struct.unpack_from("<3f", data, 84)
    assert normal == (0.0, 0.0, -1.0)


def test_an_obj_has_each_part_an_object() -> None:
    text = obj([TETRA, NECK]).decode()

    assert "o Body" in text and "o NeckBack" in text
    assert text.count("\nv ") == 7
    # The second part's faces count on from the first's points.
    assert "f 5 6 7" in text


def test_a_3mf_is_a_package_in_millimetres() -> None:
    package = zipfile.ZipFile(io.BytesIO(three_mf([TETRA, NECK])))

    assert set(package.namelist()) == {
        "[Content_Types].xml",
        "_rels/.rels",
        "3D/3dmodel.model",
    }
    model = ElementTree.fromstring(package.read("3D/3dmodel.model"))
    core = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
    assert model.get("unit") == "millimeter"
    objects = model.findall(f"{core}resources/{core}object")
    assert [o.get("name") for o in objects] == ["Body", "NeckBack"]
    assert len(objects[0].findall(f"{core}mesh/{core}triangles/{core}triangle")) == 4
    assert len(model.findall(f"{core}build/{core}item")) == 2


def test_a_glb_is_gltf_in_metres_each_part_a_coloured_node() -> None:
    data = glb([TETRA, NECK])

    magic, version, length = struct.unpack_from("<III", data, 0)
    assert (magic, version, length) == (0x46546C67, 2, len(data))
    json_length, kind = struct.unpack_from("<II", data, 12)
    assert kind == 0x4E4F534A and json_length % 4 == 0
    document = json.loads(data[20 : 20 + json_length])
    assert [node["name"] for node in document["nodes"]] == ["Body", "NeckBack"]
    assert document["accessors"][0]["max"] == [0.01, 0.01, 0.01]
    assert document["materials"][1]["pbrMetallicRoughness"]["baseColorFactor"] == [
        0.9,
        0.7,
        0.5,
        1.0,
    ]
    binary_length, binary_kind = struct.unpack_from("<II", data, 20 + json_length)
    assert binary_kind == 0x004E4942
    assert binary_length == document["buffers"][0]["byteLength"]
