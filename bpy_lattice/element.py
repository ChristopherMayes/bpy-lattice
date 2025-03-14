import csv
from dataclasses import dataclass, asdict, fields
from typing import List, Dict, Any

from .types import ApertureType, KeyType


@dataclass
class Element:
    name: str = ""
    # Global floor
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    theta: float = 0.0
    phi: float = 0.0
    psi: float = 0.0
    # External files
    cad_model: str = ""
    # Bmad attributes
    key: KeyType = KeyType.MARKER
    L: float = 0.0
    angle: float = 0.0
    e1: float = 0.0
    e2: float = 0.0
    aperture_type: ApertureType = ApertureType.RECTANGULAR
    x1_limit: float = 0.0
    x2_limit: float = 0.0
    y1_limit: float = 0.0
    y2_limit: float = 0.0


def cast_values(data: Dict[str, Any], cls) -> Dict[str, Any]:
    """Casts dictionary values to the types defined in the dataclass and fills in missing fields."""
    field_types = {f.name: f.type for f in fields(cls)}
    default_values = {f.name: f.default for f in fields(cls)}

    # Strip spaces from keys and values
    cleaned_data = {k.strip(): v.strip() for k, v in data.items()}

    casted_data = {}
    for key, field_type in field_types.items():
        value = cleaned_data.get(key, "")

        if field_type == ApertureType:  # Handle ApertureType Enum
            casted_data[key] = (
                ApertureType(value)
                if value in ApertureType.__members__.values()
                else default_values[key]
            )
        elif field_type == KeyType:  # Handle KeyType Enum
            casted_data[key] = (
                KeyType(value)
                if value in KeyType.__members__.values()
                else default_values[key]
            )
        elif value != "":
            try:
                casted_data[key] = field_type(value)
            except ValueError:
                casted_data[key] = default_values[key]
        else:
            casted_data[key] = default_values[key]

    return casted_data


def save_elements_to_csv(elements: List[Element], filename: str):
    """Saves a list of Element objects to a CSV file with a header."""
    fieldnames = [f.name for f in fields(Element)]

    with open(filename, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for elem in elements:
            writer.writerow(asdict(elem))  # No need for `.value` conversion


def load_elements_from_csv(filename: str) -> List[Element]:
    """Loads a list of Element objects from a CSV file, ensuring correct data types and handling missing columns."""
    elements = []
    with open(filename, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            cleaned_row = {k.strip(): v.strip() for k, v in row.items()}  # Clean spaces
            casted_data = cast_values(cleaned_row, Element)
            elements.append(Element(**casted_data))
    return elements
