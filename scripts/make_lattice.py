import bpy
import bpy_lattice
import bpy_lattice.mesh
import bpy_lattice.objects
import bpy_lattice.elements

from pathlib import Path
import os
import importlib

from bpy_lattice.elements import load_elements_from_json
from bpy_lattice.objects import add_children_from_blend

importlib.reload(bpy_lattice)
importlib.reload(bpy_lattice.mesh)
importlib.reload(bpy_lattice.objects)
importlib.reload(bpy_lattice.elements)


def remove_unused_data():
    """
    Remove all unused datablocks from the current Blender file.
    This includes meshes, materials, textures, images, curves,
    armatures, lights, and collections with zero users.
    """
    for datablock in [
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.textures,
        bpy.data.images,
        bpy.data.curves,
        bpy.data.armatures,
        bpy.data.lights,
        bpy.data.collections,
    ]:
        for block in list(datablock):  # use list() to avoid modifying while iterating
            if block.users == 0:
                datablock.remove(block)


remove_unused_data()

JSON_FILE = Path("lat.json")

assert JSON_FILE.exists()

eles = load_elements_from_json(JSON_FILE)


library_cache = {}
library_collection_name = "library"
library_collection = bpy.data.collections.new(library_collection_name)
bpy.context.scene.collection.children.link(library_collection)


catalogue = Path(os.path.expandvars("$BLENDER_CATALOGUE"))
assert catalogue.exists()

objs = []
for ele in eles:
    # Make collection
    cname = ele.__class__.__name__ + "s"
    collection_name = cname
    # Get or create the target collection
    if collection_name in bpy.data.collections:
        collection = bpy.data.collections[collection_name]
    else:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

    obj = ele.to_object()

    bfile = None
    if ele.cad_model:
        bfile = Path(ele.cad_model)

        if not bfile.exists():
            bfile = catalogue / ele.cad_model

        if bfile.exists():
            print(f"Blend file exists: {bfile}")
            add_children_from_blend(
                obj, bfile, library_cache, collection=library_collection
            )

    objs.append(obj)

    collection.objects.link(obj)
    for child in obj.children_recursive:
        collection.objects.link(child)


bpy.context.view_layer.update()
