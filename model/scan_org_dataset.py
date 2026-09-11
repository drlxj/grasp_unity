#!/usr/bin/env python3
"""
Build the trial-level index of dataset/ORG_dataset as a CSV.

The dataset is ~8 GB of JSON, and every overview figure needs only the seven scalars
at the head of each trial plus two frame counts. Parsing all 1710 files with json.load
takes minutes and several GB of RAM; the fields we want sit in a fixed order in the
compact JSON, so a regex over the raw bytes gets the same numbers in seconds.

The output is checked against a full json.load of a random sample -- see --verify.

Usage: python scan_org_dataset.py [--out outputs/org_dataset/trials.csv] [--verify 6]
"""
import argparse
import csv
import os
import random
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
ORG_DATASET = MODEL_DIR.parent / "dataset" / "ORG_dataset"
DEFAULT_OUT = MODEL_DIR / "outputs" / "org_dataset" / "trials.csv"

# The seven scalars are written in this order by DataLogger.cs and precede the big
# per-frame arrays, so one pass over the bytes finds every trial header in the file.
HEADER = re.compile(
    rb'"userId":"([^"]*)",'
    rb'"sessionId":"([^"]*)",'
    rb'"targetObjectName":"([^"]*)",'
    rb'"objectName":"([^"]*)",'
    rb'"trialIndex":(-?\d+),'
    rb'"oorLabel":(-?\d+),'
    rb'"irLabel":(-?\d+)'
)
# Boolean arrays, so the contents can never contain a closing bracket.
LABELED_FRAMES = re.compile(rb'"isLabeledFrame":\[([^\]]*)\]')
IN_REACH_FRAMES = re.compile(rb'"isInReachFrame":\[([^\]]*)\]')

FIELDS = [
    "subject", "obj_dir", "session_ts", "user_id", "session_id",
    "target_object", "object_name", "trial_index", "oor_label", "ir_label",
    "n_frames", "n_labeled", "n_in_reach", "file_mb", "rel_path",
]


def _bool_array_stats(segment):
    """(length, number of true) for the body of a JSON array of booleans."""
    if not segment:
        return 0, 0
    return segment.count(b",") + 1, segment.count(b"true")


def scan_file(path):
    """Every trial in one all_trials.json, as a list of dicts keyed by FIELDS."""
    raw = Path(path).read_bytes()
    headers = HEADER.findall(raw)
    labeled = LABELED_FRAMES.findall(raw)
    in_reach = IN_REACH_FRAMES.findall(raw)
    rel = os.path.relpath(path, ORG_DATASET).replace(os.sep, "/")
    subject, obj_dir, session_ts = rel.split("/")[:3]

    rows = []
    for i, head in enumerate(headers):
        n_frames, n_labeled = _bool_array_stats(labeled[i] if i < len(labeled) else b"")
        _, n_in_reach = _bool_array_stats(in_reach[i] if i < len(in_reach) else b"")
        rows.append(dict(
            subject=subject, obj_dir=obj_dir, session_ts=session_ts,
            user_id=head[0].decode(), session_id=head[1].decode(),
            target_object=head[2].decode(), object_name=head[3].decode(),
            trial_index=int(head[4]), oor_label=int(head[5]), ir_label=int(head[6]),
            n_frames=n_frames, n_labeled=n_labeled, n_in_reach=n_in_reach,
            file_mb=round(len(raw) / 1e6, 2), rel_path=rel,
        ))
    return rows


def verify(rows, n_files, seed=0):
    """
    Re-read a random sample of files with json.load and compare every scanned field.

    The regex trusts a field order it does not enforce, so this is what makes the fast
    path safe to rely on: if the logger ever writes the scalars in another order, the
    header simply stops matching and this reports the missing trials.
    """
    import json

    by_file = {}
    for row in rows:
        by_file.setdefault(row["rel_path"], []).append(row)

    rng = random.Random(seed)
    sample = rng.sample(sorted(by_file), min(n_files, len(by_file)))
    mismatches = 0
    for rel in sample:
        trials = json.loads((ORG_DATASET / rel).read_text())
        scanned = sorted(by_file[rel], key=lambda r: r["trial_index"])
        if len(trials) != len(scanned):
            print(f"  MISMATCH {rel}: {len(trials)} trials in file, {len(scanned)} scanned")
            mismatches += 1
            continue
        for trial, row in zip(trials, scanned):
            expected = {
                "trial_index": trial["trialIndex"],
                "oor_label": trial["oorLabel"],
                "ir_label": trial["irLabel"],
                "object_name": trial["objectName"],
                "target_object": trial["targetObjectName"],
                "n_frames": len(trial["isLabeledFrame"]),
                "n_labeled": sum(trial["isLabeledFrame"]),
                "n_in_reach": sum(trial["isInReachFrame"]),
            }
            for key, want in expected.items():
                if row[key] != want:
                    print(f"  MISMATCH {rel} trial {trial['trialIndex']} {key}: "
                          f"scanned {row[key]!r}, file {want!r}")
                    mismatches += 1
    print(f"verified {len(sample)} files: {mismatches} mismatches")
    return mismatches


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT,
                   help=f"CSV to write (default: {DEFAULT_OUT.relative_to(MODEL_DIR)})")
    p.add_argument("--verify", type=int, default=6, metavar="N",
                   help="re-parse N random files with json.load and compare (default: 6, 0 to skip)")
    p.add_argument("--workers", type=int, default=8, help="parallel readers (default: 8)")
    return p.parse_args()


def main():
    args = parse_args()
    if not ORG_DATASET.exists():
        sys.exit(f"No dataset at {ORG_DATASET}")

    files = sorted(ORG_DATASET.glob("*/*/*/all_trials.json"))
    if not files:
        sys.exit(f"No */*/*/all_trials.json under {ORG_DATASET}\n"
                 f"Expected layout: ORG_dataset/<subject>/<object>/<timestamp>/all_trials.json")
    print(f"scanning {len(files)} session files under {ORG_DATASET}")

    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(scan_file, files, chunksize=8):
            rows.extend(result)
    total_gb = sum({r["rel_path"]: r["file_mb"] for r in rows}.values()) / 1000
    print(f"{len(rows)} trials from {len(files)} files ({total_gb:.2f} GB)")

    if args.verify:
        verify(rows, args.verify)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
