import csv
import json
from dataclasses import dataclass, asdict, fields, is_dataclass, MISSING
from typing import List, Dict, Any, Type
from abc import ABC
from .types import ApertureShape

from dataclasses import field
from enum import StrEnum

from bpy_lattice.objects import (
    make_basic_box_object,
    make_basic_dipole_object,
    make_basic_pipe_object,
    make_basic_empty_object,
)

from bpy_lattice.materials import assign_color_material

# Principles:
# simple data structures only (no nested objects)
# enums when possible
# serialize/deserialize to dict and include the class name


@dataclass
class BaseElement(ABC):
    """
    Abstract base class for all element types.
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
    parent: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Converts the dataclass to a dictionary, adding `class` for reconstruction."""
        d = asdict(self)
        d["class"] = self.__class__.__name__  # Store class type
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseElement":
        """Reconstructs an object from a dictionary."""
        if cls is BaseElement:
            raise TypeError("Cannot instantiate BaseElement directly. Use a subclass.")

        data_copy = data.copy()
        data_copy.pop("class", None)

        # Reconstruct nested dataclass fields
        init_args = {}
        for f in fields(cls):
            value = data_copy.get(f.name, MISSING)
            if value is not MISSING:
                if is_dataclass(f.type) and isinstance(value, dict):
                    init_args[f.name] = f.type(**value)
                else:
                    init_args[f.name] = value

        return cls(**init_args)

    def to_json(self) -> str:
        """Serializes the object to a JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "BaseElement":
        """Deserializes an object from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def available_classes(cls) -> Dict[str, Type["BaseElement"]]:
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

    length: float = 1
    width: float = 0.2
    height: float = 0.2
    aperture: Aperture = field(default_factory=Aperture)
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
        print("here!", self.name, length, width, height)
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
        print(aperture)
        if aperture.x1_limit + aperture.x2_limit == 0:
            return None
        if aperture.y1_limit + aperture.y2_limit == 0:
            return None

        if hasattr(self, "curvature"):
            curvature = self.curvature
        else:
            curvature = 0

        obj = make_basic_pipe_object(
            name=f"{self.name}{suffix}",
            length=self.length,
            a=aperture.x1_limit,
            b=aperture.y1_limit,
            a2=aperture.x2_limit,
            b2=aperture.y2_limit,
            curvature=curvature,
            thickness=aperture.thickness,
        )

        return obj

    def align_object_location_and_rotation(self, obj):
        obj.rotation_euler.z = self.theta
        obj.rotation_euler.y = -self.phi
        obj.rotation_euler.x = self.psi
        obj.location = (self.z, self.x, self.y)


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
        print("here!", self.name, length, width, height, self.gap)
        obj = make_basic_dipole_object(
            name=self.name,
            length=length,
            width=width,
            height=height,
            curvature=self.curvature,
            gap=self.gap,
        )
        # Set color
        for child in obj.children:
            assign_color_material(child, self.color)

        # Look for apertures
        aperture_obj = self.aperture_object()
        if aperture_obj is not None:
            print("adding aperture to bend")
            aperture_obj.parent = obj

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
    color = "black"


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

    color = "darkgrey"


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

    pass


@dataclass
class Multipole(BeamElement):
    """
    Multipole
    """

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

    color = "grey"

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


def get_all_subclasses(cls):
    """Recursively finds all subclasses of a given class."""
    subclasses = set(cls.__subclasses__())
    for subclass in cls.__subclasses__():
        subclasses.update(get_all_subclasses(subclass))
    return subclasses


CLASS_MAP: Dict[str, Type[BaseElement]] = {
    cls.__name__: cls for cls in get_all_subclasses(BaseElement)
}


def get_element_class(class_name: str) -> Type[BaseElement]:
    """Safely retrieves a BaseElement subclass by name."""
    cls = CLASS_MAP.get(class_name)
    if cls is None:
        raise ValueError(
            f"Unknown element class: {class_name}. Available: {list(CLASS_MAP.keys())}"
        )
    return cls


def cast_values(data: Dict[str, Any], cls: Type[Element]) -> Dict[str, Any]:
    """Casts dictionary values to the correct types based on the dataclass fields."""
    casted_data = {}
    field_types = {f.name: f.type for f in fields(cls)}

    for key, value in data.items():
        if key not in field_types:
            continue  # Skip unknown fields

        target_type = field_types[key]

        # Convert Enums
        if issubclass(target_type, StrEnum):
            casted_data[key] = target_type(value) if value else target_type()

        # Convert numeric types
        elif target_type in (int, float):
            try:
                casted_data[key] = target_type(value) if value else target_type()
            except ValueError:
                casted_data[key] = target_type()  # Use default if conversion fails

        # Default case (str, bool, etc.)
        else:
            casted_data[key] = value

    return casted_data


def save_elements_to_csv(elements: List[Element], filename: str):
    """Saves a list of Element objects to a CSV file, dynamically handling missing fields."""
    if not elements:
        raise ValueError("Element list is empty. Cannot save to CSV.")

    # Collect all possible field names across all elements
    fieldnames = set()
    for elem in elements:
        fieldnames.update(elem.to_dict().keys())
    fieldnames = sorted(fieldnames)  # Sort to maintain consistency

    with open(filename, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for elem in elements:
            row = elem.to_dict()
            # Ensure only known fields are written (avoid missing key errors)
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def load_elements_from_csv(filename: str) -> List[Element]:
    """Loads a list of Element objects from a CSV file, ensuring type conversion."""
    elements = []
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            print(row)
            class_name = row.get("class")  # Ensure "class" is read before modification
            if not class_name:
                raise ValueError(f"Missing 'class' field in CSV row: {row}")

            if class_name not in CLASS_MAP:
                raise ValueError(
                    f"Unknown class type: {class_name}. Available: {list(CLASS_MAP.keys())}"
                )

            cls = CLASS_MAP[class_name]  # Get the correct class

            row_copy = row.copy()  # Preserve "class" before casting
            row_copy.pop("class", None)  # Remove before passing to `from_dict()`

            # Cast values to correct types
            casted_row = cast_values(row_copy, cls)

            # Call from_dict() on the correct class
            elements.append(cls.from_dict(casted_row))
    return elements


def save_elements_to_json(elements: List[BaseElement], filename: str):
    """Saves a list of Element objects to a JSON file."""
    with open(filename, "w") as file:
        json.dump([elem.to_dict() for elem in elements], file, indent=4)


def load_elements_from_json(filename: str) -> List[BaseElement]:
    """Loads a list of Element objects from a JSON file."""
    with open(filename, "r") as file:
        data = json.load(file)
    return [CLASS_MAP[item["class"]].from_dict(item) for item in data]
