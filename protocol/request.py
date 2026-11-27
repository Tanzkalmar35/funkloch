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

@dataclass
class MessageRecord:
    message_id: str
    chat_id: str
    origin_id: str
    msg: str
    created_at: int
    updated_at: int
    deleted_at: int | None = None

@dataclass
class CreateMessageRequest:
    request_id: str
    chat_id: str
    origin_id: str
    msg: str

@dataclass
class GetMessagesRequest:
    request_id: str
    chat_id: str

@dataclass
class UpdateMessageRequest:
    request_id: str
    message_id: str
    origin_id: str
    msg: str

@dataclass
class DeleteMessageRequest:
    request_id: str
    message_id: str
    origin_id: str
