import numpy as np
import torch
import torch.nn as nn
import os
from pathlib import Path

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

        self.model = nn.Sequential(
            nn.Linear(1084, 512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, 1),  # Binary classification (graspable or not)
            nn.Sigmoid()
        )
        self.compute_total_params()
    
    def compute_total_params(self, str="inference_net"):
      params = 0
      for p in list(self.parameters()):
          params += np.prod(list(p.size()))
      self.total_params = params
      print(f"[ {str} ] total trainable parameters : {self.total_params}")

    
    def forward(self, hand_joints, obj_bps):
        # obj_bps = self.bps.encode(obj_pcl, feature_type=["dists"])["dists"]
        x = torch.cat([obj_bps, hand_joints], dim=1)
        # enc_hand_obj = self.encoder_sbjobj(x)
        # logit = self.decoder_logit(enc_hand_obj)
        logit = self.model(x)
        predictions = {"obj_logit": logit, "obj_translation": torch.zeros(logit.shape[0], 3)}
        return predictions
    
    def load(self, ckpt_path):
      """
      Load model, optimizer, and scheduler from the latest checkpoint
      """
      ckpt = torch.load(ckpt_path)
      self.load_state_dict(ckpt["model_state_dict"])
      print(f"[ inference model - loaded checkpoint ] {ckpt_path}")

# class InferenceNet(NetFrame):
#   def __init__(self, config):
#     super().__init__(config)
#     self.file_path = os.path.join(
#       Path(__file__).parent.parent,
#       "files",
#     )
#     self.encoder_net = MLPEncoder(in_dim=1084, out_dim=256, n_mlp_block=4)
#     # self.encoder_net = TransformerEncoder(config["encoder"])
#     self.logit_net = nn.Sequential(
#       nn.Linear(256, 1),
#       nn.Sigmoid()
#     )
#     self.regression_net = nn.Sequential(
#       nn.Linear(256, 3),
#     )
#     self.lambda_regr = 1e-1  # weight for regression net
#     self.lambda_l2 = 1e-2 # regularization strength
#     self._set_device(config)
#     self.compute_total_params()

#   def compute_total_params(self, str="inference_net"):
#       params = 0
#       for p in list(self.parameters()):
#           params += np.prod(list(p.size()))
#       self.total_params = params
#       print(f"[ {str} ] total trainable parameters : {self.total_params}")

#   def _set_device(self, config):
#     """
#     Set device for the model. 
#     If device is not specified in the config, it will be automatically set.
#     config (dict): Configuration dictionary for the amortizer model.
#     """
#     if "device" not in config:
#       self.given_device = get_auto_device()
#     elif config["device"] is None:
#       self.given_device = get_auto_device()
#     else:
#       self.given_device = torch.device(config["device"])
#     self.to(self.given_device)
#   def forward(self, inputs):
#     B = inputs["obj_bps"].size(0)
#     x = torch.cat([inputs["obj_bps"], inputs["hand_obs"]], dim=1)
#     # x = torch.cat([inputs["obj_pcl"], inputs["hand_obs"].reshape((B, -1, 3))], dim=1)
#     cond = self.encoder_net(x) # cond: (batch_sz, d_latents)
#     prob = self.logit_net(cond)
#     param_hat = self.regression_net(cond)
#     return prob, param_hat
  
#   def infer(self, inputs, n_sample=100, infer_type="mode", return_samples=False):
#     """
#     Infer the posterior distribution of the parameters given the static and trajectory data.
#     inputs (dict)
#     n_sample (int, optional): Number of posterior samples, default is 100.
#     infer_type (str, optional): Type of inference from distribution ("mode", "mean", "median"), default is "mode".
#     return_samples (bool, optional): Whether to return posterior samples, default is False.
#     ---
#     outputs (tuple): Tuple containing inferred parameters (torch.Tensor) and posterior samples (torch.Tensor).
#     """
#     B = inputs["obj_bps"].size(0)
#     x = torch.cat([inputs["obj_bps"], inputs["hand_obs"]], dim=1)
#     # x = torch.cat([inputs["obj_pcl"], inputs["hand_obs"].reshape((B, -1, 3))], dim=1)
#     cond = self.encoder_net(x)
#     param_hat = self.regression_net(cond)
#     return param_hat
  
#   def load(self):
#     """
#     Load model, optimizer, and scheduler from the latest checkpoint
#     """
#     ckpt_path = os.path.join(self.file_path, "model.pt")
#     ckpt = torch.load(ckpt_path, map_location=self.device.type)
#     self.load_state_dict(ckpt["model_state_dict"])
#     print(f"[ inference model - loaded checkpoint ] {ckpt_path}")