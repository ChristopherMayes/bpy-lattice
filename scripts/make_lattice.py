import bpy_lattice
import bpy_lattice.mesh
import bpy_lattice.objects
import bpy_lattice.elements
import bpy_lattice.blend

from pathlib import Path
import importlib

from bpy_lattice.elements import load_elements_from_json

importlib.reload(bpy_lattice)
importlib.reload(bpy_lattice.mesh)
importlib.reload(bpy_lattice.objects)
importlib.reload(bpy_lattice.elements)
importlib.reload(bpy_lattice.blend)


JSON_FILE = Path("lat.json")

assert JSON_FILE.exists()

eles = load_elements_from_json(JSON_FILE)

bpy_lattice.blend.add_elements_to_blender(eles)

bpy_lattice.blend.remamp_axes()
