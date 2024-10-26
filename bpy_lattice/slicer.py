import bpy

from mathutils import Matrix

def slice_object(object, punch, use_ops_method=False):
    if object.type != 'MESH': return
    print('slicing', object.name, 'with',punch.name)
    if object == punch:
        print(object.name, punch.name)
        return
    if object.data.users > 1:
        print(object.name, ' data already has users, skipping slice')
        return
    object.modifiers.new('cut', type = 'BOOLEAN')
    object.modifiers['cut'].operation = 'DIFFERENCE'
    object.modifiers['cut'].object = punch
    if use_ops_method:
        bpy.context.view_layer.objects.active = object
        bpy.ops.object.modifier_apply(apply_as='DATA', modifier='cut')
        return
    # Save old mesh    
    old_mesh = object.data

    #new_mesh = object.to_mesh(scene=bpy.context.scene, apply_modifiers=True, settings='PREVIEW')
    new_mesh = object.to_mesh()
    

    
    print('sliced number of vertices: ', len(new_mesh.vertices))
    object.data = new_mesh

    # Cleanup
    print('cleaning up')
    object.modifiers.clear()
    bpy.data.meshes.remove(old_mesh)
    
    #name = 'sliced_'+object.name
    #object.name = name
    
    
def cube_slicer(location=(0,0,0)):    
    bpy.ops.mesh.primitive_cube_add(location=location)
    punch = bpy.context.view_layer.objects.active
    punch.name = 'slicer'
    #Shift up and move to obj
    #punch.scale = Vector((5,1,1))
    # Scale doesn't work properly. Scale by hand:
    mat = Matrix([[5,0,0],[0,1,0],[0,0,1]])
    for v in punch.data.vertices:
        v.co = mat @ v.co 
    print('punch.name = ', punch.name)
    return punch
    
def slice_all():
    i = 1
    punch = cube_slicer(location=(0,0, 1))
    imax = len(bpy.data.objects)
    olist = [o for o in bpy.data.objects]
    #myo = bpy.context.scene.objects.active 
    #olist = [o for o in bpy.data.objects]
    #olist = [myo]
    for o in olist:
        if o == punch: continue
        print(o.name, i, '/', imax)
        slice_object(o, punch)
        i = i + 1    
    bpy.context.scene.objects.active = punch
    bpy.ops.object.delete()
    
if __name__=='__main__':
    slice_all()

#    i = 1
 #   object = bpy.context.scene.objects.active
#    punch= plane_slicer(location=(0,0,0))
    #slice(o, plane)
   # object.modifiers.new('Boolean', type = 'BOOLEAN')
#    print('2')
  #  object.modifiers["Boolean"].object = punch
#    print('3')
 #   object.modifiers["Boolean"].operation = 'DIFFERENCE'
#    print('4')
    
#    bpy.context.scene.objects.active = object
 #   bpy.ops.object.modifier_apply(apply_as='DATA', modifier="Boolean")
    #new_mesh = object.to_mesh(scene=bpy.context.scene, apply_modifiers=True, settings='PREVIEW')
    #new_mesh.name = 'sliced_'+new_mesh.name
    #object.data = new_mesh
    #print('5')
    
    
    
    #imax = len(bpy.data.objects)
    
    #slice_object_with(o, plane)
    

    #for o in bpy.data.objects:
    #    if o == plane: continue
    #    print(o.name, i, '/', imax)
    #    slice_object_with(o, plane)
    #    i = i + 1
        
    #bpy.context.scene.objects.active = plane
    #bpy.ops.object.delete()