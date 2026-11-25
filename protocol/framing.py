import pickle
import struct
from typing import Any


HEADER = struct.Struct("!I")
MAX_FRAME_SIZE = 16 * 1024 * 1024


def serialize(message: Any) -> bytes:
    return pickle.dumps(message)


def deserialize(data: bytes) -> Any:
    return pickle.loads(data)
