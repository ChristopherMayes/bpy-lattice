import bpy


def emission_material(name, strength=50):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    for n in nodes:  # Clear out default nodes
        nodes.remove(n)
    node = nodes.new(type="ShaderNodeEmission")
    # node_emission.inputs[0].default_value = (0,1,0,1)  # green RGBA
    node.inputs[1].default_value = strength  # strength
    # node_emission.location = 0,0
    node_output = nodes.new(type="ShaderNodeOutputMaterial")
    node_output.location = 400, 0
    links = mat.node_tree.links
    links.new(node_output.inputs[0], node.outputs[0])
    return mat


def diffuse_material(name, color=(1, 0, 0, 1)):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    for n in nodes:  # Clear out default nodes
        nodes.remove(n)
    node = nodes.new(type="ShaderNodeBsdfDiffuse")

    node.inputs[0].default_value = color
    # node.inputs[1].default_value = strength # strength
    # node_emission.location = 0,0
    node_output = nodes.new(type="ShaderNodeOutputMaterial")
    node_output.location = 400, 0
    links = mat.node_tree.links
    links.new(node_output.inputs[0], node.outputs[0])
    return mat


LIGHT_MATERIAL = emission_material("light", strength=100)
