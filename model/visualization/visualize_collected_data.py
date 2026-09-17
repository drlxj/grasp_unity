#!/usr/bin/env python3
"""
Visualize one trial from dataset/ORG_dataset (hand skeleton + object) with aitviewer.
Uses the full aitviewer UI (Scene, Playback, etc.).

Usage: python visualize_collected_data.py [user_id] [object_name] [options]
  e.g. python visualize_collected_data.py s1 bowl
       python visualize_collected_data.py s1 teapot --json-idx 1 --trial 2
"""
import argparse
import sys
from pathlib import Path

import numpy as np

# dataset_utils, aitviewer_utils and app/ live in model/, one level up. Anchored on this
# file rather than the working directory, so the script runs from anywhere.
MODEL_DIR = Path(__file__).resolve().parents[1]
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

from aitviewer_utils import (build_trial_renderables, cast_shadow_from_camera_side,
                             connect_window_events, frame_camera, place_floor)
from dataset_utils import load_object_sources, load_trial

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
# Share of the half-frame the trial may occupy, measured on screen, so that the distant
# out-of-reach object does not end up glued to the frame edge.
CAMERA_SAFE_AREA = 0.92

# A fixed ground plane for depth, placed once per trial this far below the lowest point
# the trial ever reaches, so nothing passes through it. It is kept close on purpose: the
# first-person camera looks down at 22 degrees and sees nothing steeper than 44.5, so
# with the floor 70 cm down the patch under the object is out of shot and its shadow
# cannot land near it. At 15 cm the shadow sits right under the object.
FLOOR_DROP = 0.15

# The shadow comes from the light on the camera's side, raised to this elevation. Left at
# its default 34 degrees -- close to the camera's own 22 -- the shadow falls straight
# behind the object and is hidden by it.
KEY_LIGHT_ELEVATION_DEG = 60.0


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


def build_renderables(trial):
    """The hand and object nodes for one trial, in this viewer's palette."""
    color, _ = verdict(trial)
    return build_trial_renderables(
        trial, object_color=color, joint_color=JOINT_COLOR, bone_color=BONE_COLOR,
        joint_radius=JOINT_RADIUS, bone_radius=BONE_RADIUS,
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
    p.add_argument("--no-gui", action="store_true",
                   help="start with aitviewer's panels hidden (press Esc to bring them back)")
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
    try:
        trial = load_trial(json_path, args.trial, sources)
    except (IndexError, KeyError) as e:
        sys.exit(e.args[0])
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
                 aspect=v.window_size[0] / v.window_size[1], safe_area=CAMERA_SAFE_AREA)
    # Everything is wrist-relative, so the origin gizmo just sits inside the hand.
    v.scene.origin.enabled = False
    place_floor(v.scene, trial, drop=FLOOR_DROP)
    cast_shadow_from_camera_side(v.scene, args.camera[0], elevation_deg=KEY_LIGHT_ELEVATION_DEG)
    connect_window_events(v)
    v.render_gui = not args.no_gui
    v.run()


if __name__ == "__main__":
    main()
