import torch
import numpy as np
import trimesh
from app.misc import quaternion_to_matrix, visualize_hand_obs
from app.obj_dataset import ObjectDataset
obj_dataset = ObjectDataset()

input_str = """
1,wineglass,0.5254482|0.6291167|0.2855043|-0.4965922,0.1497221|1.078608|-0.2310635,-0.02765245|0.02890062|0.03015408/-0.0470214|0.04257023|0.05237873/-0.06096655|0.05074036|0.08203548/-0.07350529|0.05648088|0.1024165/-0.01019727|0.05488336|0.08183329/-0.01639657|0.06266105|0.118412/-0.03571933|0.05911481|0.1326979/-0.05575394|0.05212617|0.1398035/0.001378462|0.03689063|0.08823282/-0.01903637|0.0379653|0.1259531/-0.04520599|0.02957046|0.124268/-0.06361602|0.02247655|0.1089478/0.003529117|0.01623201|0.08904754/-0.02096406|0.01461565|0.1193217/-0.04622708|0.009960294|0.112577/-0.06144979|0.007696748|0.09368476/0.001986682|-0.005370378|0.08627364/-0.01892842|-0.00421679|0.1087226/-0.03906779|-0.004769802|0.1062311/-0.05513419|-0.002304792|0.09148647,wineglass|0.4863|0.7775|0.5|0.6673/bowl|0.3294|0.2599|0.5|0.1511/headphones|0.0002|0.2711|0.5|0.0001/hammer|0.0069|0.7598|0.5|0.0092/camera|0.0231|0.4355|0.5|0.0178/stapler|0.1665|0.5203|0.5|0.1529/spherelarge|0.0026|0.3581|0.5|0.0016
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

obj_types = [split_data[1]]

obj_str = "52,-0.4635683|0.9549549|2.07406,-0.5382641|-0.4406037|-0.4626515|0.5496306"
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