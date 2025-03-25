import os
import shutil
import argparse

# Set up command line argument parsing
parser = argparse.ArgumentParser(description="Process 3D model files by organizing them into separate folders with textures")
parser.add_argument('source_dir', type=str, help="Path to the source directory containing model folders")
args = parser.parse_args()

source_dir = args.source_dir

# Ensure source directory exists
os.makedirs(source_dir, exist_ok=True)

# Traverse all subfolders
for folder in os.listdir(source_dir):
    folder_path = os.path.join(source_dir, folder)
    if os.path.isdir(folder_path):
        # Remove 'doom2_' prefix if exists
        folder_clean = folder.replace('doom2_', '')

        # Initialize
        obj_files = [f for f in os.listdir(folder_path) if f.endswith('.obj')]
        png_files = [f for f in os.listdir(folder_path) if f.endswith('.png')]  # Collect all texture files
        mtl_files = [f for f in os.listdir(folder_path) if f.endswith('.mtl')]

        if mtl_files:
            mtl_file = mtl_files[0]  # Assume there's only one MTL file per folder
            mtl_file_path = os.path.join(folder_path, mtl_file)

        obj_counter = 0

        # Create a subdirectory for each OBJ file
        for obj_file in obj_files:
            new_folder_name = f"{folder_clean}_{obj_counter}"
            new_folder_path = os.path.join(source_dir, new_folder_name)
            os.makedirs(new_folder_path, exist_ok=True)

            texture_subfolder_path = os.path.join(new_folder_path, "textures")
            os.makedirs(texture_subfolder_path, exist_ok=True)

            # New file names
            new_obj_name = f"{new_folder_name}.obj"
            new_obj_path = os.path.join(new_folder_path, new_obj_name)
            new_mtl_name = f"{new_folder_name}.mtl"
            new_mtl_path = os.path.join(new_folder_path, new_mtl_name)

            # Copy and rename OBJ file
            shutil.copy(os.path.join(folder_path, obj_file), new_obj_path)

            # Copy all PNG files to textures folder
            for png_file in png_files:
                source_png_path = os.path.join(folder_path, png_file)
                shutil.copy(source_png_path, texture_subfolder_path)

            # If MTL file exists, copy and update texture paths
            if mtl_files:
                with open(mtl_file_path, 'r') as file:
                    mtl_content = file.read()

                # Update texture paths in MTL content to relative paths
                updated_mtl_content = mtl_content
                for png_file in png_files:
                    old_texture_path = png_file
                    new_texture_path = os.path.join("textures", png_file)
                    updated_mtl_content = updated_mtl_content.replace(old_texture_path, new_texture_path)

                # Write to new MTL file
                with open(new_mtl_path, 'w') as file:
                    file.write(updated_mtl_content)

            obj_counter += 1

        # Clean up original folder
        shutil.rmtree(folder_path)

print("Processing complete!")