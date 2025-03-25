import bpy
import bmesh
import os
import statistics
import argparse
from mathutils import Vector

def process_obj(obj_file_path):
    # Clear all existing objects in Blender to ensure a clean environment
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Import OBJ file
    bpy.ops.wm.obj_import(filepath=obj_file_path)
    
    # Get the newly imported OBJ object
    obj = bpy.context.selected_objects[0]  # Assuming the imported OBJ file contains only one object

    # Apply transformations and modify the object
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.scale *= 0.004
    bpy.ops.object.transform_apply(scale=True)
    obj.location.z += 0.2
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh_center = sum((v.co for v in obj.data.vertices), Vector()) / len(obj.data.vertices)
    obj.location -= mesh_center

    # Enter edit mode for cutting operations
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    bm.normal_update()

    z_values = [v.co.z for v in bm.verts]
    z_median = statistics.median(z_values)

    # Perform cutting operations
    bmesh.ops.bisect_plane(
        bm,
        dist=0.01,
        geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
        plane_co=(0, 0, z_median + 1.1),
        plane_no=(0, 0, 1),
        clear_outer=True,
        clear_inner=False  
    )
    bmesh.ops.bisect_plane(
        bm,
        dist=0.01,
        geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
        plane_co=(0, 0, z_median - 0.3),
        plane_no=(0, 0, -1),
        clear_outer=True,  
        clear_inner=False
    )

    # Delete all vertices except the largest connected component
    for v in bm.verts:
        v.tag = False
    connected_components = []
    def walk(vert, visited):
        stack = [vert]
        while stack:
            v = stack.pop()
            if not v.tag:
                v.tag = True
                visited.add(v)
                stack.extend([e.other_vert(v) for e in v.link_edges if not e.other_vert(v).tag])
    for v in bm.verts:
        if not v.tag:
            verts_visited = set()
            walk(v, verts_visited)
            connected_components.append(verts_visited)

    largest_component = max(connected_components, key=len)
    all_other_verts = [v for component in connected_components if component != largest_component for v in component]
    bmesh.ops.delete(bm, geom=all_other_verts, context='VERTS')
    
    bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Save the processed OBJ file, overwriting the original file
    bpy.ops.wm.obj_export(filepath=obj_file_path, export_selected_objects=True)

# Set up command line argument parsing
parser = argparse.ArgumentParser(description="Process 3D model files in Blender by cleaning and trimming them")
parser.add_argument('folder_path', type=str, help="Path to the directory containing model folders")
args = parser.parse_args()

# Iterate through all subfolders in the specified folder and process each OBJ file
folder_path = args.folder_path
for folder in os.listdir(folder_path):
    sub_folder_path = os.path.join(folder_path, folder)
    if os.path.isdir(sub_folder_path):
        for file_name in os.listdir(sub_folder_path):
            if file_name.endswith('.obj'):
                obj_path = os.path.join(sub_folder_path, file_name)
                process_obj(obj_path)

print("All files processed successfully.")