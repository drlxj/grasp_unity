# import numpy as np
# from scipy.spatial.transform import Rotation as R

# # Define the T_camera transformation matrix
# T_camera = np.array([
#     [1, 0, 0, 0],
#     [0, 0, -1, 0],
#     [0, 1, 0, 0],
#     [0, 0, 0, 1]
# ])

# # Define the T_unity2python transformation matrix
# T_unity2python = np.array([
#     [-1, 0, 0, 0],
#     [0, 1, 0, 0],
#     [0, 0, 1, 0],
#     [0, 0, 0, 1]
# ])

# # 165.46
# # -14.54

# # Step 1: Convert Unity's Euler angles to a quaternion
# euler_angles = [90, -50, 0]  # Unity's rotation in degrees
# euler_angles[0] += 180

# # Step 2: Convert Unity's Euler angles to matrix_unity (4x4 transformation matrix)
# rotation_matrix_unity = R.from_euler('xyz', euler_angles, degrees=True).as_matrix()  # Convert to 3x3 rotation matrix
# matrix_unity = np.eye(4)  # Initialize a 4x4 identity matrix
# matrix_unity[:3, :3] = rotation_matrix_unity  # Embed the 3x3 rotation matrix into the 4x4 matrix

# # Step 3: Reverse the transformation to calculate matrix_python
# T_unity2python_inv = np.linalg.inv(T_unity2python)  # Inverse of T_unity2python
# matrix_python = T_unity2python_inv @ np.linalg.inv(T_camera) @ matrix_unity @ T_unity2python_inv

# # Step 4: Extract the 3x3 rotation matrix from matrix_python
# object_rotation_matrix = matrix_python[:3, :3]

# # Step 5: Convert to nested list format with 15 decimal places
# object_rotation_matrix_list = [[round(value, 15) for value in row] for row in object_rotation_matrix]

# # Print the result
# print("object_rotation_matrix:")
# print(object_rotation_matrix_list)

import torch
from ..model.app.misc import quaternion_to_matrix

R_unity2python = torch.Tensor(
    [
        [-1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0,],
        [0.0, 0.0, 1.0,],
    ]
)
R_camera = torch.Tensor(
    [
        [0.0, 0.0, 1.0],
        [-1.0, 0.0, 0.0],
        [0.0, -1.0, 0.0],
    ]
)
T_quat_unity2python = torch.eye(4)
T_quat_unity2python[1:, 1:] = -R_unity2python

obj_quats_unity =  # (n_objects, 4) TODO: reading from a directory
obj_quats_python = torch.einsum("ij,nj->ni", T_quat_unity2python, obj_quats_unity)

obj_rot_matrices = quaternion_to_matrix(obj_quats_python) # (n_objects, 3, 3)
obj_rot_matrices = torch.einsum("ik,nkj->nij", R_camera, obj_rot_matrices)


# TODO: create json file that contains for each object what are the rotation matrix candidates in python coordinates


