import torch
import numpy as np
import trimesh
from app.misc import quaternion_to_matrix
from app.obj_dataset import ObjectDataset
from app.objects import ObjectType
import os
import glob
import csv

obj_dataset = ObjectDataset()

session_name = "20250331_151156.961_I"

LogDataDir = r"../DistanceGrasp/Assets/LogData/"

matching_files = [
    file for file in glob.glob(os.path.join(LogDataDir, f"*{session_name}*"))
    if not file.endswith(".meta")
]

gesture_file_prefix = "GestureData_"
grasping_file_prefix = "GraspingData_"
object_file_prefix = "ObjectData_"
rotation_file_prefix = "RotationSeqData_"

gesture_file = [file for file in matching_files if os.path.basename(file).startswith(gesture_file_prefix)][0]
grasping_file = [file for file in matching_files if os.path.basename(file).startswith(grasping_file_prefix)][0]
object_file = [file for file in matching_files if os.path.basename(file).startswith(object_file_prefix)][0]
rotation_file = [file for file in matching_files if os.path.basename(file).startswith(rotation_file_prefix)][0]

success_grasping_rows = []
with open(gesture_file, mode='r', encoding='utf-8') as file:
    csv_reader = csv.reader(file)
    for row in csv_reader:
        if row and row[0] == "1":
            success_grasping_rows.append(row)

# Read the rotation sequence file and store it in a dictionary
seq_dict = {}
with open(rotation_file, mode='r', encoding='utf-8') as file:
    csv_reader = csv.reader(file)
    for row in csv_reader:
        if len(row) == 2:  # Ensure the row has exactly two elements
            key, value = row
            seq_dict[key] = value  # Store the key-value pair in the dictionary

# Read the object data file and store all rows
object_rows = []
with open(object_file, mode='r', encoding='utf-8') as file:
    csv_reader = csv.reader(file)
    for row in csv_reader:
        object_rows.append(row)  # Append each row to the object_rows list

# Create the session folder if it doesn't exist
session_npz_files_dir = "session_npz_files"
session_folder_path = os.path.join(session_npz_files_dir, session_name)
os.makedirs(session_folder_path, exist_ok=True)

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

# Process each successful grasping row
for row in success_grasping_rows:

    # Create a folder for the target object
    folder_name = row[1]  # The target object name
    target_obj_name = row[1]
    folder_path = os.path.join(session_folder_path, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    # Parse scores and store them in a dictionary
    scores = row[5].split("/")  # Scores are separated by "/"
    scores_dic = {}
    for score in scores:
        key, value = score.split("|", 1)  # Split into key and value
        value_tuple = tuple(map(float, value.split("|")))  # Convert value to a tuple of floats
        scores_dic[key] = value_tuple  # Store in the dictionary

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

    # Process each object row
    for object_row in object_rows:
        obj_enum = object_row[0]  # Object enum value
        obj_type = ObjectType(int(obj_enum))  # Convert to ObjectType enum
        obj_types = [obj_type.name.replace("_", "").lower()]  # Get object type name

        # Parse object rotation quaternion
        object_rotation = object_row[2].split("|")  # Split by "|"
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

        # Get object point cloud
        obj_pcl = obj_dataset.get_pcl(obj_types, obj_rot_matrices)

        # Create a point cloud for the object
        obj_pcl_colors = np.tile(obj_color, (obj_pcl[0].shape[0], 1))
        obj_pcl_mesh = trimesh.PointCloud(obj_pcl[0], colors=obj_pcl_colors)

        # Create a scene with the object and hand point clouds
        scene = trimesh.Scene([obj_pcl_mesh, hand_pcl_mesh])

        # Extract vertices for saving
        obj_vertices = np.array(obj_pcl_mesh.vertices)
        hand_vertices = np.array(hand_pcl_mesh.vertices)

        # Save data to an .npz file
        file_name = os.path.join(folder_path, f"{obj_types[0]}.npz")
        seq_name = seq_dict.get(obj_types[0])
        np.savez(file_name, 
                 obj_vertices=obj_vertices, 
                 hand_vertices=hand_vertices, 
                 seq=seq_name, 
                 target_obj_scores=scores_dic.get(target_obj_name), 
                 obj_scores=scores_dic.get(obj_types[0]))