#!/usr/bin/env python3
"""
Visualize one NPZ (skeleton hand + object point cloud) with aitviewer.
Usage: python visualize_npz_aitviewer.py [path_to.npz]
  Default: first features_ir_*_oor_*_*.npz under ../dataset/preprocessed_dataset/
"""
from pathlib import Path
import sys
import numpy as np

from dataset_utils import load_npz_sample
from aitviewer_utils import build_hand_object_renderables
from aitviewer.viewer import Viewer


def find_default_npz():
    base = Path("../dataset/preprocessed_dataset")
    if not base.exists():
        return None
    for p in sorted(base.rglob("features_ir_*_oor_*_*.npz")):
        return p
    return None


def main():
    if len(sys.argv) >= 2:
        npz_path = Path(sys.argv[1])
    else:
        npz_path = find_default_npz()
    if not npz_path or not npz_path.exists():
        print("No NPZ path given or found. Usage: python visualize_npz_aitviewer.py [path_to.npz]")
        sys.exit(1)
    hand_pts, obj_pcl, obj_trans = load_npz_sample(npz_path)
    obj_trans = obj_trans.reshape(3)
    s, l, p = build_hand_object_renderables(hand_pts, obj_pcl, obj_trans, is_sequence=False)
    v = Viewer()
    v.scene.add(s, l, p)
    v.scene.camera.position = np.array([0.15, 0.15, 0.5])
    v.wnd.render_func = v.render
    v.run()


if __name__ == "__main__":
    main()
