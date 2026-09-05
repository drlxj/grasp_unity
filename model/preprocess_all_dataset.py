#!/usr/bin/env python3
"""
Process all users in ../dataset/ORG_dataset and save NPZ to ../dataset/preprocessed_dataset/{user}/{object}_{json_idx}/t_{trial_idx}/features_ir_{ir}_oor_{oor}_{object_name}.npz
"""
from pathlib import Path
import json
import sys

from dataset_utils import process_trial_to_features, save_feature_npz, get_save_path

COLLECTED_ROOT = Path("../dataset/ORG_dataset")
OUTPUT_ROOT = Path("../dataset/preprocessed_dataset")


def main():
    if not COLLECTED_ROOT.exists():
        print(f"Not found: {COLLECTED_ROOT}")
        sys.exit(1)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    user_dirs = sorted([d for d in COLLECTED_ROOT.iterdir() if d.is_dir()])
    total = 0
    for user_dir in user_dirs:
        user_id = user_dir.name
        out_user = OUTPUT_ROOT / user_id
        for obj_dir in sorted(user_dir.iterdir()):
            if not obj_dir.is_dir():
                continue
            object_name = obj_dir.name
            json_files = sorted(obj_dir.glob("**/all_trials.json"))
            for json_idx, json_file in enumerate(json_files):
                with open(json_file, "r") as f:
                    trials = json.load(f)
                for trial in trials:
                    target = trial["targetObjectName"]
                    if trial["objectName"] != target:
                        continue
                    ir, oor = trial["irLabel"], trial["oorLabel"]
                    trial_idx = trial["trialIndex"]
                    try:
                        feat = process_trial_to_features(trial)
                    except Exception as e:
                        print(f"Skip {user_id}/{object_name} t_{trial_idx}: {e}")
                        continue
                    save_path = get_save_path(OUTPUT_ROOT, user_id, object_name, json_idx, trial_idx, ir, oor)
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    save_feature_npz(save_path, feat)
                    total += 1
    print(f"Saved {total} NPZ under {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
