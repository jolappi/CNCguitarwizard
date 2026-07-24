# Building Prototype001

Generate the complete FreeCAD package with one command:

```bash
python -m cncguitarwizard build-prototype001 --output build/
```

An installed package also provides:

```bash
cncguitarwizard build-prototype001 --output build/
```

The command creates:

- `Prototype001.FCMacro`, for execution as a FreeCAD macro;
- `Prototype001_freecad.py`, for FreeCAD's Python interpreter;
- `build.json`, containing parameters, version, timestamp, target names, and
  the generated script's SHA-256 checksum.

The macro or Python script then creates:

- `Prototype001.FCStd`;
- `Prototype001.step`.

The output paths embedded in both scripts are absolute, so launching FreeCAD
from another working directory does not redirect the build artifacts.
