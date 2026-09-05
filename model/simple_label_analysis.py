import json
from pathlib import Path
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def analyze_labels_simple():
    """
    简单统计ir_label和oor_label的情况
    """
    # 初始化统计变量
    ir_label_counts = Counter()  # ir_label统计
    oor_label_counts = Counter()  # oor_label统计
    combined_label_counts = Counter()  # 组合标签统计
    object_label_stats = defaultdict(lambda: {'ir_0': 0, 'ir_1': 0, 'oor_0': 0, 'oor_1': 0, 'total': 0})
    subject_stats = defaultdict(lambda: Counter())  # 每个subject的组合标签统计
    
    # 尝试多个可能的数据目录
    possible_data_dirs = [
        "../dataset/collected_data/s1",
        "../dataset/collected_data/s2",
        "../dataset/collected_data/s3",
        "../dataset/collected_data/s4",
        "../dataset/collected_data/s5",
        "../dataset/collected_data/s6",
        "../dataset/collected_data/s7",
        "../dataset/collected_data/s8",
        "../dataset/collected_data/s9",
        "../dataset/collected_data/s10",
        "../dataset/collected_data/s11",
        "../dataset/collected_data/s12",
        "../dataset/collected_data/s13",
        "../dataset/collected_data/s14",
        "../dataset/collected_data/s15",
        # "../dataset/collected_data/s16",
        "../dataset/collected_data/s17",
        "../dataset/collected_data/s18",
        "../dataset/collected_data/s19",
        "../dataset/collected_data/s20",
    ]
    
    # 查找所有存在的数据目录
    existing_data_dirs = []
    for dir_path in possible_data_dirs:
        test_path = Path(dir_path)
        if test_path.exists():
            existing_data_dirs.append(test_path)
            print(f"找到数据目录: {test_path}")
    
    if not existing_data_dirs:
        print("未找到数据目录，尝试分析现有的session_npz_files...")
        # 如果没有找到原始数据，尝试分析现有的npz文件
        analyze_existing_npz_files()
        return
    
    # 从所有数据目录中查找所有json文件
    all_json_files = []
    for data_dir in existing_data_dirs:
        json_files = list(data_dir.rglob("**/all_trials.json"))
        all_json_files.extend(json_files)
        print(f"在 {data_dir} 中找到 {len(json_files)} 个JSON文件")
    
    print(f"总共找到 {len(all_json_files)} 个JSON文件")
    
    if len(all_json_files) == 0:
        print("未找到JSON文件，尝试分析现有的session_npz_files...")
        analyze_existing_npz_files()
        return
    
    total_trials = 0
    processed_subjects = set()
    
    for json_file in all_json_files:
        # 从文件路径中提取subject ID
        path_parts = json_file.parts
        subject_id = None
        for part in path_parts:
            if part.startswith('s') and part[1:].isdigit():
                subject_id = part
                break
        
        if subject_id is None:
            continue
            
        processed_subjects.add(subject_id)
        print(f"处理文件: {json_file} (Subject: {subject_id})")
        
        try:
            with open(json_file, "r", encoding='utf-8') as f:
                trials = json.load(f)
        except Exception as e:
            print(f"读取文件失败 {json_file}: {e}")
            continue
        
        for trial in trials:
            total_trials += 1
            
            # 提取标签
            ir_label = trial.get("irLabel", -1)  # in-reach label
            oor_label = trial.get("oorLabel", -1)  # out-of-reach label
            object_name = trial.get("objectName", "unknown")
            
            # 统计单个标签
            ir_label_counts[ir_label] += 1
            oor_label_counts[oor_label] += 1
            
            # 统计组合标签
            combined_label = (ir_label, oor_label)
            combined_label_counts[combined_label] += 1
            
            # 按subject统计
            subject_stats[subject_id][combined_label] += 1
            
            # # 按对象统计
            # object_label_stats[object_name]['total'] += 1
            # if ir_label == 0:
            #     object_label_stats[object_name]['ir_0'] += 1
            # elif ir_label == 1:
            #     object_label_stats[object_name]['ir_1'] += 1
            
            # if oor_label == 0:
            #     object_label_stats[object_name]['oor_0'] += 1
            # elif oor_label == 1:
            #     object_label_stats[object_name]['oor_1'] += 1
    
    print(f"\n处理了 {len(processed_subjects)} 个subjects: {sorted(processed_subjects)}")
    
    # 打印统计结果
    print_statistics(ir_label_counts, oor_label_counts, combined_label_counts, object_label_stats, total_trials)
    
    # 创建堆叠柱状图
    if subject_stats:
        print("\n创建堆叠柱状图...")
        create_stacked_bar_chart(subject_stats)
        save_subject_statistics(subject_stats)

def create_stacked_bar_chart(subject_stats):
    """
    创建堆叠柱状图
    """
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 获取所有可能的组合标签
    all_combinations = set()
    for subject_data in subject_stats.values():
        all_combinations.update(subject_data.keys())
    
    # 排序组合标签
    sorted_combinations = sorted(all_combinations)
    print(f"发现的组合标签: {sorted_combinations}")
    
    # 获取所有subjects并排序
    subjects = sorted(subject_stats.keys(), key=lambda x: int(x[1:]))
    
    # 准备数据
    data_matrix = []
    for subject in subjects:
        row = []
        for combo in sorted_combinations:
            row.append(subject_stats[subject][combo])
        data_matrix.append(row)
    
    data_matrix = np.array(data_matrix)
    
    # 创建堆叠柱状图
    fig, ax = plt.subplots(figsize=(15, 8))
    
    # 设置颜色
    colors = plt.cm.Set3(np.linspace(0, 1, len(sorted_combinations)))
    
    # 创建堆叠柱状图
    bottom = np.zeros(len(subjects))
    bars = []
    
    for i, combo in enumerate(sorted_combinations):
        values = data_matrix[:, i]
        bar = ax.bar(subjects, values, bottom=bottom, 
                    label=f'({combo[0]},{combo[1]})', 
                    color=colors[i], alpha=0.8)
        bars.append(bar)
        bottom += values
    
    # 设置图表属性
    ax.set_xlabel('Subject ID', fontsize=12)
    ax.set_ylabel('# of samples', fontsize=12)
    ax.set_title('Distribution of (ir_label, oor_label) for each subject', fontsize=14, pad=20)
    
    # 添加图例
    ax.legend(title='(ir_label, oor_label)', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # 在柱子上添加数值标签
    for i, subject in enumerate(subjects):
        total = sum(subject_stats[subject].values())
        ax.text(i, total + 1, str(total), ha='center', va='bottom', fontweight='bold')
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图片
    plt.savefig('subject_label_distribution.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return data_matrix, subjects, sorted_combinations

def save_subject_statistics(subject_stats):
    """
    保存subject统计结果到CSV
    """
    # 准备数据
    data_rows = []
    all_combinations = set()
    
    for subject_data in subject_stats.values():
        all_combinations.update(subject_data.keys())
    
    sorted_combinations = sorted(all_combinations)
    subjects = sorted(subject_stats.keys(), key=lambda x: int(x[1:]))
    
    for subject in subjects:
        row = {'subject': subject}
        total = sum(subject_stats[subject].values())
        row['total_samples'] = total
        
        for combo in sorted_combinations:
            count = subject_stats[subject][combo]
            percentage = (count / total * 100) if total > 0 else 0
            row[f'({combo[0]},{combo[1]})_count'] = count
            row[f'({combo[0]},{combo[1]})_percentage'] = percentage
        
        data_rows.append(row)
    
    # 创建DataFrame并保存
    df = pd.DataFrame(data_rows)
    df.to_csv('subject_label_statistics.csv', index=False)
    
    print("\n详细统计结果已保存到 subject_label_statistics.csv")
    
    # 打印汇总统计
    print("\n" + "="*60)
    print("汇总统计")
    print("="*60)
    
    total_samples = sum(sum(subject_data.values()) for subject_data in subject_stats.values())
    print(f"总样本数: {total_samples}")
    
    # 全局组合标签统计
    global_combinations = Counter()
    for subject_data in subject_stats.values():
        for combo, count in subject_data.items():
            global_combinations[combo] += count
    
    print("\n全局组合标签分布:")
    for combo, count in sorted(global_combinations.items()):
        percentage = (count / total_samples) * 100
        print(f"  ({combo[0]},{combo[1]}): {count} 次 ({percentage:.2f}%)")

def analyze_existing_npz_files():
    """
    分析现有的npz文件中的标签
    """
    print("分析session_npz_files中的标签...")
    
    # 初始化统计变量
    ir_label_counts = Counter()
    oor_label_counts = Counter()
    combined_label_counts = Counter()
    object_label_stats = defaultdict(lambda: {'ir_0': 0, 'ir_1': 0, 'oor_0': 0, 'oor_1': 0, 'total': 0})
    
    npz_dir = Path("session_npz_files")
    if not npz_dir.exists():
        print("session_npz_files目录不存在")
        return
    
    total_files = 0
    
    # 遍历所有npz文件
    for npz_file in npz_dir.rglob("*.npz"):
        try:
            import numpy as np
            data = np.load(npz_file, allow_pickle=True)
            
            # 尝试读取标签
            if 'ir_label' in data:
                ir_label = int(data['ir_label'])
                oor_label = int(data['oor_label'])
                object_name = str(data['object_name']) if 'object_name' in data else "unknown"
                
                ir_label_counts[ir_label] += 1
                oor_label_counts[oor_label] += 1
                combined_label_counts[(ir_label, oor_label)] += 1
                
                object_label_stats[object_name]['total'] += 1
                if ir_label == 0:
                    object_label_stats[object_name]['ir_0'] += 1
                elif ir_label == 1:
                    object_label_stats[object_name]['ir_1'] += 1
                
                if oor_label == 0:
                    object_label_stats[object_name]['oor_0'] += 1
                elif oor_label == 1:
                    object_label_stats[object_name]['oor_1'] += 1
                
                total_files += 1
                
        except Exception as e:
            print(f"读取文件失败 {npz_file}: {e}")
            continue
    
    print(f"成功分析了 {total_files} 个npz文件")
    print_statistics(ir_label_counts, oor_label_counts, combined_label_counts, object_label_stats, total_files)

def print_statistics(ir_label_counts, oor_label_counts, combined_label_counts, object_label_stats, total_count):
    """
    打印统计结果
    """
    print("\n" + "="*50)
    print("标签统计结果")
    print("="*50)
    
    print(f"\n总数据量: {total_count}")
    
    print("\n1. ir_label (in-reach label) 统计:")
    print("-" * 30)
    for label, count in sorted(ir_label_counts.items()):
        percentage = (count / total_count) * 100
        print(f"  ir_label = {label}: {count} 次 ({percentage:.2f}%)")
    
    print("\n2. oor_label (out-of-reach label) 统计:")
    print("-" * 30)
    for label, count in sorted(oor_label_counts.items()):
        percentage = (count / total_count) * 100
        print(f"  oor_label = {label}: {count} 次 ({percentage:.2f}%)")
    
    print("\n3. 组合标签统计:")
    print("-" * 30)
    for (ir, oor), count in sorted(combined_label_counts.items()):
        percentage = (count / total_count) * 100
        print(f"  (ir={ir}, oor={oor}): {count} 次 ({percentage:.2f}%)")
    
    print("\n4. 按对象统计:")
    print("-" * 30)
    for obj_name, stats in sorted(object_label_stats.items()):
        if stats['total'] > 0:  # 只显示有数据的对象
            print(f"\n  对象: {obj_name}")
            print(f"    总数据量: {stats['total']}")
            print(f"    ir_label=0: {stats['ir_0']} ({stats['ir_0']/stats['total']*100:.2f}%)")
            print(f"    ir_label=1: {stats['ir_1']} ({stats['ir_1']/stats['total']*100:.2f}%)")
            print(f"    oor_label=0: {stats['oor_0']} ({stats['oor_0']/stats['total']*100:.2f}%)")
            print(f"    oor_label=1: {stats['oor_1']} ({stats['oor_1']/stats['total']*100:.2f}%)")

if __name__ == "__main__":
    analyze_labels_simple() 