"""
手势旋转对齐模块
用于将相同object_category下的手势旋转对齐到参考手势的坐标系
"""

import numpy as np
import pickle
from typing import Dict, Tuple, Optional
from scipy.spatial.transform import Rotation as R
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


def load_gesture_data(pkl_file: str) -> Tuple[Dict, Dict]:
    """
    加载手势数据
    
    Args:
        pkl_file: pickle文件路径
        
    Returns:
        object_unity_hand_joints: Unity手势数据字典
        object_grab_hand_joints: GRAB手势数据字典
    """
    with open(pkl_file, 'rb') as f:
        data = pickle.load(f)
    
    return data['object_unity_hand_joints'], data['object_grab_hand_joints']


def select_reference_gesture(hand_joints: np.ndarray, method: str = 'centroid') -> int:
    """
    选择参考手势
    
    Args:
        hand_joints: 手势数据 (num_samples, 21, 3)
        method: 选择方法 ('centroid', 'pca_first', 'random')
        
    Returns:
        参考手势的索引
    """
    if method == 'centroid':
        # 选择最接近所有手势质心的手势
        centroids = np.mean(hand_joints, axis=1)  # (num_samples, 3)
        overall_centroid = np.mean(centroids, axis=0)  # (3,)
        distances = np.linalg.norm(centroids - overall_centroid, axis=1)
        return np.argmin(distances)
    
    elif method == 'pca_first':
        # 选择PCA第一主成分上投影最大的手势
        flattened = hand_joints.reshape(hand_joints.shape[0], -1)  # (num_samples, 63)
        pca = PCA(n_components=1)
        pca.fit(flattened)
        projections = pca.transform(flattened)
        return np.argmax(np.abs(projections))
    
    elif method == 'random':
        return np.random.randint(0, len(hand_joints))
    
    else:
        raise ValueError(f"Unknown method: {method}")


def compute_rotation_alignment(source_joints: np.ndarray, target_joints: np.ndarray) -> np.ndarray:
    """
    计算从源手势到目标手势的旋转矩阵
    
    Args:
        source_joints: 源手势关节位置 (21, 3)
        target_joints: 目标手势关节位置 (21, 3)
        
    Returns:
        旋转矩阵 (3, 3)
    """
    # 使用Kabsch算法计算最优旋转矩阵
    # 首先将手势中心化
    source_centered = source_joints - np.mean(source_joints, axis=0)
    target_centered = target_joints - np.mean(target_joints, axis=0)
    
    # 计算协方差矩阵
    H = source_centered.T @ target_centered
    
    # SVD分解
    U, S, Vt = np.linalg.svd(H)
    
    # 计算旋转矩阵
    R = Vt.T @ U.T
    
    # 确保是右手坐标系
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = Vt.T @ U.T
    
    return R


def align_gesture_to_reference(gesture_joints: np.ndarray, reference_joints: np.ndarray) -> np.ndarray:
    """
    将手势对齐到参考手势
    
    Args:
        gesture_joints: 要对齐的手势 (21, 3)
        reference_joints: 参考手势 (21, 3)
        
    Returns:
        对齐后的手势 (21, 3)
    """
    # 计算旋转矩阵
    R = compute_rotation_alignment(gesture_joints, reference_joints)
    
    # 应用旋转
    aligned_joints = gesture_joints @ R.T
    
    return aligned_joints


def align_gestures_by_category(object_unity_hand_joints: Dict, 
                              object_grab_hand_joints: Dict,
                              reference_method: str = 'centroid') -> Tuple[Dict, Dict, Dict]:
    """
    按object_category对齐所有手势
    
    Args:
        object_unity_hand_joints: Unity手势数据
        object_grab_hand_joints: GRAB手势数据
        reference_method: 参考手势选择方法
        
    Returns:
        aligned_unity_joints: 对齐后的Unity手势
        aligned_grab_joints: 对齐后的GRAB手势
        reference_gestures: 每个类别的参考手势
    """
    aligned_unity_joints = {}
    aligned_grab_joints = {}
    reference_gestures = {}
    
    for category in object_unity_hand_joints.keys():
        print(f"处理类别: {category}")
        
        # 获取该类别的手势数据
        unity_joints = object_unity_hand_joints[category]  # (num_samples, 21, 3)
        grab_joints = object_grab_hand_joints[category]    # (num_samples, 21, 3)
        
        # 选择参考手势（从Unity数据中选择）
        if len(unity_joints) > 0:
            ref_idx = select_reference_gesture(unity_joints, reference_method)
            reference_gesture = unity_joints[ref_idx]
            reference_gestures[category] = reference_gesture
            
            print(f"  选择参考手势索引: {ref_idx}")
            
            # 对齐Unity手势
            aligned_unity = []
            for i, gesture in enumerate(unity_joints):
                if i == ref_idx:
                    # 参考手势本身不需要对齐
                    aligned_unity.append(gesture)
                else:
                    aligned_gesture = align_gesture_to_reference(gesture, reference_gesture)
                    aligned_unity.append(aligned_gesture)
            
            aligned_unity_joints[category] = np.array(aligned_unity)
            
            # 对齐GRAB手势
            aligned_grab = []
            for gesture in grab_joints:
                aligned_gesture = align_gesture_to_reference(gesture, reference_gesture)
                aligned_grab.append(aligned_gesture)
            
            aligned_grab_joints[category] = np.array(aligned_grab)
            
            print(f"  对齐完成: Unity {len(aligned_unity)} 个手势, GRAB {len(aligned_grab)} 个手势")
        else:
            print(f"  警告: {category} 类别没有Unity手势数据")
            aligned_unity_joints[category] = np.array([])
            aligned_grab_joints[category] = grab_joints
            reference_gestures[category] = None
    
    return aligned_unity_joints, aligned_grab_joints, reference_gestures


def visualize_alignment_results(original_unity: np.ndarray, 
                              aligned_unity: np.ndarray,
                              original_grab: np.ndarray,
                              aligned_grab: np.ndarray,
                              reference_gesture: np.ndarray,
                              category: str,
                              save_path: Optional[str] = None):
    """
    可视化对齐结果
    
    Args:
        original_unity: 原始Unity手势
        aligned_unity: 对齐后Unity手势
        original_grab: 原始GRAB手势
        aligned_grab: 对齐后GRAB手势
        reference_gesture: 参考手势
        category: 类别名称
        save_path: 保存路径
    """
    fig = plt.figure(figsize=(20, 12))
    
    # 原始Unity手势
    ax1 = fig.add_subplot(2, 3, 1, projection='3d')
    for i, gesture in enumerate(original_unity[:5]):  # 只显示前5个
        ax1.scatter(gesture[:, 0], gesture[:, 1], gesture[:, 2], 
                   alpha=0.6, s=20, label=f'Gesture {i}' if i < 3 else '')
    ax1.set_title(f'{category} - 原始Unity手势')
    ax1.legend()
    
    # 对齐后Unity手势
    ax2 = fig.add_subplot(2, 3, 2, projection='3d')
    for i, gesture in enumerate(aligned_unity[:5]):  # 只显示前5个
        ax2.scatter(gesture[:, 0], gesture[:, 1], gesture[:, 2], 
                   alpha=0.6, s=20, label=f'Gesture {i}' if i < 3 else '')
    ax2.scatter(reference_gesture[:, 0], reference_gesture[:, 1], reference_gesture[:, 2], 
               c='red', s=100, marker='*', label='Reference')
    ax2.set_title(f'{category} - 对齐后Unity手势')
    ax2.legend()
    
    # 原始GRAB手势
    ax3 = fig.add_subplot(2, 3, 3, projection='3d')
    for i, gesture in enumerate(original_grab[:5]):  # 只显示前5个
        ax3.scatter(gesture[:, 0], gesture[:, 1], gesture[:, 2], 
                   alpha=0.6, s=20, label=f'Gesture {i}' if i < 3 else '')
    ax3.set_title(f'{category} - 原始GRAB手势')
    ax3.legend()
    
    # 对齐后GRAB手势
    ax4 = fig.add_subplot(2, 3, 4, projection='3d')
    for i, gesture in enumerate(aligned_grab[:5]):  # 只显示前5个
        ax4.scatter(gesture[:, 0], gesture[:, 1], gesture[:, 2], 
                   alpha=0.6, s=20, label=f'Gesture {i}' if i < 3 else '')
    ax4.scatter(reference_gesture[:, 0], reference_gesture[:, 1], reference_gesture[:, 2], 
               c='red', s=100, marker='*', label='Reference')
    ax4.set_title(f'{category} - 对齐后GRAB手势')
    ax4.legend()
    
    # 对比：原始vs对齐后Unity
    ax5 = fig.add_subplot(2, 3, 5, projection='3d')
    ax5.scatter(original_unity[0, :, 0], original_unity[0, :, 1], original_unity[0, :, 2], 
               c='blue', alpha=0.6, s=20, label='原始')
    ax5.scatter(aligned_unity[0, :, 0], aligned_unity[0, :, 1], aligned_unity[0, :, 2], 
               c='red', alpha=0.6, s=20, label='对齐后')
    ax5.scatter(reference_gesture[:, 0], reference_gesture[:, 1], reference_gesture[:, 2], 
               c='green', s=100, marker='*', label='参考')
    ax5.set_title(f'{category} - Unity对齐对比')
    ax5.legend()
    
    # 对比：原始vs对齐后GRAB
    ax6 = fig.add_subplot(2, 3, 6, projection='3d')
    ax6.scatter(original_grab[0, :, 0], original_grab[0, :, 1], original_grab[0, :, 2], 
               c='blue', alpha=0.6, s=20, label='原始')
    ax6.scatter(aligned_grab[0, :, 0], aligned_grab[0, :, 1], aligned_grab[0, :, 2], 
               c='red', alpha=0.6, s=20, label='对齐后')
    ax6.scatter(reference_gesture[:, 0], reference_gesture[:, 1], reference_gesture[:, 2], 
               c='green', s=100, marker='*', label='参考')
    ax6.set_title(f'{category} - GRAB对齐对比')
    ax6.legend()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"可视化结果已保存到: {save_path}")
    
    plt.show()


def save_aligned_data(aligned_unity_joints: Dict, 
                     aligned_grab_joints: Dict, 
                     reference_gestures: Dict,
                     output_file: str):
    """
    保存对齐后的数据
    
    Args:
        aligned_unity_joints: 对齐后的Unity手势
        aligned_grab_joints: 对齐后的GRAB手势
        reference_gestures: 参考手势
        output_file: 输出文件路径
    """
    aligned_data = {
        'aligned_unity_hand_joints': aligned_unity_joints,
        'aligned_grab_hand_joints': aligned_grab_joints,
        'reference_gestures': reference_gestures
    }
    
    with open(output_file, 'wb') as f:
        pickle.dump(aligned_data, f)
    
    print(f"对齐后的数据已保存到: {output_file}")


def main():
    """主函数"""
    print("开始手势旋转对齐...")
    
    # 加载数据
    print("加载数据...")
    unity_joints, grab_joints = load_gesture_data('plot_data_tsne.pkl')
    
    # 执行对齐
    print("执行手势对齐...")
    aligned_unity, aligned_grab, references = align_gestures_by_category(
        unity_joints, grab_joints, reference_method='centroid'
    )
    
    # 保存结果
    print("保存对齐结果...")
    save_aligned_data(aligned_unity, aligned_grab, references, 'aligned_gestures.pkl')
    
    # 可视化几个类别的结果
    print("生成可视化结果...")
    categories_to_visualize = ['bowl', 'apple', 'cup']  # 选择几个类别进行可视化
    
    for category in categories_to_visualize:
        if category in unity_joints and len(unity_joints[category]) > 0:
            visualize_alignment_results(
                unity_joints[category][:10],  # 只显示前10个
                aligned_unity[category][:10],
                grab_joints[category][:10],
                aligned_grab[category][:10],
                references[category],
                category,
                f'alignment_visualization_{category}.png'
            )
    
    print("手势旋转对齐完成！")


if __name__ == "__main__":
    main()
