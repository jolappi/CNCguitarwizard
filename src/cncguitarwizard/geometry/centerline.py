from .line import Line2D
from .point import Point2D


class Centerline:

    @staticmethod
    def create(scale_length: float) -> Line2D:

        return Line2D(
            Point2D(0.0, 0.0),
            Point2D(scale_length, 0.0),
        )
