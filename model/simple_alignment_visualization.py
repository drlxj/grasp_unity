"""
简化的对齐后手势可视化脚本
专门展示GRAB和Unity手势对齐后的比较
"""

import numpy as np
import pickle
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import warnings
warnings.filterwarnings('ignore')

def load_data():
    """加载对齐后的数据"""
    with open('aligned_gestures.pkl', 'rb') as f:
        data = pickle.load(f)
    return data['aligned_unity_hand_joints'], data['aligned_grab_hand_joints'], data['reference_gestures']

def plot_hand_joints(ax, joints, color='blue', alpha=0.7, size=20, label='Hand'):
    """绘制手部关节"""
    ax.scatter(joints[:, 0], joints[:, 1], joints[:, 2], 
              c=color, alpha=alpha, s=size, label=label)

def create_comparison_plot(category, unity_data, grab_data, reference):
    """创建比较图"""
    fig = plt.figure(figsize=(15, 10))
    
    # 1. 对齐后的Unity手势
    ax1 = fig.add_subplot(2, 2, 1, projection='3d')
    for i in range(min(3, len(unity_data))):
        alpha = 0.6 if i > 0 else 0.8
        plot_hand_joints(ax1, unity_data[i], 'red', alpha, 30, 'Unity' if i == 0 else '')
    plot_hand_joints(ax1, reference, 'black', 1.0, 100, 'Reference')
    ax1.set_title(f'{category} - 对齐后Unity手势')
    ax1.legend()
    
    # 2. 对齐后的GRAB手势
    ax2 = fig.add_subplot(2, 2, 2, projection='3d')
    for i in range(min(3, len(grab_data))):
        alpha = 0.6 if i > 0 else 0.8
        plot_hand_joints(ax2, grab_data[i], 'blue', alpha, 30, 'GRAB' if i == 0 else '')
    plot_hand_joints(ax2, reference, 'black', 1.0, 100, 'Reference')
    ax2.set_title(f'{category} - 对齐后GRAB手势')
    ax2.legend()
    
    # 3. 直接比较
    ax3 = fig.add_subplot(2, 2, 3, projection='3d')
    plot_hand_joints(ax3, unity_data[0], 'red', 0.8, 50, 'Unity')
    plot_hand_joints(ax3, grab_data[0], 'blue', 0.8, 50, 'GRAB')
    plot_hand_joints(ax3, reference, 'black', 1.0, 100, 'Reference')
    ax3.set_title(f'{category} - Unity vs GRAB 直接比较')
    ax3.legend()
    
    # 4. 质心比较
    ax4 = fig.add_subplot(2, 2, 4, projection='3d')
    unity_centroid = np.mean(unity_data, axis=0)
    grab_centroid = np.mean(grab_data, axis=0)
    plot_hand_joints(ax4, unity_centroid, 'red', 0.8, 100, 'Unity质心')
    plot_hand_joints(ax4, grab_centroid, 'blue', 0.8, 100, 'GRAB质心')
    plot_hand_joints(ax4, reference, 'black', 1.0, 100, 'Reference')
    ax4.set_title(f'{category} - 质心比较')
    ax4.legend()
    
    plt.suptitle(f'{category} - 对齐后手势比较分析', fontsize=16)
    plt.tight_layout()
    plt.savefig(f'alignment_comparison_{category}.png', dpi=300, bbox_inches='tight')
    print(f"已保存: alignment_comparison_{category}.png")
    plt.show()

def main():
    print("加载对齐后的手势数据...")
    unity_data, grab_data, references = load_data()
    
    # 选择几个类别进行可视化
    categories = ['bowl', 'apple', 'cup']
    
    for category in categories:
        if category in unity_data and len(unity_data[category]) > 0:
            print(f"\n分析类别: {category}")
            print(f"  Unity样本数: {len(unity_data[category])}")
            print(f"  GRAB样本数: {len(grab_data[category])}")
            
            # 计算一些基本统计
            unity_centroid = np.mean(unity_data[category], axis=0)
            grab_centroid = np.mean(grab_data[category], axis=0)
            reference = references[category]
            
            unity_to_ref = np.linalg.norm(unity_centroid - reference)
            grab_to_ref = np.linalg.norm(grab_centroid - reference)
            unity_grab_dist = np.linalg.norm(unity_centroid - grab_centroid)
            
            print(f"  Unity质心到参考距离: {unity_to_ref:.4f}")
            print(f"  GRAB质心到参考距离: {grab_to_ref:.4f}")
            print(f"  Unity-GRAB质心距离: {unity_grab_dist:.4f}")
            
            create_comparison_plot(category, unity_data[category], grab_data[category], reference)
    
    print("\n可视化完成！")

if __name__ == "__main__":
    main()

