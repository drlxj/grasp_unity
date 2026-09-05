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

def get_object_rotation_matrix(quat_unity, T_quat_unity2python):
    """Convert Unity quaternions (N, 4) to rotation matrices (N, 3, 3)."""
    # quat_unity shape: (N, 4) with Unity format (x, y, z, w)
    # Convert to Python format (w, x, y, z)
    quat_unity = quat_unity[:, [3, 0, 1, 2]]  # (N, 4)
    quat_python = torch.einsum("ij,nj->ni", T_quat_unity2python, quat_unity)
    
    # Convert to rotation matrices
    transformed_matrices = quaternion_to_matrix(quat_python)  # (N, 3, 3)
    
    return transformed_matrices

data_queue = queue.Queue()

np.set_printoptions(precision=4, suppress=True)

sock = UdpComms(ip="127.0.0.1", out_queue=data_queue, 
                tx_port=20001, rx_port=20002,
                enable_rx=True, suppress_warnings=True)

# Inference model init & load
# model = InferenceNet(config=model_config)
# model.load()
model = InferenceNet(**model_config).to('cpu')
ckpt = torch.load(r'./files/0025_unityall_hand63_objects25_pos=neg.tar', map_location=torch.device('cpu'))  # Force loading on CPU

model.load_state_dict(ckpt['model_state_dict'])
model.eval()

# Get object point cloud data
obj_dataset = ObjectDataset()

# Receiving and sending messages
obj_bps_loaded = False
actual_user_data = {'obj_bps':[], 'hand_obs': []}

is_record = False
count = 0

R_unity2python = torch.tensor([[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
T_quat_unity2python = torch.eye(4)
T_quat_unity2python[1:, 1:] = -R_unity2python

hand_joint_position_null = np.load(r'./files/hand_joint_position_wo_orientation_1.npz')['hand_joint_position_wo_orientation']
while True:
    """
    Receiving
    """
    # Receive the message from Unity
    telemetry_packet = TelemetryMessage.from_bytes(data_queue.get())

    # if not obj_bps_loaded:
    print("Loading for the objects' orientation info") 
    # Convert the point-cloud to bps data for each object in the scene
    obj_types = telemetry_packet.object_types
    object_type_ids = telemetry_packet.object_type_ids
    num_objects = telemetry_packet.object_count
    print("obj_types: ", obj_types)

    obj_quats_unity = torch.Tensor(telemetry_packet.object_orientations) # (n_objects, 4) (w, x, y, z) quaternion
    obj_rot_matrices = get_object_rotation_matrix(obj_quats_unity, T_quat_unity2python) # (n_objects, 3, 3)
    
    obj_positions = telemetry_packet.object_positions

    # obj_dataset.visualize_obj(obj_types, obj_rot_matrices)
    # obj_bps = torch.Tensor(obj_dataset.get_bps(obj_types, obj_rot_matrices)) # (n_objects, 1024)
    obj_bps_loaded = True
    print("Done")

    # hand pose
    hand_joint_position_unity = torch.Tensor(telemetry_packet.hand_joint_position) # (n_joints, 3)
    hand_joint_position_python = torch.einsum("ij,nj->ni", R_unity2python, hand_joint_position_unity)
    hand_joint_position_python = torch.cat([torch.zeros((1, 3)), hand_joint_position_python], dim=0) # (n_joints + 1, 3)
    hand_joint_position_obs = hand_joint_position_python.expand((num_objects, -1,  -1))

    hand_root_position_unity = torch.Tensor(telemetry_packet.hand_root_position)
    hand_root_position_python = torch.einsum("ij,j->i", R_unity2python, hand_root_position_unity)
    global_hand_joint_position_python = hand_root_position_python + hand_joint_position_python

    hand_root_quats_unity = torch.Tensor(telemetry_packet.hand_root_orientation).unsqueeze(0)
    hand_root_rot_matrix = get_object_rotation_matrix(hand_root_quats_unity, T_quat_unity2python).squeeze(0) 
    # 去除hand root的orientation：将每个点从世界坐标系旋转回手部根节点局部坐标系
    hand_joint_position_wo_orientation = torch.einsum("ij,nj->ni", hand_root_rot_matrix.T, hand_joint_position_python)

    joint_distances = np.linalg.norm(hand_joint_position_wo_orientation - hand_joint_position_null, axis=1)
    if np.all(joint_distances < 0.05):
        is_null = True
    else:
        is_null = False

    # # 保存hand_joint_position_wo_orientation到files文件夹
    # from pathlib import Path
    # files_dir = Path("./files")
    # files_dir.mkdir(parents=True, exist_ok=True)
    # save_path = files_dir / f"hand_joint_position_wo_orientation_1.npz"
    # np.savez(
    #     save_path,
    #     hand_joint_position_wo_orientation=hand_joint_position_wo_orientation.detach().cpu().numpy(),
    # )
    # print(f"Saved hand_joint_position_wo_orientation to {save_path}")

    # object pose
    obj_pcl = obj_dataset.get_pcl(obj_types, obj_rot_matrices) # (n_obj, n_points, 3)
    obj_transl =  torch.einsum("ij,nj->ni", R_unity2python, torch.tensor(obj_positions)) # (n_obj, 3)
    obj_pcl_global = (obj_pcl + obj_transl.unsqueeze(1)).detach()

    # convert to object-centric coordinates
    def apply_rotation_to_points(points, rotation_matrix):
        """Apply rotation matrix to points using einsum."""
        return torch.einsum("ij,nj->ni", rotation_matrix, points)
    
    # # 可视化
    # import trimesh
    # # 预定义颜色常量
    # OBJ_COLOR = np.array([255, 0, 0, 255])  # Red with full opacity
    # HAND_COLOR = np.array([0, 0, 255, 255])  # Blue with full opacity
    # for i in range(num_objects):
    #     # 创建点云颜色
    #     obj_pcl_colors = np.tile(OBJ_COLOR, (obj_pcl[i].shape[0], 1))
    #     hand_pcl_colors = np.tile(HAND_COLOR, (hand_joint_position_obs[i].shape[0], 1))
        
    #     # 创建点云网格
    #     obj_pcl_mesh = trimesh.PointCloud(obj_pcl[i], colors=obj_pcl_colors)
    #     # hand_pcl_mesh = trimesh.PointCloud(hand_joint_position_obs[i], colors=hand_pcl_colors)
    #     hand_pcl_mesh = trimesh.PointCloud(hand_joint_position_wo_orientation, colors=hand_pcl_colors)
    #     axis = trimesh.creation.axis(origin_size=0.02, axis_length=0.1)

    #     # 创建场景并显示
    #     scene = trimesh.Scene([obj_pcl_mesh, hand_pcl_mesh, axis])
    #     scene.show()
    
    # convert to object-centric coordinates
    hand_joint_position_obs_copy = hand_joint_position_obs.clone()
    for obj_idx, obj_rot_matrix in enumerate(obj_rot_matrices):
        R_world_to_obj = obj_rot_matrix.T  # (3, 3)
        
        obj_pcl[obj_idx] = apply_rotation_to_points(obj_pcl[obj_idx], R_world_to_obj)
        hand_joint_position_obs_copy[obj_idx] = apply_rotation_to_points(hand_joint_position_obs[obj_idx], R_world_to_obj)
        

    # for obj_idx, obj_name in enumerate(obj_types):
    #     path = Path("session_npz_files/test") / f"{obj_name}.npz"
    #     path.parent.mkdir(parents=True, exist_ok=True)
        
    #     np.savez(path, 
    #             object_name=obj_name, 
    #             object_orientation=obj_rot_matrices[obj_idx], 
    #             object_point_cloud=obj_pcl[obj_idx], 
    #             object_translation=obj_transl[obj_idx], 
    #             subject_joints_pos_rel2wrist=hand_joint_position_obs_copy[obj_idx])

    


    """
    Model run
    """
    if not is_null:
        with torch.no_grad():  
            prediction = model(obj_pcl=obj_pcl, hand_joints=hand_joint_position_obs_copy)
            obj_probs = torch.sigmoid(prediction["obj_logit"])
    else:
        obj_probs = torch.ones((num_objects, 1))
        
    obj_transls = torch.zeros((num_objects, 3))  

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
    # 转换坐标系并准备发送数据
    obj_transls = torch.einsum("ik,nk->ni", R_unity2python, obj_transls)
    obj_transls_np = obj_transls.detach().cpu().numpy()
    
    # 创建并发送命令消息
    command_message = CommandMessage(
        packetid=telemetry_packet.telemetry_packet_idx,
        object_count=telemetry_packet.object_count,
        confidence_score=obj_probs,
        object_type_ids=object_type_ids,
        object_position=obj_transls_np,
        # hand_root_position=telemetry_packet.hand_root_position
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

