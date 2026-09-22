#!/usr/bin/env python3
"""
Per-joint distance between the out-of-reach and the in-reach posture of every trial
that has both, as a CSV.

Each trial is one continuous take in which the participant first grasps at the object
while it is out of reach (the isLabeledFrame keyframe), then refines the same posture
once it is moved within reach (the isInReachFrame keyframe). Same person, same object,
same orientation, seconds apart -- so the difference between the two keyframes is how
far an out-of-reach grasp sits from the contact grasp it stands in for.

Both postures are taken relative to the wrist by translation only, as load_trial and the
model's rel2wrist inputs do, so a change in how the wrist is turned counts towards the
offset. Measured in the wrist's own frame instead, the offsets shrink to roughly a third:
much of the gap is the whole hand turning, not the fingers changing shape.

Only trials that reached the in-reach phase have both keyframes: every target trial
(trial 0), plus the replacements the participant accepted out of reach.

Usage: python compute_pose_offsets.py [--out outputs/org_dataset/pose_offsets.csv]
"""
import argparse
import csv
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

# This file lives in model/visualization/; outputs stay in model/outputs/.
MODEL_DIR = Path(__file__).resolve().parents[1]
ORG_DATASET = MODEL_DIR.parent / "dataset" / "ORG_dataset"
DEFAULT_OUT = MODEL_DIR / "outputs" / "org_dataset" / "pose_offsets.csv"

# The 20 non-wrist joints in the dataset's order (dataset_utils.HAND_SKELETON_LINES):
# four per finger, base to tip, so <finger>4 is the fingertip.
JOINTS = [f"{finger}{k}" for finger in ("thumb", "index", "middle", "ring", "pinky")
          for k in range(1, 5)]
FINGERTIPS = [JOINTS.index(f"{finger}4") for finger in ("thumb", "index", "middle", "ring", "pinky")]
FIELDS = ["subject", "obj_dir", "session_ts", "trial_index", "object_name",
          "oor_frame", "ir_frame", "mean_cm", "extension_cm", *JOINTS, "rel_path"]


def _first_true(mask):
    idx = np.flatnonzero(np.asarray(mask, dtype=bool))
    return int(idx[0]) if len(idx) else None


def offsets_in_file(path):
    """One row per trial in this file that has both keyframes; distances in cm."""
    with open(path, "r") as f:
        trials = json.load(f)
    rel = os.path.relpath(path, ORG_DATASET).replace(os.sep, "/")
    subject, obj_dir, session_ts = rel.split("/")[:3]

    rows = []
    for trial in trials:
        oor, ir = _first_true(trial["isLabeledFrame"]), _first_true(trial["isInReachFrame"])
        if oor is None or ir is None:
            continue
        joints = np.asarray(trial["gestures"]["jointsPositionWorld"])
        posture_oor = joints[oor, 1:] - joints[oor, 0]
        posture_ir = joints[ir, 1:] - joints[ir, 0]
        cm = np.linalg.norm(posture_oor - posture_ir, axis=1) * 100
        # How much further the fingertips reach from the wrist out of reach than in reach:
        # positive when the out-of-reach hand is the more extended one.
        reach = [np.linalg.norm(p[FINGERTIPS], axis=1).mean() for p in (posture_oor, posture_ir)]
        rows.append(dict(
            subject=subject, obj_dir=obj_dir, session_ts=session_ts,
            trial_index=trial["trialIndex"], object_name=trial["objectName"],
            oor_frame=oor, ir_frame=ir, mean_cm=round(float(cm.mean()), 3),
            extension_cm=round(float(reach[0] - reach[1]) * 100, 3),
            **{name: round(float(v), 3) for name, v in zip(JOINTS, cm)},
            rel_path=rel,
        ))
    return rows


def summarize(rows):
    """Print the numbers the project page quotes, target trials only."""
    target = np.array([[r[j] for j in JOINTS] for r in rows if r["trial_index"] == 0])
    extension = np.array([r["extension_cm"] for r in rows if r["trial_index"] == 0])
    per_joint = target.mean(axis=0)
    q1, med, q3 = np.percentile(target.mean(axis=1), [25, 50, 75])
    print(f"target trials: {len(target)}")
    print(f"  per-trial mean offset  median {med:.2f} cm (IQR {q1:.2f}-{q3:.2f})")
    print(f"  per-joint mean offset  {per_joint.min():.2f}-{per_joint.max():.2f} cm, "
          f"largest at {JOINTS[int(per_joint.argmax())]}")
    print(f"  fingertips             {per_joint[FINGERTIPS].mean():.2f} cm on average")
    print(f"  more extended out of reach in {np.mean(extension > 0):.1%} of trials, "
          f"by {np.median(extension):+.2f} cm at the median")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT,
                   help=f"CSV to write (default: {DEFAULT_OUT.relative_to(MODEL_DIR)})")
    p.add_argument("--workers", type=int, default=8, help="parallel readers (default: 8)")
    return p.parse_args()


def main():
    args = parse_args()
    files = sorted(ORG_DATASET.glob("*/*/*/all_trials.json"))
    if not files:
        sys.exit(f"No */*/*/all_trials.json under {ORG_DATASET}")
    print(f"reading {len(files)} session files under {ORG_DATASET}")

    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(offsets_in_file, files, chunksize=4):
            rows.extend(result)
    summarize(rows)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} trials to {args.out}")


if __name__ == "__main__":
    main()
