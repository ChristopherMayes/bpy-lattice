
import bpy
from math import pi, sqrt
from bpy_lattice import materials

def camera_at(d):
  cam = bpy.data.objects['Camera'] # bpy.types.Camera
  cam.location.x = 0.0
  cam.location.y = -d/sqrt(2)
  cam.location.z = d/sqrt(2)
  cam.rotation_euler.x = pi/4
  cam.rotation_euler.y = 0
  cam.rotation_euler.z = 0

def ortho_camera_at(z, scale):
  cam = bpy.data.objects['Camera'] # bpy.types.Camera
  cam.data.type = 'ORTHO'
  cam.location.x = 0.0
  cam.location.y = 0
  cam.location.z = z
  cam.rotation_euler.x = 0
  cam.rotation_euler.y = 0
  cam.rotation_euler.z = 0
  cam.data.ortho_scale = scale
 

def lamp_energy(energy):
  lamp = bpy.data.objects['Lamp']
  lamp.location.z = 10
  lamp.data.energy = energy


def lighting(x,y,z):
    bpy.ops.mesh.primitive_plane_add(location=(x,y,z))
    bpy.context.active_object.data.materials.append(materials.LIGHT_MATERIAL)

def sun(strength):
    #bpy.data.node_groups["Shader Nodetree"].nodes["Emission"].inputs[1].default_value = 0.8
    bpy.ops.object.lamp_add(type='SUN', view_align=False, location=(0, 0, 10) )
    bpy.context.active_object.data.node_tree.nodes["Emission"].inputs[1].default_value = strength


# Floor
def make_floor():
    bpy.ops.mesh.primitive_plane_add(location=(0,0,0))  
    bpy.context.object.scale[0] = 20
    bpy.context.object.scale[1] = 10    
    mat = materials.diffuse_material('floor_material', color=(.2,.2,.2,1))
    bpy.context.active_object.data.materials.append(mat)


