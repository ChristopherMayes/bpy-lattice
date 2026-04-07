from typing import Optional, Dict, List, Any
from dataclasses import dataclass, fields
import json
from pathlib import Path
from .blend import (
    add_elements_to_blender,
    add_tracks_to_blender,
    add_envelopes_to_blender,
)
from .usd import lattice_to_usd
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

    def to_usd(
        self,
        filepath: str | Path = "lattice.usda",
        *,
        up_axis: str = "Y",
        meters_per_unit: float = 1.0,
        catalogue: str | Path | None = None,
        blender_cmd: str | None = None,
        copy_models: bool = True,
        models_dir: str | Path | None = None,
    ):
        """
        Export the lattice to a USD file.

        Parameters
        ----------
        filepath : str or Path
            Output file path.  Use ``.usda`` for ASCII, ``.usd`` / ``.usdc``
            for binary.
        up_axis : str
            ``'Y'`` (USD / Omniverse default) or ``'Z'``.
        meters_per_unit : float
            Scene scale factor (default ``1.0`` = metres).
        catalogue : str or Path, optional
            Directory containing CAD model files.  Element
            ``cad_model`` paths are resolved relative to this.
        blender_cmd : str, optional
            Path to the Blender executable for ``.blend`` → ``.usd``
            conversion.  Auto-detected if *None*.
        copy_models : bool
            If ``True`` (default), USD model files from the catalogue
            are copied next to the output for portability.  If
            ``False``, they are referenced in place.
        models_dir : str or Path, optional
            Directory for converted / copied CAD model files.  Defaults
            to a ``models/`` subdirectory next to the output file.

        Returns
        -------
        pxr.Usd.Stage
        """
        return lattice_to_usd(
            elements=self.elements,
            tracks=self.tracks,
            envelopes=self.envelopes,
            filepath=filepath,
            up_axis=up_axis,
            meters_per_unit=meters_per_unit,
            catalogue=catalogue,
            blender_cmd=blender_cmd,
            copy_models=copy_models,
            models_dir=models_dir,
        )
