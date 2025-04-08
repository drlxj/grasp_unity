import torch
import numpy as np
import trimesh
from app.misc import quaternion_to_matrix, visualize_hand_obs
from app.obj_dataset import ObjectDataset
from app.objects import ObjectType
obj_dataset = ObjectDataset()

input_str = """
1,bowl,-0.01788801|-0.6881008|0.5145874|0.5112702,-0.3645718|1.102655|-0.6036674,-0.02668333|-0.007973433|0.04246283/-0.0392777|-0.01344371|0.07263142/-0.04173821|-0.002475381|0.1051975/-0.0373458|0.008887053|0.1271443/-0.06023404|0.03383756|0.073735/-0.07010102|0.05039656|0.107254/-0.06666434|0.05110502|0.1317814/-0.05933645|0.04884672|0.1532799/-0.04644001|0.05127716|0.06878978/-0.05176055|0.06964099|0.1081559/-0.04371822|0.06568277|0.1347735/-0.03394654|0.05755877|0.1568581/-0.02689731|0.05896151|0.06585997/-0.03171343|0.08042979|0.09897268/-0.028431|0.08246052|0.1257875/-0.02491802|0.0801053|0.1502806/-0.005042017|0.06183887|0.06268179/-0.005463392|0.07994747|0.08823133/-0.002104402|0.0846709|0.1081108/-0.0007733405|0.08891809|0.1300491,bowl|0.8884|0.336|0.5|0.3449/spherelarge|0.0297|0.0427|0.5|0.0015/wineglass|0.3806|0.6345|0.5|0.279/stapler|0.3809|0.1957|0.5|0.0861/hammer|0.2475|0.7099|0.5|0.203/headphones|0.1719|0.3152|0.5|0.0626/camera|0.7547|0.0263|0.5|0.0229
"""

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

R_camera = torch.Tensor(
    [
        [0.0, 0.0, 1.0],
        [-1.0, 0.0, 0.0],
        [0.0, -1.0, 0.0],
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
hand_joint_position_python = torch.einsum("ij,nj->ni", R_camera, hand_joint_position_python)


hand_pcl_mesh = trimesh.PointCloud(hand_joint_position_python, colors=hand_pcl_colors)

obj_str = "25,0.3469146|1.100217|2.112172,-0.692229|-0.02651604|0.01651645|0.7210015"

split_obj_str = obj_str.split(',')
obj_enum = split_obj_str[0]
obj_type = ObjectType(int(obj_enum))
obj_types = [obj_type.name.replace("_", "").lower()]

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
obj_rot_matrices = torch.einsum("ik,nkj->nij", R_camera, obj_rot_matrices)

obj_pcl = obj_dataset.get_pcl(obj_types, obj_rot_matrices)

obj_color = np.array([255, 0, 0, 255])

obj_pcl_colors = np.tile(obj_color, (obj_pcl[0].shape[0], 1))

obj_pcl_mesh = trimesh.PointCloud(obj_pcl[0], colors=obj_pcl_colors)

scene = trimesh.Scene([obj_pcl_mesh, hand_pcl_mesh])
scene.show()

obj_vertices = np.array(obj_pcl_mesh.vertices)
hand_vertices = np.array(hand_pcl_mesh.vertices)


np.savez("scene.npz", obj_vertices=obj_vertices, hand_vertices=hand_vertices)

print("Meshes saved successfully!")