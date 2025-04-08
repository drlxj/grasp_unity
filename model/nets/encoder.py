from typing import Optional, Union, Tuple, Dict
import torch
import torch.nn as nn
import numpy as np
import math

from nets.base import LinearBlock, ResidualBlock

class MLPEncoder(nn.Module):
    def __init__(self, in_dim, out_dim, n_mlp_block):
        super().__init__()
        layers = []

        # First MLP block (reducing dim)
        layers.append(nn.Linear(in_dim, out_dim))
        layers.append(nn.GELU())

        for _ in range(n_mlp_block - 1):
            layers.append(ResidualBlock(out_dim))

        self.layers = nn.Sequential(*layers)

    def forward(self, x):
        B = x.size(0)
        x = x.view(B, -1)
        return self.layers(x)

