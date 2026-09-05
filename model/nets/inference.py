import numpy as np
import torch
import torch.nn as nn
import os
from pathlib import Path
from bps_torch.bps import bps_torch
from typing import Dict, Any

from .base import NetFrame
from .encoder import MLPEncoder
from .decoder import DecoderLogitNet, DecoderPointNet2
from .utils import get_auto_device

  
dtype_mapping = {
    "torch.float32": torch.float32, # float
    "torch.float64": torch.float64, # double
    "torch.float16": torch.float16,
    "torch.int32": torch.int32,
    "torch.int64": torch.int64,
} 

class InferenceNet(nn.Module):
    def __init__(self, bps_params, encoder_subject_params, encoder_subjectobject_params):
        super().__init__()

        # ==> ENCODER OBJECT
        bps_fname = Path(bps_params["filepath"], "bps_new.npz")
        bps_dtype = dtype_mapping[bps_params["dtype"]]
        self.bps_basis = torch.from_numpy(np.load(bps_fname)["basis"]).to(bps_dtype)
        self.bps = bps_torch(bps_type="custom", custom_basis=self.bps_basis)
        
        # 添加BPS编码缓存
        self._bps_cache = {}

         # Hand branch
        self.hand_mlp = nn.Sequential(
            nn.Linear(63, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(p=0.2),
            nn.Linear(256, 256),
            nn.BatchNorm1d(256),
            nn.ReLU()
        )

        # Object branch
        self.obj_mlp = nn.Sequential(
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(p=0.2),
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU()
        )

        # Fusion + prediction head
        self.fusion_mlp = nn.Sequential(
            nn.Linear(256 * 2, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(p=0.2),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(p=0.2),
            nn.Linear(64, 1)  # output logits
        )
        self.compute_total_params()
    
    def compute_total_params(self, str="inference_net"):
      params = 0
      for p in list(self.parameters()):
          params += np.prod(list(p.size()))
      self.total_params = params
      print(f"[ {str} ] total trainable parameters : {self.total_params}")
    
    def _get_bps_cache_key(self, obj_pcl):
        """生成BPS缓存的键"""
        # 使用点云的形状和部分数据作为缓存键
        shape = obj_pcl.shape
        # 取前几个点的坐标作为键的一部分
        sample_points = obj_pcl[:min(5, shape[0]), :min(5, shape[1]), :].detach().cpu()
        return hash((shape, tuple(sample_points.flatten().tolist())))
    
    def _cached_bps_encode(self, obj_pcl):
        """带缓存的BPS编码"""
        cache_key = self._get_bps_cache_key(obj_pcl)
        
        if cache_key in self._bps_cache:
            return self._bps_cache[cache_key]
        
        # 计算BPS编码，确保在CPU上
        obj_bps = self.bps.encode(obj_pcl, feature_type=["dists"])["dists"][:, ::4].cpu()
        
        # 缓存结果（限制缓存大小）
        if len(self._bps_cache) < 100:  # 限制缓存大小
            self._bps_cache[cache_key] = obj_bps
        
        return obj_bps


    # V1
    def forward(self, hand_joints, obj_pcl):
        # 使用缓存的BPS编码
        obj_bps = self._cached_bps_encode(obj_pcl)
        hand_joints_reshaped = hand_joints.reshape(-1, 63)  # (N, 63)

        h_emb = self.hand_mlp(hand_joints_reshaped)
        o_emb = self.obj_mlp(obj_bps)

       
        fused = torch.cat([h_emb, o_emb], dim=1) 
        logit = self.fusion_mlp(fused)
        # position = self.decoder_position(enc)
 
        predictions = {"obj_logit": logit, "obj_translation": None, "fused": fused}
        return predictions
    
    def load(self, ckpt_path):
      """
      Load model, optimizer, and scheduler from the latest checkpoint
      """
      ckpt = torch.load(ckpt_path)
      self.load_state_dict(ckpt["model_state_dict"])
      print(f"[ inference model - loaded checkpoint ] {ckpt_path}")
