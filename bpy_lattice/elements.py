from dataclasses import dataclass
from typing import Union


@dataclass
class Element:
    name: str
    index: int
    x: float
    y: float
    z: float
    theta: float
    phi: float
    psi: float
    key: str
    L: float
    descrip: str


@dataclass
class SBend(Element):
    angle: float
    e1: float
    e2: float


@dataclass
class Pipe(Element):
    radius_x: float
    radius_y: float
    thickness: float


@dataclass
class Wiggler(Element):
    radius_x: float
    radius_y: float


def map_table_element(line: str) -> Union[SBend, Pipe, Wiggler, Element]:
    """Maps a comma-separated line to the appropriate beamline element dataclass."""
    vals = line.split(",")[0:14]
    
    # Common parameters for all elements
    base_params = {
        "name": vals[0].strip(),
        "index": int(vals[1]),
        "x": float(vals[2]),
        "y": float(vals[3]),
        "z": float(vals[4]),
        "theta": float(vals[5]),
        "phi": float(vals[6]),
        "psi": float(vals[7]),
        "key": vals[8].strip().upper(),
        "L": float(vals[9]),
        "descrip": vals[13]
    }
    
    element_type = base_params["key"]
    
    if element_type == "SBEND":
        return SBend(
            **base_params,
            angle=float(vals[10]),
            e1=float(vals[11]),
            e2=float(vals[12])
        )
    elif element_type == "PIPE":
        return Pipe(
            **base_params,
            radius_x=float(vals[10]),
            radius_y=float(vals[11]),
            thickness=float(vals[12])
        )
    elif element_type == "WIGGLER":
        return Wiggler(
            **base_params,
            radius_x=float(vals[10]),
            radius_y=float(vals[11])
        )
    else:
        return Element(**base_params)


def import_lattice(file):
    with open(file, "r") as f:
        next(f)  # Skip the header line
        lat = [map_table_element(line) for line in f]
    return lat
