#!/usr/bin/env python3
"""
Visualize collected_data (hand + object from all_trials.json) with aitviewer.
Uses the full aitviewer UI (Scene, Playback, etc.).
Usage: python visualize_collected_data.py [user_id] [object_name] [trial_idx]
  e.g. python visualize_collected_data.py s1 bowl 0
"""
from pathlib import Path
import sys
import numpy as np

from dataset_utils import load_trial_sequence
from aitviewer_utils import build_hand_object_renderables
from aitviewer.viewer import Viewer

COLLECTED_ROOT = Path("../dataset/collected_data")


def find_first_all_trials(user_id, object_name):
    obj_dir = COLLECTED_ROOT / user_id / object_name
    if not obj_dir.exists():
        return None
    json_files = sorted(obj_dir.glob("**/all_trials.json"))
    return json_files[0] if json_files else None


def main():
    user_id = sys.argv[1] if len(sys.argv) > 1 else "s1"
    object_name = sys.argv[2] if len(sys.argv) > 2 else "bowl"
    trial_idx = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    json_path = find_first_all_trials(user_id, object_name)
    if not json_path or not json_path.exists():
        print(f"Not found: {COLLECTED_ROOT}/{user_id}/{object_name}/ ... all_trials.json")
        sys.exit(1)

    hand_T, obj_pcl_T, obj_trans_T, _ = load_trial_sequence(json_path, trial_index=trial_idx)
    hand_spheres, hand_lines, obj_pc = build_hand_object_renderables(
        hand_T, obj_pcl_T, obj_trans_T, is_sequence=True
    )

    v = Viewer(title=f"Collected: {user_id}/{object_name} trial {trial_idx}")
    v.run_animations = True
    v.scene.add(hand_spheres, hand_lines, obj_pc)
    v.scene.camera.position = np.array([0.2, 0.2, 0.6])
    # Viewer does not implement on_render; use its render() as the window callback
    v.wnd.render_func = v.render
    v.run()


if __name__ == "__main__":
    main()
