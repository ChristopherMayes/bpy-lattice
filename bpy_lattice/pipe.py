import numpy as np
from .mesh import build_aperture_mesh, rectangle_points, ellipse_points, revolve_section
from .types import ApertureType
import bpy


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


def make_centered_pipe(
    L=1,
    g=0,
    a=1,
    b=2,
    n=30,
    thickness=0.01,
    aperture_type: ApertureType = ApertureType.RECTANGULAR,
):
    # Baseline section
    aperture_type = ApertureType(aperture_type)

    if aperture_type == ApertureType.ELLIPTICAL:
        section0 = ellipse_points(a, b, n=n)
    elif aperture_type == ApertureType.RECTANGULAR:
        section0 = rectangle_points(a, b)

    if g == 0:
        srels = [-L / 2, L / 2]
    else:
        srels = np.linspace(-L / 2, L / 2, 20)

    inner_sections = [revolve_section(section0, s, g=g, L=L) for s in srels]

    vertices, faces = build_aperture_mesh(inner_sections)

    obj = create_blender_mesh_with_solidify(vertices, faces, thickness, apply=True)

    return obj
