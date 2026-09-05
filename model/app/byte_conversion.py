import struct
import numpy as np

class SequentialByteDecoder:
    def __init__(self, arr: bytes):
        self.arr = arr
        self.idx = 0

    def get_int(self) -> int:
        if self.idx + 4 > len(self.arr):
            raise struct.error(f"Not enough bytes for int. Required: 4, Available: {len(self.arr) - self.idx}")
        x = struct.unpack('i', self.arr[self.idx:self.idx + 4])[0]
        self.idx += 4
        return x
    
    def get_unsigned_long_long(self) -> int:
        x = struct.unpack('Q', self.arr[self.idx:self.idx + 8])[0]
        self.idx += 8
        return x

    def get_vector(self, dim=3) -> np.array:
        required_bytes = 4 * dim
        if self.idx + required_bytes > len(self.arr):
            raise struct.error(f"Not enough bytes for vector. Required: {required_bytes}, Available: {len(self.arr) - self.idx}")
        x =  struct.unpack(f"{dim}f", self.arr[self.idx:self.idx + required_bytes])
        self.idx += required_bytes
        return np.array(x, dtype=np.float32)

    # Change from (x, y, z, w) to (w, x, y, z)
    def get_quaternion(self) -> np.array:
        required_bytes = 4 * 4  # 4 floats * 4 bytes each
        if self.idx + required_bytes > len(self.arr):
            raise struct.error(f"Not enough bytes for quaternion. Required: {required_bytes}, Available: {len(self.arr) - self.idx}")
        x, y, z, w = struct.unpack("4f", self.arr[self.idx : self.idx + required_bytes])
        self.idx += required_bytes
        return np.array([x, y, z, w], dtype=np.float32)

    def get_vector_array(self, n, dim=3):
        out = np.empty((n, dim), dtype=np.float32)
        for i in range(n):
            out[i] = self.get_vector(dim)
        
        return out
    
    def get_quaternion_array(self, n):
        return self.get_vector_array(n, dim=4)

class SequentialByteEncoder:
    def __init__(self):
        self.bytes = None
    
    def _add_bytes(self, x: bytes):
        if self.bytes is None:
            self.bytes = x
        else:
            self.bytes += x
    
    def get_bytes(self) -> bytes:
        return self.bytes
    
    def add_vector(self, x: np.array):
        b = struct.pack(F"{len(x)}f", *list(x))
        self._add_bytes(b)

    def add_vector_list(self, x: np.array):
        x = x.astype(np.float32).flatten() 
        b = struct.pack(f"{len(x)}f", *list(x))
        self._add_bytes(b)
    
    def add_quaternion(self, x: np.array):
        self.add_vector(x)
        
    def add_int(self, x: int):
        b = struct.pack("i", x)
        self._add_bytes(b)

    def add_float(self, x: float):
        b = struct.pack("f", x)
        self._add_bytes(b)
