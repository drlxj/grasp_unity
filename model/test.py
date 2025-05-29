import queue
import numpy as np
import torch
import matplotlib.pyplot as plt

from app.udp import UdpComms
from app.messages import TelemetryMessage, CommandMessage, ObjectType
from app.misc import quaternion_to_matrix, visualize_hand_obs
from app.obj_dataset import ObjectDataset
from nets import InferenceNet
from config import model_config

data_queue = queue.Queue()

np.set_printoptions(precision=4, suppress=True)

sock = UdpComms(ip="127.0.0.1", out_queue=data_queue, 
                tx_port=20001, rx_port=20002,
                enable_rx=True, suppress_warnings=True)

# Inference model init & load
# model = InferenceNet(config=model_config)
# model.load()
model = InferenceNet(**model_config).to('cpu')
# ckpt = torch.load(r'./files/0015_acc_vr_allx5.tar', map_location=torch.device('cpu'))  # Force loading on CPU
# ckpt = torch.load(r'./files/0012_acc_pos.tar', map_location=torch.device('cpu'))
# ckpt = torch.load(r'./files/0016_acc_vr_level1.tar', map_location=torch.device('cpu'))  # Force loading on CPU
ckpt = torch.load(r'./files//0018_acc_vr_restored.tar', map_location=torch.device('cpu'))  # Force loading on CPU
model.load_state_dict(ckpt['model_state_dict'])
model.eval()

# Get object point cloud data
obj_dataset = ObjectDataset()

# Receiving and sending messages
obj_bps_loaded = False
actual_user_data = {'obj_bps':[], 'hand_obs': []}

is_record = False
count = 0

R_unity2python = torch.Tensor(
    [
        [-1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0,],
        [0.0, 0.0, 1.0,],
    ]
)

T_quat_unity2python = torch.eye(4)
T_quat_unity2python[1:, 1:] = -R_unity2python

data = np.load(r'features.npz', allow_pickle=True)

# hand pose
hand_joint_position_python = torch.Tensor(data['subject_joints_pos_rel2wrist'])
obj_pcl = torch.Tensor(data['pcl'])
obj_bps = torch.Tensor(data['bps'])

import trimesh
obj_color = np.array([255, 0, 0, 255])  # Red with full opacity
hand_color = np.array([0, 0, 255, 255])  # Blue with full opacity

obj_pcl_colors = np.tile(obj_color, (obj_pcl.shape[0], 1))
hand_pcl_colors = np.tile(hand_color, (hand_joint_position_python.shape[0], 1))

obj_pcl_mesh = trimesh.PointCloud(obj_pcl, colors=obj_pcl_colors)
# # obj_pcl_mesh = trimesh.PointCloud(obj_pcl[0]+obj_transl[0], colors=obj_pcl_colors)
hand_pcl_mesh = trimesh.PointCloud(hand_joint_position_python, colors=hand_pcl_colors)

axis = trimesh.creation.axis(origin_size=0.02, axis_length=0.1)

scene = trimesh.Scene([obj_pcl_mesh, hand_pcl_mesh, axis])
scene.show()


"""
Model run
"""
# inputs = dict(obj_bps=obj_bps, hand_obs=hand_joint_position_obs)
# obj_probs, obj_transls = model(inputs)
obj_bps = obj_bps[::4].unsqueeze(0)  # Add batch dimension
hand_joint_position_obs = hand_joint_position_python.flatten().unsqueeze(0)  # Add batch dimension
prediction = model(obj_bps=obj_bps, hand_joints=hand_joint_position_obs[:, 3:])
obj_probs = prediction["obj_logit"]
# obj_transls = prediction["obj_translation"]
obj_transls = torch.ones((obj_probs.size(0), 3)) 
# probs: (n_objcts, 1)
# transls: (n_objcts, 3)
# obj_transls = torch.einsum("ij,nj->ni", yz_swap_matrix, obj_transls)

# import trimesh
# obj_color = np.array([255, 0, 0, 255])  # Red with full opacity
# hand_color = np.array([0, 0, 255, 255])  # Blue with full opacity

# obj_pcl_colors = np.tile(obj_color, (obj_pcl[0].shape[0], 1))
# hand_pcl_colors = np.tile(hand_color, (hand_joint_position_python.shape[0], 1))

# # obj_pcl_mesh = trimesh.PointCloud(obj_pcl[0]+obj_transl[0], colors=obj_pcl_colors)
# obj_pcl_mesh = trimesh.PointCloud(obj_pcl[0]+obj_transls.detach().cpu().numpy()[0], colors=obj_pcl_colors)
# hand_pcl_mesh = trimesh.PointCloud(hand_joint_position_python, colors=hand_pcl_colors)

# scene = trimesh.Scene([obj_pcl_mesh, hand_pcl_mesh])
# scene.show()

