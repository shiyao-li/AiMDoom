import bpy
import os
import shutil
import argparse

def process_folder(folder_path):
    # Ensure we are in object mode
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    # Delete all objects in the scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Delete all collections
    for collection in bpy.data.collections:
        bpy.data.collections.remove(collection)

    # Automatically find OBJ file and texture folder
    obj_filename = None
    texture_folder = None

    for file in os.listdir(folder_path):
        if file.lower().endswith(".obj"):
            obj_filename = file
        if os.path.isdir(os.path.join(folder_path, file)):
            texture_folder = os.path.join(folder_path, file)

    if not obj_filename or not texture_folder:
        raise FileNotFoundError("OBJ file or texture folder not found")

    # Import OBJ file
    import_path = os.path.join(folder_path, obj_filename)
    print("Importing OBJ file from:", import_path)
    bpy.ops.wm.obj_import(filepath=import_path)

    # Select the newly imported object
    original_obj = bpy.context.selected_objects[0]

    # Duplicate the object
    bpy.ops.object.duplicate(linked=False, mode='TRANSLATION')
    duplicated_obj = bpy.context.selected_objects[0]
    bpy.context.view_layer.objects.active = duplicated_obj
    duplicated_obj.name = "dup.obj"  
    duplicated_obj.select_set(True)
    original_obj.select_set(False)

    # Remove all materials
    duplicated_obj.data.materials.clear()

    # Create new material and set up nodes
    new_material = bpy.data.materials.new(name="NewMaterial")
    duplicated_obj.data.materials.append(new_material)
    new_material.use_nodes = True
    nodes = new_material.node_tree.nodes
    links = new_material.node_tree.links

    # Clear default nodes
    for node in nodes:
        nodes.remove(node)

    # Create and link nodes
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
    image_texture_node = nodes.new(type='ShaderNodeTexImage')
    links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])
    links.new(image_texture_node.outputs['Color'], bsdf_node.inputs['Base Color'])

    # Create new 2048x2048 image
    baked_image = bpy.data.images.new(name="BakedTexture", width=2048, height=2048)
    image_texture_node.image = baked_image

    # Set roughness
    bsdf_node.inputs['Roughness'].default_value = 1.0

    # Set render engine to Cycles
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.feature_set = 'SUPPORTED'

    # Set bake type to diffuse
    bpy.context.scene.cycles.bake_type = 'DIFFUSE'

    # Turn off direct and indirect contributions
    bpy.context.scene.render.bake.use_pass_direct = False
    bpy.context.scene.render.bake.use_pass_indirect = False
    bpy.context.scene.render.bake.use_pass_color = True

    # Set baking options
    bpy.context.scene.render.bake.use_selected_to_active = True
    bpy.context.scene.render.bake.use_cage = False
    bpy.context.scene.render.bake.cage_extrusion = 0.01

    # UV unwrap
    bpy.context.view_layer.objects.active = duplicated_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project()
    bpy.ops.object.mode_set(mode='OBJECT')

    # Bake texture
    original_obj.select_set(True)
    duplicated_obj.select_set(True)
    print("Starting baking...")
    bpy.ops.object.bake(type='DIFFUSE')
    print("Baking complete.")

    # Export new OBJ, MTL and texture
    export_path = os.path.join(folder_path, "exported")
    os.makedirs(export_path, exist_ok=True)

    # Set export filename
    export_obj_filename = "dup_modified.obj"  # Set export filename to dup_modified.obj
    export_obj_filepath = os.path.join(export_path, export_obj_filename)

    # Save texture
    new_texture_path = os.path.join(export_path, "new_texture.png")
    try:
        baked_image.save_render(filepath=new_texture_path)
        print("Texture saved to:", new_texture_path)
    except Exception as e:
        print("Error saving texture:", e)

    # Modify texture path in material
    if duplicated_obj.data.materials:
        for mat in duplicated_obj.data.materials:
            if mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        node.image.filepath = new_texture_path

    # Create a new temporary collection and move the duplicated object to it
    temp_collection = bpy.data.collections.new(name="TempCollection")
    bpy.context.scene.collection.children.link(temp_collection)
    bpy.ops.object.select_all(action='DESELECT')
    duplicated_obj.select_set(True)
    bpy.ops.collection.objects_remove_all()
    temp_collection.objects.link(duplicated_obj)

    # Ensure export path uses relative paths
    bpy.context.preferences.filepaths.use_relative_paths = True

    # Export OBJ file and generate new MTL file
    bpy.ops.wm.obj_export(
        filepath=export_obj_filepath,
        export_material_groups=True,
        export_selected_objects=True,
        path_mode='STRIP'
    )

    # Get current directory
    current_folder = folder_path

    # Find OBJ and MTL files in current folder
    obj_file = None
    mtl_file = None
    for file in os.listdir(current_folder):
        if file.lower().endswith('.obj'):
            obj_file = file
        elif file.lower().endswith('.mtl'):
            mtl_file = file

    # Check if OBJ file was found
    if not obj_file:
        raise FileNotFoundError("OBJ file not found")

    # Copy OBJ filename (without extension)
    original_name = os.path.splitext(obj_file)[0]

    # Delete current OBJ, MTL files and textures folder
    if obj_file:
        os.remove(os.path.join(current_folder, obj_file))
    if mtl_file:
        os.remove(os.path.join(current_folder, mtl_file))
    textures_folder = os.path.join(current_folder, 'textures')
    if os.path.exists(textures_folder):
        shutil.rmtree(textures_folder)

    # Copy all files from exported folder to current folder
    exported_folder = os.path.join(current_folder, 'exported')
    if os.path.exists(exported_folder):
        for item in os.listdir(exported_folder):
            s = os.path.join(exported_folder, item)
            d = os.path.join(current_folder, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        # Delete exported folder
        shutil.rmtree(exported_folder)

    # Rename OBJ and MTL files to match original OBJ filename
    for file in os.listdir(current_folder):
        if file.lower().endswith('.obj'):
            new_obj_name = original_name + '.obj'
            os.rename(os.path.join(current_folder, file), os.path.join(current_folder, new_obj_name))
        elif file.lower().endswith('.mtl'):
            new_mtl_name = original_name + '.mtl'
            os.rename(os.path.join(current_folder, file), os.path.join(current_folder, new_mtl_name))

    # Delete all objects in the scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Delete all collections
    for collection in bpy.data.collections:
        bpy.data.collections.remove(collection)

# Set up command line argument parsing
parser = argparse.ArgumentParser(description="Process 3D model files in Blender by baking textures and simplifying materials")
parser.add_argument('main_folder_path', type=str, help="Path to the main directory containing model folders")
args = parser.parse_args()

main_folder_path = args.main_folder_path

# Process all subfolders in the main folder
for sub_folder in os.listdir(main_folder_path):
    sub_folder_path = os.path.join(main_folder_path, sub_folder)
    if os.path.isdir(sub_folder_path):
        print(f"Processing folder: {sub_folder_path}")
        process_folder(sub_folder_path)