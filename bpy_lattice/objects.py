import bpy
import numpy as np
from .mesh import build_aperture_mesh, rectangle_points, ellipse_points, revolve_section
from .types import ApertureShape


def create_blender_mesh_with_solidify(
    vertices,
    faces,
    thickness,
    mesh_name="PipeMesh",
    object_name="PipeObject",
    apply=True,
):
    """
    Create a Blender mesh and apply a Solidify modifier.

    Parameters
    ----------
    vertices : List[Tuple[float, float, float]]
        List of vertex coordinates.
    faces : List[Tuple[int, int, int, int]]
        List of face indices.
    thickness : float
        Thickness of the solidified object.
    apply : bool, optional
        Whether to apply the Solidify modifier immediately (default is True).
    """
    # Create mesh
    mesh = bpy.data.meshes.new(mesh_name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    # Create object and link to scene
    obj = bpy.data.objects.new(object_name, mesh)
    bpy.context.collection.objects.link(obj)

    # Ensure object is selected and active
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Apply Solidify Modifier
    solidify = obj.modifiers.new(name="Solidify", type="SOLIDIFY")
    solidify.thickness = thickness  # Set thickness
    solidify.offset = 1.0  # Expands outward

    # Apply the modifier
    if apply:
        bpy.ops.object.modifier_apply(modifier=solidify.name)

    # Deselect object after applying
    obj.select_set(False)

    return obj


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
    print("make_basic_pipe_object", aperture_shape)
    # Baseline section
    aperture_shape = ApertureShape(aperture_shape)

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

    obj = create_blender_mesh_with_solidify(
        vertices, faces, thickness, apply=True, object_name=name, mesh_name=name
    )

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
    # bpy.context.collection.objects.link(obj) # user should do this

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
