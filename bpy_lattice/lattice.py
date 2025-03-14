import bpy
import bmesh
import os
import re
from mathutils import Matrix, Vector
from math import sin, cos, pi
from typing import Tuple, Optional, List

from bpy_lattice import materials
from .constants import ELE_COLOR, ELE_X_SCALE, ELE_X_SCALE_FACTOR
from .elements import (
    map_table_element,
    Element,
    SBend,
    Pipe,
)  # Needed for old code referencing lattice.import_lattice


def ele_material(ele: Element):
    key = ele.key
    name = key + "_material"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    return materials.diffuse_material(name, color=ele_color(ele) + tuple([1]))


def blendfile(ele: Element):
    match = re.search("3DMODEL=(.+?).blend", ele.descrip)
    if match:
        return match.group(1) + ".blend"
    else:
        return None


def ele_x_scale(ele: Element):
    """
    Scale factor for an element
    """
    key = ele.key
    scale = 1
    if key in ELE_X_SCALE:
        scale = ELE_X_SCALE[key]
    else:
        print(f"missing {key} in ELE_X_SCALE ")

    return ELE_X_SCALE_FACTOR * scale


def ele_color(ele: Element):
    """
    Color for an element
    """
    color = (0, 0, 0)
    key = ele.key
    if key in ELE_COLOR:
        color = ELE_COLOR[key]

    return color


def faces_from(sections, closed=True):
    """
    A section is a list of vertices that defines a cross-section of an element
    This makes rectangle faces
    """
    nix = [len(s) for s in sections]
    if len(set(nix)) > 1:
        print("ERROR: sections must have the same number of points")
        return
    n = nix[0]
    faces = []
    for i0 in range(len(sections) - 1):
        for j in range(n - 1):
            faces.append(
                (i0 * n + j, (i0 + 1) * n + j, (i0 + 1) * n + j + 1, i0 * n + j + 1)
            )
        faces.append((i0 * n + n - 1, (i0 + 1) * n + n - 1, (i0 + 1) * n, i0 * n))
    if closed:
        faces.append(list(reversed(range(n))))  # first section
        faces.append(
            range((len(sections) - 1) * n, (len(sections) - 1) * n + n)
        )  # Last section
    return faces


def box_section(X, haperture, vaperture):
    return (
        (X, haperture, vaperture),
        (X, -haperture, vaperture),
        (X, -haperture, -vaperture),
        (X, haperture, -vaperture),
    )


def ellipse_section(X, haperture, vaperture, n=30):
    angles = [2 * pi * i / n for i in range(n)]
    return [(X, haperture * cos(a), vaperture * sin(a)) for a in angles]


def multipole_section(X, aperture, n):
    angles = [pi * i / n + pi / (2 * n) for i in range(2 * n)]
    return [(X, aperture * cos(a), aperture * sin(a)) for a in angles]


def ele_section(s_rel, ele: Element):
    """
    Make sections relative to center of element
    """
    sc = ele_x_scale(ele)
    if ele.key == "QUADRUPOLE":
        return multipole_section(s_rel, sc, 4)
    if ele.key == "SEXTUPOLE":
        return multipole_section(s_rel, sc, 6)
    elif isinstance(ele, SBend):
        a = ele.angle
        if abs(a) < 1e-5 or abs(ele.L) < 1e-5:
            return box_section(s_rel, sc, sc)
        L = ele.L
        rho = L / a
        # Baseline section
        s0 = box_section(0, sc, sc)
        # Edge angle
        f = s_rel / L + 0.5
        edge = ele.e2 * f + (-1) * ele.e1 * (1 - f)
        m0 = Matrix.Rotation(edge, 4, "Z")
        m1 = Matrix.Translation((0, rho, 0))
        m2 = Matrix.Rotation(-s_rel / rho, 4, "Z")
        m3 = Matrix.Translation((0, -rho, 0))
        m = m3 @ m2 @ m1 @ m0
        sec = []
        for p in s0:
            v = m @ Vector(p)
            sec.append(v[:])
        return sec

    elif ele.key == "WIGGLER":
        return box_section(s_rel, sc, 2 * sc)
    elif isinstance(ele, Pipe):
        rx = ele.radius_x
        ry = ele.radius_y
        t = ele.thickness
        if rx == 0 or ry == 0:
            return ellipse_section(s_rel, sc, sc)
        else:
            return ellipse_section(s_rel, rx + t, ry + t)
    else:
        return ellipse_section(s_rel, sc, sc)


def ele_mesh(ele: Element):
    name = ele.name
    print("Mesh: ", name)
    L = ele.L
    if ele.key == "SBEND":
        n = 20
        slist = [L * i / (n - 1) - L / 2 for i in range(n)]
    else:
        slist = [-L / 2, L / 2]
    sections = [ele_section(s_rel, ele) for s_rel in slist]
    faces = faces_from(sections)
    verts = []
    for s in sections:
        for p in s:
            verts.append(p)

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update(calc_edges=True)
    return mesh


# ------ Pipe stuff


def rotate_mesh(mesh, mat=Matrix.Rotation(pi / 2, 4, "Y")):
    for v in mesh.vertices:
        v.co = mat * v.co


def new_ellipse(radius_x=1, radius_y=1, length=1, vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius_x, depth=length, vertices=vertices
    )
    ob = bpy.context.scene.objects.active
    mesh = ob.data
    for v in mesh.vertices:
        v.co[0] *= radius_y / radius_x
    return ob


# ------------------------------------------


def load_blend(filepath):
    """
    Load .blend model objects.
    """
    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        onames = [name for name in data_from.objects if True]
        print("Library: ", filepath)
        print("         has objects", onames)
        data_to.objects = data_from.objects
    return data_to.objects


def add_children_from_blend(parent, blendfilepath, libdict):
    if blendfilepath in libdict:
        print("Library already loaded: ", blendfilepath)
        print("Data will be linked")
        # Library has already been loaded. Copy meshes and materials
        children = []
        for o in libdict[blendfilepath]:
            child = bpy.data.objects.new(o.name, o.data)
            child.location = o.location
            child.rotation_euler = o.rotation_euler
            children.append(child)
    else:
        print("New library: ", blendfilepath)
        children = load_blend(blendfilepath)
        libdict[blendfilepath] = children
    for child in children:
        bpy.context.collection.objects.link(child)
        if child.parent is None:
            child.parent = parent


def fix_mesh(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()


def old_fix_mesh(object):
    bpy.context.scene.objects.active = object
    bpy.ops.object.mode_set(mode="EDIT")

    # select all faces
    bpy.ops.mesh.select_all(action="SELECT")

    # recalculate outside normals
    bpy.ops.mesh.normals_make_consistent(inside=False)

    # go object mode again
    bpy.ops.object.editmode_toggle()


def ele_object(
    ele: Element,
    library: dict = {},
    use_real_model: bool = False,
    catalogue: Optional[str] = None,
    hide_real_model: bool = True,
    keep_simple_model: bool = True,
):
    print("Object: ", ele.name)

    # Load blender model of element
    bfile = blendfile(ele)

    # Setup material
    mat = ele_material(ele)
    mat.diffuse_color = ele_color(ele) + tuple([1])

    object = None
    if bfile and use_real_model and catalogue:
        f = os.path.join(catalogue, bfile)
        if os.path.isfile(f):
            print("blend file: ", f, "exists!")

            # Setup parent
            if keep_simple_model:
                object = bpy.data.objects.new(ele.name, ele_mesh(ele))
                object.data.materials.append(mat)
            else:
                object = bpy.data.objects.new(ele.name, None)
            bpy.context.collection.objects.link(object)

            # Add the CAD model from blend file
            add_children_from_blend(object, f, library)

            # Hide options for preview
            if hide_real_model:
                for c in object.children:
                    c.hide_set(True)
            else:
                object.hide_set(True)
            object.hide_render = True
        else:
            print("Blend file missing: ", f)

    if object is None:
        object = bpy.data.objects.new(ele.name, ele_mesh(ele))
        object.data.materials.append(mat)
        bpy.context.collection.objects.link(object)

    object.location = (0, 0, 0)

    return object


def ele_objects(
    eles: List[Element],
    library: dict = {},
    use_real_model: bool = False,
    catalogue: Optional[str] = None,
    hide_real_model: bool = True,
    origin: Tuple[float, float, float] = (0, 0, 0),
    keep_simple_model: bool = True,
):
    """
    Create multiple objects from a list of eles (a lattice)
    """
    Xcenter, Ycenter, Zcenter = origin

    objects = []
    for ele in eles:
        if ele.L == 0:
            if ele.key in ("MARKER", "MIRROR"):
                ele.L = 1e-3
            else:
                continue

        ob = ele_object(
            ele,
            library=library,
            use_real_model=use_real_model,
            hide_real_model=hide_real_model,
            catalogue=catalogue,
            keep_simple_model=keep_simple_model,
        )

        # Set location and angles
        ob.rotation_euler.z = ele.theta
        ob.rotation_euler.y = -ele.phi
        ob.rotation_euler.x = ele.psi
        ob.location = (ele.z - Xcenter, ele.x - Ycenter, ele.y - Zcenter)

        objects.append(ob)

    return objects


def lat_borders(lat, dim="x"):
    xlist = [ele[dim] for ele in lat]
    return min(xlist), max(xlist)


def import_lattice(file):
    with open(file, "r") as f:
        next(f)  # Skip the header line
        lat = [map_table_element(line) for line in f]
    return lat
