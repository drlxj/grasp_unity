"""
快速手势可视化脚本
专门用于查看对齐后的手势形状，包含完整的骨架连线
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

def draw_hand_skeleton(ax, joints, color='blue', alpha=0.8, linewidth=2, label='Hand'):
    """绘制完整的手部骨架"""
    # 手部骨架连接定义
    connections = [
        # 拇指
        (0, 1), (1, 2), (2, 3), (3, 4),
        # 食指
        (0, 5), (5, 6), (6, 7), (7, 8),
        # 中指
        (0, 9), (9, 10), (10, 11), (11, 12),
        # 无名指
        (0, 13), (13, 14), (14, 15), (15, 16),
        # 小指
        (0, 17), (17, 18), (18, 19), (19, 20),
        # 手掌连接
        (1, 5), (5, 9), (9, 13), (13, 17)
    ]
    
    # 绘制关节点
    ax.scatter(joints[:, 0], joints[:, 1], joints[:, 2], 
              c=color, s=40, alpha=alpha, label=label)
    
    # 绘制骨架连接
    for start_idx, end_idx in connections:
        start_point = joints[start_idx]
        end_point = joints[end_idx]
        ax.plot([start_point[0], end_point[0]], 
               [start_point[1], end_point[1]], 
               [start_point[2], end_point[2]], 
               color=color, alpha=alpha, linewidth=linewidth)

def create_gesture_comparison(category, unity_data, grab_data, reference):
    """创建手势比较图"""
    fig = plt.figure(figsize=(15, 10))
    
    # 1. Unity手势
    ax1 = fig.add_subplot(2, 2, 1, projection='3d')
    draw_hand_skeleton(ax1, unity_data[0], 'red', 0.8, 2, 'Ours')
    draw_hand_skeleton(ax1, reference, 'black', 1.0, 3, 'Reference')
    ax1.set_title(f'{category} - Ours vs Reference', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.set_xlabel('X')
    ax1.set_ylabel('Y')
    ax1.set_zlabel('Z')
    
    # 2. GRAB手势
    ax2 = fig.add_subplot(2, 2, 2, projection='3d')
    draw_hand_skeleton(ax2, grab_data[0], 'blue', 0.8, 2, 'GRAB')
    draw_hand_skeleton(ax2, reference, 'black', 1.0, 3, 'Reference')
    ax2.set_title(f'{category} - GRAB vs Reference', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.set_xlabel('X')
    ax2.set_ylabel('Y')
    ax2.set_zlabel('Z')
    
    # 3. 直接比较
    ax3 = fig.add_subplot(2, 2, 3, projection='3d')
    draw_hand_skeleton(ax3, unity_data[0], 'red', 0.8, 2, 'Ours')
    draw_hand_skeleton(ax3, grab_data[0], 'blue', 0.8, 2, 'GRAB')
    draw_hand_skeleton(ax3, reference, 'black', 1.0, 3, 'Reference')
    ax3.set_title(f'{category} - Ours vs GRAB', fontsize=14, fontweight='bold')
    ax3.legend()
    ax3.set_xlabel('X')
    ax3.set_ylabel('Y')
    ax3.set_zlabel('Z')
    
    # 4. 多个样本叠加
    ax4 = fig.add_subplot(2, 2, 4, projection='3d')
    # 绘制多个Unity样本
    for i in range(min(5, len(unity_data))):
        alpha = 0.4 + 0.4 * (i == 0)
        draw_hand_skeleton(ax4, unity_data[i], 'red', alpha, 1, 'Ours' if i == 0 else '')
    # 绘制多个GRAB样本
    for i in range(min(5, len(grab_data))):
        alpha = 0.4 + 0.4 * (i == 0)
        draw_hand_skeleton(ax4, grab_data[i], 'blue', alpha, 1, 'GRAB' if i == 0 else '')
    draw_hand_skeleton(ax4, reference, 'black', 1.0, 3, 'Reference')
    ax4.set_title(f'{category} - Multiple Samples', fontsize=14, fontweight='bold')
    ax4.legend()
    ax4.set_xlabel('X')
    ax4.set_ylabel('Y')
    ax4.set_zlabel('Z')
    
    plt.suptitle(f'{category} - Aligned Gesture Comparison', fontsize=16, fontweight='bold')
    plt.tight_layout()
    # plt.savefig(f'quick_gesture_comparison_{category}.png', dpi=300, bbox_inches='tight')
    # print(f"Saved: quick_gesture_comparison_{category}.png")
    plt.show()

def main():
    print("Loading aligned gesture data...")
    unity_data, grab_data, references = load_data()
    
    # 选择要分析的类别
    # categories = ['bowl', 'apple', 'cup', 'hammer', 'mug']
    # categories = ['spheresmall', 'spherlarge', 'waterbottle']
    # categories = ['flashlight', 'knife', 'mouse', 'scissors']
    categories = ['headphones']
    
    for category in categories:
        if category in unity_data and len(unity_data[category]) > 0:
            print(f"\nAnalyzing {category}...")
            print(f"  Ours samples: {len(unity_data[category])}")
            print(f"  GRAB samples: {len(grab_data[category])}")
            
            create_gesture_comparison(category, unity_data[category], grab_data[category], references[category])
    
    print("\nVisualization complete!")

if __name__ == "__main__":
    main()
