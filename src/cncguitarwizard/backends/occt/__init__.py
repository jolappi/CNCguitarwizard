"""The finished model's other 3D formats made in the browser, as files.

The build's FreeCAD script runs on OpenCascade compiled for the web
(replicad-opencascadejs, in the page's model worker): ``freecad_api`` is
FreeCAD's ``FreeCAD`` and ``Part`` modules over it, ``model`` builds the
script's model and writes it as STEP, BREP, STL, 3MF, OBJ or GLB (the
meshes by ``meshes``), each part on its own and the whole guitar.
"""

from .model import FORMATS, build, connect, export_zip, files

__all__ = ["FORMATS", "build", "connect", "export_zip", "files"]
