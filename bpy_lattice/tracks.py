from dataclasses import dataclass, fields
import numpy as np
import json
from typing import Optional, Dict, Any, List, Union, Tuple
from .colors import resolve_color
from .curves import create_curve_from_data


@dataclass
class Track:
    """
    Represents a 3D particle track with optional styling metadata.

    Parameters
    ----------
    x : np.ndarray
        X-coordinates of the track, in meters.
    y : np.ndarray
        Y-coordinates of the track, in meters.
    z : np.ndarray
        Z-coordinates of the track, in meters.
    weight : float, optional
        Visual weight of the track for rendering purposes. Default is 1.0.
    name : str, optional
        Optional name for the track.
    color : str or tuple of float, optional
        Track color, either as a string name (e.g., "blue") or an (R, G, B, A) tuple.
        Default is "blue".

    Raises
    ------
    ValueError
        If `x`, `y`, and `z` are not the same length.

    Notes
    -----
    This class is intended for storing and visualizing particle or geometric
    tracks in 3D space, and can be serialized to and from JSON.
    """

    x: np.ndarray  # Position x in meters
    y: np.ndarray  # Position y in meters
    z: np.ndarray  # Position z in meters
    weight: float = 1.0  # Weight (default=1.0)
    name: Optional[str] = None  # Optional name of the track
    color: Optional[Union[str, Tuple[float, float, float, float]]] = (
        "blue"  # Default color is blue
    )

    def __post_init__(self):
        # Check that x, y, z arrays have the same length
        mandatory_fields = ["x", "y", "z"]
        lengths = {len(getattr(self, f)) for f in mandatory_fields}
        if len(lengths) > 1:
            raise ValueError("Fields x, y, and z must have the same length.")

        # Resolve color if provided as a string
        if isinstance(self.color, str):
            self.color = resolve_color(self.color)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Track instance to a serializable dictionary.

        Returns
        -------
        dict
            A dictionary containing all fields, with numpy arrays converted to lists
            and color tuples converted to lists.
        """
        result = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if isinstance(value, np.ndarray):
                result[f.name] = value.tolist()
            elif f.name == "color" and isinstance(value, tuple):
                result[f.name] = list(value)  # Store color as a list
            else:
                result[f.name] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Track":
        """
        Create a Track instance from a dictionary.

        Parameters
        ----------
        data : dict
            Dictionary with keys corresponding to Track fields.

        Returns
        -------
        Track
            An instance of the Track class initialized with the provided data.
        """
        init_args = {}
        for f in fields(cls):
            value = data.get(f.name)
            if isinstance(value, list) and f.name != "color":
                init_args[f.name] = np.array(value)
            else:
                init_args[f.name] = value
        return cls(**init_args)

    def __len__(self):
        """
        Return the number of points in the track.

        Returns
        -------
        int
            The number of coordinate points.
        """
        return len(self.x)

    def to_curve(self):
        """
        Generate a Blender curve object from the track data.

        Returns
        -------
        bpy.types.Object
            A Blender curve object representing the track.
        """
        return create_curve_from_data(
            x=self.x,
            y=self.y,
            z=self.z,
            color=self.color,
            weight=self.weight,
            name=self.name,
        )


def save_tracks_to_json(tracks: List[Track], filepath: str) -> None:
    """
    Save a list of Track objects to a JSON file.

    Parameters
    ----------
    tracks : list of Track
        The list of Track objects to serialize.
    filepath : str
        Path to the output JSON file.

    Returns
    -------
    None
    """
    track_dicts = [track.to_dict() for track in tracks]
    with open(filepath, "w") as f:
        json.dump(track_dicts, f, indent=4)


def load_tracks_from_json(filepath: str) -> List[Track]:
    """
    Load a list of Track objects from a JSON file.

    Parameters
    ----------
    filepath : str
        Path to the JSON file to read.

    Returns
    -------
    list of Track
        List of deserialized Track objects.
    """
    with open(filepath, "r") as f:
        track_dicts = json.load(f)
    return [Track.from_dict(track_dict) for track_dict in track_dicts]
