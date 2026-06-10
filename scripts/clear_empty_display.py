import bpy

for obj in bpy.data.objects:
    if obj.type == "EMPTY":
        # obj.empty_display_type = 'SPHERE'
        obj.empty_display_size = 0
