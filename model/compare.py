import numpy as np

unity_data = np.load(r"C:\Users\Researcher\grasping-unity\model\session_npz_files\s1\apple_1\t_0\features.npz")
# grab_data = np.load(r"C:\Users\Researcher\grasping-unity\model\teapot_s7_t0.npz")
grab_data = np.load(r"C:\Users\Researcher\grasping-unity\model\s7_apple_eat_1_t_9.npz")

unity_object_pcl = unity_data['pcl']
unity_hand_joints = unity_data['subject_joints_pos_rel2wrist']

grab_object_pcl = grab_data['object_pointcloud'] - grab_data['object_translation']
grab_hand_joints = grab_data['subject_joints_pos_rel2wrist'] 

import trimesh

unity_object_pcl_trimesh = trimesh.PointCloud(unity_object_pcl)
unity_hand_joints_trimesh = trimesh.PointCloud(unity_hand_joints)
grab_object_pcl_trimesh = trimesh.PointCloud(grab_object_pcl)
grab_hand_joints_trimesh = trimesh.PointCloud(grab_hand_joints)
scene = trimesh.Scene([unity_object_pcl_trimesh, grab_object_pcl_trimesh])
scene.show()