import pickle
from typing import Any

HEADER = b"Funkloch:"
MAX_FRAME_SIZE = 16 * 1024 * 1024


def serialize(message: Any) -> bytes:
    payload = pickle.dumps(message)
    return HEADER + str(len(payload)).encode("ascii") + b":" + payload


def deserialize(data: bytes) -> Any:
    if not data.startswith(HEADER):
        raise ValueError("Invalid frame header")

    length_end = data.find(b":", len(HEADER))
    if length_end == -1:
        raise ValueError("Missing frame length delimiter")

    try:
        payload_length = int(data[len(HEADER) : length_end])
    except ValueError as exc:
        raise ValueError("Invalid frame length") from exc

    payload = data[length_end + 1 :]
    if len(payload) != payload_length:
        raise ValueError("Frame payload length does not match header")

    return pickle.loads(payload)
