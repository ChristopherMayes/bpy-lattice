from dataclasses import dataclass, fields
import numpy as np
import json
from typing import Optional, Dict, Any, List, Union, Tuple
from .colors import resolve_color
from .curves import create_curve_from_data


@dataclass
class Track:
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
        init_args = {}
        for f in fields(cls):
            value = data.get(f.name)
            if isinstance(value, list) and f.name != "color":
                init_args[f.name] = np.array(value)
            else:
                init_args[f.name] = value
        return cls(**init_args)

    def __len__(self):
        return len(self.x)

    def to_curve(self):
        return create_curve_from_data(
            x=self.x,
            y=self.y,
            z=self.z,
            color=self.color,
            weight=self.weight,
            name=self.name,
        )


def save_tracks_to_json(tracks: List[Track], filepath: str) -> None:
    """Save a list of Track objects to a single JSON file."""
    track_dicts = [track.to_dict() for track in tracks]
    with open(filepath, "w") as f:
        json.dump(track_dicts, f, indent=4)


def load_tracks_from_json(filepath: str) -> List[Track]:
    """Load a list of Track objects from a single JSON file."""
    with open(filepath, "r") as f:
        track_dicts = json.load(f)
    return [Track.from_dict(track_dict) for track_dict in track_dicts]
