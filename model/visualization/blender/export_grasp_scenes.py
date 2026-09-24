#!/usr/bin/env python3
"""
The grasp stages' scenes, written out for Blender as plain arrays its own Python can read.

Two sets of cells, one column per object and one grasp per cell:

  showcase   the grasp figure: render_showcase_rows.row_grasps' eight objects, one per
             cluster of the paper, and down each column its five distinct grasps
  all        the whole dataset: all 30 objects, grouped by the paper's eight clusters,
             and down each column every participant's in-reach grasp of it at every
             orientation (19 x 3), ordered so that similar grasps sit together

Blender cannot import torch or aitviewer, so the choosing happens here, in the grasping
environment, and render_grasps.py only lays out and draws what it is given. Every cell
is already in its object's own frame (in_object_frame), the object centred on the
origin in its default orientation, so placing a cell on the stage is a translation.
Everything stays in the dataset's frame (y up, metres); the one change of axes to
Blender's z-up lives in render_grasps.py.

Writes <out>/scene.json (the columns, their cells and each cell's provenance) and
<out>/<object>.npz (each object's mesh, once).

Usage (grasping env):
  python export_grasp_scenes.py --set showcase
  python export_grasp_scenes.py --set all
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
VIS_DIR = HERE.parent
if str(VIS_DIR) not in sys.path:
    sys.path.insert(0, str(VIS_DIR))

import render_showcase_rows as rows  # also puts model/ on sys.path

import dataset_utils
import visualize_collected_data as viz

OUT_ROOT = rows.DEFAULT_OUT / "blender"

# The paper's eight clusters of the 30 objects (Silhouette method on the similarity
# matrix), in the paper's order. The paper's list leaves out the cup; its text groups
# the cup with the mug, wineglass and water bottle, so it goes in cluster 2 here.
CLUSTERS = (
    ("bowl", "spherelarge"),
    ("alarmclock", "crackerbox", "apple", "cup", "mug", "waterbottle", "wineglass"),
    ("eyeglasses", "scissors", "watch"),
    ("camera", "pottedmeatcan"),
    ("headphones", "teapot"),
    ("banana", "binoculars", "flashlight", "spheresmall", "stapler", "toothpaste"),
    ("fryingpan", "hammer", "knife"),
    ("disklid", "gamecontroller", "mouse", "plate", "smartphone"),
)


def cell(grasp, still, **extra):
    return dict(subject=grasp["subject"],
                rel_path=Path(grasp["path"]).relative_to(rows.ORG_DATASET).as_posix(),
                hand=still.hand[0].round(6).tolist(),
                obj_rot=still.obj_rot[0].round(6).tolist(),
                obj_trans=still.obj_trans[0].round(6).tolist(), **extra)


def save_mesh(out_dir, object_name, entry):
    np.savez_compressed(out_dir / f"{object_name}.npz", verts=np.asarray(entry["verts"], dtype=np.float32),
                        faces=np.asarray(entry["faces"], dtype=np.int32))


def showcase_columns(out_dir, sources):
    """The grasp figure's columns: five distinct grasps of each cluster's representative."""
    columns = []
    for cluster, object_name in enumerate(rows.GRASP_OBJECTS, start=1):
        grasps = [g for g in rows.object_grasps(object_name, sources) if rows.in_contact(g["still"])]
        chosen = rows.distinct_grasps(grasps, rows.GRASP_ROWS, symmetric=object_name in rows.SYMMETRIC_OBJECTS)
        save_mesh(out_dir, object_name, chosen[0][0]["trial"].entry)
        columns.append(dict(object=object_name, cluster=cluster,
                            cells=[cell(g, g["still"], share=round(share, 3)) for g, share in chosen]))
        print(f"  {object_name:<15} {len(grasps)} grasps in contact; rows cover "
              + ", ".join(f"{share:.0%}" for _, share in chosen))
    return columns


def similarity_order(postures):
    """
    The order that puts similar grasps next to each other, for (n, 21, 3) postures.

    Grasps are compared as the paper compares them: the hand's joints relative to the
    wrist, and between two grasps the mean over joints of the Euclidean distance between
    matching joints. Average-linkage clustering of that distance matrix, with its leaves
    put in the order that keeps neighbours closest (optimal leaf ordering), gives the
    order. The wrist is the origin of every posture, so it adds nothing to any distance
    and is left out of the mean; leaving it in would scale every distance alike.
    """
    from scipy.cluster.hierarchy import leaves_list, linkage, optimal_leaf_ordering
    from scipy.spatial.distance import squareform

    X = np.asarray(postures)[:, 1:]
    D = squareform(np.linalg.norm(X[:, None] - X[None], axis=-1).mean(axis=-1), checks=False)
    return leaves_list(optimal_leaf_ordering(linkage(D, method="average"), D))


def all_columns(out_dir, sources):
    """Every object's every in-reach target grasp, similar grasps together."""
    columns = []
    for cluster, members in enumerate(CLUSTERS, start=1):
        for object_name in members:
            grasps = rows.object_grasps(object_name, sources)
            postures = [g["trial"].hand[g["trial"].ir_frame] for g in grasps]
            order = similarity_order(postures)
            save_mesh(out_dir, object_name, grasps[0]["trial"].entry)
            touching = [rows.in_contact(g["still"]) for g in grasps]
            columns.append(dict(object=object_name, cluster=cluster,
                                cells=[cell(grasps[i], grasps[i]["still"], in_contact=bool(touching[i]))
                                       for i in order]))
            print(f"  cluster {cluster}  {object_name:<15} {len(grasps)} grasps "
                  f"({len(grasps) - sum(touching)} not within {rows.CONTACT_CM:g} cm of the object)", flush=True)
    return columns


def export(out_dir, which, sources):
    out_dir.mkdir(parents=True, exist_ok=True)
    columns = (showcase_columns if which == "showcase" else all_columns)(out_dir, sources)
    for column in columns:
        for r, c in enumerate(column["cells"], start=1):
            c["row"] = r
    scene = dict(camera=dict(azimuth=rows.GRASP_CAMERA[0], elevation=rows.GRASP_CAMERA[1]),
                 joint_radius=viz.JOINT_RADIUS, bone_radius=viz.BONE_RADIUS,
                 skeleton=dataset_utils.HAND_SKELETON_LINES, columns=columns)
    with open(out_dir / "scene.json", "w", encoding="utf-8") as f:
        json.dump(scene, f)
    print(f"wrote {sum(len(c['cells']) for c in columns)} cells in {len(columns)} columns to {out_dir}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--set", choices=("showcase", "all"), default="showcase")
    p.add_argument("--out-dir", type=Path, help="default: <outputs>/blender/scenes_<set>")
    args = p.parse_args()
    export(args.out_dir or OUT_ROOT / f"scenes_{args.set}", args.set, dataset_utils.load_object_sources())


if __name__ == "__main__":
    main()
