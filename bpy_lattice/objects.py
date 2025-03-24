import bpy

import numpy as np
from .mesh import (
    build_aperture_mesh,
    rectangle_points,
    ellipse_points,
    revolve_section,
    create_solidified_mesh,
)
from .types import ApertureShape


def make_basic_empty_object(name="empty", empty_display_type="ARROWS"):
    # Create the empty object
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = empty_display_type
    return obj


def make_basic_pipe_object(
    name="basic_pipe",
    length=1,
    curvature=0,
    a=0.1,
    b=0.04,
    n=None,
    thickness=0.01,
    n_ellipse=30,
    a2=None,
    b2=None,
    aperture_shape: ApertureShape = ApertureShape.ELLIPTICAL,
):
    print(f"make_basic_pipe_object {length=}", aperture_shape)
    # Baseline section
    aperture_shape = ApertureShape(aperture_shape)

    length = max(length, 1e-6)  # TODO: better logic for zero length elements

    if aperture_shape == ApertureShape.ELLIPTICAL:
        section0 = ellipse_points(a, b, n=n_ellipse, a2=a2, b2=b2)
    elif aperture_shape == ApertureShape.RECTANGULAR:
        section0 = rectangle_points(a, b, a2=a2, b2=b2)
    else:
        raise ValueError(aperture_shape)

    if n is None:
        n = int(abs(curvature * length) * 180 / np.pi / 5)  # every 5 deg
    n = max(n, 2)
    srels = np.linspace(-length / 2, length / 2, n)

    inner_sections = [
        revolve_section(section0, s, g=curvature, L=length) for s in srels
    ]

    vertices, faces = build_aperture_mesh(inner_sections)

    mesh = create_solidified_mesh(vertices, faces, thickness, mesh_name=name)
    obj = bpy.data.objects.new(name, mesh)

    return obj


def make_basic_box_object(
    name="basic_box",
    length=1,
    width=2,
    height=0.5,
    x=0,
    y=0,
    z=0,
    curvature=0,
    n=None,
):
    print("make_basic_box_object")
    # Baseline section
    section0 = rectangle_points(width / 2, height / 2, x=x, y=y, z=z)

    if n is None:
        n = int(abs(curvature * length) * 180 / np.pi) + 1  # every deg
    n = max(n, 2)
    srels = np.linspace(-length / 2, length / 2, n)

    inner_sections = [
        revolve_section(section0, s, g=curvature, L=length) for s in srels
    ]

    vertices, faces = build_aperture_mesh(inner_sections, cap_ends=True)

    # Create mesh
    mesh_name = name  # same as object for simplicity
    mesh = bpy.data.meshes.new(mesh_name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    # Create object and link to scene
    obj = bpy.data.objects.new(name, mesh)

    return obj


def make_basic_dipole_object(
    name="basic_dipole",
    length=1,
    width=0.2,
    height=0.3,
    curvature=0,
    gap=0.1,
):
    height1 = (height - gap) / 2
    zoffset = gap / 2 + height1 / 2

    # make empty parent
    obj = bpy.data.objects.new(name, None)

    for z1, name1 in [(zoffset, "top"), (-zoffset, "bottom")]:
        child = make_basic_box_object(
            name=f"{name}_{name1}",
            length=length,
            width=width,
            height=height1,
            x=0,
            y=0,
            z=z1,
            curvature=curvature,
        )
        child.parent = obj

    return obj


def load_blend_objects(blend_filepath):
    """
    Load all objects from a .blend file.

    Parameters
    ----------
    blend_filepath : str
        Absolute path to the .blend file.

    Returns
    -------
    List[bpy.types.Object]
        List of Blender objects loaded from the file.
    """
    blend_filepath = str(blend_filepath)
    with bpy.data.libraries.load(blend_filepath, link=False) as (data_from, data_to):
        data_to.objects = data_from.objects
    return [obj for obj in data_to.objects if obj is not None]


def generate_unique_name(base_name, existing_names):
    """
    Generate a unique object name by appending a numeric suffix if needed.

    Parameters
    ----------
    base_name : str
        Proposed base name for the object.
    existing_names : set of str
        Set of names currently in use in bpy.data.objects.

    Returns
    -------
    str
        A unique object name.
    """
    count = 1
    new_name = base_name
    while new_name in existing_names:
        new_name = f"{base_name}_{count}"
        count += 1
    return new_name


def add_children_from_blend(
    parent, blend_filepath, library_cache, collection=None, copy_data=False
):
    """
    Load and parent child objects from a .blend file to a parent object.

    Ensures all child objects are uniquely named, unlinked from original
    collections, and correctly parented while preserving transforms.
    Optionally links them to a specified collection, and controls whether
    mesh data is copied or shared.

    Parameters
    ----------
    parent : bpy.types.Object
        The parent object to which imported children will be attached.
    blend_filepath : str
        Absolute path to the .blend file.
    library_cache : dict
        Dictionary to cache previously loaded libraries by filepath.
        Keys are filepaths, values are lists of previously loaded bpy objects.
    collection : bpy.types.Collection, optional
        The collection to link imported objects to. If None, uses context collection.
    copy_data : bool, optional
        If True, each object gets its own copy of the mesh data.
        If False, objects will share the same mesh datablock.

    Returns
    -------
    None
    """
    name_prefix = parent.name
    existing_names = {obj.name for obj in bpy.data.objects}

    if blend_filepath in library_cache:
        print(f"Library already loaded: {blend_filepath}")
        children = []
        for source_obj in library_cache[blend_filepath]:
            if source_obj.type == "MESH":
                new_data = source_obj.data.copy() if copy_data else source_obj.data
            else:
                new_data = source_obj.data  # For empties, lights, etc.
            new_name = generate_unique_name(
                f"{name_prefix}_{source_obj.name}", existing_names
            )
            new_obj = bpy.data.objects.new(new_name, new_data)
            new_obj.location = source_obj.location.copy()
            new_obj.rotation_euler = source_obj.rotation_euler.copy()
            new_obj.scale = source_obj.scale.copy()
            children.append(new_obj)
            existing_names.add(new_name)
    else:
        print(f"Loading new library: {blend_filepath}")
        children = load_blend_objects(blend_filepath)
        library_cache[blend_filepath] = children

    print("len children", len(children))
    target_collection = collection or bpy.context.collection

    for child in children:
        for c in list(child.users_collection):
            c.objects.unlink(child)

        target_collection.objects.link(child)

        if child.parent is None:
            child.parent = parent
            child.matrix_parent_inverse = parent.matrix_world.inverted()
