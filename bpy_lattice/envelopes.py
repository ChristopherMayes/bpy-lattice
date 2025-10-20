import bpy
from .mesh import build_aperture_mesh
from .materials import assign_color_material

from dataclasses import dataclass, fields
from typing import List, Union, Iterable, Dict, Any, Optional, Tuple
from collections import namedtuple
import json

# Immutable vertex definition
Vertex = namedtuple("Vertex", ["x", "y", "z"])


@dataclass
class EnvelopeLoop:
    """
    A loop of vertices that form a single closed 2D cross-section of an Envelope.

    Parameters
    ----------
    vertices : list of Vertex or list of tuple
        A sequence of 3D points defining the loop. Elements not already of type
        `Vertex` will be cast as such.

    Methods
    -------
    to_dict() -> dict
        Serialize the EnvelopeLoop to a dictionary.
    from_dict(data) -> EnvelopeLoop
        Construct an EnvelopeLoop from a dictionary.
    __len__() -> int
        Return the number of vertices in the loop.
    __getitem__(index)
        Get a vertex by index.
    """

    vertices: List[Vertex]

    def __post_init__(self):
        self.vertices = [
            v if isinstance(v, Vertex) else Vertex(*v) for v in self.vertices
        ]

    def __iter__(self):
        return iter(self.vertices)

    def __len__(self):
        return len(self.vertices)

    def __getitem__(self, index):
        return self.vertices[index]

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if f.name == "vertices":
                result[f.name] = [list(v) for v in value]
            else:
                result[f.name] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnvelopeLoop":
        init_args = {}
        for f in fields(cls):
            value = data.get(f.name)
            if f.name == "vertices":
                init_args[f.name] = [Vertex(*v) for v in value]
            else:
                init_args[f.name] = value
        return cls(**init_args)


@dataclass
class Envelope:
    """
    A 3D envelope constructed from one or more EnvelopeLoops.

    Parameters
    ----------
    loops : list of EnvelopeLoop or list of list of Vertex-like
        Cross-sectional profiles making up the envelope. Elements are converted
        to `EnvelopeLoop` if necessary.
    name : str, optional
        Name of the envelope. Default is "envelope".
    color : str or tuple of float, optional
        Color used for rendering, either a color name or RGBA tuple. Default is "blue".

    Methods
    -------
    to_dict() -> dict
        Serialize the Envelope to a dictionary.
    to_json(filepath) -> None
        Save the Envelope to a JSON file.
    from_dict(data) -> Envelope
        Load an Envelope from a dictionary.
    from_json(filepath) -> Envelope
        Load an Envelope from a JSON file.
    to_mesh(name=None) -> bpy.types.Mesh
        Create a Blender mesh object from the envelope.
    to_object() -> bpy.types.Object
        Create a Blender object from the envelope, assigning color as a material.
    __len__() -> int
        Number of loops in the envelope.
    __getitem__(index)
        Get a loop by index.
    """

    loops: List[Union[EnvelopeLoop, List[Union[Vertex, Iterable[float]]]]]
    name: Optional[str] = "envelope"
    color: Optional[Union[str, Tuple[float, float, float, float]]] = "blue"

    def __post_init__(self):
        self.loops = [
            loop
            if isinstance(loop, EnvelopeLoop)
            else EnvelopeLoop(
                vertices=[v if isinstance(v, Vertex) else Vertex(*v) for v in loop]
            )
            for loop in self.loops
        ]

    def __iter__(self):
        return iter(self.loops)

    def __len__(self):
        return len(self.loops)

    def __getitem__(self, index):
        return self.loops[index]

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if f.name == "loops":
                result[f.name] = [loop.to_dict() for loop in value]
            elif f.name == "color" and isinstance(value, tuple):
                result[f.name] = list(value)
            else:
                result[f.name] = value
        return result

    def to_json(self, filepath: str) -> None:
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Envelope":
        init_args = {}
        for f in fields(cls):
            value = data.get(f.name)
            if f.name == "loops":
                init_args[f.name] = [
                    EnvelopeLoop.from_dict(loop_data) for loop_data in value
                ]
            elif f.name == "color" and isinstance(value, list):
                init_args[f.name] = tuple(value)
            else:
                init_args[f.name] = value
        return cls(**init_args)

    @classmethod
    def from_json(cls, filepath: str) -> "Envelope":
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_mesh(self, name=None):
        vertices, faces = build_aperture_mesh(self.loops)
        if name is None:
            name = f"{self.name}_mesh"
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()  # Update the mesh with new data
        return mesh

    def to_object(self):
        obj = bpy.data.objects.new(self.name, self.to_mesh())
        assign_color_material(obj, self.color)
        return obj
