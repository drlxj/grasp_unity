import numpy as np
from dataclasses import dataclass

from .objects import ObjectType
from .byte_conversion import SequentialByteDecoder, SequentialByteEncoder

# unity -> python
@dataclass
class TelemetryMessage:
    N_JOINTS = 20

    telemetry_packet_idx: int

    hand_root_orientation: np.array # (4) quaternion
    hand_root_position: np.array # (3) vector

    hand_joint_position: np.array # (N_JOINTS, 3) vectors

    object_count: int
    object_types: list
    # object_idxs: list
    object_positions: np.array # (object_count, 3) vector
    object_orientations: np.array # (object_count, 4) quaternion

    @staticmethod
    def from_bytes(data: bytes):
        decoder = SequentialByteDecoder(data)
        telemetry_packet_idx = decoder.get_unsigned_long_long()

        hand_root_orientation = decoder.get_quaternion()
        hand_root_position = decoder.get_vector()

        hand_joint_position = decoder.get_vector_array(TelemetryMessage.N_JOINTS)
        
        object_count = decoder.get_int()
        object_positions = None if object_count == 0 else np.empty((object_count, 3), dtype=np.float32)
        object_orientations = None if object_count == 0 else np.empty((object_count, 4), dtype=np.float32)
        object_types = []
        # object_idxs = []
        for i in range(object_count):
            object_type_id = decoder.get_int()
            obj_type = ObjectType(object_type_id)
            object_types.append(obj_type.name.lower().replace("_", ""))
            # object_idxs.append(decoder.get_int())
            object_orientations[i] = decoder.get_quaternion()
            object_positions[i] = decoder.get_vector()

            
        
        return TelemetryMessage(telemetry_packet_idx, 
                                hand_root_orientation, hand_root_position, 
                                hand_joint_position,
                                object_count, 
                                object_types, 
                                # object_idxs,
                                object_positions, object_orientations)

# python -> unity
@dataclass
class CommandMessage:
    object_count: int
    confidence_score: list
    object_position: np.array # (object_count, 3) vector3
    # hand_root_position: np.array # (3) vector

    def to_bytes(self) -> bytes:
        encoder = SequentialByteEncoder()
        encoder.add_int(self.object_count)

        # for i in range(self.object_count):
        #     encoder.add_int(self.object_idxs[i])

        for i in range(self.object_count):
            encoder.add_float(self.confidence_score[i])

        
        # for i in range(self.object_count):
        #     encoder.add_float(self.object_position[i])
        encoder.add_vector_list(self.object_position)

        # encoder.add_vector(self.hand_root_position)

        return encoder.get_bytes()
        