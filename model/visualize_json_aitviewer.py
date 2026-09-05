#!/usr/bin/env python3
"""
Visualize hand-object interaction sequence from one all_trials.json with aitviewer.
Usage: python visualize_json_aitviewer.py <user_id> <object_name> [json_idx] [trial_idx]
  e.g. python visualize_json_aitviewer.py s1 teapot 0 0
  json_idx: which all_trials.json (0,1,2 under ../dataset/collected_data/{user_id}/{object_name}/)
  trial_idx: which trial in that json (default 0)
"""
# Prefer GLFW to avoid PyQt5 resize/_ctx bug on Windows
import os
os.environ.setdefault("MODERNGL_WINDOW", "glfw")

from pathlib import Path
import sys
import numpy as np

from dataset_utils import load_trial_sequence
from aitviewer_utils import build_hand_object_renderables
from aitviewer.viewer import Viewer

COLLECTED_ROOT = Path("../dataset/collected_data")


def find_all_trials_path(user_id, object_name, json_idx=0):
    obj_dir = COLLECTED_ROOT / user_id / object_name
    if not obj_dir.exists():
        return None
    json_files = sorted(obj_dir.glob("**/all_trials.json"))
    if json_idx >= len(json_files):
        return None
    return json_files[json_idx]


def main():
    if len(sys.argv) < 3:
        print("Usage: python visualize_json_aitviewer.py <user_id> <object_name> [json_idx=0] [trial_idx=0]")
        sys.exit(1)
    user_id = sys.argv[1]
    object_name = sys.argv[2]
    json_idx = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    trial_idx = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    json_path = find_all_trials_path(user_id, object_name, json_idx)
    if not json_path or not json_path.exists():
        print(f"Not found: {COLLECTED_ROOT}/{user_id}/{object_name}/ ... all_trials.json (json_idx={json_idx})")
        sys.exit(1)
    hand_T, obj_pcl_T, obj_trans_T, _ = load_trial_sequence(json_path, trial_index=trial_idx)
    s, l, p = build_hand_object_renderables(hand_T, obj_pcl_T, obj_trans_T, is_sequence=True)
    v = Viewer()
    v.run_animations = True
    v.scene.add(s, l, p)
    v.scene.camera.position = np.array([0.2, 0.2, 0.6])
    v.wnd.render_func = v.render
    v.run()


if __name__ == "__main__":
    main()
