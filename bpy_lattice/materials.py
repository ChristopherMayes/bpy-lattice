import bpy
from .colors import resolve_color

# def emission_material(name, strength=50):
#    mat = bpy.data.materials.new(name)
#    mat.use_nodes = True
#    nodes = mat.node_tree.nodes
#    for n in nodes:  # Clear out default nodes
#        nodes.remove(n)
#    node = nodes.new(type="ShaderNodeEmission")
#    # node_emission.inputs[0].default_value = (0,1,0,1)  # green RGBA
#    node.inputs[1].default_value = strength  # strength
#    # node_emission.location = 0,0
#    node_output = nodes.new(type="ShaderNodeOutputMaterial")
#    node_output.location = 400, 0
#    links = mat.node_tree.links
#    links.new(node_output.inputs[0], node.outputs[0])
#    return mat
#
#
# def diffuse_material(name, color=(1, 0, 0, 1)):
#    mat = bpy.data.materials.new(name)
#    mat.use_nodes = True
#    nodes = mat.node_tree.nodes
#    for n in nodes:  # Clear out default nodes
#        nodes.remove(n)
#    node = nodes.new(type="ShaderNodeBsdfDiffuse")
#
#    node.inputs[0].default_value = color
#    # node.inputs[1].default_value = strength # strength
#    # node_emission.location = 0,0
#    node_output = nodes.new(type="ShaderNodeOutputMaterial")
#    node_output.location = 400, 0
#    links = mat.node_tree.links
#    links.new(node_output.inputs[0], node.outputs[0])
#    return mat
#
#
# LIGHT_MATERIAL = emission_material("light", strength=100)


def assign_color_material(obj, color, material_name_prefix="Mat"):
    """
    Create and assign a diffuse material with the given color to a Blender object.

    Args:
        obj: The Blender object to assign the material to.
        color: The color (ColorName, str, hex, or tuple).
        material_name_prefix: Prefix for the auto-generated material name.
    """
    if not hasattr(obj, "data") or not hasattr(obj.data, "materials"):
        print(f"⚠️ Object '{obj.name}' does not support materials. Skipping.")
        return None

    rgba = resolve_color(color)
    color_str = f"{int(rgba[0]*255):02x}{int(rgba[1]*255):02x}{int(rgba[2]*255):02x}"
    mat_name = f"{material_name_prefix}_{color_str}"

    # Check if material already exists
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = rgba

    # Assign material to object
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    return mat
