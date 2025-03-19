import torch
import numpy as np
import trimesh
from app.misc import quaternion_to_matrix, visualize_hand_obs
from app.obj_dataset import ObjectDataset


input_str = "1,waterbottle,0.1739016|-0.92238|-0.09425847|0.3317967,-0.01071227|-0.4115045|0.9399728,-0.03864405|-0.03201029|-0.005057693/-0.05862665|-0.05793095|-0.008697152/-0.07517025|-0.08614221|0.001399755/-0.08402801|-0.1077945|0.01003754/-0.08340964|-0.04270923|0.03600419/-0.1015669|-0.07365698|0.04972434/-0.1006668|-0.09821683|0.04832792/-0.09506142|-0.1198955|0.04474485/-0.07014853|-0.03940994|0.05404299/-0.08787835|-0.07418895|0.0731864/-0.08571017|-0.1018123|0.06989062/-0.07867354|-0.1241017|0.0601716/-0.05150533|-0.04156852|0.06360817/-0.06887984|-0.06937706|0.08562732/-0.07330739|-0.09584737|0.08765972/-0.07474899|-0.1200286|0.08286572/-0.03027651|-0.04510403|0.0687499/-0.04263839|-0.06377947|0.09035003/-0.04781342|-0.08191556|0.09856749/-0.05526525|-0.1018431|0.1050456,waterbottle|0.6516|0.4755|0.5|0.6911/eyeglasses|0.0255|0.1985|0.5|0.0113/toruslarge|0.1863|0.4132|0.5|0.1718/toothpaste|0.247|0.2284|0.5|0.1258"


split_data = input_str.split(',')

hand_joints = split_data[4]

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