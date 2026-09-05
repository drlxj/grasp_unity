import json
import math
import itertools
from pathlib import Path
from typing import List, Tuple, Dict, Any, Sequence

import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.spatial import procrustes
from scipy.stats import ttest_rel, f_oneway
from sklearn.manifold import TSNE
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Global configuration (edit as needed)
# ---------------------------------------------------------------------------

USER_IDS: List[str] = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11", "s12", "s13", "s14", "s15", "s17", "s18", "s19", "s20"]
DATA_ROOT: Path = Path("../dataset/collected_data")
RNG_SEED: int = 42  # Keep visualisations deterministic

# Output artefacts
OUT_DIR: Path = Path("outputs")
OUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def extract_labeled_gesture(trial: Dict[str, Any], *, in_reach: bool = True) -> torch.Tensor:
    """Return the joint positions (shape ``[F, 21, 3]``) for labeled frames.

    Frames are translated so that joint‑0 is at the origin, matching the
    original behaviour of the script.
    """
    joints_positions = torch.tensor(trial["gestures"]["jointsPositionWorld"], dtype=torch.float32)
    flag = trial["isInReachFrame"] if in_reach else trial["isLabeledFrame"]
    selected = joints_positions[flag]
    # Translate so that the wrist/root (joint‑0) is at the origin.
    return selected - selected[:, 0:1]

def compute_aperture(joint_frame: torch.Tensor) -> float:
    """Distance between thumb tip (4) and index tip (8) for a *single* frame."""
    return torch.norm(joint_frame[4] - joint_frame[8]).item()

def compute_jointwise_l2(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """Per‑joint Euclidean distance between two single-frame gestures."""
    return torch.norm(a - b, dim=1)

def compute_procrustes_distance(a: torch.Tensor, b: torch.Tensor) -> float:
    """Orthogonal Procrustes disparity between two single‑frame gestures."""
    mtx1, mtx2, disparity = procrustes(a.numpy(), b.numpy())
    return float(disparity)

def flatten_gesture(gesture: torch.Tensor) -> np.ndarray:
    """Flatten a ``(21,3)`` gesture to 63‑D vector for TSNE."""
    return gesture.reshape(-1).numpy()

def get_label_from_trial(trial: Dict[str, Any], *, in_reach: bool = True) -> int:
    return trial["irLabel"] if in_reach else trial["oorLabel"]

# ---------------------------------------------------------------------------
# Data ingestion
# ---------------------------------------------------------------------------

def load_data(user_ids: Sequence[str] = USER_IDS, data_root: Path = DATA_ROOT
             ) -> Tuple[pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
    """Load JSON trials and assemble *gesture* and *label* DataFrames.

    Returns
    -------
    gestures_df : pd.DataFrame
        One row per (user, object, trial_index) — contains numeric metrics.
    labels_df : pd.DataFrame
        One row per (user, object, trial_index) — contains categorical labels.
    raw_records : list[dict]
        Original per‑trial dictionaries for downstream custom analyses (e.g. TSNE).
    """
    gesture_records: List[Dict[str, Any]] = []
    label_records: List[Dict[str, Any]] = []



    for user_id in tqdm(user_ids):
        for obj_dir in (data_root / user_id).iterdir():
            if not obj_dir.is_dir():
                continue
            for json_file in obj_dir.glob("**/all_trials.json"):
                with open(json_file, "r", encoding="utf-8") as f:
                    trials = json.load(f)

                for trial_id, trial in enumerate(trials):
                    # Use first frame of each labelled sequence (consistent with original code)
                    oor_gesture = extract_labeled_gesture(trial, in_reach=False).squeeze(0)
                    ir_gesture = extract_labeled_gesture(trial, in_reach=True).squeeze(0)
                    # if oor_gesture.numel() and ir_gesture.numel():
                    if trial_id == 0:  
                        gesture_records.append({
                            "user": user_id,
                            "object": trial["objectName"],
                            "trial_index": trial["trialIndex"],
                            "oor_gesture": oor_gesture,
                            "ir_gesture": ir_gesture,
                            "jointwise_l2": compute_jointwise_l2(oor_gesture, ir_gesture).numpy(),
                            "l2": compute_jointwise_l2(oor_gesture, ir_gesture).mean().item(),
                            "procrustes": compute_procrustes_distance(oor_gesture, ir_gesture),
                            "oor_aperture": compute_aperture(oor_gesture),
                            "ir_aperture": compute_aperture(ir_gesture),
                        })

                    # # Label bookkeeping for every frame regardless of gesture availability
                    # label_records.append({
                    #     "user": user_id,
                    #     "object": trial["objectName"],
                    #     "trial_index": trial["trialIndex"],
                    #     "oor_label": get_label_from_trial(trial, in_reach=False),
                    #     "ir_label": get_label_from_trial(trial, in_reach=True),
                    # })
    gestures_df = pd.DataFrame(gesture_records)
    labels_df = pd.DataFrame(label_records)

    return gestures_df, labels_df, gesture_records

# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def summarise_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """Compute all summary statistics and return as a dict."""
    summary = {
        "L2 Mean": df["l2"].mean(),
        "Procrustes Mean": df["procrustes"].mean(),
        "OOR Aperture Mean": df["oor_aperture"].mean(),
        "IR Aperture Mean": df["ir_aperture"].mean(),
        "L2 vs 0 p-value": ttest_rel(df["l2"], np.zeros(len(df))).pvalue,
        "Procrustes vs 0 p-value": ttest_rel(df["procrustes"], np.zeros(len(df))).pvalue,
        "OOR vs IR aperture p-value": ttest_rel(df["oor_aperture"], df["ir_aperture"]).pvalue,
    }
    # Variance analysis
    inter_subject_var = df.groupby("user")["l2"].mean().var()
    intra_subject_var = df.groupby(["user", "object"])["l2"].var().mean()
    summary["Inter-subject variance"] = inter_subject_var
    summary["Intra-subject variance"] = intra_subject_var
    return summary

def save_summary_csv(summary: Dict[str, float], out_path: Path = OUT_DIR / "gesture_statistics_summary.csv") -> None:
    pd.DataFrame.from_dict(summary, orient="index", columns=["Value"]).to_csv(out_path)
    print(f"✅ Summary CSV saved to {out_path}")

# ---------------------------------------------------------------------------
# Visualisation helpers
# ---------------------------------------------------------------------------

def plot_boxplot_by_object(df: pd.DataFrame) -> None:
    plt.figure(figsize=(14, 5))
    sns.boxplot(data=df, x="object", y="l2")
    plt.title("L2 Gesture Distance by Object")
    plt.ylabel("L2 Distance (OOR vs IR)")
    plt.xlabel("Object Name")
    plt.xticks(rotation=30)
    plt.tight_layout()
    out_file = OUT_DIR / "l2_boxplot_by_object.png"
    plt.savefig(out_file, dpi=200)
    plt.close()
    print(f"✅ Saved {out_file}")

def plot_joint_mean_distance(df: pd.DataFrame) -> None:
    joint_diffs = np.stack(df["jointwise_l2"].values)  # (N,21)
    mean_per_joint = joint_diffs.mean(axis=0)
    std_per_joint = joint_diffs.std(axis=0)
    var_per_joint = joint_diffs.var(axis=0)

    # 计算每个关节在不同用户间的标准差
    joint_std_across_users = []
    for joint_idx in range(21):
        joint_values_across_users = []
        for user_id in df['user'].unique():
            user_data = df[df['user'] == user_id]
            user_joint_diffs = np.stack(user_data["jointwise_l2"].values)
            joint_values_across_users.extend([user_joint_diffs[:, joint_idx].mean()])
        
        # 计算这个关节在所有用户中的标准差
        joint_std = np.std(joint_values_across_users)
        joint_std_across_users.append(joint_std)
    
    joint_std_across_users = np.array(joint_std_across_users)
    mean_joint_std_across_users = np.mean(joint_std_across_users)
    std_joint_std_across_users = np.std(joint_std_across_users)
    min_joint_std_across_users = np.min(joint_std_across_users)
    max_joint_std_across_users = np.max(joint_std_across_users)

    plt.figure(figsize=(10, 3))
    x_pos = np.arange(21)
    
    # 定义关节颜色（根据手部关节图）
    joint_colors = []
    for i in range(21):
        if i == 0:  # 手腕根部 - 黑色
            joint_colors.append('black')
        elif 1 <= i <= 4:  # 拇指 - 紫色
            joint_colors.append('purple')
        elif 5 <= i <= 8:  # 食指 - 蓝色
            joint_colors.append('blue')
        elif 9 <= i <= 12:  # 中指 - 绿色
            joint_colors.append('green')
        elif 13 <= i <= 16:  # 无名指 - 黄色
            joint_colors.append('orange')  # 使用orange代替黄色，更清晰
        elif 17 <= i <= 20:  # 小指 - 红色
            joint_colors.append('red')
    
    # Create bar plot with error bars showing standard deviation
    bars = plt.bar(x_pos, mean_per_joint, yerr=joint_std_across_users, 
                   capsize=5, alpha=0.7, color=joint_colors)
    
    plt.xticks(x_pos, [f"J{i}" for i in range(21)], fontsize=12)
    plt.xlabel("Joint Index", fontsize=14)
    plt.ylabel("L2 Distance [m]", fontsize=14)
    plt.title("Per-Joint Mean Distance and Variation Across Users", fontsize=16)
    plt.grid(True, alpha=0.3)
    
    # 添加图例
    from matplotlib.patches import Patch
    legend_elements = [
        # Patch(facecolor='black', label='Wrist (J0)'),
        Patch(facecolor='purple', label='Thumb'),
        Patch(facecolor='blue', label='Index'),
        Patch(facecolor='green', label='Middle'),
        Patch(facecolor='orange', label='Ring'),
        Patch(facecolor='red', label='Pinky')
    ]
    plt.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0.005, 1.0), fontsize=10)
    plt.tight_layout()
    out_file = OUT_DIR / "joint_mean_distance.png"
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.show()
    print(f"✅ Saved {out_file}")

def plot_tsne(gesture_records: List[Dict[str, Any]]) -> None:
    """Compute and save t-SNE scatterplot distinguishing OOR vs IR with object information."""
    # Prepare data with object information
    features = []
    labels = []
    objects = []
    gesture_types = []
    
    for r in gesture_records:
        # Add OOR gesture
        features.append(flatten_gesture(r["oor_gesture"]))
        labels.append("OOR")
        objects.append(r["object"])
        gesture_types.append("OOR")
        
        # Add IR gesture
        features.append(flatten_gesture(r["ir_gesture"]))
        labels.append("IR")
        objects.append(r["object"])
        gesture_types.append("IR")

    sns.set_context("notebook")
    np.random.seed(RNG_SEED)
    tsne_emb = TSNE(n_components=2, perplexity=30, random_state=RNG_SEED).fit_transform(np.array(features))
    
    # Create DataFrame with all information
    df_tsne = pd.DataFrame(tsne_emb, columns=["dim1", "dim2"])
    df_tsne["label"] = labels
    df_tsne["object"] = objects
    df_tsne["gesture_type"] = gesture_types

    # Get unique objects for color mapping
    unique_objects = sorted(df_tsne["object"].unique())
    colors = plt.cm.Set3(np.linspace(0, 1, len(unique_objects)))
    color_map = dict(zip(unique_objects, colors))

    plt.figure(figsize=(12, 8))
    
    # Plot each object with different colors and markers
    for obj in unique_objects:
        obj_data = df_tsne[df_tsne["object"] == obj]
        
        # Plot OOR gestures with 'o' marker
        oor_data = obj_data[obj_data["gesture_type"] == "OOR"]
        if not oor_data.empty:
            plt.scatter(oor_data["dim1"], oor_data["dim2"], 
                       c=[color_map[obj]], marker='o', s=60, alpha=0.7, 
                       label=f'{obj} (OOR)', edgecolors='black', linewidth=0.5)
        
        # Plot IR gestures with 'x' marker
        ir_data = obj_data[obj_data["gesture_type"] == "IR"]
        if not ir_data.empty:
            plt.scatter(ir_data["dim1"], ir_data["dim2"], 
                       c=[color_map[obj]], marker='x', s=80, alpha=0.7, 
                       label=f'{obj} (IR)', linewidth=2)

    plt.title("t-SNE of Out-of-Reach vs In-Reach Gestures by Object")
    plt.xlabel("t-SNE Dimension 1")
    plt.ylabel("t-SNE Dimension 2")
    
    # Create custom legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Out-of-Reach (O)', 
               markerfacecolor='gray', markersize=8, markeredgecolor='black'),
        Line2D([0], [0], marker='x', color='w', label='In-Reach (×)', 
               markerfacecolor='gray', markersize=8, linewidth=2)
    ]
    
    # Add object color legend
    for obj, color in color_map.items():
        legend_elements.append(Line2D([0], [0], marker='s', color='w', 
                                     label=obj, markerfacecolor=color, 
                                     markersize=8, markeredgecolor='black'))
    
    plt.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    out_file = OUT_DIR / "gesture_tsne.png"
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Saved {out_file}")




# ---------------------------------------------------------------------------
# Advanced analyses
# ---------------------------------------------------------------------------

def compatibility_table(labels_df: pd.DataFrame) -> pd.DataFrame:
    """Return a per‑object compatibility DataFrame and save to CSV."""
    def _count(sub: pd.DataFrame, label: str) -> pd.Series:
        return pd.Series({
            "pos": (sub[label] == 1).sum(),
            "neg": (sub[label] == 0).sum(),
            "uns": (sub[label] == 2).sum(),
            "tot": len(sub),
        })

    compat = pd.concat([
        labels_df.groupby("object").apply(lambda d: _count(d, "oor_label")).add_prefix("oor_"),
        labels_df.groupby("object").apply(lambda d: _count(d, "ir_label")).add_prefix("ir_"),
    ], axis=1)

    compat["oor_uns_ratio"] = compat["oor_uns"] / compat["oor_tot"]
    compat["ir_uns_ratio"] = compat["ir_uns"] / compat["ir_tot"]

    out_csv = OUT_DIR / "gesture_object_compatibility.csv"
    compat.to_csv(out_csv)
    print(f"✅ Saved compatibility table → {out_csv}")
    return compat

def conditional_rate_by_user(labels_df: pd.DataFrame) -> pd.DataFrame:
    """Compute P(IR = Yes | OOR = Yes) per user and save bar‑plot."""
    res = []
    for user, sub in labels_df.groupby("user"):
        oor_yes = sub[sub["oor_label"] == 1]
        rate = np.nan if oor_yes.empty else (oor_yes["ir_label"] == 1).mean()
        res.append({"user": user, "cond_rate": rate})
    df_cond = pd.DataFrame(res)

    # Save CSV
    out_csv = OUT_DIR / "per_user_conditional_rate.csv"
    df_cond.to_csv(out_csv, index=False)
    print(f"✅ Saved {out_csv}")

    # Bar‑plot
    plt.figure(figsize=(6, 4))
    sns.barplot(data=df_cond, x="user", y="cond_rate", palette="viridis")
    plt.ylim(0, 1)
    plt.ylabel("P(IR = Yes | OOR = Yes)")
    plt.title("Conditional Compatibility per User")
    plt.tight_layout()
    out_png = OUT_DIR / "per_user_conditional.png"
    plt.savefig(out_png, dpi=200)
    plt.close()
    print(f"✅ Saved {out_png}")
    return df_cond

# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------

def main() -> None:
    # """End‑to‑end execution of the analysis pipeline."""
    # print("⏳ Loading data …")
    # gestures_df, labels_df, gesture_records = load_data()
    # print(f"   • Loaded {len(gestures_df)} gesture pairs from {len(USER_IDS)} users.")
    # # save gestures_df to csv
    # gestures_df.to_csv(OUT_DIR / "gestures_df.csv", index=False)
    # print(f"✅ Saved {OUT_DIR / 'gestures_df.csv'}")

    # # ---------------------------------------------------------------------
    # # Statistics
    # print("📊 Computing summary statistics …")
    # summary = summarise_metrics(gestures_df)
    # save_summary_csv(summary)
    # print("   • Summary:")
    # for k, v in summary.items():
    #     print(f"     {k:<35}: {v}")

    # ---------------------------------------------------------------------
    # Visualisations
    print("🖼  Generating plots …")
    # plot_boxplot_by_object(gestures_df)
    gestures_df = pd.read_csv(OUT_DIR / "gestures_df.csv")

     # 解析jointwise_l2列，将字符串转换回numpy数组
    def parse_jointwise_l2(item):
        if isinstance(item, str):
            # 移除tensor(和)包装，只保留数组部分
            array_str = item.replace('tensor(', '').replace(')', '')
            # 移除方括号和换行符
            clean_str = array_str.replace('[', '').replace(']', '').replace('\n', ' ').strip()
            # 分割字符串并转换为浮点数
            values = [float(x) for x in clean_str.split() if x.strip()]
            return np.array(values)
        else:
            return item
     
    gestures_df['jointwise_l2'] = [parse_jointwise_l2(item) for item in gestures_df['jointwise_l2']]
    plot_joint_mean_distance(gestures_df)
    # plot_tsne(gesture_records)

    # # ---------------------------------------------------------------------
    # # Compatibility & conditional probabilities
    # print("🔗 Compatibility analysis …")
    # compatibility_table(labels_df)
    # conditional_rate_by_user(labels_df)

    print("✅ All done! Outputs saved to", OUT_DIR.resolve())

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
