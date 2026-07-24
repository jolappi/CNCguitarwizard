# Truss-rod channel

Prototype001 uses a centered double-action truss rod:

| Parameter | Value |
| --- | ---: |
| Length | 440 mm |
| Width | 6 mm |
| Depth | 9 mm |
| Start position | 12 mm from nut |
| Adjustment | Heel side |

The current start position places the 440 mm channel end at 452 mm, shortly
before the calculated 24th-fret position at 457.2 mm.

```python
from cncguitarwizard.geometry.neck import NeckOutline, TrussRodChannel

neck = NeckOutline(609.6, 24, 42.0, 56.0, 56.0, 63.0)
channel = TrussRodChannel(
    neck_outline=neck,
    start_position=12.0,
    length=440.0,
    width=6.0,
    depth=9.0,
    adjustment_side="heel",
)
```

The channel validates its overall length and side clearance against the neck
outline. The spokewheel pocket is intentionally not generated yet because its
diameter, thickness, and required tool clearance depend on the selected
hardware.
