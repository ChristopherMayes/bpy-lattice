import bpy_lattice
import bpy_lattice.mesh
import bpy_lattice.objects
import bpy_lattice.elements
import bpy_lattice.blend

from pathlib import Path
import importlib

from bpy_lattice.elements import load_elements_from_json
from bpy_lattice.tracks import load_tracks_from_json


importlib.reload(bpy_lattice)
importlib.reload(bpy_lattice.mesh)
importlib.reload(bpy_lattice.objects)
importlib.reload(bpy_lattice.elements)
importlib.reload(bpy_lattice.tracks)
importlib.reload(bpy_lattice.blend)


JSON_FILE = Path("lat.json")

assert JSON_FILE.exists()

eles = load_elements_from_json(JSON_FILE)

bpy_lattice.blend.add_elements_to_blender(eles)


# Tracks
tracks_file = Path("tracks.json")
if tracks_file.exists():
    tracks = load_tracks_from_json(tracks_file)
    bpy_lattice.blend.add_tracks_to_blender(tracks)

bpy_lattice.blend.remamp_axes()
