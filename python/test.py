import torch
import numpy as np
import trimesh
from app.misc import quaternion_to_matrix, visualize_hand_obs
from app.obj_dataset import ObjectDataset


input_str = "1,eyeglasses,0.04077119|-0.1998562|0.666889/0.04077119|-0.1998562|0.666889/0.01604635|-0.2049475|0.6620697/-0.007696524|-0.2093061|0.6551185/-0.03405993|-0.2244981|0.6427016/-0.0582176|-0.2482979|0.6386139/-0.05314863|-0.2222364|0.6936209/-0.0775388|-0.2485944|0.6802029/-0.08276176|-0.2621169|0.6603703/-0.04015823|-0.2371702|0.7044967/-0.07302618|-0.2654502|0.70288/-0.09113881|-0.2841318|0.6929622/-0.02493018|-0.251659|0.7042001/-0.05281964|-0.278367|0.6962928/-0.06709731|-0.2935304|0.6793319/0.02281256|-0.2360733|0.6804183/-0.008032203|-0.2649026|0.6990361/-0.02946332|-0.2836708|0.6866803/-0.03819537|-0.2911879|0.669688/-0.07375246|-0.2673515|0.6347436/-0.08453378|-0.2742281|0.641336/-0.1075853|-0.3014184|0.6846637/-0.07880118|-0.3047248|0.6607575/-0.0477722|-0.2955487|0.650147,eyeglasses|0.8154|0.9872|0.5|0.4209/waterbottle|0.2385|0.8172|0.5|0.1019/toothpaste|0.8982|0.6987|0.5|0.3282/toruslarge|0.3376|0.8441|0.5|0.149"


split_data = input_str.split(',')

hand_joints = split_data[2]

joint_positions = hand_joints.split('/')

print(len(joint_positions))

positions = []
for joint in joint_positions:
    coords = list(map(float, joint.split('|')))
    positions.append(coords)

index_mapping = [
    3, 4, 5, 19,  # Thumb
    6, 7, 8, 20,  # Index
    9, 10, 11, 21,  # Middle
    12, 13, 14, 22,  # Ring
    16, 17, 18, 23  # Pinky
]

relative_pos_globals = []

for i in range(20):
    t = positions[index_mapping[i]]

    # 计算相对位置
    relative_pos_global = [t[0] - positions[0][0], t[1] - positions[0][1], t[2] - positions[0][2]]

    # 存入 message
    relative_pos_globals.append(relative_pos_global)

hand_root_position_unity = torch.tensor(positions[0]).unsqueeze(0)
hand_joint_position_unity = torch.tensor(relative_pos_globals)

R_unity2python = torch.Tensor(
    [
            [-1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0,],
            [0.0, 0.0, 1.0,],
        ]
)

hand_root_position_python = torch.einsum("ij,nj->ni", R_unity2python, hand_root_position_unity)

hand_joint_position_python = torch.einsum("ij,nj->ni", R_unity2python, hand_joint_position_unity)
global_hand_joint_position_python = hand_root_position_python + hand_joint_position_python

thumb_color = np.array([255, 0, 0, 255])   # Red color for Thumb
index_color = np.array([0, 255, 0, 255])   # Green color for Index finger
middle_color = np.array([0, 0, 255, 255])  # Blue color for Middle finger
ring_color = np.array([255, 255, 0, 255])   # Yellow color for Ring finger
pinky_color = np.array([255, 0, 255, 255])  # Purple color for Pinky finger
root_color = np.array([0, 255, 255, 255])   # Cyan color for Root (Wrist)


finger_colors = [
    thumb_color, thumb_color, thumb_color, thumb_color,
    index_color, index_color, index_color, index_color,
    middle_color, middle_color, middle_color, middle_color,
    ring_color, ring_color, ring_color, ring_color,
    pinky_color, pinky_color, pinky_color, pinky_color
]

hand_pcl_colors = np.array(finger_colors)

root_pcl_colors = np.tile(root_color, (hand_root_position_python.shape[0], 1))

hand_pcl_mesh = trimesh.PointCloud(hand_joint_position_python, colors=hand_pcl_colors)
root_pcl_mesh = trimesh.PointCloud(hand_root_position_python, colors=root_pcl_colors)

obj_str = "eyeglasses,-0.1|-0.5|0.1,13.18135|10.15843|123.5202,0.1315742|-0.05910337|0.8669076|0.4771439"
split_obj_str = obj_str.split(',')
object_type = split_obj_str[0]
object_pos = split_obj_str[1].split("|")
object_pos = [float(x) for x in object_pos]
object_rotation = split_obj_str[3].split("|")
object_rotation = [float(x) for x in object_rotation]

T_quat_unity2python = torch.eye(4)
T_quat_unity2python[1:, 1:] = -R_unity2python


obj_types = []
obj_types.append(object_type)

object_rotations = []
object_rotations.append(object_rotation)

obj_quats_unity = torch.Tensor(object_rotations)
obj_quats_python = torch.einsum("ij,nj->ni", T_quat_unity2python, obj_quats_unity)
obj_rot_matrices = quaternion_to_matrix(obj_quats_python)

obj_positions = []
obj_positions.append(object_pos)

obj_dataset = ObjectDataset()

obj_pcl = obj_dataset.get_pcl(obj_types, obj_rot_matrices)

# print(obj_pcl)

obj_transl =  torch.einsum("ij,nj->ni", R_unity2python, torch.tensor(obj_positions))

obj_pcl_global = (obj_pcl + obj_transl.unsqueeze(1)).detach()

obj_color = np.array([255, 0, 0, 255])
obj_pcl_colors = np.tile(obj_color, (obj_pcl_global[0].shape[0], 1))
obj_pcl_mesh = trimesh.PointCloud(obj_pcl_global[0], colors=obj_pcl_colors)

axis = trimesh.creation.axis(origin_size=0.02)

scene = trimesh.Scene([hand_pcl_mesh, obj_pcl_mesh])

# obj_dataset.visualize_obj(obj_names=obj_types, obj_pcls=obj_pcl_global, hand_joints=global_hand_joint_position_python)
scene.show()