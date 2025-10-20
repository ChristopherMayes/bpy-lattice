import csv
import json
from abc import ABC
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from enum import StrEnum

# Principles:
# simple data structures only (no nested objects)
# enums when possible
# serialize/deserialize to dict and include the class name
from typing import Any, Type, TypeVar

from .materials import assign_color_material
from .objects import (
    make_basic_box_object,
    make_basic_dipole_object,
    make_basic_empty_object,
    make_basic_pipe_object,
)
from .types import ApertureShape

T = TypeVar("T", bound="BaseElement")


@dataclass
class BaseElement(ABC):
    """
    Abstract base class for all element types.

    Attributes
    ----------
    name : str
        The name of the element.
    x : float
        X-coordinate position.
    y : float
        Y-coordinate position.
    z : float
        Z-coordinate position.
    theta : float
        Rotation angle around x-axis in radians.
    phi : float
        Rotation angle around y-axis in radians.
    psi : float
        Rotation angle around z-axis in radians.
    cad_model : str
        Path or reference to CAD model file.
    description : str
        Text description of the element.
    parent : str
        Name of the parent element.
    """

    name: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    theta: float = 0.0
    phi: float = 0.0
    psi: float = 0.0
    cad_model: str = ""
    description: str = ""
    type: str = ""
    parent: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        for attr, value in _cast_values(asdict(self), type(self)).items():
            setattr(self, attr, value)

    def to_dict(self) -> dict[str, Any]:
        """Converts the dataclass to a dictionary, adding `class` for reconstruction."""
        d = asdict(self)
        d["class"] = self.__class__.__name__  # Store class type
        return d

    def to_flat_dict(self) -> dict[str, Any]:
        """Converts the dataclass to a dictionary, adding `class` for reconstruction."""
        return _flatten_dict(self.to_dict())

    @classmethod
    def from_dict(cls: Type[T], data: dict[str, Any]) -> T:
        """Reconstructs an object from a dictionary."""
        init_args = data.copy()
        clsname = init_args.pop("class", None)

        if clsname:
            cls = CLASS_MAP[clsname]

        if cls is BaseElement:
            raise TypeError("Cannot instantiate BaseElement directly. Use a subclass.")

        return cls(**init_args)

    @classmethod
    def from_flat_dict(cls: Type[T], data: dict[str, Any]) -> T:
        clsname = data.get("class", cls.__name__)

        cls = CLASS_MAP[clsname]

        field_names = {f.name for f in fields(cls)}
        dct = {
            key: value
            for key, value in _unflatten_dict(data).items()
            if key in field_names
        }

        return cls.from_dict(dct)

    def to_json(self) -> str:
        """Serializes the object to a JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls: Type[T], json_str: str) -> T:
        """Deserializes an object from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def available_classes(cls) -> dict[str, Type["AnyElement"]]:
        """Returns a dictionary of all registered element types."""
        return CLASS_MAP


@dataclass
class Element(BaseElement):
    """
    Concrete class for basic element.

    Note that this does not have any special attributes (e.g., 'L')
    """


@dataclass
class Aperture:
    shape: ApertureShape = ApertureShape.RECTANGULAR
    x1_limit: float = 0.0
    x2_limit: float = 0.0
    y1_limit: float = 0.0
    y2_limit: float = 0.0
    thickness: float = 0.001
    material: str = ""


@dataclass
class BeamElement(BaseElement, ABC):
    """
    Abstract Beam element with outer physical dimensions and an aperture
    """

    aperture: Aperture = field(default_factory=Aperture)
    length: float = 1
    width: float = 0.2
    height: float = 0.2
    color = "grey"

    def to_object(self):
        return self.to_basic_object()
        # if self.cad_model:
        #    return self.to_empty_object()
        # else:

    def to_empty_object(self):
        obj = make_basic_empty_object(self.name)
        self.align_object_location_and_rotation(obj)
        return obj

    def to_basic_object(self):
        length = max(self.length, 1e-6)
        width = max(self.width, 1e-6)
        height = max(self.height, 1e-6)
        obj = make_basic_box_object(
            name=self.name, length=length, width=width, height=height
        )

        # Add color material
        assign_color_material(obj, self.color)

        # Look for apertures
        # aperture_obj = self.aperture_object()
        # if aperture_obj is not None:
        #    print('adding aperture')
        #    aperture_obj.parent = obj

        # Set location and angles
        self.align_object_location_and_rotation(obj)

        return obj

    def aperture_object(self, suffix="_aperture"):
        aperture = self.aperture
        if aperture.x1_limit + aperture.x2_limit == 0:
            return None
        if aperture.y1_limit + aperture.y2_limit == 0:
            return None

        if hasattr(self, "curvature"):
            curvature = self.curvature
        else:
            curvature = 0

        if hasattr(self, "tilt"):
            tilt = self.tilt
        else:
            tilt = 0

        thickness = aperture.thickness or 0.001

        obj = make_basic_pipe_object(
            name=f"{self.name}{suffix}",
            length=self.length,
            a=aperture.x1_limit,
            b=aperture.y1_limit,
            a2=aperture.x2_limit,
            b2=aperture.y2_limit,
            curvature=curvature,
            thickness=thickness,
            aperture_shape=aperture.shape,
            tilt=tilt,
        )

        return obj

    def align_object_location_and_rotation(self, obj):
        """
        Set position and angles

        Note the sign of pitch
        """
        yaw = self.theta
        pitch = self.phi
        roll = self.psi
        # No axes swapping
        obj.rotation_mode = "ZXY"
        obj.rotation_euler = (-pitch, yaw, roll)
        obj.location = (self.x, self.y, self.z)


# PALS standard elements
# https://github.com/campa-consortium/pals/issues/2


@dataclass
class ACKicker(BeamElement):
    """
    Time varying kicker.
    """

    pass


@dataclass
class BeamBeam(BeamElement):
    """
    Colliding beam element.
    """

    pass


@dataclass
class BeginningEle(BaseElement):  # Note: not a BeamElement because it has no aperture
    """
    Initial element at start of a branch.
    """

    pass

    def to_object(self):
        return make_basic_empty_object(self.name)


@dataclass
class Bend(BeamElement):
    """
    Dipole bend.
    """

    gap: float = 0.04
    curvature: float = 0.0
    tilt: float = 0.0
    edge_angle1: float = 0.0
    edge_angle2: float = 0.0
    b_field: float = 0.0
    color = "red"

    @property
    def angle(self):
        return self.curvature * self.length

    def to_basic_object(self):
        length = max(self.length, 1e-6)
        width = max(self.width, 1e-6)
        height = max(self.height, 1e-6)
        obj = make_basic_dipole_object(
            name=self.name,
            length=length,
            width=width,
            height=height,
            curvature=self.curvature,
            gap=self.gap,
            tilt=self.tilt,
        )
        # Set color
        for child in obj.children:
            assign_color_material(child, self.color)

        # Look for apertures
        aperture_obj = self.aperture_object()
        if aperture_obj is not None:
            aperture_obj.parent = obj
            assign_color_material(child, "darkgrey")

        # Set location and angles
        self.align_object_location_and_rotation(obj)

        return obj


@dataclass
class Collimator(BeamElement):
    """
    Collimation element.
    """

    color = "darkgrey"


@dataclass
class Converter(BeamElement):
    """
    Target to produce new species. EG: Positron converter.
    """

    color = "gold"


@dataclass
class CrabCavity(BeamElement):
    """
    RF crab cavity.
    """

    voltage: float = 0.0
    color = "darkviolet"


@dataclass
class Crystal(BeamElement):
    """
    X-ray Diffraction crystal.
    """

    color = "azure"


@dataclass
class Drift(BeamElement):
    """
    Field free region.
    """

    curvature: float = 0.0
    color = "grey"


@dataclass
class EGun(BeamElement):
    """
    Electron gun.
    """

    voltage: float = 0.0
    color = "honeydew"


@dataclass
class Fiducial(BaseElement):  # Note: not a BeamElement because it has no aperture
    """
    Global coordinate system fiducial point.
    """

    pass

    def to_object(self):
        return make_basic_empty_object(self.name)


@dataclass
class FloorShift(BeamElement):
    """
    Global coordinates shift.
    """

    pass


@dataclass
class Foil(BeamElement):
    """
    Strips electrons from an atom.
    """

    color = "silver"
    pass


@dataclass
class Fork(BeamElement):
    """
    Connect lattice branches together.
    """

    pass


@dataclass
class Girder(BeamElement):
    """
    Support element.
    """

    pass


@dataclass
class Instrument(BeamElement):
    """
    Measurement element.
    """

    color = "brown"


@dataclass
class Kicker(BeamElement):
    """
    Particle kicker element.
    """

    pass


@dataclass
class LCavity(BeamElement):
    """
    Linac accelerating RF cavity.
    """

    voltage: float = 0.0
    color = "green"


@dataclass
class Marker(BeamElement):
    """
    Zero length element to mark a particular position.
    """

    width: float = 0.4
    height: float = 0.4
    color = "black"


# Use collimator
# @dataclass
# class Mask(BeamElement):
#    """
#    Zero length collimator.
#    """
#    length: float = 0.0


@dataclass
class Match(BeamElement):
    """
    Orbit, Twiss, and dispersion matching element.
    """

    pass


@dataclass
class Mirror(BeamElement):
    """
    X-ray mirror.
    """

    color = "silver"

    def to_basic_object(self):
        """
        Special mirror geomer
        TODO: better parameters
        """
        length = max(self.length, 0.2)
        # NOTE: remapped definitions
        width = max(self.height, 0.01)
        height = max(self.width, 0.1)
        obj = make_basic_box_object(
            name=self.name,
            length=length,
            width=width,
            height=height,
            x=width / 2,
        )

        # Add color material
        assign_color_material(obj, self.color)

        # Set location and angles
        self.align_object_location_and_rotation(obj)

        return obj


@dataclass
class Multipole(BeamElement):
    """
    Multipole
    """

    color = "pink"
    pass


@dataclass
class MultiLayerMirror(BeamElement):
    """
    Mirror made up of multiple layers.
    """

    pass


# @dataclass
# class NullEle(BeamElement):
#    """
#    Placeholder element used for bookkeeping.
#    """
#    length: float = 0.0


@dataclass
class Octupole(BeamElement):
    """
    Octupole element.
    """

    b3_gradient: float = 0.0
    color = "purple"


@dataclass
class Patch(BeamElement):
    """
    Reference orbit shift.
    """

    pass


@dataclass
class Pipe(BeamElement):
    """
    Reference orbit shift.
    """

    color = "darkgrey"

    def to_object(self):
        # A pipe is the aperture
        obj = self.aperture_object(suffix="")
        if obj is None:
            obj = make_basic_empty_object(name=self.name)

        assign_color_material(obj, self.color)

        # Set location and angles
        self.align_object_location_and_rotation(obj)

        return obj


@dataclass
class Quadrupole(BeamElement):
    """
    Quadrupole element.
    """

    b1_gradient: float = 0.0
    color = "blue"


@dataclass
class RFCavity(BeamElement):
    """
    RF cavity element.
    """

    voltage: float = 0.0
    color = "green"


@dataclass
class Sextupole(BeamElement):
    """
    Sextupole element.
    """

    b2_gradient: float = 0.0
    color = "yellow"


@dataclass
class Solenoid(BeamElement):
    """
    Solenoid.
    """

    bs_field: float = 0.0
    color = "purple"


@dataclass
class Taylor(BeamElement):
    """
    General Taylor map element.
    """

    color = "olive"
    pass


@dataclass
class Undulator(BeamElement):
    """
    Undulator.
    """

    color = "orange"


# not sure about this one
# @dataclass
# class UnionEle(BeamElement):
#    """
#    Container element for overlapping elements.
#    """
#    length: float = 0.0

# use Undulator
# @dataclass
# class Wiggler(BeamElement):
#    """
#    Wiggler.
#    """
#    length: float = 0.0


AnyElement = (
    BeamElement
    | ACKicker
    | BeamBeam
    | BeginningEle
    | Bend
    | Collimator
    | Converter
    | CrabCavity
    | Crystal
    | Drift
    | EGun
    | Fiducial
    | FloorShift
    | Foil
    | Fork
    | Girder
    | Instrument
    | Kicker
    | LCavity
    | Marker
    # | Mask
    | Match
    | Mirror
    | Multipole
    | MultiLayerMirror
    # | NullEle
    | Octupole
    | Patch
    | Pipe
    | Quadrupole
    | RFCavity
    | Sextupole
    | Solenoid
    | Taylor
    | Undulator
    # | UnionEle
    # | Wiggler
)


def get_all_subclasses(cls) -> set[Type[AnyElement]]:
    """Recursively finds all subclasses of a given class."""
    subclasses = set(cls.__subclasses__())
    for subclass in cls.__subclasses__():
        subclasses.update(get_all_subclasses(subclass))
    return subclasses


CLASS_MAP: dict[str, Type[AnyElement]] = {
    cls.__name__: cls for cls in get_all_subclasses(BaseElement)
}


def get_element_class(class_name: str) -> Type[AnyElement]:
    """Safely retrieves a BaseElement subclass by name."""
    cls = CLASS_MAP.get(class_name)
    if cls is None:
        raise ValueError(
            f"Unknown element class: {class_name}. Available: {list(CLASS_MAP.keys())}"
        )
    return cls


def _cast_values(data: dict[str, Any], cls: Type[AnyElement]) -> dict[str, Any]:
    """Casts dictionary values to the correct types based on the dataclass fields."""
    casted_data = {}
    field_types = {f.name: f.type for f in fields(cls)}

    for key, value in data.items():
        if key not in field_types:
            continue  # Skip unknown fields

        target_type = field_types[key]

        if issubclass(target_type, StrEnum):
            casted_data[key] = target_type(value) if value else target_type()

        elif target_type in (int, float):
            # Convert numeric types
            try:
                casted_data[key] = target_type(value) if value else target_type()
            except ValueError:
                casted_data[key] = target_type()  # Use default if conversion fails

        elif is_dataclass(target_type):
            if isinstance(value, dict):
                casted_data[key] = target_type(**value)
            else:
                raise ValueError(
                    f"Expected 'dict' for dataclass of type `{target_type.__name__}` got {type(value).__name__}"
                )
        else:
            # Default case (str, bool, etc.)
            casted_data[key] = value

    return casted_data


def save_elements_to_csv(elements: list[AnyElement], filename: str):
    """Saves a list of Element objects to a CSV file, dynamically handling missing fields."""
    if not elements:
        raise ValueError("Element list is empty. Cannot save to CSV.")

    # Collect all possible field names across all elements
    fieldnames = set()

    data = [elem.to_flat_dict() for elem in elements]
    for row in data:
        fieldnames.update(set(row))

    fieldnames = sorted(fieldnames)  # Sort to maintain consistency

    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def load_elements_from_csv(filename: str) -> list[AnyElement]:
    """Loads a list of Element objects from a CSV file, ensuring type conversion."""
    elements = []
    with open(filename, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            elements.append(BaseElement.from_flat_dict(row))

    return elements


def save_elements_to_json(elements: list[BaseElement], filename: str):
    """Saves a list of Element objects to a JSON file."""
    with open(filename, "w") as file:
        json.dump([elem.to_dict() for elem in elements], file, indent=4)


def load_elements_from_json(filename: str) -> list[BaseElement]:
    """Loads a list of Element objects from a JSON file."""
    with open(filename) as file:
        data = json.load(file)
    return [BaseElement.from_dict(item) for item in data]


def _flatten_dict(dct: dict) -> dict:
    res = {}
    for key, value in dct.items():
        if isinstance(value, dict):
            for inner_key, inner_value in _flatten_dict(value).items():
                res[f"{key}.{inner_key}"] = inner_value
        else:
            res[key] = value
    return res


def _unflatten_dict(dct: dict) -> dict:
    res = {}
    for key, value in dct.items():
        if "." in key:
            parts = key.split(".")
            current = res
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            res[key] = value
    return res
