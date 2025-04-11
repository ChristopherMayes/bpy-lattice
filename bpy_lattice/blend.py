import os
from pathlib import Path
import pathlib

import bpy

from .elements import AnyElement, Bend, Undulator
from .tracks import Track
from .objects import add_children_from_blend, remap_axes


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

    elements_collection_name = "Elements"
    elements_collection = bpy.data.collections.new(elements_collection_name)
    bpy.context.scene.collection.children.link(elements_collection)

    library_cache = {}
    library_collection_name = "Library"
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
            # bpy.context.scene.collection.children.link(collection)

            # Link under Elements
            elements_collection.children.link(collection)

        bfile = None
        if ele.cad_model:
            bfile = Path(ele.cad_model)

            if not bfile.exists():
                bfile = catalogue / ele.cad_model

            if bfile.exists():
                print(f"✅ Blend file exists: {bfile}")
                obj = ele.to_empty_object()
                obj.empty_display_type = "ARROWS"
                obj.empty_display_size = 0.1
                add_children_from_blend(
                    obj,
                    bfile,
                    library_cache,
                    collection=library_collection,
                )
                if isinstance(ele, (Bend, Undulator)):
                    aperture_obj = ele.aperture_object()
                    if aperture_obj is not None:
                        aperture_obj.parent = obj

            else:
                print(f"⛔️ MISSING Blend file: {bfile}")
                obj = ele.to_object()

        else:
            obj = ele.to_object()

        objs.append(obj)

        collection.objects.link(obj)
        for child in obj.children_recursive:
            collection.objects.link(child)

    bpy.context.view_layer.update()

    return library_cache, objs


def add_tracks_to_blender(tracks: list[Track], collection=None):
    if collection is None:
        collection = bpy.data.collections.new("Tracks")
        bpy.context.scene.collection.children.link(collection)
    for track in tracks:
        curve = track.to_curve()
        collection.objects.link(curve)


def remamp_axes(objects=None):
    if objects is None:
        objects = bpy.data.objects
    print(f"🟣 remapping {len(objects)} objects Z->X")
    parentless_objects = [obj for obj in objects if obj.parent is None]
    remap_axes(parentless_objects, x_axis="Z", y_axis="X", z_axis="Y")
