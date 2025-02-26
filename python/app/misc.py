import numpy as np
import torch
from math import sin, cos, atan2, asin
import matplotlib.pyplot as plt


def visualize_hand_obs(fig, hand_obs):
    """
    hand_obs: Tensor (n_joints, 3)
    """
    def plot_joints(ax, joints):
      # ax.scatter(joints[:, 0], joints[:, 1], joints[:, 2], c='r')
      for i in range(5):
          finger_joints = np.concatenate([np.zeros((1, 3)), joints[4*i:4*(i+1)]], axis=0)
          ax.plot(finger_joints[:, 0], finger_joints[:, 1], finger_joints[:, 2])
      x_min, x_max = joints[:, 0].min(), joints[:, 0].max()
      y_min, y_max = joints[:, 1].min(), joints[:, 1].max()
      z_min, z_max = joints[:, 2].min(), joints[:, 2].max()
      
      # Calculate ranges
      x_range = x_max - x_min
      y_range = y_max - y_min
      z_range = z_max - z_min
      
      # Find the maximum range
      max_range = max(x_range, y_range, z_range)
      
      # Calculate the new limits
      x_mid = (x_max + x_min) / 2
      y_mid = (y_max + y_min) / 2
      z_mid = (z_max + z_min) / 2
      x_limits = (x_mid - max_range / 2, x_mid + max_range / 2)
      y_limits = (y_mid - max_range / 2, y_mid + max_range / 2)
      z_limits = (z_mid - max_range / 2, z_mid + max_range / 2)
      ax.set_xlim(x_limits)
      ax.set_ylim(y_limits)
      ax.set_zlim(z_limits)

      # Set labels
      ax.set_xlabel("x")
      ax.set_ylabel("y")
      ax.set_zlabel("z")

    ax = fig.add_subplot(221, projection='3d')
    plot_joints(ax, hand_obs.detach().cpu().numpy())
    ax.view_init(elev=10., azim=-180)

    ax = fig.add_subplot(222, projection='3d')
    plot_joints(ax, hand_obs.detach().cpu().numpy())
    ax.view_init(elev=10., azim=-90)
    
    ax = fig.add_subplot(223, projection='3d')
    plot_joints(ax, hand_obs.detach().cpu().numpy())
    ax.view_init(elev=90., azim=-180)

    ax = fig.add_subplot(224, projection='3d')
    plot_joints(ax, hand_obs.detach().cpu().numpy())
    ax.view_init(elev=90., azim=-90)

def quaternion_to_matrix(quats):
    """
    quats: (n_objects, 4) with last-dimension with the order of (w, x, y, z)
    """
    w, x, y, z = torch.unbind(quats, -1)
    two_s = 2.0 / (quats * quats).sum(-1)

    o = torch.stack(
        (
            1 - two_s * (y * y + z * z),
            two_s * (x * y - z * w),
            two_s * (x * z + y * w),
            two_s * (x * y + z * w),
            1 - two_s * (x * x + z * z),
            two_s * (y * z - x * w),
            two_s * (x * z - y * w),
            two_s * (y * z + x * w),
            1 - two_s * (x * x + y * y),
        ),
        -1,
    )
    return o.reshape(quats.shape[:-1] + (3, 3))

def quaternion_multiply(q1, q2):
    """
    multiplies two quaternions
    """
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2

    w = w1*w2 - x1*x2 - y1*y2 - z1*z2
    x = w1*x2 + x1*w2 + y1*z2 - z1*y2
    y = w1*y2 + y1*w2 + z1*x2 - x1*z2 
    z = w1*z2 + z1*w2 + x1*y2 - y1*x2
    return [x, y, z, w]

def euler_from_quaternion(x, y, z, w):
    """
    Convert a quaternion into euler angles (roll, pitch, yaw)
    roll is rotation around x in radians (counterclockwise)
    pitch is rotation around y in radians (counterclockwise)
    yaw is rotation around z in radians (counterclockwise)
    """
    ysqr = y * y

    t0 = +2.0 * (w * x + y * z)
    t1 = +1.0 - 2.0 * (x * x + ysqr)
    X = atan2(t0, t1)

    t2 = +2.0 * (w * y - z * x)
    t2 = +1.0 if t2 > +1.0 else t2
    t2 = -1.0 if t2 < -1.0 else t2
    Y = asin(t2)

    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (ysqr + z * z)
    Z = atan2(t3, t4)

    return np.array((X, Y, Z), dtype=np.float32) # in radians

def quaternion_from_euler(roll, pitch, yaw):
    cy = cos(yaw * 0.5)
    sy = sin(yaw * 0.5)
    cr = cos(roll * 0.5)
    sr = sin(roll * 0.5)
    cp = cos(pitch * 0.5)
    sp = sin(pitch * 0.5)

    w = cy * cr * cp + sy * sr * sp
    x = cy * sr * cp - sy * cr * sp
    y = cy * cr * sp + sy * sr * cp
    z = sy * cr * cp - cy * sr * sp
    
    return np.array((x, y, z, w), dtype=np.float32)

def hand_pose_sim_to_unity(x: np.array) -> np.array:
    x = np.roll(x, -1)

    x_new = np.zeros_like(x)
    x_new[:, 0] =  x[:, 0]
    x_new[:, 1] = -x[:, 1]
    x_new[:, 2] = -x[:, 2]
    x_new[:, 3] =  x[:, 3]

    return x_new

# +x: yaw turining right
# +y: rotating toward right
# +z: rotating downward
def orientation_sim_to_unity(x: np.array) -> np.array:
    x = np.roll(x, -1)
    x_new = np.empty_like(x)
    x_new[2] = -x[0]
    x_new[0] =  x[1]
    x_new[1] = -x[2]
    x_new[3] = x[3]

    return x_new

def hand_rotation_sim_to_unity(x: np.array):
    rot_x_pos = [0.7071, 0.0, 0.0, 0.7071] # rotate 90 degrees around the X-axis
    rot_z_pos = [0.0, 0.0, 0.7071, 0.7071] # rotate 90 degrees around the Z-axis

    x = quaternion_multiply(x, rot_x_pos)
    x = quaternion_multiply(x, rot_z_pos)
    return x

def translation_sim_to_unity(x: np.array):
    out = np.empty_like(x)
    out[0] = -x[1]
    out[1] = x[2]
    out[2] = x[0]
    return out

def joint_rotation_to_global(x: np.array, hand_root_rotation: np.array):
    out = np.empty_like(x)

    for i in range(out.shape[0]):
        out[i] = quaternion_multiply(hand_root_rotation, x[i])
    
    return out