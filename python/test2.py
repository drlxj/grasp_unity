import torch
import numpy as np
import trimesh
from app.misc import quaternion_to_matrix, visualize_hand_obs
from app.obj_dataset import ObjectDataset
obj_dataset = ObjectDataset()

input_str = "1,eyeglasses,0.3542671|-0.7642571|-0.2927838|0.4524198,0.02043551|-0.5225396|0.9428334,-0.03086507|-0.03979766|-0.00961566/-0.04674917|-0.06816441|-0.01732928/-0.05474627|-0.1019467|-0.01636487/-0.05911821|-0.1268433|-0.01751089/-0.05318421|-0.08082819|0.03183663/-0.05711967|-0.1194673|0.03512681/-0.05273479|-0.1409225|0.02311444/-0.04537821|-0.156821|0.008196712/-0.03425539|-0.08055305|0.04483271/-0.04006493|-0.1230135|0.05530262/-0.03777802|-0.149533|0.04565364/-0.03413469|-0.1710308|0.03207797/-0.0129652|-0.07966101|0.04649484/-0.01727843|-0.1175771|0.05873805/-0.01713473|-0.1436949|0.05075985/-0.01698208|-0.1643911|0.03663701/0.00908941|-0.07725799|0.04304689/0.007680655|-0.1078312|0.05079663/0.00799191|-0.1269302|0.04237854/0.00552094|-0.1442201|0.0280897,eyeglasses|0.8015|0.8622|0.5|0.356/waterbottle|0.7063|0.4595|0.5|0.1672/toothpaste|0.7149|0.642|0.5|0.2365/toruslarge|0.7561|0.6171|0.5|0.2404"


split_data = input_str.split(',')

hand_joints = split_data[4]

joint_positions = hand_joints.split('/')

hand_joint_position = []
for joint in joint_positions:
    coords = list(map(float, joint.split('|')))
    hand_joint_position.append(coords)

R_unity2python = torch.Tensor(
    [
            [-1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0,],
            [0.0, 0.0, 1.0,],
        ]
)

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

hand_joint_position_unity = torch.Tensor(hand_joint_position)

hand_joint_position_python = torch.einsum("ij,nj->ni", R_unity2python, hand_joint_position_unity)


hand_pcl_mesh = trimesh.PointCloud(hand_joint_position_python, colors=hand_pcl_colors)

obj_types = ["eyeglasses"]

obj_str = "18,0.1|-2|0.1,-0.05778112|0.01197947|0.9924962|0.1070939"
split_obj_str = obj_str.split(',')
object_rotation = split_obj_str[2].split("|")
object_rotation = [float(x) for x in object_rotation]
object_rotation = [object_rotation[3], object_rotation[0], object_rotation[1], object_rotation[2]]

object_rotations = []
object_rotations.append(object_rotation)

obj_quats_unity = torch.Tensor(object_rotations)

T_quat_unity2python = torch.eye(4)
T_quat_unity2python[1:, 1:] = -R_unity2python

obj_quats_python = torch.einsum("ij,nj->ni", T_quat_unity2python, obj_quats_unity)

obj_rot_matrices = quaternion_to_matrix(obj_quats_python)

obj_pcl = obj_dataset.get_pcl(obj_types, obj_rot_matrices)

obj_color = np.array([255, 0, 0, 255])

obj_pcl_colors = np.tile(obj_color, (obj_pcl[0].shape[0], 1))

obj_pcl_mesh = trimesh.PointCloud(obj_pcl[0], colors=obj_pcl_colors)

scene = trimesh.Scene([obj_pcl_mesh, hand_pcl_mesh])
scene.show()