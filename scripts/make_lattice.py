# bpy_lattice make_lattice script
# 
import bpy
from bpy_lattice import lattice, slicer
from mathutils import Vector
import os


# For development
import imp
imp.reload(lattice)


FILE = 'lat.layout_table'
# Change the overall scale factor for drawing elements
lattice.ELE_X_SCALE_FACTOR = 3

# Change a particular type of element scale
lattice.ELE_X_SCALE['LCAVITY'] = 0.1

# Basic settings
SETTINGS = {
'use_real_model':True,
'catalogue':None,
'hide_real_model':True,
'origin': (0, 0, 0)
}


# Import layout_talbe
print('Importing', FILE)
eles = lattice.import_lattice(FILE)    

# Create objects
objects = lattice.ele_objects(eles, **SETTINGS)


# Optional: Slice
#slicer_object = slicer.cube_slicer()
slicer_object = None

if slicer_object:
    print('slicing with ')
    for ob in objects:  
        slicer_object.location = ob.location +Vector((0,0,1))
        print(ob, ob.children)
        for c in ob.children:
            print('slicing child')
            slicer.slice_object(c, slicer_object, use_ops_method=True)
        slicer.slice_object(ob, slicer_object, use_ops_method=True)            