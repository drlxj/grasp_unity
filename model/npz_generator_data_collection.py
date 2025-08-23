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

def rotation_matrix_to_6d(R: torch.Tensor) -> torch.Tensor:
    """Convert (N, 3, 3) rotation matrices to 6D representation (N, 6)."""
    return R[..., :3, :2].reshape(*R.shape[:-2], 6)


def get_object_rotation_matrix(quat_unity, T_quat_unity2python):
    """Convert Unity quaternions (N, 4) to rotation matrices (N, 3, 3)."""
    # quat_unity shape: (N, 4) with Unity format (x, y, z, w)
    # Convert to Python format (w, x, y, z)
    quat_unity = quat_unity[:, [3, 0, 1, 2]]  # (N, 4)
    quat_python = torch.einsum("ij,nj->ni", T_quat_unity2python, quat_unity)
    
    # Convert to rotation matrices
    transformed_matrices = quaternion_to_matrix(quat_python)  # (N, 3, 3)
    
    return transformed_matrices

def create_hand_pointcloud(joint_positions, root_position, R, with_root=True):
    relative_pos = torch.Tensor(joint_positions - root_position)
    hand_pts = convert_unity_to_python(relative_pos, R)
    if with_root:
        hand_pts = torch.cat([torch.zeros((1, 3)), hand_pts], dim=0)
    return hand_pts

# def create_hand_pointcloud(joint_positions, root_position, R, with_root=True):
#     hand_pts = torch.cat([root_position, joint_positions], dim=0)
#     return convert_unity_to_python(hand_pts, R) 

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

def visualize_joint_orientations(hand_pts, hand_rot_matrices, scene, scale=0.02):
    """Visualize joint orientations as coordinate frames."""
    for i, (pos, rot_matrix) in enumerate(zip(hand_pts, hand_rot_matrices)):
        # rot_matrix is already in the correct format (3, 3)
        rot_matrix_np = rot_matrix.numpy()
        
        # Create coordinate frame
        axis = trimesh.creation.axis(
            origin_size=0.005, 
            axis_radius=0.002, 
            axis_length=scale,
            transform=np.eye(4)
        )
        axis.apply_transform(
            np.array([
                [rot_matrix_np[0,0], rot_matrix_np[0,1], rot_matrix_np[0,2], pos[0]],
                [rot_matrix_np[1,0], rot_matrix_np[1,1], rot_matrix_np[1,2], pos[1]],
                [rot_matrix_np[2,0], rot_matrix_np[2,1], rot_matrix_np[2,2], pos[2]],
                [0, 0, 0, 1]
            ])
        )
        scene.add_geometry(axis)


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
    # camera_transform = make_camera_look_at(eye=[0.3, 0.3, -1])
    camera_transform = make_camera_look_at(eye=[0.15, 0.15, -0.5])
    scene.camera_transform = camera_transform

def save_feature_file(path, object_name, obj_rot, obj_pcl, bps_feat, obj_trans, hand_verts, hand_joint_rot_6d, ir_label, oor_label, in_reach_hand=None):
    np.savez(
        path,
        object_name = object_name,
        object_orientation=obj_rot.squeeze().detach().cpu(),
        object_pointcloud=obj_pcl, #(1024, 3)
        object_bps=bps_feat.squeeze().detach().cpu(), # (1, 4096)
        object_translation=obj_trans.squeeze().detach().cpu(), # (1, 3)
        subject_joints_pos_rel2wrist=hand_verts, # (21, 3)
        subject_joints_rot=hand_joint_rot_6d.detach().cpu(), # (21, 6)
        in_reach_subject_joints_pos_rel2wrist=in_reach_hand if in_reach_hand is not None else None,
        ir_label=ir_label,  # in-reach label
        oor_label=oor_label,  # out-of-reach label
    )

def get_save_path_and_dir(output_dir, target_object_name, json_idx, trial_idx, ir_label, oor_label, object_name):
    """Return (save_path, save_dir, fname) for the given sample type."""
    if oor_label == 2 or ir_label == 2:
        fname = f"features_not_sure_{object_name}.npz"
        save_dir = Path("session_npz_files") / "not_sure"
    else:
        fname = f"features_ir_{ir_label}_oor_{oor_label}_{object_name}.npz"
        save_dir = output_dir / f"{target_object_name}_{json_idx}" / f"t_{trial_idx}"
    save_path = save_dir / fname
    return save_path, save_dir, fname

def save_scene_as_image(scene, save_path, width=920, height=800):
    """Save the scene as an image file."""
    # Set the scene size
    scene.camera.resolution = (width, height)
    
    # Render the scene to an image
    png = scene.save_image(resolution=(width, height), visible=True)
    
    # Save the image
    with open(save_path, 'wb') as f:
        f.write(png)
    print(f"Saved image to: {save_path}")

def visualize_scene(hand_pts, joint_colors, obj_pcl, obj_trans, hand_rot_matrices=None, save_image=False, save_path=None):
    scene = trimesh.Scene()
    visualize_hand_with_skeleton(hand_pts, joint_colors, scene)
    # if hand_rot_matrices is not None:
    #     visualize_joint_orientations(hand_pts, hand_rot_matrices, scene)
    obj_mesh = trimesh.PointCloud(obj_pcl + obj_trans, colors=np.tile([255, 0, 0, 255], (obj_pcl.shape[0], 1)))
    scene.add_geometry(obj_mesh)
    add_coordinate_frame(scene)
    set_camera(scene)
    
    if save_image and save_path:
        save_scene_as_image(scene, save_path)
    else:
        scene.show()

obj_dataset = ObjectDataset()
bps_basis = torch.from_numpy(np.load("./files/bps_new.npz")['basis']).to(torch.float32)
bps = bps_torch(bps_type="custom", custom_basis=bps_basis)

R_unity2python = torch.tensor([[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
T_quat_unity2python = torch.eye(4)
T_quat_unity2python[1:, 1:] = -R_unity2python

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

test_user_id = "s2"
is_visualize = False
data_dir = Path("../collected_data") / test_user_id
output_dir = Path("session_npz_files") / test_user_id
output_dir.mkdir(parents=True, exist_ok=True)

root_positions = []
count_dir = 0
idx = 0
for obj_dir in data_dir.iterdir():
    if not obj_dir.is_dir():
        continue
    json_files = list(obj_dir.glob("**/all_trials.json"))

    for json_idx, json_file in enumerate(json_files):
        with open(json_file, "r") as f:
            trials = json.load(f)

        for trial in trials:
            trial_idx = trial["trialIndex"]
            target_object_name = trial["targetObjectName"]
            object_name = trial["objectName"]
            trial_index = trial["trialIndex"]
            ir_label = trial["irLabel"]  # in-reach label
            oor_label = trial["oorLabel"]  # out-of-reach label
            is_in_reach_frame = trial["isInReachFrame"]
            is_labeled_frame = trial["isLabeledFrame"]
            obj_pos_world = torch.Tensor(trial["objectPoseWorld"]["position"])
            obj_rot_world = torch.Tensor(trial["objectPoseWorld"]["rotation"])
            joint_pos_world = torch.Tensor(trial["gestures"]["jointsPositionWorld"])
            joint_rot_world = torch.Tensor(trial["gestures"]["jointsRotationWorld"])
            
            # obj_pos_world = torch.Tensor(trial["objectPoseCamera"]["position"])
            # obj_rot_world = torch.Tensor(trial["objectPoseCamera"]["rotation"])
            # joint_pos_world = torch.Tensor(trial["gestures"]["jointsPositionCamera"])

            obj_pos_in_labeled_frame = obj_pos_world[is_labeled_frame]
            obj_rot_in_labeled_frame = obj_rot_world[is_labeled_frame]
            obj_rot_matrix = get_object_rotation_matrix(obj_rot_in_labeled_frame, T_quat_unity2python)
            obj_pcl = obj_dataset.get_pcl([object_name], obj_rot_matrix)
            obj_bps = bps.encode(obj_pcl.reshape(-1, 3), feature_type=["dists"])["dists"]
            obj_trans = convert_unity_to_python(torch.tensor([[0.0, 0.0, 0.0]]), R_unity2python)
            
            root_pos_in_labeled_frame = joint_pos_world[is_labeled_frame, 0:1].squeeze(0)
            leaf_pos_in_labeled_frame = joint_pos_world[is_labeled_frame, 1:].squeeze(0)
            hand_rot_in_labeled_frame = joint_rot_world[is_labeled_frame, :].squeeze(0)
            hand_rot_matrix = get_object_rotation_matrix(hand_rot_in_labeled_frame, T_quat_unity2python)
            hand_pts = create_hand_pointcloud(leaf_pos_in_labeled_frame, root_pos_in_labeled_frame, R_unity2python, with_root=True)
            

            # # Convert to object system
            # R_world_to_obj = obj_rot_matrix.squeeze().T
            # obj_pcl[0] = convert_unity_to_python(obj_pcl[0], R_world_to_obj)
            # hand_pts = torch.einsum("ij,nj->ni", R_world_to_obj, hand_pts)
            # hand_rot_matrix = torch.einsum("ij,njk->nik", R_world_to_obj, hand_rot_matrix)
            
            hand_rot_6d = rotation_matrix_to_6d(hand_rot_matrix)
            
            if ir_label == 1 and oor_label == 1:
                # Positive sample - save with in-reach data
                in_reach_root = joint_pos_world[is_in_reach_frame, 0:1].squeeze(0)
                in_reach_leaf = joint_pos_world[is_in_reach_frame, 1:].squeeze(0)
                hand_rot_in_reach_frame = joint_rot_world[is_in_reach_frame, :].squeeze(0)
                in_reach_pts = create_hand_pointcloud(in_reach_leaf, in_reach_root, R_unity2python, with_root=True)
                hand_rot_matrix = get_object_rotation_matrix(hand_rot_in_reach_frame, T_quat_unity2python)
                

                obj_trans = obj_pos_world[is_in_reach_frame] - in_reach_root
                obj_trans = convert_unity_to_python(obj_trans.float(), R_unity2python)

                # # Convert to object system
                # in_reach_pts = torch.einsum("ij,nj->ni", R_world_to_obj, in_reach_pts)
                # obj_trans = convert_unity_to_python(obj_trans, R_world_to_obj)
                # hand_rot_matrix = torch.einsum("ij,njk->nik", R_world_to_obj, hand_rot_matrix)

                hand_rot_6d = rotation_matrix_to_6d(hand_rot_matrix)

                if trial_idx == 0:
                    root_positions.append(root_pos_in_labeled_frame.squeeze())

                save_path, save_dir, fname = get_save_path_and_dir(output_dir, target_object_name, json_idx, trial_idx, ir_label, oor_label, object_name)
                if is_visualize:
                    print(save_path)
                    # Create image save path
                    folder, subject, target, trial, filename = save_path.parts
                    img_save_path = Path(folder) / subject / f"{target}_{save_path.stem}.png"
                    # if img_save_path.exists():
                    #     print(f"Image already exists, skipping: {img_save_path}")
                    #     continue
                    
                    img_save_path.parent.mkdir(parents=True, exist_ok=True)
                    visualize_scene(in_reach_pts.numpy(), joint_colors, obj_pcl[0], obj_trans, hand_rot_matrix, save_image=False, save_path=img_save_path)
                    continue
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_feature_file(save_path, object_name, obj_rot_matrix, obj_pcl[0].numpy(), obj_bps, obj_trans, hand_pts.numpy(), hand_rot_6d, ir_label, oor_label, in_reach_pts.numpy())
            else:
                save_path, save_dir, fname = get_save_path_and_dir(output_dir, target_object_name, json_idx, trial_idx, ir_label, oor_label, object_name)
                if is_visualize:
                    if 'not_sure' in str(save_path):
                        continue
                    print(save_path)
                    folder, subject, target, trial, filename = save_path.parts
                    img_save_path = Path(folder) / subject / f"{target}_{save_path.stem}.png"
                    
                    # if img_save_path.exists():
                    #     print(f"Image already exists, skipping: {img_save_path}")
                    #     continue
                    img_save_path.parent.mkdir(parents=True, exist_ok=True)
                    visualize_scene(hand_pts.numpy(), joint_colors, obj_pcl[0], obj_trans, hand_rot_matrix, save_image=False, save_path=img_save_path)
                    continue
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_feature_file(save_path, object_name, obj_rot_matrix, obj_pcl[0].numpy(), obj_bps, obj_trans, hand_pts.numpy(), hand_rot_6d, ir_label, oor_label)
            idx += 1

print(idx)

root_positions = torch.cat(root_positions).reshape(-1, 3).numpy()
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
plt.savefig(f'root_positions_xy_{test_user_id}.png', dpi=300)
plt.show()