import numpy as np
from sklearn.cluster import SpectralClustering
from sklearn.metrics import silhouette_score
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import json
from typing import Sequence, Tuple, List, Dict, Any
from tqdm import tqdm

# 配置
OUT_DIR = Path("outputs")
COMPATIBILITY_MATRIX_PATH = OUT_DIR / "object_compatibility_matrix.csv"

# 从analyze_collected_data.py移动过来的配置
USER_IDS = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11", "s12", "s13", "s14", "s15", "s17", "s18", "s19", "s20"]
DATA_ROOT = Path("../dataset/collected_data")

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

    count_yes = defaultdict(int)
    count_total = defaultdict(int)
    all_objects = set()

    for user_id in tqdm(user_ids):
        for obj_dir in (data_root / user_id).iterdir():
            if not obj_dir.is_dir():
                continue
            for json_file in obj_dir.glob("**/all_trials.json"):
                with open(json_file, "r", encoding="utf-8") as f:
                    trials = json.load(f)

                for trial_id, trial in enumerate(trials):
                    target = trial["targetObjectName"]
                    all_objects.add(target)
                    name = trial["objectName"]
                    oor_label = trial["oorLabel"]
                    ir_label = trial["irLabel"]
                    if oor_label == 2:
                        continue  # skip unsure
                    key = (target, name)
                    if oor_label == 1:
                        if ir_label == 1:
                            count_yes[key] += 1
                        elif ir_label == 0:
                            continue
                        elif ir_label == 2:
                            continue
                    count_total[key] += 1
                    all_objects.add(name)

    gestures_df = pd.DataFrame(gesture_records)
    labels_df = pd.DataFrame(label_records)

    objects = sorted(all_objects)
    matrix = pd.DataFrame(index=objects, columns=objects, dtype=float)
    for t in objects:
        for d in objects:
            total = count_total.get((t, d), 0)
            yes = count_yes.get((t, d), 0)
            matrix.loc[t, d] = yes / total if total > 0 else np.nan

    return gestures_df, labels_df, gesture_records, matrix

def plot_sns_object_matrix():
    """从保存的CSV文件中读取并绘制对象兼容性矩阵"""
    # 从保存的CSV文件读取原始矩阵
    matrix_path = OUT_DIR / "object_compatibility_matrix.csv"
    if not matrix_path.exists():
        print(f"❌ Matrix file not found at {matrix_path}")
        print("请先运行 generate_compatibility_matrix() 生成矩阵文件")
        return
    
    matrix = pd.read_csv(matrix_path, index_col=0)
    print(f"✅ Loaded matrix from {matrix_path} with {len(matrix)} objects")
    
    # 创建对称化矩阵用于可视化
    symmetric_matrix = (matrix + matrix.T) / 2
    
    # Create mask for upper triangle (to show only half of the matrix)
    mask = np.triu(np.ones_like(symmetric_matrix, dtype=bool))
    
    # Heatmap showing only the lower triangle
    plt.figure(figsize=(12, 10))
    ax = sns.heatmap(symmetric_matrix, cmap="viridis", vmin=0, vmax=1, 
                mask=mask, annot=False, cbar_kws={'label': 'Similarity Score', 'location': 'left', 'pad': 0.13})
    
    # 调整颜色条文字大小
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=12)
    cbar.set_label('Similarity Score', fontsize=14)
    # plt.title("Object Confusion Matrix")
    # plt.xlabel("Object", fontsize=14)
    # plt.ylabel("Object", fontsize=14)
    plt.xticks(rotation=45, ha="right", fontsize=12)
    plt.yticks(rotation=0, fontsize=12)
    plt.tight_layout()
    out_png = OUT_DIR / "object_compatibility_matrix.png"
    plt.savefig(out_png, dpi=200)
    plt.close()
    print(f"✅ Saved symmetric heatmap → {out_png}")

def load_matrix() -> pd.DataFrame:
    """Load the compatibility matrix from CSV."""
    if not COMPATIBILITY_MATRIX_PATH.exists():
        raise FileNotFoundError(f"Matrix not found at {COMPATIBILITY_MATRIX_PATH}")
    df = pd.read_csv(COMPATIBILITY_MATRIX_PATH, index_col=0)
    print(f"✅ Loaded matrix with {len(df)} objects")
    return df

def prepare_similarity(df: pd.DataFrame):
    """对称化 + 对角线置1，并返回 numpy 相似度矩阵和对象名列表"""
    df_sym = (df + df.T) / 2
    S = df_sym.to_numpy(dtype=float)
    np.fill_diagonal(S, 1.0)
    S = np.clip(S, 0.0, 1.0)
    names = df_sym.index.tolist()
    return S, names

def generate_compatibility_matrix():
    """生成对象兼容性矩阵的主函数"""
    print("⏳ Loading data and generating object compatibility matrix...")
    gestures_df, labels_df, gesture_records, object_matrix = load_data()
    print(f"   • Loaded data with {len(object_matrix)} objects.")

    # 保存原始矩阵
    out_csv = OUT_DIR / "object_compatibility_matrix.csv"
    object_matrix.to_csv(out_csv)
    print(f"✅ Saved original object compatibility matrix → {out_csv}")
    

def analyze_similarity_clustering():
    """分析相似度矩阵的聚类"""
    print("⏳ Loading existing compatibility matrix for clustering analysis...")
    df = load_matrix()
    S, names = prepare_similarity(df)

    # 距离矩阵：相似度越高 -> 距离越近
    D = 1.0 - S

    best_score = -1
    best_k = None
    best_labels = None

    for k in range(2, 11):
        spc = SpectralClustering(
            n_clusters=k,
            affinity='precomputed',
            assign_labels='kmeans',
            random_state=0
        ).fit(S)
        labels = spc.labels_
        sil = silhouette_score(D, labels, metric='precomputed')

        print(f"k={k}, silhouette={sil:.3f}")
        if sil > best_score:
            best_score = sil
            best_k = k
            best_labels = labels

    print("\nSilhouette 最优: k={}, score={:.3f}".format(best_k, best_score))

    # 按簇打印物体名称
    clusters = {}
    for idx, lab in enumerate(best_labels):
        clusters.setdefault(lab, []).append(names[idx])

    print("\n====== 聚类结果 ======")
    for lab in sorted(clusters.keys()):
        print(f"Cluster {lab} ({len(clusters[lab])}): {clusters[lab]}")

def find_zero_similarity_pairs():
    """找出每个物体与哪些物体的相似度得分为0（完全不相似）"""
    print("🔍 分析每个物体与完全不相似（similarity score = 0）的物体...")
    
    # 要排除的物体列表
    objects_to_exclude = ['crackerbox', 'disklid', 'pottedmeatcan', 'smartphone']
    
    # 加载矩阵
    df = load_matrix()
    
    # 对称化矩阵
    df_sym = (df + df.T) / 2
    
    # 过滤掉要排除的物体
    objects_to_keep = [obj for obj in df_sym.index if obj not in objects_to_exclude]
    df_filtered = df_sym.loc[objects_to_keep, objects_to_keep]
    
    print(f"   • 排除了 {len(objects_to_exclude)} 个物体: {', '.join(objects_to_exclude)}")
    print(f"   • 剩余 {len(objects_to_keep)} 个物体用于分析")
    
    results = {}
    zero_pairs_set = set()  # 使用set避免重复对
    
    # 遍历每个物体（只处理保留的物体）
    for obj1 in df_filtered.index:
        zero_similarity_objects = []
        
        # 检查与所有其他物体（只检查保留的物体）的相似度
        for obj2 in df_filtered.columns:
            if obj1 == obj2:
                continue  # 跳过自身
            
            similarity = df_filtered.loc[obj1, obj2]
            
            # 检查相似度是否为0（不包含NaN）
            if pd.notna(similarity) and similarity == 0.0:
                zero_similarity_objects.append(obj2)
                # 添加到set中，确保object1 < object2以避免重复
                pair = tuple(sorted([obj1, obj2]))
                zero_pairs_set.add(pair)
        
        results[obj1] = zero_similarity_objects
    
    # 转换为列表格式
    zero_pairs_list = [{'object1': pair[0], 'object2': pair[1], 'similarity': 0.0} 
                       for pair in sorted(zero_pairs_set)]
    
    # 打印结果
    print("\n" + "="*80)
    print("每个物体与完全不相似（similarity score = 0）的物体列表")
    print("="*80)
    
    # 按物体名称排序
    sorted_objects = sorted(results.keys())
    
    for obj in sorted_objects:
        zero_objs = results[obj]
        if zero_objs:
            print(f"{obj}: {', '.join(sorted(zero_objs))}")
        else:
            print(f"{obj}:")
    
    # 保存结果到CSV
    if zero_pairs_list:
        results_df = pd.DataFrame(zero_pairs_list)
        results_file = OUT_DIR / "zero_similarity_pairs.csv"
        results_file.parent.mkdir(exist_ok=True)
        results_df.to_csv(results_file, index=False)
        print(f"\n💾 完全不相似物体对已保存到: {results_file}")
        
        # 保存每个物体的完全不相似物体列表
        summary_data = []
        for obj in sorted_objects:
            zero_objs = results[obj]
            summary_data.append({
                'object': obj,
                'zero_similarity_count': len(zero_objs),
                'zero_similarity_objects': ', '.join(sorted(zero_objs)) if zero_objs else 'None'
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_file = OUT_DIR / "zero_similarity_by_object.csv"
        summary_df.to_csv(summary_file, index=False)
        print(f"💾 每个物体的完全不相似列表已保存到: {summary_file}")
    
    # 统计信息
    objects_with_zeros = sum(1 for obj, zero_objs in results.items() if zero_objs)
    total_zero_pairs = len(zero_pairs_list)
    
    print(f"\n📊 统计信息:")
    print(f"  总物体数: {len(results)}")
    print(f"  有完全不相似物体的物体数: {objects_with_zeros}")
    print(f"  完全不相似的物体对总数: {total_zero_pairs}")
    
    return results

def find_low_confusion_combinations(max_confusion=0.2, combination_size=5):
    """寻找confusion value低于阈值的物体组合"""
    print(f"🔍 寻找confusion value < {max_confusion} 的{combination_size}物体组合...")
    
    # 加载矩阵
    df = load_matrix()
    print(f"   • 加载了包含 {len(df)} 个物体的矩阵")
    
    # 要去掉的物体列表
    objects_to_remove = ['fryingpan', 'knife', 'scissors', 'smartphone', 'wineglass']
    
    # 过滤掉指定的物体
    original_objects = df.index.tolist()
    filtered_objects = [obj for obj in original_objects if obj not in objects_to_remove]
    
    print(f"   • 去掉了 {len(objects_to_remove)} 个物体: {', '.join(objects_to_remove)}")
    print(f"   • 剩余 {len(filtered_objects)} 个物体用于组合")
    
    # 创建过滤后的矩阵
    filtered_df = df.loc[filtered_objects, filtered_objects]
    matrix = filtered_df.to_numpy()
    object_names = filtered_objects
    
    # 找到所有可能的组合
    from itertools import combinations
    all_combinations = list(combinations(range(len(object_names)), combination_size))
    print(f"   • 总共 {len(all_combinations)} 个可能的{combination_size}物体组合")
    
    # 筛选符合条件的组合
    valid_combinations = []
    
    for i, combo in enumerate(all_combinations):
        if i % 1000 == 0:  # 进度显示
            print(f"   检查进度: {i}/{len(all_combinations)}")
        
        # 检查这个组合中所有物体对之间的confusion value
        is_valid = True
        max_confusion_in_combo = 0
        min_confusion_in_combo = float('inf')
        sum_confusion_in_combo = 0.0
        
        for obj1_idx in combo:
            for obj2_idx in combo:
                if obj1_idx != obj2_idx:
                    confusion_val = matrix[obj1_idx, obj2_idx]
                    if not np.isnan(confusion_val) and confusion_val >= max_confusion:
                        is_valid = False
                        break
                    if not np.isnan(confusion_val):
                        max_confusion_in_combo = max(max_confusion_in_combo, confusion_val)
                        min_confusion_in_combo = min(min_confusion_in_combo, confusion_val)
                        sum_confusion_in_combo += confusion_val
            
            if not is_valid:
                break
        
        if is_valid:
            # 确保min_confusion有有效值
            if min_confusion_in_combo == float('inf'):
                min_confusion_in_combo = 0.0
            
            valid_combinations.append({
                'indices': combo,
                'objects': [object_names[idx] for idx in combo],
                'max_confusion': max_confusion_in_combo,
                'min_confusion': min_confusion_in_combo,
                'sum_confusion': sum_confusion_in_combo
            })
    
    print(f"✅ 找到 {len(valid_combinations)} 个符合条件的组合")
    
    # 按最大confusion value排序
    valid_combinations.sort(key=lambda x: x['max_confusion'])
    
    # 保存结果
    results_file = OUT_DIR / f"low_confusion_combinations_{combination_size}objects.csv"
    results_data = []
    
    for i, combo in enumerate(valid_combinations):
        results_data.append({
            'id': i + 1,
            'objects': ', '.join(combo['objects']),
            'max_confusion': combo['max_confusion'],
            'min_confusion': combo['min_confusion'],
            'sum_confusion': combo['sum_confusion'],
            'object1': combo['objects'][0],
            'object2': combo['objects'][1],
            'object3': combo['objects'][2],
            'object4': combo['objects'][3],
            'object5': combo['objects'][4]
        })
    
    results_df = pd.DataFrame(results_data)
    results_df.to_csv(results_file, index=False)
    print(f"💾 结果已保存到: {results_file}")
    
    # 打印前10个最佳组合
    print(f"\n🏆 前10个最佳组合 (按最大confusion value排序):")
    print("-" * 100)
    for i, combo in enumerate(valid_combinations[:10]):
        print(f"{i+1:2d}. 最大confusion: {combo['max_confusion']:.4f}, "
              f"最小confusion: {combo['min_confusion']:.4f}, "
              f"总和confusion: {combo['sum_confusion']:.4f}")
        print(f"    物体: {', '.join(combo['objects'])}")
        print()
    
    return valid_combinations

if __name__ == "__main__":
    # 同时执行两个功能
    print("🚀 开始执行对象相似度分析...")
    
    # # 1. 生成兼容性矩阵
    # print("\n" + "="*50)
    # print("步骤 1: 生成对象兼容性矩阵")
    # print("="*50)
    # generate_compatibility_matrix()

    # 生成兼容性矩阵
    print("🖼  Generating object compatibility matrix...")
    plot_sns_object_matrix()
    print("✅ Object compatibility matrix generated and saved!")
    
    # 2. 分析相似度聚类
    print("\n" + "="*50)
    print("步骤 2: 分析相似度聚类")
    print("="*50)
    analyze_similarity_clustering()
    
    # 3. 找出完全不相似的物体对
    print("\n" + "="*50)
    print("步骤 3: 找出完全不相似（similarity score = 0）的物体对")
    print("="*50)
    find_zero_similarity_pairs()
    
    # # 4. 寻找低confusion组合
    # print("\n" + "="*50)
    # print("步骤 3: 寻找低confusion物体组合")
    # print("="*50)
    # find_low_confusion_combinations(max_confusion=0.2, combination_size=5)
    
    # # 4. 选择平衡组合
    # print("\n" + "="*50)
    # print("步骤 4: 选择平衡物体组合")
    # print("="*50)
    # select_balanced_combinations(min_occurrence=1, max_occurrence=2)
    
    print("\n✅ 所有分析完成！")
