import pickle
import socket
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


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("Connection closed while reading frame")
        data.extend(chunk)
    return bytes(data)


def recv_frame(sock: socket.socket) -> Any:
    if _recv_exact(sock, len(HEADER)) != HEADER:
        raise ValueError("Invalid frame header")

    length_bytes = bytearray()
    while True:
        char = _recv_exact(sock, 1)
        if char == b":":
            break
        if not char.isdigit() or len(length_bytes) >= 10:
            raise ValueError("Invalid frame length")
        length_bytes.extend(char)

    try:
        payload_length = int(length_bytes)
    except ValueError as exc:
        raise ValueError("Invalid frame length") from exc

    if payload_length > MAX_FRAME_SIZE:
        raise ValueError("Frame too large")

    payload = _recv_exact(sock, payload_length)
    return pickle.loads(payload)
