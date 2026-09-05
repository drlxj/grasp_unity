"""
Shared utils for preprocessing and loading hand-object dataset.
Used by preprocess_all_dataset.py, visualize_npz_aitviewer.py, visualize_json_aitviewer.py.
"""
from pathlib import Path
import json
import numpy as np
import torch

# Lazy imports for heavy deps (ObjectDataset, bps)
_obj_dataset = None
_bps = None
_R_unity2python = None
_T_quat_unity2python = None


def _get_rigid():
    global _obj_dataset, _bps, _R_unity2python, _T_quat_unity2python
    if _obj_dataset is None:
        from app.obj_dataset import ObjectDataset
        from app.misc import quaternion_to_matrix
        from bps_torch.bps import bps_torch
        _obj_dataset = ObjectDataset()
        _bps = bps_torch(bps_type="custom", custom_basis=torch.from_numpy(np.load("./files/bps_new.npz")['basis']).to(torch.float32))
        _R_unity2python = torch.tensor([[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        T = torch.eye(4)
        T[1:, 1:] = -_R_unity2python
        _T_quat_unity2python = T
    return _obj_dataset, _bps, _R_unity2python, _T_quat_unity2python


def convert_unity_to_python(vec, R):
    return torch.einsum("ij,nj->ni", R, vec)


def get_object_rotation_matrix(quat_unity, T_quat_unity2python):
    from app.misc import quaternion_to_matrix
    quat_unity = quat_unity[:, [3, 0, 1, 2]]
    quat_python = torch.einsum("ij,nj->ni", T_quat_unity2python, quat_unity)
    return quaternion_to_matrix(quat_python)


def create_hand_pointcloud(joint_positions, root_position, R, with_root=True):
    relative_pos = torch.Tensor(joint_positions - root_position)
    hand_pts = convert_unity_to_python(relative_pos, R)
    if with_root:
        hand_pts = torch.cat([torch.zeros((1, 3)), hand_pts], dim=0)
    return hand_pts


def rotation_matrix_to_6d(R):
    return R[..., :3, :2].reshape(*R.shape[:-2], 6)


# 21-joint hand skeleton connections (start, end) indices
HAND_SKELETON_LINES = [
    [0, 1], [1, 2], [2, 3], [3, 4],
    [0, 5], [5, 6], [6, 7], [7, 8],
    [0, 9], [9, 10], [10, 11], [11, 12],
    [0, 13], [13, 14], [14, 15], [15, 16],
    [0, 17], [17, 18], [18, 19], [19, 20],
]


def load_npz_sample(npz_path):
    """Load one NPZ and return hand_pts (21,3), obj_pcl (1024,3), obj_trans (3,) as numpy."""
    data = np.load(npz_path, allow_pickle=True)
    hand = np.asarray(data["subject_joints_pos_rel2wrist"], dtype=np.float32)
    obj_pcl = np.asarray(data["object_pointcloud"], dtype=np.float32)
    obj_trans = np.asarray(data["object_translation"], dtype=np.float32).reshape(3)
    return hand, obj_pcl, obj_trans


def process_trial_to_features(trial):
    """
    Convert one trial (dict from all_trials.json) to feature arrays for saving NPZ.
    Returns dict with keys: object_name, ir_label, oor_label, hand_pts, obj_pcl, obj_trans, obj_rot_matrix,
    obj_bps, hand_rot_6d, and optionally in_reach_hand (for positive samples).
    """
    obj_dataset, bps, R, T_quat = _get_rigid()
    ir = trial["irLabel"]
    oor = trial["oorLabel"]
    is_in_reach = trial["isInReachFrame"]
    is_labeled = trial["isLabeledFrame"]
    object_name = trial["objectName"]
    target_name = trial["targetObjectName"]

    obj_pos_world = torch.Tensor(trial["objectPoseWorld"]["position"])
    obj_rot_world = torch.Tensor(trial["objectPoseWorld"]["rotation"])
    joint_pos_world = torch.Tensor(trial["gestures"]["jointsPositionWorld"])
    joint_rot_world = torch.Tensor(trial["gestures"]["jointsRotationWorld"])

    obj_pos_labeled = obj_pos_world[is_labeled]
    obj_rot_labeled = obj_rot_world[is_labeled]
    obj_rot_matrix = get_object_rotation_matrix(obj_rot_labeled, T_quat)
    obj_pcl = obj_dataset.get_pcl([object_name], obj_rot_matrix)
    obj_bps = bps.encode(obj_pcl.reshape(-1, 3), feature_type=["dists"])["dists"]
    obj_trans = convert_unity_to_python(torch.tensor([[0.0, 0.0, 0.0]]), R)

    root_labeled = joint_pos_world[is_labeled, 0:1].squeeze(0)
    leaf_labeled = joint_pos_world[is_labeled, 1:].squeeze(0)
    hand_rot_labeled = joint_rot_world[is_labeled, :].squeeze(0)
    hand_rot_matrix = get_object_rotation_matrix(hand_rot_labeled, T_quat)
    hand_pts = create_hand_pointcloud(leaf_labeled, root_labeled, R, with_root=True)
    hand_rot_6d = rotation_matrix_to_6d(hand_rot_matrix)

    out = {
        "object_name": object_name,
        "target_object_name": target_name,
        "ir_label": ir,
        "oor_label": oor,
        "hand_pts": hand_pts.numpy(),
        "obj_pcl": obj_pcl[0].numpy(),
        "obj_trans": obj_trans.squeeze().numpy(),
        "obj_rot_matrix": obj_rot_matrix,
        "obj_bps": obj_bps,
        "hand_rot_6d": hand_rot_6d,
    }
    if ir == 1 and oor == 1:
        root_reach = joint_pos_world[is_in_reach, 0:1].squeeze(0)
        leaf_reach = joint_pos_world[is_in_reach, 1:].squeeze(0)
        in_reach_pts = create_hand_pointcloud(leaf_reach, root_reach, R, with_root=True)
        obj_trans_reach = obj_pos_world[is_in_reach] - root_reach
        obj_trans_reach = convert_unity_to_python(obj_trans_reach.float(), R)
        out["obj_trans"] = obj_trans_reach.squeeze().numpy()
        out["in_reach_hand"] = in_reach_pts.numpy()
    return out


def save_feature_npz(path, feat):
    obj_trans = np.asarray(feat["obj_trans"]).reshape(-1, 3)
    np.savez(
        path,
        object_name=feat["object_name"],
        object_orientation=feat["obj_rot_matrix"].squeeze().detach().cpu().numpy(),
        object_pointcloud=feat["obj_pcl"],
        object_bps=feat["obj_bps"].squeeze().detach().cpu().numpy(),
        object_translation=obj_trans,
        subject_joints_pos_rel2wrist=feat["hand_pts"],
        subject_joints_rot=feat["hand_rot_6d"].detach().cpu().numpy(),
        in_reach_subject_joints_pos_rel2wrist=feat.get("in_reach_hand"),
        ir_label=feat["ir_label"],
        oor_label=feat["oor_label"],
    )


def get_save_path(output_base, user_id, object_name, json_idx, trial_idx, ir_label, oor_label):
    """Return path under preprocessed_dataset/{user}/{object}_{json_idx}/t_{trial_idx}/features_ir_*_oor_*_*.npz"""
    if oor_label == 2 or ir_label == 2:
        return Path(output_base) / "not_sure" / f"features_not_sure_{object_name}.npz"
    base = Path(output_base) / user_id / f"{object_name}_{json_idx}" / f"t_{trial_idx}"
    return base / f"features_ir_{ir_label}_oor_{oor_label}_{object_name}.npz"


def load_trial_sequence(json_path, trial_index=0):
    """
    Load one trial from all_trials.json and return per-frame arrays for visualization.
    Returns: hand_pts (T, 21, 3), obj_pcl (T, 1024, 3), obj_trans (T, 3), object_name.
    """
    obj_dataset, _, R, T_quat = _get_rigid()
    with open(json_path, "r") as f:
        trials = json.load(f)
    trial = trials[trial_index]
    object_name = trial["objectName"]
    obj_pos_world = torch.Tensor(trial["objectPoseWorld"]["position"])
    obj_rot_world = torch.Tensor(trial["objectPoseWorld"]["rotation"])
    joint_pos_world = torch.Tensor(trial["gestures"]["jointsPositionWorld"])
    T = joint_pos_world.shape[0]
    hand_pts_list = []
    obj_pcl_list = []
    obj_trans_list = []
    for t in range(T):
        root_t = joint_pos_world[t, 0:1]
        leaf_t = joint_pos_world[t, 1:]
        hand_pts_t = create_hand_pointcloud(leaf_t, root_t, R, with_root=True)
        hand_pts_list.append(hand_pts_t.numpy())
        obj_rot_t = get_object_rotation_matrix(obj_rot_world[t : t + 1], T_quat)
        obj_pcl_t = obj_dataset.get_pcl([object_name], obj_rot_t)[0]
        obj_trans_t = convert_unity_to_python((obj_pos_world[t] - root_t).float(), R).squeeze(0)
        obj_pcl_list.append(obj_pcl_t.numpy())
        obj_trans_list.append(obj_trans_t.numpy())
    return (
        np.stack(hand_pts_list),
        np.stack(obj_pcl_list),
        np.stack(obj_trans_list),
        object_name,
    )
