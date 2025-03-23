from enum import StrEnum


class ApertureShape(StrEnum):
    RECTANGULAR = "rectangular"
    ELLIPTICAL = "elliptical"
    VERTICES = "vertices"
    CUSTOM_SHAPE = "custom_shape"
