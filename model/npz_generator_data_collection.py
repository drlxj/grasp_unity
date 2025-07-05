from pathlib import Path
import torch
import numpy as np
import trimesh
import json
from app.misc import quaternion_to_matrix
from app.obj_dataset import ObjectDataset
from bps_torch.bps import bps_torch

def convert_unity_to_python(vec, R):
    return torch.einsum("ij,nj->ni", R, vec)

def get_object_rotation_matrix(quat_unity, R):
    quat = quat_unity[[-1, 0, 1, 2]].reshape(1, 4)
    T = torch.eye(4)
    T[1:, 1:] = -R
    quat_python = torch.einsum("ij,nj->ni", T, quat)
    return quaternion_to_matrix(quat_python)

def create_hand_pointcloud(joint_positions, root_position, R, with_root=True):
    relative_pos = torch.Tensor(joint_positions - root_position)
    hand_pts = convert_unity_to_python(relative_pos, R)
    if with_root:
        hand_pts = torch.cat([torch.zeros((1, 3)), hand_pts], dim=0)
    return hand_pts

def visualize_hand_with_skeleton(hand_pts, joint_colors, scene):
    hand_mesh = trimesh.PointCloud(hand_pts, colors=joint_colors)
    scene.add_geometry(hand_mesh)
    lines = [
        [0, 1], [1, 2], [2, 3], [3, 4],
        [0, 5], [5, 6], [6, 7], [7, 8],
        [0, 9], [9,10], [10,11], [11,12],
        [0,13], [13,14], [14,15], [15,16],
        [0,17], [17,18], [18,19], [19,20],
    ]
    segments = np.array([[hand_pts[s], hand_pts[e]] for s, e in lines])
    path = trimesh.load_path(segments)
    scene.add_geometry(path)


def make_camera_look_at(eye, target=np.zeros(3), up=np.array([0, 1, 0])):
    eye = np.asarray(eye)
    target = np.asarray(target)
    up = np.asarray(up)

    forward = eye - target
    forward /= np.linalg.norm(forward)

    right = np.cross(up, forward)
    right /= np.linalg.norm(right)

    true_up = np.cross(forward, right)

    camera_transform = np.eye(4)
    camera_transform[:3, 0] = right     # X → red → right
    camera_transform[:3, 1] = true_up   # Y → green → up
    camera_transform[:3, 2] = forward   # Z → blue → forward
    camera_transform[:3, 3] = eye       # camera position
    return camera_transform

def add_coordinate_frame(scene):
    axis = trimesh.creation.axis(origin_size=0.005, axis_radius=0.002, axis_length=0.1)
    scene.add_geometry(axis)

def set_camera(scene):
    camera_transform = make_camera_look_at(eye=[0.3, 0.3, -1])
    scene.camera_transform = camera_transform

def save_feature_file(path, obj_rot, obj_pcl, bps_feat, obj_trans, hand_verts, in_reach_hand=None):
    np.savez(
        path,
        object_orientation=obj_rot.squeeze().detach().cpu(),
        object_pointcloud=obj_pcl,
        object_bps=bps_feat.squeeze().detach().cpu(),
        object_translation=obj_trans.squeeze().detach().cpu(),
        subject_joints_pos_rel2wrist=hand_verts,
        in_reach_subject_joints_pos_rel2wrist=in_reach_hand if in_reach_hand is not None else None,
    )

obj_dataset = ObjectDataset()
bps_basis = torch.from_numpy(np.load("./files/bps_new.npz")['basis']).to(torch.float32)
bps = bps_torch(bps_type="custom", custom_basis=bps_basis)

R_unity2python = torch.tensor([[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])

colors = {
    "thumb": [255, 0, 0, 255],
    "index": [0, 255, 0, 255],
    "middle": [0, 0, 255, 255],
    "ring": [255, 255, 0, 255],
    "pinky": [255, 0, 255, 255],
    "root": [0, 255, 255, 255],
}
joint_colors = np.array(
    [colors["root"]] +
    [colors["thumb"]]*4 + [colors["index"]]*4 + [colors["middle"]]*4 +
    [colors["ring"]]*4 + [colors["pinky"]]*4
)

test_user_id = "s3"
is_visualize = True
grasping_position = torch.tensor([0.0, 0.0, 0.5])
data_dir = Path("../collected_data") / test_user_id
output_dir = Path("session_npz_files") / test_user_id
output_dir.mkdir(parents=True, exist_ok=True)

root_positions = []
for obj_dir in data_dir.iterdir():
    if not obj_dir.is_dir():
        continue
    json_file = next(obj_dir.glob("**/all_trials.json"), None)
    
    with open(json_file, "r") as f:
        trials = json.load(f)

    for trial in trials:
        object_name = trial["objectName"]
        trial_index = trial["trialIndex"]
        gesture_label = trial["label"]
        is_in_reach_frame = trial["isInReachFrame"]
        is_labeled_frame = trial["isLabeledFrame"]
        obj_pos = torch.Tensor(trial["objectPoseWorld"]["position"])[is_labeled_frame].squeeze()
        obj_rot = torch.Tensor(trial["objectPoseWorld"]["rotation"])[is_labeled_frame].squeeze()
        joint_pos = torch.Tensor(trial["gestures"]["jointsPositionWorld"])
        root_pos = joint_pos[is_labeled_frame, 0:1].squeeze()
        leaf_pos = joint_pos[is_labeled_frame, 1:].squeeze()

        hand_pts = create_hand_pointcloud(leaf_pos, root_pos, R_unity2python, with_root=True)
        obj_rot_matrix = get_object_rotation_matrix(obj_rot, R_unity2python)
        obj_types = [object_name]
        obj_pcl = obj_dataset.get_pcl(obj_types, obj_rot_matrix)
        obj_bps = bps.encode(obj_pcl.reshape(-1, 3), feature_type=["dists"])["dists"]
        obj_trans = convert_unity_to_python(torch.tensor([[0.0, 0.0, 0.0]]), R_unity2python)

        if is_visualize:
            scene = trimesh.Scene()
            visualize_hand_with_skeleton(hand_pts.numpy(), joint_colors, scene)
            obj_mesh = trimesh.PointCloud(obj_pcl[0] + obj_trans, colors=np.tile([255, 0, 0, 255], (obj_pcl[0].shape[0], 1)))
            scene.add_geometry(obj_mesh)
            add_coordinate_frame(scene)
            set_camera(scene)
            scene.show()

        if gesture_label == 1:
            obj_trans = grasping_position - torch.tensor(root_pos)
            obj_trans = convert_unity_to_python(obj_trans.unsqueeze(0).float(), R_unity2python)
            in_reach_leaf =joint_pos[is_in_reach_frame, 1:].squeeze()
            in_reach_pts = create_hand_pointcloud(in_reach_leaf, root_pos, R_unity2python, with_root=True)
            root_positions.append(root_pos)

            if is_visualize:
                scene = trimesh.Scene()
                visualize_hand_with_skeleton(in_reach_pts.numpy(), joint_colors, scene)
                obj_mesh = trimesh.PointCloud(obj_pcl[0] + obj_trans, colors=np.tile([255, 0, 0, 255], (obj_pcl[0].shape[0], 1)))
                scene.add_geometry(obj_mesh)
                add_coordinate_frame(scene)
                set_camera(scene)
                scene.show()

            save_path = output_dir / f"{object_name}_{trial_index}" / "t_0" / "features.npz"
            save_path.parent.mkdir(parents=True, exist_ok=True)
            # save_feature_file(save_path, obj_rot_matrix, obj_pcl[0].numpy(), obj_bps, obj_trans, hand_pts.numpy(), in_reach_pts.numpy())
        else:
            fname = "features_counter.npz" if gesture_label == 0 else f"features_not_sure_{object_name}.npz"
            save_dir = output_dir if gesture_label == 0 else Path("session_npz_files") / "not_sure"
            save_dir.mkdir(parents=True, exist_ok=True)
            # save_feature_file(save_dir / fname, obj_rot_matrix, obj_pcl[0].numpy(), obj_bps, obj_trans, hand_pts.numpy())


root_positions = np.array(root_positions)
# project root positions to the xy plane and visualize the point distribution with matplotlib, and make (0, 0) as the figure center
root_positions_xy = root_positions[:, :2]
import matplotlib.pyplot as plt
plt.figure(figsize=(8, 8))
plt.scatter(root_positions_xy[:, 0], root_positions_xy[:, 1], alpha=0.5)
x_max = np.max(np.abs(root_positions_xy[:, 0]))
y_max = np.max(np.abs(root_positions_xy[:, 1]))
max_range = max(x_max, y_max)
plt.xlim(-max_range, max_range)
plt.ylim(-max_range, max_range)
plt.axhline(0, color='gray', linewidth=0.5)
plt.axvline(0, color='gray', linewidth=0.5)
plt.xlabel('X')
plt.ylabel('Y')
plt.title('Root Positions Projected to XY Plane')
plt.gca().set_aspect('equal', adjustable='box')
plt.savefig('root_positions_xy_s2.png', dpi=300)
plt.show()