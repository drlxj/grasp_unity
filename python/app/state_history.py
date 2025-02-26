import numpy as np
from dataclasses import dataclass
from .messages import TelemetryMessage

@dataclass
class StateHistory:
    joint_orientations: np.array
    hand_root_orientations: np.array
    hand_root_positions: np.array

    object_orientations: np.array
    object_positions: np.array

    object_cls: np.array

    current_length: int
    n_frames: int

    def __init__(self, n_frames=48, n_object=6, n_joints=TelemetryMessage.N_JOINTS):
        self.joint_orientations = np.zeros((n_frames, n_joints, 4), dtype=np.float32)
        self.hand_root_orientations = np.zeros((n_frames, 4), dtype=np.float32)
        self.hand_root_positions = np.zeros((n_frames, 3), dtype=np.float32)

        self.object_orientations = np.zeros((n_frames, n_object, 4), dtype=np.float32)
        self.object_positions = np.zeros((n_frames, n_object, 3), dtype=np.float32)
        
        self.object_cls = None

        self.current_length = 0
        self.n_frames = n_frames

    def update_from_telemetry_message(self, message: TelemetryMessage):
        self.joint_orientations = np.roll(self.joint_orientations, 1, axis=0)
        self.hand_root_orientations = np.roll(self.hand_root_orientations, 1, axis=0)
        self.hand_root_positions = np.roll(self.hand_root_positions, 1, axis=0)
        self.object_orientations = np.roll(self.object_orientations, 1, axis=0)
        self.object_positions = np.roll(self.object_positions, 1, axis=0)

        self.joint_orientations[0] = message.joint_orientation
        self.hand_root_orientations[0] = message.hand_root_orientation
        self.hand_root_positions[0] = message.hand_root_position
        self.object_orientations[0] = message.object_orientations
        self.object_positions[0] = message.object_positions
        
        self.current_length += 1

    def is_complete(self):
        return self.current_length >= self.n_frames
