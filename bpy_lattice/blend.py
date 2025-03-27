import os
from pathlib import Path
import pathlib

import bpy

from .elements import AnyElement
from .objects import add_children_from_blend


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


def add_elements_to_blender(
    eles: list[AnyElement],
    *,
    remove_unused: bool = True,
    catalogue: pathlib.Path | None = None,
) -> None:
    if remove_unused:
        remove_unused_data()

    library_cache = {}
    library_collection_name = "library"
    library_collection = bpy.data.collections.new(library_collection_name)
    bpy.context.scene.collection.children.link(library_collection)

    if catalogue is None:
        catalogue = Path(os.path.expandvars("$BLENDER_CATALOGUE"))
        assert catalogue.exists()

    objs = []
    for ele in eles:
        collection_name = f"{ele.__class__.__name__}s"
        try:
            collection = bpy.data.collections[collection_name]
        except KeyError:
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
                    obj,
                    bfile,
                    library_cache,
                    collection=library_collection,
                )

        objs.append(obj)

        collection.objects.link(obj)
        for child in obj.children_recursive:
            collection.objects.link(child)

    bpy.context.view_layer.update()
    return library_cache, objs
