from dataclasses import dataclass

from .point import Point2D


@dataclass(slots=True, frozen=True)
class Line2D:
    start: Point2D
    end: Point2D

    @property
    def length(self) -> float:
        return (
            ((self.end.x - self.start.x) ** 2)
            + ((self.end.y - self.start.y) ** 2)
        ) ** 0.5
