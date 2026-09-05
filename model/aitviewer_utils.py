"""
Build aitviewer renderables for hand skeleton + object (single frame or sequence).
Used by visualize_npz_aitviewer.py and visualize_json_aitviewer.py.
"""
import numpy as np
from dataset_utils import HAND_SKELETON_LINES


def _skeleton_line_strip(hand_pts):
    """hand_pts (21, 3) -> line_strip (2*num_edges, 3) for Lines(mode='lines')."""
    strip = []
    for i, j in HAND_SKELETON_LINES:
        strip.append(hand_pts[i])
        strip.append(hand_pts[j])
    return np.array(strip, dtype=np.float32)


def build_hand_object_renderables(hand_pts, obj_pcl, obj_trans, is_sequence=False):
    """
    hand_pts: (21, 3) or (T, 21, 3)
    obj_pcl: (1024, 3) or (T, 1024, 3)
    obj_trans: (3,) or (T, 3)
    Returns (hand_spheres, hand_lines, obj_pc) for aitviewer.
    """
    from aitviewer.renderables.spheres import Spheres
    from aitviewer.renderables.lines import Lines
    from aitviewer.renderables.point_clouds import PointClouds

    hand_pts = np.asarray(hand_pts, dtype=np.float32)
    obj_pcl = np.asarray(obj_pcl, dtype=np.float32)
    obj_trans = np.asarray(obj_trans, dtype=np.float32)
    if obj_trans.ndim == 1:
        obj_trans = obj_trans.reshape(1, 3)
    if hand_pts.ndim == 2:
        hand_pts = hand_pts[np.newaxis]
    if obj_pcl.ndim == 2:
        obj_pcl = obj_pcl[np.newaxis]
    T = hand_pts.shape[0]
    if obj_trans.shape[0] == 1 and T > 1:
        obj_trans = np.broadcast_to(obj_trans, (T, 3))

    obj_world = obj_pcl + obj_trans[:, np.newaxis, :]

    hand_spheres = Spheres(hand_pts, radius=0.006, color=(0.2, 0.5, 0.9, 1.0))
    line_strips = np.array([_skeleton_line_strip(hand_pts[t]) for t in range(T)], dtype=np.float32)
    hand_lines = Lines(line_strips.reshape(T, -1, 3), mode="lines", color=(0.3, 0.3, 0.3, 1.0))
    obj_pc = PointClouds(points=obj_world, color=(0.9, 0.3, 0.2, 0.8))
    return hand_spheres, hand_lines, obj_pc
