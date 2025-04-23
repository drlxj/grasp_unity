import numpy as np
import trimesh


data = np.load(r"C:\Users\Researcher\grasping-unity\model\session_npz_files\s13\crackerbox_8\t_0\features.npz")




obj_vertices = data["pcl"]
hand_vertices = data["subject_joints_pos_rel2wrist"]
# seq = data["seq"]
# target_obj_scores = data["target_obj_scores"]
# obj_scores = data["obj_scores"]

# print(seq)
# print(target_obj_scores)
# print(obj_scores)

obj_colors = np.tile([255, 0, 0, 255], (obj_vertices.shape[0], 1))   # 红色

thumb_color = np.array([255, 0, 0, 255])   # Red color for Thumb
index_color = np.array([0, 255, 0, 255])   # Green color for Index finger
middle_color = np.array([0, 0, 255, 255])  # Blue color for Middle finger
ring_color = np.array([255, 255, 0, 255])   # Yellow color for Ring finger
pinky_color = np.array([255, 0, 255, 255])  # Purple color for Pinky finger
root_color = np.array([0, 255, 255, 255])   # Cyan color for Root (Wrist)


finger_colors = [
    thumb_color, thumb_color, thumb_color, thumb_color,
    index_color, index_color, index_color, index_color,
    middle_color, middle_color, middle_color, middle_color,
    ring_color, ring_color, ring_color, ring_color,
    pinky_color, pinky_color, pinky_color, pinky_color
]

obj_pcl_mesh = trimesh.PointCloud(obj_vertices, obj_colors)
hand_pcl_mesh = trimesh.PointCloud(hand_vertices, finger_colors)


scene = trimesh.Scene([obj_pcl_mesh, hand_pcl_mesh])


scene.show()