from enum import StrEnum


class ApertureShape(StrEnum):
    RECTANGULAR = "rectangular"
    ELLIPTICAL = "elliptical"
    VERTICES = "vertices"
    CUSTOM_SHAPE = "custom_shape"
    AUTO = "auto"  #! Default for detector, mask and diffraction_plate elements
