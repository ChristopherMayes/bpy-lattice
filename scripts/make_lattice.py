import bpy
import bpy_lattice
import importlib
from bpy_lattice.elements import load_elements_from_json
from pathlib import Path
import bpy_lattice.mesh
import bpy_lattice.objects
import bpy_lattice.elements

importlib.reload(bpy_lattice)
importlib.reload(bpy_lattice.mesh)
importlib.reload(bpy_lattice.objects)
importlib.reload(bpy_lattice.elements)


def remove_unused_data():
    for datablock in [
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.textures,
        bpy.data.images,
        bpy.data.curves,
        bpy.data.armatures,
        bpy.data.lights,
    ]:
        for block in datablock:
            if block.users == 0:
                datablock.remove(block)


remove_unused_data()

JSON_FILE = Path("lat.json")

assert JSON_FILE.exists()

eles = load_elements_from_json(JSON_FILE)


objs = []
for ele in eles:
    obj = ele.to_object()
    objs.append(obj)


def link_object_and_children(obj, collection):
    """
    Recursively link an object and all of its children to the specified collection.
    Avoids linking duplicates.
    """
    if obj.name not in collection.objects:
        collection.objects.link(obj)
    for child in obj.children:
        link_object_and_children(child, collection)


def link_objects_to_scene(objects):
    """
    Efficiently link a list of objects to the active scene:
    - Links only root objects directly
    - Recursively ensures all children are also linked to the scene's collection
    """
    scene_collection = bpy.context.scene.collection

    # Filter out objects not in bpy.data.objects (just in case)
    objects = [obj for obj in objects if obj.name in bpy.data.objects]

    # Find root objects (those without a parent in the list)
    roots = [obj for obj in objects if obj.parent not in objects]

    for root in roots:
        link_object_and_children(root, scene_collection)


link_objects_to_scene(objs)
bpy.context.view_layer.update()
