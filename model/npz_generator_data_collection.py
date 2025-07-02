# # import torch
# # import numpy as np
# # import trimesh
# # from app.misc import quaternion_to_matrix
# # from app.obj_dataset import ObjectDataset
# # from app.objects import ObjectType
# # import os
# # import glob
# # import csv
# # from bps_torch.bps import bps_torch
# # from pathlib import Path
# # import re 

# # obj_dataset = ObjectDataset()


# # target_obj_name_list = ["apple","banana","binoculars","bowl","camera", "crackerbox",
# #                         "cup", "disklid", "fryingpan","glue", "hammer","headphones", "knife", "mouse","mug", "plate"
# #                         "spheremedium","teapot","toothpaste","toruslarge","watch",
# #                         "waterbottle","wineglass", "crackerbox", "disklid", "pottedmeatcan","smartphone","spherelarge",
# #                         "spheresmall"]
# # # target_obj_name_list = ["cup"]

# # test_user_id = "s1"
# # LogDataDir = f"../collected_data/{test_user_id}/"

# # timestamp = "t_0"


# # grasping_position = torch.tensor([0.0, 0.0, 0.5])

# # for target_obj_name in target_obj_name_list:
# #     session_name_dirs = [
# #         file for file in glob.glob(os.path.join(LogDataDir, target_obj_name, "*"))
# #         if not file.endswith(".meta")
# #     ]
    
# #     for session_name_dir in session_name_dirs:
# #         gesture_file_prefix = "GestureData"

# #         files_root_dir = [
# #             file for file in glob.glob(os.path.join(session_name_dir, "*"))
# #             if file.endswith(".meta")
# #         ]

# #         gesture_file = [file for file in files_root_dir if os.path.basename(file).startswith(gesture_file_prefix)][0]

# #         grasping_rows = []
# #         with open(gesture_file, mode='r', encoding='utf-8') as file:
# #             csv_reader = csv.reader(file)
# #             for row in csv_reader:
# #                 grasping_rows.append(row)

# #         meta_files_root_dir = [
# #             file for file in glob.glob(os.path.join(session_name_dir, "meta_data", "*"))
# #             if not file.endswith(".meta")
# #         ]

# #         object_info_file = [file for file in meta_files_root_dir if os.path.basename(file) == "ObjectInfoData.csv"]
# #         # rotation_seq_file = [file for file in meta_files_root_dir if os.path.basename(file) == "RotationSeqData.csv"]

# #         # print(f"Object info file: {object_info_file}")

# #         object_info_dict = {}
# #         with open(object_info_file[0], mode='r', encoding='utf-8') as file:
# #             csv_reader = csv.reader(file)
# #             for row in csv_reader:
# #                 if len(row) == 3:  # Ensure the row has exactly two elements
# #                     obj_enum = row[0]
# #                     obj_type = ObjectType(int(obj_enum)).name.replace("_", "").lower()  # Convert to ObjectType enum and get the name
# #                     value = row[2]
# #                     object_info_dict[obj_type] = value  # Store the key-value pair in the dictionary

# #         # print(f"Object info dict: {object_info_dict}")

# #         # seq_dict = {}
# #         # with open(rotation_seq_file[0], mode='r', encoding='utf-8') as file:
# #         #     csv_reader = csv.reader(file)
# #         #     for row in csv_reader:
# #         #         if len(row) == 2:  # Ensure the row has exactly two elements
# #         #             key, value = row
# #         #             seq_dict[key] = value  # Store the key-value pair in the dictionary



# #         # # Create the session folder if it doesn't exist
# #         session_npz_files_dir = "session_npz_files"

# #         # Define transformation matrices for Unity to Python coordinate conversion
# #         R_unity2python = torch.Tensor(
# #             [
# #                 [-1.0, 0.0, 0.0],
# #                 [0.0, 1.0, 0.0],
# #                 [0.0, 0.0, 1.0],
# #             ]
# #         )

# #         # Define colors for objects and hand joints
# #         obj_color = np.array([255, 0, 0, 255])  # Red color for objects
# #         thumb_color = np.array([255, 0, 0, 255])  # Red color for Thumb
# #         index_color = np.array([0, 255, 0, 255])  # Green color for Index finger
# #         middle_color = np.array([0, 0, 255, 255])  # Blue color for Middle finger
# #         ring_color = np.array([255, 255, 0, 255])  # Yellow color for Ring finger
# #         pinky_color = np.array([255, 0, 255, 255])  # Purple color for Pinky finger
# #         root_color = np.array([0, 255, 255, 255])  # Cyan color for Root (Wrist)

# #         # Define colors for all hand joints
# #         finger_colors = [
# #             thumb_color, thumb_color, thumb_color, thumb_color,
# #             index_color, index_color, index_color, index_color,
# #             middle_color, middle_color, middle_color, middle_color,
# #             ring_color, ring_color, ring_color, ring_color,
# #             pinky_color, pinky_color, pinky_color, pinky_color
# #         ]

# #         hand_pcl_colors = np.array(finger_colors)

# #         bps_fname = Path("./files/bps_new.npz")
# #         bps_basis = torch.from_numpy(np.load(bps_fname)['basis']).to(torch.float32)
# #         bps = bps_torch(bps_type="custom", custom_basis=bps_basis)

# #         os.makedirs(os.path.join(session_npz_files_dir, test_user_id), exist_ok=True)
# #         test_user_id_folders = [
# #             folder for folder in os.listdir(os.path.join(session_npz_files_dir, test_user_id))
# #             if os.path.isdir(os.path.join(session_npz_files_dir, test_user_id, folder))
# #         ]

# #         # print(f"Test user ID folders: {test_user_id_folders}")

# #         # Process each successful grasping row
# #         for row in grasping_rows:
# #             object_name = row[1]  # Object name

# #             # print(f"Processing object: {object_name}")

# #             matching_folders = []  # List to store matching folders
# #             for folder in test_user_id_folders:
# #                 # print(f"Checking folder: {folder}")
# #                 if object_name in folder: 
# #                     matching_folders.append(folder)

# #             # print(f"Matching folders: {matching_folders}")
            
# #             max_number = 0
# #             for folder in matching_folders:
# #                 match = re.search(rf"{object_name}_(\d+)", folder)
# #                 if match:
# #                     number = int(match.group(1))
# #                     max_number = max(max_number, number)

# #             new_folder_name = f"{object_name}_{max_number + 1}"
# #             new_folder_path = os.path.join(session_npz_files_dir, test_user_id, new_folder_name, timestamp)
# #             os.makedirs(new_folder_path, exist_ok=True)

# #             flag = row[0]  # Grasping flag

# #             # Parse hand joint positions
# #             hand_joints = row[4]  # Hand joint data
# #             joint_positions = hand_joints.split('/')  # Split by "/"
# #             hand_joint_position = []
# #             for joint in joint_positions:
# #                 coords = list(map(float, joint.split('|')))  # Convert to a list of floats
# #                 hand_joint_position.append(coords)  # Append to the list

# #             # Convert hand joint positions from Unity to Python coordinates
# #             hand_joint_position_unity = torch.Tensor(hand_joint_position)
# #             hand_joint_position_python = torch.einsum("ij,nj->ni", R_unity2python, hand_joint_position_unity)

# #             # get object from object_info_dict
# #             object_rotation_value = object_info_dict.get(object_name)  # Get the enum value from the dictionary
# #             object_rotation = object_rotation_value.split("|")  # Split by "|"
# #             object_rotation = [float(x) for x in object_rotation]  # Convert to floats
# #             object_rotations = [[object_rotation[3], object_rotation[0], object_rotation[1], object_rotation[2]]]  # [x, y, z, w] -> [w, x, y, z]

# #             # Convert object rotation from Unity to Python coordinates
# #             obj_quats_unity = torch.Tensor(object_rotations)
# #             T_quat_unity2python = torch.eye(4)
# #             T_quat_unity2python[1:, 1:] = -R_unity2python
# #             obj_quats_python = torch.einsum("ij,nj->ni", T_quat_unity2python, obj_quats_unity)

# #             # Convert quaternion to rotation matrix
# #             obj_rot_matrices = quaternion_to_matrix(obj_quats_python)
# #             obj_types = [object_name]

# #             # Get object point cloud and BPS encoding
# #             obj_pcl = obj_dataset.get_pcl(obj_types, obj_rot_matrices)
# #             bps_encode = bps.encode(obj_pcl.reshape(-1, 3), feature_type=['dists'])["dists"]

# #             # Visualize the object and hand point clouds
# #             obj_pcl_colors = np.tile(obj_color, (obj_pcl[0].shape[0], 1))
# #             obj_pcl_mesh = trimesh.PointCloud(obj_pcl[0], colors=obj_pcl_colors)
# #             hand_pcl_mesh = trimesh.PointCloud(hand_joint_position_python, colors=hand_pcl_colors)
# #             scene = trimesh.Scene([obj_pcl_mesh, hand_pcl_mesh])
# #             # scene.show()
            
# #             obj_vertices = np.array(obj_pcl_mesh.vertices)
# #             hand_vertices = np.array(hand_pcl_mesh.vertices)
# #             hand_vertices = np.vstack([np.zeros((1, 3)), hand_vertices])

# #             obj_translation =  torch.einsum("ij,nj->ni", R_unity2python, torch.zeros((1,3)))

# #             if flag == "1":
# #                 wrist_pos = row[5].split("|")
# #                 wrist_pos = torch.tensor([float(x) for x in wrist_pos])
# #                 obj_translation = grasping_position - wrist_pos  # Wrist position data
# #                 obj_translation = torch.Tensor(obj_translation).unsqueeze(0)
# #                 obj_translation = torch.einsum("ij,nj->ni", R_unity2python, obj_translation)

# #                 in_reach_hand_joints = row[8]  # Hand joint data
# #                 in_reach_joint_positions = in_reach_hand_joints.split('/')  # Split by "/"
# #                 in_reach_hand_joint_position = []
# #                 for joint in in_reach_joint_positions:
# #                     coords = list(map(float, joint.split('|')))  # Convert to a list of floats
# #                     in_reach_hand_joint_position.append(coords)  # Append to the list

# #                 # Convert hand joint positions from Unity to Python coordinates
# #                 in_reach_hand_joint_position_unity = torch.Tensor(in_reach_hand_joint_position)
# #                 in_reach_hand_joint_position_python = torch.einsum("ij,nj->ni", R_unity2python, in_reach_hand_joint_position_unity)
# #                 in_reach_hand_joint_position_python = torch.cat(
# #                     [torch.zeros((1, 3)), in_reach_hand_joint_position_python], dim=0
# #                 )

# #                 in_reach_hand_pcl_mesh = trimesh.PointCloud(in_reach_hand_joint_position_python, colors=hand_pcl_colors)

# #                 obj_pcl_colors = np.tile(obj_color, (obj_pcl[0].shape[0], 1))
# #                 obj_pcl_mesh = trimesh.PointCloud(obj_pcl[0] + obj_translation, colors=obj_pcl_colors)

# #                 # Create a scene with the object and hand point clouds
# #                 scene = trimesh.Scene([obj_pcl_mesh, in_reach_hand_pcl_mesh])
# #                 # scene.show()

# #                 save_path = os.path.join(new_folder_path, f"features.npz")
# #                 np.savez(
# #                     save_path,
# #                     object_orientation = obj_rot_matrices.squeeze().detach().cpu(), # (3,3)
# #                     object_pointcloud=obj_vertices, # (1024,3) without translation
# #                     object_bps=bps_encode.squeeze().detach().cpu(), # (4096)
# #                     object_translation=obj_translation.squeeze().detach().cpu(),  # (3)
# #                     subject_joints_pos_rel2wrist=hand_vertices, #(21,3)
# #                     in_reach_subject_joints_pos_rel2wrist=in_reach_hand_joint_position_python.squeeze().detach().cpu()
# #                 )
# #             elif flag == "0":
# #                 save_path = os.path.join(new_folder_path, f"features_counter.npz")
# #                 np.savez(
# #                     save_path,
# #                     object_orientation = obj_rot_matrices.squeeze().detach().cpu(),
# #                     object_pointcloud=obj_vertices, 
# #                     object_bps=bps_encode.squeeze().detach().cpu(), 
# #                     object_translation=obj_translation.squeeze().detach().cpu(), 
# #                     subject_joints_pos_rel2wrist=hand_vertices
# #                 )
# #             else:
# #                 not_sure_path = os.path.join(session_npz_files_dir, "not_sure")
# #                 os.makedirs(not_sure_path, exist_ok=True)
# #                 save_path = os.path.join(not_sure_path, f"features_not_sure_{object_name}.npz")
# #                 np.savez(
# #                     save_path,
# #                     object_orientation = obj_rot_matrices.squeeze().detach().cpu(),
# #                     object_pointcloud=obj_vertices, 
# #                     object_bps=bps_encode.squeeze().detach().cpu(), 
# #                     object_translation=obj_translation.squeeze().detach().cpu(), 
# #                     subject_joints_pos_rel2wrist=hand_vertices
# #                 )
            

# import torch
# import numpy as np
# import trimesh
# from app.misc import quaternion_to_matrix
# from app.obj_dataset import ObjectDataset
# from app.objects import ObjectType
# import os
# import glob
# import csv
# from bps_torch.bps import bps_torch
# from pathlib import Path
# import json

# obj_dataset = ObjectDataset()


# target_obj_name_list = ["apple","banana","binoculars","bowl","camera", "crackerbox",
#                         "cup", "disklid", "fryingpan","glue", "hammer","headphones", "knife", "mouse","mug", "plate"
#                         "spheremedium","teapot","toothpaste","toruslarge","watch",
#                         "waterbottle","wineglass", "crackerbox", "disklid", "pottedmeatcan","smartphone","spherelarge",
#                         "spheresmall"]
# # target_obj_name_list = ["cup"]

# test_user_id = "s1"
# LogDataDir = f"../collected_data/{test_user_id}/"

# timestamp = "t_0"


# grasping_position = torch.tensor([0.0, 0.0, 0.5])

# for target_obj_name in target_obj_name_list:
#     session_name_dirs = [file for file in glob.glob(os.path.join(LogDataDir, target_obj_name, "*"))]
    
#     for session_name_dir in session_name_dirs:
#         json_files = [
#             file for file in glob.glob(os.path.join(session_name_dir, "*"))
#             if file.endswith("labeled_samples.json")
#         ]

#         with open(json_files[0], "r") as f:
#             data = json.load(f)

       
#         # Create the session folder if it doesn't exist
#         session_npz_files_dir = "session_npz_files"

#         # Define transformation matrices for Unity to Python coordinate conversion
#         R_unity2python = torch.Tensor(
#             [
#                 [-1.0, 0.0, 0.0],
#                 [0.0, 1.0, 0.0],
#                 [0.0, 0.0, 1.0],
#             ]
#         )

#         # Define colors for objects and hand joints
#         obj_color = np.array([255, 0, 0, 255])  # Red color for objects
#         thumb_color = np.array([255, 0, 0, 255])  # Red color for Thumb
#         index_color = np.array([0, 255, 0, 255])  # Green color for Index finger
#         middle_color = np.array([0, 0, 255, 255])  # Blue color for Middle finger
#         ring_color = np.array([255, 255, 0, 255])  # Yellow color for Ring finger
#         pinky_color = np.array([255, 0, 255, 255])  # Purple color for Pinky finger
#         root_color = np.array([0, 255, 255, 255])  # Cyan color for Root (Wrist)

#         # Define colors for all hand joints
#         finger_colors = [
#             thumb_color, thumb_color, thumb_color, thumb_color,
#             index_color, index_color, index_color, index_color,
#             middle_color, middle_color, middle_color, middle_color,
#             ring_color, ring_color, ring_color, ring_color,
#             pinky_color, pinky_color, pinky_color, pinky_color
#         ]

#         hand_pcl_colors = np.array(finger_colors)

#         bps_fname = Path("./files/bps_new.npz")
#         bps_basis = torch.from_numpy(np.load(bps_fname)['basis']).to(torch.float32)
#         bps = bps_torch(bps_type="custom", custom_basis=bps_basis)

#         os.makedirs(os.path.join(session_npz_files_dir, test_user_id), exist_ok=True)
#         test_user_id_folders = [
#             folder for folder in os.listdir(os.path.join(session_npz_files_dir, test_user_id))
#             if os.path.isdir(os.path.join(session_npz_files_dir, test_user_id, folder))
#         ]

#         # print(f"Test user ID folders: {test_user_id_folders}")

#         # Process each successful grasping row
#         trials = data["trials"]
#         for trial in trials:
#             object_name = trial["objectName"]
#             trial_index = trial["trialIndex"]
#             gesture_label = trial["gestureLabel"]
#             objectPosition = np.array(trial["objectPosition"])
#             objectRotation = np.array(trial["objectRotation"])
#             root_position = np.array(trial["outOfReachGesture"]["rootPosition"])
#             root_rotation = np.array(trial["outOfReachGesture"]["rootRotation"])
#             leaf_joint_positions = np.array(trial["outOfReachGesture"]["jointGlobalPositions"])
#             leaf_joint_rotations = np.array(trial["outOfReachGesture"]["jointGlobalRotations"])

#             # Convert hand joint positions from Unity to Python coordinates
#             hand_joint_position = leaf_joint_positions - root_position
#             hand_joint_position_unity = torch.Tensor(hand_joint_position)
#             hand_joint_position_python = torch.einsum("ij,nj->ni", R_unity2python, hand_joint_position_unity)

#             # Convert object rotation from Unity to Python coordinates
#             object_rotations = objectRotation[[-1, 0, 1, 2]].reshape(1, 4)  # [x, y, z, w] -> [w, x, y, z]
#             obj_quats_unity = torch.Tensor(object_rotations)
#             T_quat_unity2python = torch.eye(4)
#             T_quat_unity2python[1:, 1:] = -R_unity2python
#             obj_quats_python = torch.einsum("ij,nj->ni", T_quat_unity2python, obj_quats_unity)

#             # Convert quaternion to rotation matrix
#             obj_rot_matrices = quaternion_to_matrix(obj_quats_python)
#             obj_types = [object_name]

#             # Get object point cloud and BPS encoding
#             obj_pcl = obj_dataset.get_pcl(obj_types, obj_rot_matrices)
#             bps_encode = bps.encode(obj_pcl.reshape(-1, 3), feature_type=['dists'])["dists"]

#             # Visualize the object and hand point clouds
#             obj_pcl_colors = np.tile(obj_color, (obj_pcl[0].shape[0], 1))
#             obj_pcl_mesh = trimesh.PointCloud(obj_pcl[0], colors=obj_pcl_colors)
#             hand_pcl_mesh = trimesh.PointCloud(hand_joint_position_python, colors=hand_pcl_colors)
#             scene = trimesh.Scene([obj_pcl_mesh, hand_pcl_mesh])
#             scene.show()
            
#             obj_vertices = np.array(obj_pcl_mesh.vertices)
#             hand_vertices = np.array(hand_pcl_mesh.vertices)
#             hand_vertices = np.vstack([np.zeros((1, 3)), hand_vertices])

#             obj_translation =  torch.einsum("ij,nj->ni", R_unity2python, torch.zeros((1,3)))

#             if gesture_label == 1:
#                 obj_translation = grasping_position - root_position  # Wrist position data
#                 obj_translation_unity = torch.Tensor(obj_translation).unsqueeze(0)
#                 obj_translation_python = torch.einsum("ij,nj->ni", R_unity2python, obj_translation_unity.float())

#                 # Convert hand joint positions from Unity to Python coordinates
#                 in_reach_hand_joint_position =  np.array(trial["inReachGesture"]["jointGlobalPositions"])
#                 in_reach_hand_joint_position_unity = torch.Tensor(in_reach_hand_joint_position - root_position)
#                 in_reach_hand_joint_position_python = torch.einsum("ij,nj->ni", R_unity2python, in_reach_hand_joint_position_unity)

#                 in_reach_hand_pcl_mesh = trimesh.PointCloud(in_reach_hand_joint_position_python, colors=hand_pcl_colors)

#                 obj_pcl_colors = np.tile(obj_color, (obj_pcl[0].shape[0], 1))
#                 obj_pcl_mesh = trimesh.PointCloud(obj_pcl[0] + obj_translation_python, colors=obj_pcl_colors)

#                 # Create a scene with the object and hand point clouds
#                 scene = trimesh.Scene([obj_pcl_mesh, in_reach_hand_pcl_mesh])
#                 scene.show()

#                 in_reach_hand_joint_position_python = torch.cat(
#                     [torch.zeros((1, 3)), in_reach_hand_joint_position_python], dim=0
#                 )

#                 save_path = os.path.join(new_folder_path, f"features.npz")
#                 np.savez(
#                     save_path,
#                     object_orientation = obj_rot_matrices.squeeze().detach().cpu(), # (3,3)
#                     object_pointcloud=obj_vertices, # (1024,3) without translation
#                     object_bps=bps_encode.squeeze().detach().cpu(), # (4096)
#                     object_translation=obj_translation.squeeze().detach().cpu(),  # (3)
#                     subject_joints_pos_rel2wrist=hand_vertices, #(21,3)
#                     in_reach_subject_joints_pos_rel2wrist=in_reach_hand_joint_position_python.squeeze().detach().cpu()
#                 )
#             elif gesture_label == 0:
#                 save_path = os.path.join(new_folder_path, f"features_counter.npz")
#                 np.savez(
#                     save_path,
#                     object_orientation = obj_rot_matrices.squeeze().detach().cpu(),
#                     object_pointcloud=obj_vertices, 
#                     object_bps=bps_encode.squeeze().detach().cpu(), 
#                     object_translation=obj_translation.squeeze().detach().cpu(), 
#                     subject_joints_pos_rel2wrist=hand_vertices
#                 )
#             else:
#                 not_sure_path = os.path.join(session_npz_files_dir, "not_sure")
#                 os.makedirs(not_sure_path, exist_ok=True)
#                 save_path = os.path.join(not_sure_path, f"features_not_sure_{object_name}.npz")
#                 np.savez(
#                     save_path,
#                     object_orientation = obj_rot_matrices.squeeze().detach().cpu(),
#                     object_pointcloud=obj_vertices, 
#                     object_bps=bps_encode.squeeze().detach().cpu(), 
#                     object_translation=obj_translation.squeeze().detach().cpu(), 
#                     subject_joints_pos_rel2wrist=hand_vertices
#                 )
            
from pathlib import Path
import torch
import numpy as np
import trimesh
import json
from app.misc import quaternion_to_matrix
from app.obj_dataset import ObjectDataset
from bps_torch.bps import bps_torch

def convert_unity_to_python(vec, R):
    return torch.einsum("ij,nj->ni", R, vec)

def get_object_rotation_matrix(quat_unity, R):
    quat = quat_unity[[-1, 0, 1, 2]].reshape(1, 4)
    T = torch.eye(4)
    T[1:, 1:] = -R
    quat_python = torch.einsum("ij,nj->ni", T, quat)
    return quaternion_to_matrix(quat_python)

def create_hand_pointcloud(joint_positions, root_position, R, with_root=True):
    relative_pos = torch.Tensor(joint_positions - root_position)
    hand_pts = convert_unity_to_python(relative_pos, R)
    if with_root:
        hand_pts = torch.cat([torch.zeros((1, 3)), hand_pts], dim=0)
    return hand_pts

def visualize_hand_with_skeleton(hand_pts, joint_colors, scene):
    hand_mesh = trimesh.PointCloud(hand_pts, colors=joint_colors)
    scene.add_geometry(hand_mesh)
    lines = [
        [0, 1], [1, 2], [2, 3], [3, 4],
        [0, 5], [5, 6], [6, 7], [7, 8],
        [0, 9], [9,10], [10,11], [11,12],
        [0,13], [13,14], [14,15], [15,16],
        [0,17], [17,18], [18,19], [19,20],
    ]
    segments = np.array([[hand_pts[s], hand_pts[e]] for s, e in lines])
    path = trimesh.load_path(segments)
    scene.add_geometry(path)


def make_camera_look_at(eye, target=np.zeros(3), up=np.array([0, 1, 0])):
    eye = np.asarray(eye)
    target = np.asarray(target)
    up = np.asarray(up)

    forward = eye - target
    forward /= np.linalg.norm(forward)

    right = np.cross(up, forward)
    right /= np.linalg.norm(right)

    true_up = np.cross(forward, right)

    camera_transform = np.eye(4)
    camera_transform[:3, 0] = right     # X → red → right
    camera_transform[:3, 1] = true_up   # Y → green → up
    camera_transform[:3, 2] = forward   # Z → blue → forward
    camera_transform[:3, 3] = eye       # camera position
    return camera_transform

def add_coordinate_frame(scene):
    axis = trimesh.creation.axis(origin_size=0.005, axis_radius=0.002, axis_length=0.1)
    scene.add_geometry(axis)

def set_camera(scene):
    camera_transform = make_camera_look_at(eye=[0.3, 0.3, -1])
    scene.camera_transform = camera_transform

def save_feature_file(path, obj_rot, obj_pcl, bps_feat, obj_trans, hand_verts, in_reach_hand=None):
    np.savez(
        path,
        object_orientation=obj_rot.squeeze().detach().cpu(),
        object_pointcloud=obj_pcl,
        object_bps=bps_feat.squeeze().detach().cpu(),
        object_translation=obj_trans.squeeze().detach().cpu(),
        subject_joints_pos_rel2wrist=hand_verts,
        in_reach_subject_joints_pos_rel2wrist=in_reach_hand if in_reach_hand is not None else None,
    )

obj_dataset = ObjectDataset()
bps_basis = torch.from_numpy(np.load("./files/bps_new.npz")['basis']).to(torch.float32)
bps = bps_torch(bps_type="custom", custom_basis=bps_basis)

R_unity2python = torch.tensor([[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])

colors = {
    "thumb": [255, 0, 0, 255],
    "index": [0, 255, 0, 255],
    "middle": [0, 0, 255, 255],
    "ring": [255, 255, 0, 255],
    "pinky": [255, 0, 255, 255],
    "root": [0, 255, 255, 255],
}
joint_colors = np.array(
    [colors["root"]] +
    [colors["thumb"]]*4 + [colors["index"]]*4 + [colors["middle"]]*4 +
    [colors["ring"]]*4 + [colors["pinky"]]*4
)

test_user_id = "s3"
is_visualize = True
grasping_position = torch.tensor([0.0, 0.0, 0.5])
data_dir = Path("../collected_data") / test_user_id
output_dir = Path("session_npz_files") / test_user_id
output_dir.mkdir(parents=True, exist_ok=True)

root_positions = []
for obj_dir in data_dir.iterdir():
    if not obj_dir.is_dir():
        continue
    json_file = next(obj_dir.glob("**/all_trials.json"), None)
    
    with open(json_file, "r") as f:
        trials = json.load(f)

    for trial in trials:
        object_name = trial["objectName"]
        trial_index = trial["trialIndex"]
        gesture_label = trial["label"]
        is_in_reach_frame = trial["isInReachFrame"]
        is_labeled_frame = trial["isLabeledFrame"]
        obj_pos = torch.Tensor(trial["objectPoseWorld"]["position"])[is_labeled_frame].squeeze()
        obj_rot = torch.Tensor(trial["objectPoseWorld"]["rotation"])[is_labeled_frame].squeeze()
        joint_pos = torch.Tensor(trial["gestures"]["jointsPositionWorld"])
        root_pos = joint_pos[is_labeled_frame, 0:1].squeeze()
        leaf_pos = joint_pos[is_labeled_frame, 1:].squeeze()

        hand_pts = create_hand_pointcloud(leaf_pos, root_pos, R_unity2python, with_root=True)
        obj_rot_matrix = get_object_rotation_matrix(obj_rot, R_unity2python)
        obj_types = [object_name]
        obj_pcl = obj_dataset.get_pcl(obj_types, obj_rot_matrix)
        obj_bps = bps.encode(obj_pcl.reshape(-1, 3), feature_type=["dists"])["dists"]
        obj_trans = convert_unity_to_python(torch.tensor([[0.0, 0.0, 0.0]]), R_unity2python)

        if is_visualize:
            scene = trimesh.Scene()
            visualize_hand_with_skeleton(hand_pts.numpy(), joint_colors, scene)
            obj_mesh = trimesh.PointCloud(obj_pcl[0] + obj_trans, colors=np.tile([255, 0, 0, 255], (obj_pcl[0].shape[0], 1)))
            scene.add_geometry(obj_mesh)
            add_coordinate_frame(scene)
            set_camera(scene)
            scene.show()

        if gesture_label == 1:
            obj_trans = grasping_position - torch.tensor(root_pos)
            obj_trans = convert_unity_to_python(obj_trans.unsqueeze(0).float(), R_unity2python)
            in_reach_leaf =joint_pos[is_in_reach_frame, 1:].squeeze()
            in_reach_pts = create_hand_pointcloud(in_reach_leaf, root_pos, R_unity2python, with_root=True)
            root_positions.append(root_pos)

            if is_visualize:
                scene = trimesh.Scene()
                visualize_hand_with_skeleton(in_reach_pts.numpy(), joint_colors, scene)
                obj_mesh = trimesh.PointCloud(obj_pcl[0] + obj_trans, colors=np.tile([255, 0, 0, 255], (obj_pcl[0].shape[0], 1)))
                scene.add_geometry(obj_mesh)
                add_coordinate_frame(scene)
                set_camera(scene)
                scene.show()

            save_path = output_dir / f"{object_name}_{trial_index}" / "t_0" / "features.npz"
            save_path.parent.mkdir(parents=True, exist_ok=True)
            # save_feature_file(save_path, obj_rot_matrix, obj_pcl[0].numpy(), obj_bps, obj_trans, hand_pts.numpy(), in_reach_pts.numpy())
        else:
            fname = "features_counter.npz" if gesture_label == 0 else f"features_not_sure_{object_name}.npz"
            save_dir = output_dir if gesture_label == 0 else Path("session_npz_files") / "not_sure"
            save_dir.mkdir(parents=True, exist_ok=True)
            # save_feature_file(save_dir / fname, obj_rot_matrix, obj_pcl[0].numpy(), obj_bps, obj_trans, hand_pts.numpy())


root_positions = np.array(root_positions)
# project root positions to the xy plane and visualize the point distribution with matplotlib, and make (0, 0) as the figure center
root_positions_xy = root_positions[:, :2]
import matplotlib.pyplot as plt
plt.figure(figsize=(8, 8))
plt.scatter(root_positions_xy[:, 0], root_positions_xy[:, 1], alpha=0.5)
x_max = np.max(np.abs(root_positions_xy[:, 0]))
y_max = np.max(np.abs(root_positions_xy[:, 1]))
max_range = max(x_max, y_max)
plt.xlim(-max_range, max_range)
plt.ylim(-max_range, max_range)
plt.axhline(0, color='gray', linewidth=0.5)
plt.axvline(0, color='gray', linewidth=0.5)
plt.xlabel('X')
plt.ylabel('Y')
plt.title('Root Positions Projected to XY Plane')
plt.gca().set_aspect('equal', adjustable='box')
plt.savefig('root_positions_xy_s2.png', dpi=300)
plt.show()