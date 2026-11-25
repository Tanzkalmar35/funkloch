from dataclasses import dataclass

@dataclass
class Heartbeat:
    ok: bool

@dataclass
class ChatMessage:
    chat_id: str
    origin_id: str
    msg: str

@dataclass
class JoinGroupRequest:
    chat_id: str
    origin_id: str

@dataclass
class LeaveGroupRequest:
    chat_id: str
    origin_id: str

@dataclass
class DiscoverServerRequest:
    lat: str
    long: str

@dataclass
class RegisterNewUserRequest:
    username: str
