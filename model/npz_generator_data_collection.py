import torch
import numpy as np
import trimesh
from app.misc import quaternion_to_matrix
from app.obj_dataset import ObjectDataset
from app.objects import ObjectType
import os
import glob
import csv
from bps_torch.bps import bps_torch
from pathlib import Path
import re 

obj_dataset = ObjectDataset()

LogDataDir = r"../collected_data/"
target_obj_name_list = ["apple","banana","binoculars","bowl","camera",
                        "cup","hammer","knife", "mouse","mug",
                        "spheremedium","teapot","toothpaste","toruslarge","watch",
                        "waterbottle","wineglass", "crackerbox", "disklid", "pottedmeatcan", 
                        "plate","fryingpan","headphones","smartphone","spherelarge",
                        "spheresmall"]
# target_obj_name_list = ["crackerbox", "disklid", "pottedmeatcan", "plate"]
# target_obj_name_list = ["plate"]
timestamp = "t_0"

test_user_id = "s28"
grasping_position = torch.tensor([0.0, 0.0, 0.5])

for target_obj_name in target_obj_name_list:
    session_name_dirs = [
        file for file in glob.glob(os.path.join(LogDataDir, target_obj_name, "*"))
        if not file.endswith(".meta")
    ]
    
    for session_name_dir in session_name_dirs:
        gesture_file_prefix = "GestureData"

        # session_name = "20250411_120445.608"

        # suffix = target_obj_name + "/" + session_name

        files_root_dir = [
            file for file in glob.glob(os.path.join(session_name_dir, "*"))
            if not file.endswith(".meta")
        ]

        gesture_file = [file for file in files_root_dir if os.path.basename(file).startswith(gesture_file_prefix)][0]

        grasping_rows = []
        with open(gesture_file, mode='r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                grasping_rows.append(row)

        meta_files_root_dir = [
            file for file in glob.glob(os.path.join(session_name_dir, "meta_data", "*"))
            if not file.endswith(".meta")
        ]

        object_info_file = [file for file in meta_files_root_dir if os.path.basename(file) == "ObjectInfoData.csv"]
        # rotation_seq_file = [file for file in meta_files_root_dir if os.path.basename(file) == "RotationSeqData.csv"]

        # print(f"Object info file: {object_info_file}")

        object_info_dict = {}
        with open(object_info_file[0], mode='r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                if len(row) == 3:  # Ensure the row has exactly two elements
                    obj_enum = row[0]
                    obj_type = ObjectType(int(obj_enum)).name.replace("_", "").lower()  # Convert to ObjectType enum and get the name
                    value = row[2]
                    object_info_dict[obj_type] = value  # Store the key-value pair in the dictionary

        # print(f"Object info dict: {object_info_dict}")

        # seq_dict = {}
        # with open(rotation_seq_file[0], mode='r', encoding='utf-8') as file:
        #     csv_reader = csv.reader(file)
        #     for row in csv_reader:
        #         if len(row) == 2:  # Ensure the row has exactly two elements
        #             key, value = row
        #             seq_dict[key] = value  # Store the key-value pair in the dictionary



        # # Create the session folder if it doesn't exist
        session_npz_files_dir = "session_npz_files"

        # Define transformation matrices for Unity to Python coordinate conversion
        R_unity2python = torch.Tensor(
            [
                [-1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )

        R_camera = torch.Tensor(
            [
                [0.0, 0.0, 1.0],
                [-1.0, 0.0, 0.0],
                [0.0, -1.0, 0.0],
            ]
        )

        # Define colors for objects and hand joints
        obj_color = np.array([255, 0, 0, 255])  # Red color for objects
        thumb_color = np.array([255, 0, 0, 255])  # Red color for Thumb
        index_color = np.array([0, 255, 0, 255])  # Green color for Index finger
        middle_color = np.array([0, 0, 255, 255])  # Blue color for Middle finger
        ring_color = np.array([255, 255, 0, 255])  # Yellow color for Ring finger
        pinky_color = np.array([255, 0, 255, 255])  # Purple color for Pinky finger
        root_color = np.array([0, 255, 255, 255])  # Cyan color for Root (Wrist)

        # Define colors for all hand joints
        finger_colors = [
            thumb_color, thumb_color, thumb_color, thumb_color,
            index_color, index_color, index_color, index_color,
            middle_color, middle_color, middle_color, middle_color,
            ring_color, ring_color, ring_color, ring_color,
            pinky_color, pinky_color, pinky_color, pinky_color
        ]

        hand_pcl_colors = np.array(finger_colors)

        bps_fname = Path("./files/bps_new.npz")
        bps_basis = torch.from_numpy(np.load(bps_fname)['basis']).to(torch.float32)
        bps = bps_torch(bps_type="custom", custom_basis=bps_basis)

        os.makedirs(os.path.join(session_npz_files_dir, test_user_id), exist_ok=True)
        test_user_id_folders = [
            folder for folder in os.listdir(os.path.join(session_npz_files_dir, test_user_id))
            if os.path.isdir(os.path.join(session_npz_files_dir, test_user_id, folder))
        ]

        # print(f"Test user ID folders: {test_user_id_folders}")

        # Process each successful grasping row
        for row in grasping_rows:
            object_name = row[1]  # Object name

            # print(f"Processing object: {object_name}")

            matching_folders = []  # List to store matching folders
            for folder in test_user_id_folders:
                # print(f"Checking folder: {folder}")
                if object_name in folder: 
                    matching_folders.append(folder)

            # print(f"Matching folders: {matching_folders}")
            
            max_number = 0
            for folder in matching_folders:
                match = re.search(rf"{object_name}_(\d+)", folder)
                if match:
                    number = int(match.group(1))
                    max_number = max(max_number, number)

            new_folder_name = f"{object_name}_{max_number + 1}"
            new_folder_path = os.path.join(session_npz_files_dir, test_user_id, new_folder_name, timestamp)
            os.makedirs(new_folder_path, exist_ok=True)

            flag = row[0]  # Grasping flag

            # Parse hand joint positions
            hand_joints = row[4]  # Hand joint data
            joint_positions = hand_joints.split('/')  # Split by "/"
            hand_joint_position = []
            for joint in joint_positions:
                coords = list(map(float, joint.split('|')))  # Convert to a list of floats
                hand_joint_position.append(coords)  # Append to the list

            # Convert hand joint positions from Unity to Python coordinates
            hand_joint_position_unity = torch.Tensor(hand_joint_position)
            hand_joint_position_python = torch.einsum("ij,nj->ni", R_unity2python, hand_joint_position_unity)
            hand_joint_position_python = torch.einsum("ij,nj->ni", R_camera, hand_joint_position_python)

            # Create a point cloud for the hand
            hand_pcl_mesh = trimesh.PointCloud(hand_joint_position_python, colors=hand_pcl_colors)
            
            # get object from object_info_dict
            object_rotation_value = object_info_dict.get(object_name)  # Get the enum value from the dictionary


            # Parse object rotation quaternion
            object_rotation = object_rotation_value.split("|")  # Split by "|"
            object_rotation = [float(x) for x in object_rotation]  # Convert to floats
            object_rotation = [object_rotation[3], object_rotation[0], object_rotation[1], object_rotation[2]]  # Reorder

            # Store object rotations
            object_rotations = []
            object_rotations.append(object_rotation)

            # Convert object rotation from Unity to Python coordinates
            obj_quats_unity = torch.Tensor(object_rotations)
            T_quat_unity2python = torch.eye(4)
            T_quat_unity2python[1:, 1:] = -R_unity2python
            obj_quats_python = torch.einsum("ij,nj->ni", T_quat_unity2python, obj_quats_unity)

            # Convert quaternion to rotation matrix
            obj_rot_matrices = quaternion_to_matrix(obj_quats_python)
            obj_rot_matrices = torch.einsum("ik,nkj->nij", R_camera, obj_rot_matrices)

            # bps_fname = Path("data/bps_new.npz")
            # bps_basis = torch.from_numpy(np.load(bps_fname)['basis']).to(torch.float32)
            # bps = bps_torch(bps_type="custom", custom_basis=bps_basis)

            obj_types = [object_name]

            # Get object point cloud
            obj_pcl = obj_dataset.get_pcl(obj_types, obj_rot_matrices)

            bps_encode = bps.encode(obj_pcl.reshape(-1, 3), feature_type=['dists'])["dists"]

            # Create a point cloud for the object
            obj_pcl_colors = np.tile(obj_color, (obj_pcl[0].shape[0], 1))
            obj_pcl_mesh = trimesh.PointCloud(obj_pcl[0], colors=obj_pcl_colors)

            # Create a scene with the object and hand point clouds
            scene = trimesh.Scene([obj_pcl_mesh, hand_pcl_mesh])

            # scene.show()

            
            obj_vertices = np.array(obj_pcl_mesh.vertices)
            hand_vertices = np.array(hand_pcl_mesh.vertices)
            hand_vertices = np.vstack([np.zeros((1, 3)), hand_vertices])

            obj_translation =  torch.einsum("ij,nj->ni", R_unity2python, torch.zeros((1,3)))


            not_sure_path = os.path.join(session_npz_files_dir, "not_sure")
            os.makedirs(not_sure_path, exist_ok=True)

            if flag == "1":
                wrist_pos = row[5].split("|")
                wrist_pos = torch.tensor([float(x) for x in wrist_pos])
                obj_translation = grasping_position - wrist_pos  # Wrist position data
                obj_translation = torch.Tensor(obj_translation).unsqueeze(0)
                obj_translation = torch.einsum("ij,nj->ni", R_unity2python, obj_translation)
                obj_translation = torch.einsum("ij,nj->ni", R_camera, obj_translation)

                # obj_pcl_colors = np.tile(obj_color, (obj_pcl[0].shape[0], 1))
                # obj_pcl_mesh = trimesh.PointCloud(obj_pcl[0] + obj_translation, colors=obj_pcl_colors)

                # # Create a scene with the object and hand point clouds
                # scene = trimesh.Scene([obj_pcl_mesh, hand_pcl_mesh])

                # scene.show()


                save_path = os.path.join(new_folder_path, f"features.npz")
                np.savez(
                    save_path,
                    pcl=obj_vertices, # (1024,3)
                    bps=bps_encode.squeeze().detach().cpu(), # (1,4096)
                    obj_translation=obj_translation.squeeze().detach().cpu(),  # (1,3)
                    subject_joints_pos_rel2wrist=hand_vertices #(21,3)
                )
            elif flag == "0":
                save_path = os.path.join(new_folder_path, f"features_counter_{object_name}.npz")
                np.savez(
                    save_path,
                    pcl=obj_vertices, 
                    bps=bps_encode.squeeze().detach().cpu(), 
                    obj_translation=obj_translation.squeeze().detach().cpu(), 
                    subject_joints_pos_rel2wrist=hand_vertices
                )
            else:
                save_path = os.path.join(not_sure_path, f"features_not_sure_{object_name}.npz")
                np.savez(
                    save_path,
                    pcl=obj_vertices, 
                    bps=bps_encode.squeeze().detach().cpu(), 
                    obj_translation=obj_translation.squeeze().detach().cpu(), 
                    subject_joints_pos_rel2wrist=hand_vertices
                )
            

