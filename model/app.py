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
ckpt = torch.load(r'./files/0015_acc_vr_allx5.tar', map_location=torch.device('cpu'))  # Force loading on CPU
# ckpt = torch.load(r'./files/0012_acc_pos.tar', map_location=torch.device('cpu'))
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
R_camera = torch.Tensor(
    [
        [0.0, 0.0, 1.0],
        [-1.0, 0.0, 0.0],
        [0.0, -1.0, 0.0],
    ]
)
T_quat_unity2python = torch.eye(4)
T_quat_unity2python[1:, 1:] = -R_unity2python

while True:
    """
    Receiving
    """
    # Receive the message from Unity
    telemetry_packet = TelemetryMessage.from_bytes(data_queue.get())

    if not obj_bps_loaded:
        print("Loading for the objects' orientation info") 
        # Convert the point-cloud to bps data for each object in the scene
        obj_types = telemetry_packet.object_types
        object_type_ids = telemetry_packet.object_type_ids
        # obj_indices = telemetry_packet.object_idxs
        print("obj_types:")
        print(obj_types)
        obj_quats_unity = torch.Tensor(telemetry_packet.object_orientations) # (n_objects, 4)
        obj_quats_python = torch.einsum("ij,nj->ni", T_quat_unity2python, obj_quats_unity)

        obj_rot_matrices = quaternion_to_matrix(obj_quats_python) # (n_objects, 3, 3)
        obj_rot_matrices = torch.einsum("ik,nkj->nij", R_camera, obj_rot_matrices)
        # print("obj_quats_python:", obj_rot_matrices)
        obj_positions = telemetry_packet.object_positions

        # obj_dataset.visualize_obj(obj_types, obj_rot_matrices)
        obj_bps = torch.Tensor(obj_dataset.get_bps(obj_types, obj_rot_matrices)) # (n_objects, 1024)
        obj_bps_loaded = True
        print("Done")


    # print("Object Positions:")
    # print(obj_positions)

    # hand pose
    hand_joint_position_unity = torch.Tensor(telemetry_packet.hand_joint_position) # (n_joints, 3)
    hand_joint_position_python = torch.einsum("ij,nj->ni", R_unity2python, hand_joint_position_unity)
    hand_joint_position_python = torch.einsum("ij,nj->ni", R_camera, hand_joint_position_python)

    hand_joint_position_obs = hand_joint_position_python.reshape((-1,)).expand((obj_bps.size(0), -1)) # (n_objects, n_joints * 3)

    hand_root_position_unity = torch.Tensor(telemetry_packet.hand_root_position)
    hand_root_position_python = torch.einsum("ij,j->i", R_unity2python, hand_root_position_unity)
    global_hand_joint_position_python = hand_root_position_python + hand_joint_position_python

    # # visualization for checking coordination system transformation
    obj_pcl = obj_dataset.get_pcl(obj_types, obj_rot_matrices) # (n_obj, n_points, 3)
    obj_transl =  torch.einsum("ij,nj->ni", R_unity2python, torch.tensor(obj_positions)) # (n_obj, 3)
    obj_pcl_global = (obj_pcl + obj_transl.unsqueeze(1)).detach()
    # # obj_dataset.visualize_obj(obj_names=obj_types, obj_pcls=obj_pcl_global, hand_joints=global_hand_joint_position_python) #
    # import trimesh
    # obj_color = np.array([255, 0, 0, 255])  # Red with full opacity
    # hand_color = np.array([0, 0, 255, 255])  # Blue with full opacity
    
    # obj_pcl_colors = np.tile(obj_color, (obj_pcl[0].shape[0], 1))
    # hand_pcl_colors = np.tile(hand_color, (hand_joint_position_python.shape[0], 1))
    
    # obj_pcl_mesh = trimesh.PointCloud(obj_pcl[0], colors=obj_pcl_colors)
    # # # obj_pcl_mesh = trimesh.PointCloud(obj_pcl[0]+obj_transl[0], colors=obj_pcl_colors)
    # hand_pcl_mesh = trimesh.PointCloud(hand_joint_position_python, colors=hand_pcl_colors)
    
    # scene = trimesh.Scene([obj_pcl_mesh, hand_pcl_mesh])
    # scene.show()


    """
    Model run
    """
    # inputs = dict(obj_bps=obj_bps, hand_obs=hand_joint_position_obs)
    # obj_probs, obj_transls = model(inputs)
    prediction = model(obj_bps=obj_bps, hand_joints=hand_joint_position_obs)
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

    """
    Sending
    """
    obj_transls = torch.einsum("ik,nk->ni", R_camera.T, obj_transls)
    obj_transls = torch.einsum("ik,nk->ni", R_unity2python, obj_transls)
    obj_transls = obj_transls.detach().cpu().numpy()


    
    command_message = CommandMessage (
        object_count = telemetry_packet.object_count,
        confidence_score = obj_probs,
        object_type_ids = object_type_ids,
        object_position = obj_transls,

        # hand_root_position = telemetry_packet.hand_root_position
    )
    sock.send(command_message.to_bytes())

    """
    Data collection
    """
    # if is_record:
    #     actual_user_data['hand_obs'] = torch.cat([actual_user_data['hand_obs'], hand_joint_position_python])
    #     actual_user_data['obj_bps'] = torch.cat([actual_user_data['obj_bps'], obj_bps])
    # else:
    #     is_record = True
    #     actual_user_data['hand_obs'] = hand_joint_position_python
    #     actual_user_data["obj_bps"] = obj_bps
    # np.savez("actual_data.npz", obj_bps=actual_user_data['obj_bps'], hand_obs= actual_user_data['hand_obs'] )

