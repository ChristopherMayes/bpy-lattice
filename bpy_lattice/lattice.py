from typing import Optional, Dict, List, Any
from dataclasses import dataclass, fields
import json
from pathlib import Path
from .blend import (
    add_elements_to_blender,
    add_tracks_to_blender,
    add_envelopes_to_blender,
)
from .elements import Element
from .tracks import Track
from .envelopes import Envelope
from .interfaces.bmad import bpy_elements_from_tao, floor_orbit_track_from_tao


@dataclass
class Lattice:
    elements: Optional[List[Element]] = None
    tracks: Optional[List[Track]] = None
    envelopes: Optional[List[Envelope]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if value:  # Skip empty lists or None
                result[f.name] = [v.to_dict() for v in value]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Lattice":
        return cls(
            elements=[Element.from_dict(d) for d in data.get("elements", [])],
            tracks=[Track.from_dict(d) for d in data.get("tracks", [])],
            envelopes=[Envelope.from_dict(d) for d in data.get("envelopes", [])],
        )

    def to_json(self, filepath: str) -> None:
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def from_json(cls, filepath: str) -> "Lattice":
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_tao(cls, tao, ix_branch=0, include_dump_file=False):
        elements = bpy_elements_from_tao(tao)
        orbit = floor_orbit_track_from_tao(tao)

        return cls(elements=elements, tracks=[orbit])

    def add_elements_to_blender(
        self,
        *,
        remove_unused: bool = True,
        catalogue: Path | None = None,
    ) -> None:
        return add_elements_to_blender(self.elements, catalogue=catalogue)

    def add_envelopes_to_blender(self, *, collection=None):
        return add_envelopes_to_blender(self.envelopes, collection=collection)

    def add_tracks_to_blender(self, *, collection=None):
        return add_tracks_to_blender(self.tracks, collection=collection)
