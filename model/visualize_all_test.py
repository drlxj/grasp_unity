#!/usr/bin/env python3
"""
Script to visualize all NPZ files in the test folder
"""

import numpy as np
import torch
from pathlib import Path
import sys
import os

# Add the current directory to Python path

sys.path.append('.')

from npz_generator_data_collection import visualize_scene

def visualize_all_test_files():
    """Visualize all NPZ files in the test folder"""
    
    # Path to the test folder
    test_folder = Path(r"C:\Users\Researcher\grasping-unity\model\session_npz_files\test")
    
    if not test_folder.exists():
        print(f"Test folder not found: {test_folder}")
        return
    
    # Find all NPZ files
    npz_files = list(test_folder.glob("*.npz"))
    
    if not npz_files:
        print(f"No NPZ files found in: {test_folder}")
        return
    
    print(f"Found {len(npz_files)} NPZ files in test folder")
    print("=" * 50)
    
    # Create output directory
    output_dir = Path("test_visualizations")
    output_dir.mkdir(exist_ok=True)
    
    # Process each NPZ file
    for i, npz_file in enumerate(npz_files, 1):
        print(f"\n[{i}/{len(npz_files)}] Processing: {npz_file.name}")
        
        try:
            # Load the npz file
            data = np.load(npz_file, allow_pickle=True)
            
            # Check if we have the required data for visualization
            if 'object_point_cloud' in data and 'subject_joints_pos_rel2wrist' in data:
                print(f"  ✓ Found required data")
                
                # Extract data
                obj_pcl = data['object_point_cloud']
                hand_joints = data['subject_joints_pos_rel2wrist']
                
                # Get object translation if available
                # obj_trans = data.get('object_translation', np.zeros(3))
                obj_trans = np.zeros(3)
                
                print(f"  - Object point cloud: {obj_pcl.shape}")
                print(f"  - Hand joints: {hand_joints.shape}")
                print(f"  - Object translation: {obj_trans}")
                
                # Create joint colors (assuming 21 joints)
                joint_colors = np.array([
                    [255, 0, 0, 255],    # root
                    [255, 0, 0, 255],    [255, 0, 0, 255],    [255, 0, 0, 255],    [255, 0, 0, 255],    # thumb
                    [0, 255, 0, 255],    [0, 255, 0, 255],    [0, 255, 0, 255],    [0, 255, 0, 255],    # index
                    [0, 0, 255, 255],    [0, 0, 255, 255],    [0, 0, 255, 255],    [0, 0, 255, 255],    # middle
                    [255, 255, 0, 255],  [255, 255, 0, 255],  [255, 255, 0, 255],  [255, 255, 0, 255],  # ring
                    [255, 0, 255, 255],  [255, 0, 255, 255],  [255, 0, 255, 255],  [255, 0, 255, 255]   # pinky
                ])
                
                # Ensure we have enough colors
                while len(joint_colors) < len(hand_joints):
                    joint_colors = np.vstack([joint_colors, joint_colors[-1:]])
                
                # Create filename for output
                base_name = npz_file.stem
                img_path = output_dir / f"{base_name}.png"
                
                print(f"  - Saving visualization to: {img_path}")
                
                # Generate visualization
                visualize_scene(
                    hand_joints, joint_colors, obj_pcl, obj_trans, 
                    save_image=False, save_path=img_path
                )
                
                print(f"  ✓ Visualization saved successfully!")
                
            else:
                print(f"  ✗ Missing required data:")
                if 'object_point_cloud' not in data:
                    print(f"    - object_point_cloud")
                if 'subject_joints_pos_rel2wrist' not in data:
                    print(f"    - subject_joints_pos_rel2wrist")
                
                # Show what data we do have
                print(f"  - Available keys: {list(data.keys())}")
                
        except Exception as e:
            print(f"  ✗ Error processing {npz_file.name}: {e}")
            continue
    
    print("\n" + "=" * 50)
    print(f"Visualization complete!")
    print(f"Output directory: {output_dir.absolute()}")
    print(f"Successfully processed: {len([f for f in output_dir.glob('*.png')])} files")

def show_test_folder_contents():
    """Show what's in the test folder"""
    test_folder = Path(r"C:\Users\Researcher\grasping-unity\model\session_npz_files\test")
    
    if not test_folder.exists():
        print(f"Test folder not found: {test_folder}")
        return
    
    print(f"Contents of test folder: {test_folder}")
    print("=" * 50)
    
    # List all files
    all_files = list(test_folder.iterdir())
    npz_files = [f for f in all_files if f.suffix == '.npz']
    other_files = [f for f in all_files if f.suffix != '.npz']
    
    print(f"NPZ files ({len(npz_files)}):")
    for f in sorted(npz_files):
        print(f"  - {f.name}")
    
    if other_files:
        print(f"\nOther files ({len(other_files)}):")
        for f in sorted(other_files):
            print(f"  - {f.name}")

if __name__ == "__main__":
    print("Test Folder Visualization Script")
    print("=" * 50)
    
    # First show what's in the test folder
    show_test_folder_contents()
    
    print("\n" + "=" * 50)
    
    # Ask user if they want to proceed
    response = input("\nDo you want to visualize all NPZ files? (y/n): ").lower().strip()
    
    if response in ['y', 'yes', '是']:
        visualize_all_test_files()
    else:
        print("Visualization cancelled.")


