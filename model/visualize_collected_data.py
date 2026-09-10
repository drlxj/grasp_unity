#!/usr/bin/env python3
"""
Visualize one trial from dataset/ORG_dataset (hand skeleton + object) with aitviewer.
Uses the full aitviewer UI (Scene, Playback, etc.).

Replaces the former visualize_collected_data.py + visualize_json_aitviewer.py pair.

Usage: python visualize_collected_data.py [user_id] [object_name] [options]
  e.g. python visualize_collected_data.py s1 bowl
       python visualize_collected_data.py s1 teapot --json-idx 1 --trial 2
"""
import argparse
import json
import sys
from collections import namedtuple
from pathlib import Path

import numpy as np
import torch

from dataset_utils import get_object_rotation_matrix, HAND_SKELETON_LINES

# Anchor on the script, not the cwd, so the tool runs from anywhere.
MODEL_DIR = Path(__file__).resolve().parent
ORG_DATASET = MODEL_DIR.parent / "dataset" / "ORG_dataset"

# aitvconfig.yaml only applies when the cwd happens to be model/, so pin the
# window backend here instead. PyQt6 avoids the PyQt5 resize/_ctx bug on Windows.
DEFAULT_WINDOW_TYPE = "pyqt6"

# The object carries the verdict, so the hand is kept neutral: a coloured hand next to a
# coloured object leaves nothing for the eye to anchor on, and a blue hand beside a blue
# object is worse still. Dark bones, lighter joints, one grey family, no hue of its own.
BONE_COLOR = (0.26, 0.28, 0.32, 1.0)
JOINT_COLOR = (0.52, 0.55, 0.60, 1.0)
JOINT_RADIUS = 0.0065
BONE_RADIUS = 0.0038

# Blue / amber / red rather than the usual green / red, which is the one pairing that
# red-green colour blindness collapses. These three also separate by lightness, so they
# survive being printed in greyscale: amber is light, blue mid, red dark.
#
# The values are pre-divided by roughly 1.5: the scene runs at ambient_strength 2.0, and
# feeding it the colour we actually want back comes out fluorescent.
COMPATIBLE_COLOR = (0.12, 0.29, 0.47, 1.0)           # ir 1, oor 1
ORIENTATION_BLOCKED_COLOR = (0.59, 0.43, 0.10, 1.0)  # ir 0, oor 1
INCOMPATIBLE_COLOR = (0.46, 0.15, 0.12, 1.0)         # ir 0, oor 0
UNSURE_COLOR = (0.41, 0.41, 0.41, 1.0)               # either label is 2

# (2 * n_edges,) index array: hand_pts[:, _BONE_IDX, :] lays the joints out in the
# start/end pair order that Lines(mode="lines") expects.
_BONE_IDX = np.asarray(HAND_SKELETON_LINES).reshape(-1)

# One fixed viewpoint for every trial, so that figures put side by side can be read
# without working out which way each hand is facing first.
#
# The angles are the participant's own. Averaged over 250 trials, the recorded HMD sits
# at azimuth 160 and elevation 22 degrees relative to the wrist (interquartile ranges
# 154-166 and 16-29), with the out-of-reach object at azimuth 3 -- head one side, object
# the other, hand between them. Looking from there at the wrist gives the first-person,
# slightly-downward view, and keeps the object roughly centred as it approaches.
CAMERA_AZIMUTH_DEG = 160.0
CAMERA_ELEVATION_DEG = 22.0
CAMERA_MARGIN = 1.1
CAMERA_ASPECT = 16.0 / 9.0

Trial = namedtuple(
    "Trial",
    "hand obj_rot obj_trans object_name entry oor_frame ir_frame"
    " ir_label oor_label is_target",
)


def verdict(trial):
    """
    How the participant's gesture and this object were judged, as (colour, description).

    Both labels are recorded once for the whole trial, not per frame, but they come from
    two different moments: oorLabel is the spoken judgement made while the object was
    still out of reach, irLabel whether the grasp actually worked once it was in reach.
    The pair (0, 1) is the interesting one -- judged workable, then defeated by the
    object's orientation -- and it is why this is three-way and not a yes/no.
    """
    ir, oor = trial.ir_label, trial.oor_label
    if ir == 2 or oor == 2:
        return UNSURE_COLOR, "not sure"
    if ir == 1 and oor == 1:
        return COMPATIBLE_COLOR, "compatible"
    if oor == 1:
        return ORIENTATION_BLOCKED_COLOR, "judged compatible, but not in this orientation"
    return INCOMPATIBLE_COLOR, "not compatible"


def _first_true(mask):
    """Index of the first True in a per-frame boolean mask, or None if it has none."""
    idx = np.flatnonzero(np.asarray(mask, dtype=bool))
    return int(idx[0]) if len(idx) else None

R_UNITY2PYTHON = torch.tensor([[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
_T = torch.eye(4)
_T[1:, 1:] = -R_UNITY2PYTHON
T_QUAT_UNITY2PYTHON = _T


def load_object_sources():
    """
    Return the object lookup tables, without pulling in BPS.

    dataset_utils._get_rigid() builds a bps_torch alongside ObjectDataset, which drags
    in pytorch3d and is not needed for visualization, so we set up the pieces we use.

    The study mixed objects from two sources: obj.npz covers 25 of the 30 objects and
    obj_hog.npz the remaining 5 (crackerbox, plate, smartphone, pottedmeatcan, disklid).
    Both are needed; neither alone covers the dataset.
    """
    from app.obj_dataset import ObjectDataset

    primary = ObjectDataset().ds
    hog_path = MODEL_DIR / "files" / "obj_hog.npz"
    fallback = np.load(hog_path, allow_pickle=True)["ds"].item() if hog_path.exists() else {}
    return primary, fallback


def get_object_entry(sources, object_name):
    """Look the object up in obj.npz first, then obj_hog.npz."""
    for src in sources:
        if object_name in src:
            return src[object_name]
    known = sorted({k for src in sources for k in src if k != "bps_basis"})
    raise KeyError(
        f"Object '{object_name}' is in neither files/obj.npz nor files/obj_hog.npz.\n"
        f"Known objects: {', '.join(known)}"
    )


def find_all_trials_path(user_id, object_name, json_idx=0):
    """Return the json_idx-th all_trials.json for a user/object, or exit with a hint."""
    obj_dir = ORG_DATASET / user_id / object_name
    if not obj_dir.exists():
        user_dir = ORG_DATASET / user_id
        if not user_dir.exists():
            users = sorted(p.name for p in ORG_DATASET.glob("*") if p.is_dir())
            sys.exit(f"No user '{user_id}' under {ORG_DATASET}\nAvailable users: {', '.join(users)}")
        objects = sorted(p.name for p in user_dir.glob("*") if p.is_dir())
        sys.exit(f"No object '{object_name}' for user '{user_id}'\nAvailable: {', '.join(objects)}")

    json_files = sorted(obj_dir.glob("**/all_trials.json"))
    if not json_files:
        sys.exit(f"No all_trials.json under {obj_dir}")
    if json_idx >= len(json_files):
        sys.exit(f"--json-idx {json_idx} is out of range: {obj_dir} has {len(json_files)} recording(s)")
    return json_files[json_idx]


def load_trial(json_path, trial_idx, sources):
    """
    Load one trial and return the per-frame arrays plus the two phase frames.

    This is the batched form of dataset_utils.load_trial_sequence, which we cannot call
    directly because it initializes BPS (see load_object_sources). It returns the object
    rotations rather than a rotated point cloud, since we render the object as a mesh.

    A trial is recorded as one continuous take spanning both phases of Figure 3: the
    participant first grasps at the object while it is out of reach (isLabeledFrame),
    then the object is moved within reach and the posture is refined (isInReachFrame).
    """
    with open(json_path, "r") as f:
        trials = json.load(f)
    if trial_idx >= len(trials):
        sys.exit(f"--trial {trial_idx} is out of range: {json_path.name} has {len(trials)} trial(s)")

    trial = trials[trial_idx]
    object_name = trial["objectName"]
    obj_pos_world = torch.Tensor(trial["objectPoseWorld"]["position"])
    obj_rot_world = torch.Tensor(trial["objectPoseWorld"]["rotation"])
    joint_pos_world = torch.Tensor(trial["gestures"]["jointsPositionWorld"])

    # Hand joints relative to the wrist, with the wrist itself prepended as the root.
    root = joint_pos_world[:, 0:1]
    leaf = torch.einsum("ij,tnj->tni", R_UNITY2PYTHON, joint_pos_world[:, 1:] - root)
    hand_pts = torch.cat([torch.zeros(leaf.shape[0], 1, 3), leaf], dim=1)

    obj_rot = get_object_rotation_matrix(obj_rot_world, T_QUAT_UNITY2PYTHON)
    obj_trans = torch.einsum("ij,tj->ti", R_UNITY2PYTHON, obj_pos_world - root.squeeze(1))

    return Trial(
        hand=hand_pts.numpy(),
        obj_rot=obj_rot.numpy(),
        obj_trans=obj_trans.numpy(),
        object_name=object_name,
        entry=get_object_entry(sources, object_name),  # fail early, before the viewer opens
        oor_frame=_first_true(trial["isLabeledFrame"]),
        ir_frame=_first_true(trial["isInReachFrame"]),
        ir_label=trial["irLabel"],
        oor_label=trial["oorLabel"],
        is_target=object_name == trial["targetObjectName"],
    )


def build_renderables(trial):
    """
    Build the aitviewer nodes for one trial: hand joints, hand bones, object mesh.

    Local rather than reused from aitviewer_utils.build_hand_object_renderables, which
    draws the object as a point cloud and hard-codes its own colours.
    """
    from aitviewer.renderables.lines import Lines
    from aitviewer.renderables.meshes import Meshes
    from aitviewer.renderables.spheres import Spheres

    hand_pts = trial.hand
    joints = Spheres(hand_pts, radius=JOINT_RADIUS, color=JOINT_COLOR, name="Hand joints")
    bones = Lines(hand_pts[:, _BONE_IDX, :], mode="lines", r_base=BONE_RADIUS,
                  color=BONE_COLOR, name="Hand bones")

    # Static vertices plus a per-frame 4x4, rather than a full (T, V, 3) vertex sequence:
    # 0.3 MB instead of ~170 MB for a 559-frame trial. aitviewer transposes the matrices
    # itself before upload, so these are plain row-major [[R, t], [0, 1]].
    transforms = object_transforms(trial)
    color, _ = verdict(trial)
    obj = Meshes(
        np.asarray(trial.entry["verts"], dtype=np.float32),
        np.asarray(trial.entry["faces"]).astype(np.int32),
        instance_transforms=transforms[:, np.newaxis],
        color=color,
        name=trial.object_name,
    )
    return joints, bones, obj


def object_transforms(trial):
    """Per-frame object placement as (T, 4, 4) matrices."""
    transforms = np.tile(np.eye(4, dtype=np.float32), (len(trial.obj_trans), 1, 1))
    transforms[:, :3, :3] = trial.obj_rot
    transforms[:, :3, 3] = trial.obj_trans
    return transforms


def camera_direction(azimuth_deg, elevation_deg):
    """Unit vector from the wrist towards where the camera sits."""
    az, el = np.radians(azimuth_deg), np.radians(elevation_deg)
    return np.array([np.sin(az) * np.cos(el), np.sin(el), np.cos(az) * np.cos(el)])


def sequence_points(trial):
    """
    Every point the camera has to hold, over the whole trial.

    The object contributes the eight corners of its local bounding box, transformed per
    frame. An affine transform maps the box to a parallelepiped with those corners, and
    the mesh stays inside it, so this bounds the object exactly without touching all
    50k vertices on all several hundred frames.
    """
    verts = np.asarray(trial.entry["verts"], dtype=np.float32)
    lo, hi = verts.min(axis=0), verts.max(axis=0)
    corners = np.array(np.meshgrid(*zip(lo, hi))).reshape(3, -1).T  # (8, 3)
    obj = np.einsum("tij,cj->tci", trial.obj_rot, corners) + trial.obj_trans[:, None, :]
    return np.vstack([trial.hand.reshape(-1, 3), obj.reshape(-1, 3)])


def frame_camera(camera, trial, azimuth_deg, elevation_deg, aspect=CAMERA_ASPECT):
    """
    Place the fixed camera so the whole trial stays in shot, including the frame where
    the object is furthest away.

    The camera looks at the wrist, which is the origin in every trial, so the hand lands
    in the same place on screen no matter which trial is loaded. Distance is solved
    against the view frustum rather than a bounding sphere: a first-person camera looks
    almost straight down the line the object travels, so the far object sits near the
    centre of the image and costs far less room than its 1.6 m would suggest.
    """
    direction = camera_direction(azimuth_deg, elevation_deg)
    up = np.array([0.0, 1.0, 0.0])
    right = np.cross(up, direction)
    right /= np.linalg.norm(right)
    screen_up = np.cross(direction, right)

    tan_v = np.tan(np.radians(camera.fov) / 2.0)
    tan_h = tan_v * aspect

    # For a point q (relative to the target) the camera must sit at least
    # q.direction + |q.screen_axis| / tan(half fov) away for q to fall inside the frustum.
    q = sequence_points(trial)
    along = q @ direction
    distance = max(
        float(np.max(along + np.abs(q @ screen_up) / tan_v)),
        float(np.max(along + np.abs(q @ right) / tan_h)),
    ) * CAMERA_MARGIN

    camera.target = np.zeros(3)
    camera.position = direction * distance


def describe(trial, json_path, trial_idx):
    """Print where the two phases of Figure 3 sit on the timeline, so they can be found."""
    n = len(trial.hand)
    role = "target object" if trial.is_target else "replacement object"
    _, judgement = verdict(trial)
    print(f"{json_path.relative_to(ORG_DATASET)}  trial {trial_idx}  "
          f"object '{trial.object_name}'  {n} frames")
    print(f"  {role:<34} ir={trial.ir_label} oor={trial.oor_label}   {judgement}")

    def phase(label, frame):
        if frame is None:
            return f"  {label:<34} not in this trial"
        distance = np.linalg.norm(trial.obj_trans[frame])
        return f"  {label:<34} frame {frame:>4}/{n - 1}   object {distance:.2f} m from wrist"

    print(phase("1. grasp with object out of reach", trial.oor_frame))
    print(phase("2. posture refined within reach", trial.ir_frame))


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("user_id", nargs="?", default="s1", help="e.g. s1 (default: s1)")
    p.add_argument("object_name", nargs="?", default="bowl", help="e.g. bowl (default: bowl)")
    p.add_argument("--json-idx", type=int, default=0,
                   help="which recording session for this user/object (default: 0)")
    p.add_argument("--trial", type=int, default=0,
                   help="which trial inside that all_trials.json (default: 0)")
    p.add_argument("--camera", type=azimuth_elevation, metavar="AZ,EL",
                   default=(CAMERA_AZIMUTH_DEG, CAMERA_ELEVATION_DEG),
                   help="override the viewpoint, in degrees "
                        f"(default: {CAMERA_AZIMUTH_DEG:g},{CAMERA_ELEVATION_DEG:g})")
    p.add_argument("--window-type", default=DEFAULT_WINDOW_TYPE,
                   help=f"aitviewer window backend (default: {DEFAULT_WINDOW_TYPE})")
    return p.parse_args()


def azimuth_elevation(text):
    """Parse an --camera "azimuth,elevation" pair, in degrees."""
    try:
        azimuth, elevation = (float(part) for part in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected two numbers like '160,22', got {text!r}")
    if not -90.0 < elevation < 90.0:
        raise argparse.ArgumentTypeError(f"elevation must be between -90 and 90, got {elevation:g}")
    return azimuth, elevation


def main():
    args = parse_args()

    json_path = find_all_trials_path(args.user_id, args.object_name, args.json_idx)
    sources = load_object_sources()
    trial = load_trial(json_path, args.trial, sources)
    describe(trial, json_path, args.trial)

    joints, bones, obj = build_renderables(trial)

    from aitviewer.viewer import Viewer

    Viewer.window_type = args.window_type
    v = Viewer(title=f"ORG_dataset: {args.user_id}/{args.object_name} trial {args.trial}")
    v.run_animations = True
    # Viewer._init_scene() re-aims the camera and re-seats the floor on startup, which
    # would undo both of the decisions below.
    v.auto_set_camera_target = False
    v.auto_set_floor = False
    v.scene.add(joints, bones, obj)
    frame_camera(v.scene.camera, trial, *args.camera,
                 aspect=v.window_size[0] / v.window_size[1])
    # Everything is wrist-relative, so the origin gizmo just sits inside the hand.
    v.scene.origin.enabled = False
    # The floor tracks the lowest point of the *current* frame, so it jumps when the
    # object moves into reach and ends up slicing through the hand. Drop it entirely.
    v.scene.floor.enabled = False
    # Viewer does not implement on_render; use its render() as the window callback
    v.wnd.render_func = v.render
    v.run()


if __name__ == "__main__":
    main()
