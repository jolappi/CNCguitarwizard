from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Point2D:
    x: float
    y: float
