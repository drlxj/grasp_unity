import os
from pathlib import Path
from matplotlib import pyplot as plt
import numpy as np
import torch
from .bps import encode
# from bps_torch.bps import bps_torch

class ObjectDataset(object):
  def __init__(self):
    self.file_path = os.path.join(
      Path(__file__).parent.parent,
      "files",
    )
    
    self.ds_path = os.path.join(self.file_path, f"obj_hog.npz")
    self.load_or_create_datset()
    self.bps_basis = self.ds["bps_basis"][::4]

  def load_or_create_datset(self):
     if os.path.exists(self.ds_path):
        self.ds = np.load(self.ds_path, allow_pickle=True)['ds'].item()
        print(f"Loaded dataset from {self.ds_path}")
     else:
        self.ds = self.preprocessing()
        np.savez(self.ds_path, ds=self.ds)
        print(f"Saved new dataset to {self.ds_path}")      

  # def preprocessing(self):
  #   # bps processing for each object
  #   import glob
  #   from pytorch3d.structures import Meshes
  #   from pytorch3d.io import load_ply
  #   from pytorch3d.ops import sample_points_from_meshes
    
  #   ds = {}
  #   obj_fpaths = glob.glob("files/object_meshes/*.ply")
  #   for obj_fpath in obj_fpaths:
  #     base_name = os.path.basename(obj_fpath)
  #     obj_name = base_name[:-4]

  #     verts, faces = load_ply(obj_fpath)
  #     meshes = Meshes(verts=[verts], faces=[faces])
  #     pcl = sample_points_from_meshes(meshes, num_samples=1024)
  #     ds[obj_name] = {"verts": verts, "faces": faces, "pcl": pcl}

  #   # bps_basis
  #   bps_fname = os.path.join(self.file_path, "bps_new.npz")
  #   ds["bps_basis"] = np.load(bps_fname)['basis']
  #   return ds

  def preprocessing(self):
    import glob
    import trimesh
    # bps processing for each object
    ds = {}
    obj_fpaths = glob.glob(r"C:\Users\research\Documents\Xuejing Luo\grasping-unity\python\files\object_meshes_hog/*.obj")
    count = 0
    for obj_fpath in obj_fpaths:
        base_name = os.path.basename(obj_fpath)
        obj_name = base_name[3:-4]
        obj_name = obj_name.replace("_","")
        
        # Load mesh using trimesh
        mesh = trimesh.load_mesh(obj_fpath)
        
        # Get vertices and faces
        verts = torch.tensor(mesh.vertices, dtype=torch.float32)
        faces = torch.tensor(mesh.faces, dtype=torch.long)
        
        # Sample points from mesh
        pcl = mesh.sample(1024)
        pcl = torch.tensor(pcl, dtype=torch.float32).unsqueeze(0)

        ds[obj_name] = {"verts": verts, "faces": faces, "pcl": pcl}

    # bps_basis
    bps_fname = os.path.join(self.file_path, "bps_new.npz")
    ds["bps_basis"] = np.load(bps_fname)['basis']
    return ds

  def get_pcl(self, obj_names, rot_matrices):
        """
        - obj_names: a list of str
        - rot_matrices: (N, 3, 3) torch.Tensor of rotation_matrix in unity coordination
        """
        pcl_python = torch.cat([self.ds[name]["pcl"] for name in obj_names], dim=0) #(n_obj, n_points, 3)
        rotated_pcl_python = torch.einsum("nij, nmj -> nmi", rot_matrices, pcl_python)
        return rotated_pcl_python

  def get_bps(self, obj_names, rot_matrices):
        """
        - obj_names: a list of str
        - rot_matrices: (N, 3, 3) torch.Tensor of rotation_matrix
        """
        rotated_obj_pcl = self.get_pcl(obj_names=obj_names, rot_matrices=rot_matrices)
        rotated_obj_bps = encode(
            rotated_obj_pcl.detach().cpu().numpy(),
            bps_arrangement="custom",
            custom_basis=self.bps_basis,
            n_jobs=1,
            verbose=False,
        )
        # bps = bps_torch(bps_type="custom", custom_basis=self.bps_basis)
        # bps_encode = bps.encode(rotated_obj_pcl.reshape(-1, 3), feature_type=['dists'])["dists"]
        # print(rotated_obj_bps, bps_encode)
        return rotated_obj_bps

  # Function to plot point clouds
  def plot_point_cloud(self, ax, points, title, coord='python', color='blue'):
      ax.scatter(points[:, 0], points[:, 1], points[:, 2], c=color)
      ax.set_title(title)

  
  def visualize_obj(self, obj_names, obj_pcls, hand_joints):
    """
    - obj_names: a list of str
    - rot_matrices: (N, 3, 3) torch.Tensor of rotation_matrix
    """

    def plot_object(ax, pcl):
      ax.scatter(pcl[:, 0], pcl[:, 1], pcl[:, 2], c='blue')

    def plot_hand(ax, hand_joints):
       for finger in range(5):
          ax.plot(
              hand_joints[finger * 4 : (finger + 1) * 4, 0],
              hand_joints[finger * 4 : (finger + 1) * 4, 1],
              hand_joints[finger * 4 : (finger + 1) * 4, 2],
              c="r",
              label="Hand Keypoints",
          )
          ax.scatter(
              hand_joints[:, 0],
              hand_joints[:, 1],
              hand_joints[:, 2],
              c="r",
              label="Hand Keypoints",
          )
    
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    for i, obj_name in enumerate(obj_names):
      if obj_name == "stanfordbunny":
        plot_object(ax, obj_pcls[i].detach().cpu().numpy())
    
    if hand_joints is not None:
       plot_hand(ax=ax, hand_joints=hand_joints.detach().cpu().numpy())

    # ax.view_init(elev=0., azim=0)
    # Set labels
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    plt.savefig(f"results/check.png")
    plt.show()
    plt.close(fig)