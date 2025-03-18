import torch
import numpy as np
import trimesh

input_str = "1,eyeglasses,0.2461841|-0.2744585|0.9239205/0.2461841|-0.2744585|0.9239205/0.2273493|-0.2897042|0.9162219/0.2087878|-0.30308|0.9065157/0.1915347|-0.3270717|0.8929578/0.1798158|-0.3585033|0.8888719/0.1691902|-0.3350419|0.9389218/0.1630907|-0.3674383|0.9201667/0.1691038|-0.3795621|0.8999794/0.1853761|-0.3426867|0.9522935/0.1700163|-0.382004|0.9444862/0.169121|-0.4018389|0.9253876/0.2050132|-0.3489742|0.955011/0.1913328|-0.3852659|0.9509537/0.1877072|-0.4046817|0.9331766/0.243877|-0.3144416|0.9371382/0.2263146|-0.3534342|0.9531103/0.2158573|-0.3818874|0.9481295/0.212358|-0.3958448|0.9337943/0.1693443|-0.3792528|0.8807468/0.17694|-0.3895497|0.8815376/0.1706401|-0.4169577|0.9055445/0.1856544|-0.4180194|0.9128713/0.2069788|-0.407788|0.9161717,eyeglasses|0.7115|0.7573|0.5|0.4081/toothpaste|0.6771|0.4257|0.5|0.2184/waterbottle|0.269|0.6974|0.5|0.1421/toruslarge|0.6607|0.4622|0.5|0.2314"

split_data = input_str.split(',')

hand_joints = split_data[2]

joint_positions = hand_joints.split('/')

positions = []
for joint in joint_positions:
    coords = list(map(float, joint.split('|')))
    positions.append(coords)

hand_root_position_unity = torch.tensor(positions[0]).unsqueeze(0)
hand_joint_position_unity = torch.tensor(positions[1:])

R_unity2python = torch.Tensor(
    [
            [-1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0,],
            [0.0, 0.0, 1.0,],
        ]
)

hand_root_position_python = torch.einsum("ij,nj->ni", R_unity2python, hand_root_position_unity)
hand_joint_position_python = torch.einsum("ij,nj->ni", R_unity2python, hand_joint_position_unity)

hand_color = np.array([0, 0, 255, 255])  # Blue with full opacity
root_color = np.array([0, 255, 0, 255])

hand_pcl_colors = np.tile(hand_color, (hand_joint_position_python.shape[0], 1))
root_pcl_colors = np.tile(root_color, (hand_root_position_python.shape[0], 1))

hand_pcl_mesh = trimesh.PointCloud(hand_joint_position_python, colors=hand_pcl_colors)
root_pcl_mesh = trimesh.PointCloud(hand_root_position_python, colors=root_pcl_colors)

scene = trimesh.Scene([root_pcl_mesh, hand_pcl_mesh])
scene.show()