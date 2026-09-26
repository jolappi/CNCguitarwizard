"""Ready-to-build CNCguitarwizard instrument configurations."""

from .body_shapes import (
    BODY_SHAPE_KINDS,
    BODY_SHAPE_LABELS,
    BodyShapeSpec,
    DesignByJoneShape,
    YourDesignShape,
    body_shape_from_dict,
)
from .prototype001 import (
    HEADSTOCK_RESERVES,
    HEADSTOCK_STYLES,
    BodyLayout,
    HeadstockStyle,
    Prototype001Geometry,
    Prototype001Parameters,
)

__all__ = [
    "BodyLayout",
    "BODY_SHAPE_KINDS",
    "BODY_SHAPE_LABELS",
    "BodyShapeSpec",
    "DesignByJoneShape",
    "YourDesignShape",
    "body_shape_from_dict",
    "HEADSTOCK_RESERVES",
    "HEADSTOCK_STYLES",
    "HeadstockStyle",
    "Prototype001Geometry",
    "Prototype001Parameters",
]
