import importlib

import bpy_lattice
import bpy_lattice.mesh
import bpy_lattice.objects
import bpy_lattice.elements
import bpy_lattice.blend
from bpy_lattice import Lattice, remap_zx

importlib.reload(bpy_lattice)
importlib.reload(bpy_lattice.mesh)
importlib.reload(bpy_lattice.objects)
importlib.reload(bpy_lattice.elements)
importlib.reload(bpy_lattice.tracks)
importlib.reload(bpy_lattice.blend)

JSON_FILE = "lat.json"

lattice = Lattice.from_json(JSON_FILE)

# Add elements
lattice.add_elements_to_blender()

# Add tracks (orbit)
lattice.add_tracks_to_blender()

# Remap Z->X
remap_zx()
