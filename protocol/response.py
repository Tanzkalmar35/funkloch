from dataclasses import dataclass, field

from protocol.request import MessageRecord


@dataclass
class StatusResponse:
    ok: bool
    msg: str


@dataclass
class DiscoverServerResponse:
    ok: bool
    remote_addr: str
    port: int


@dataclass
class RegisterNewUserResponse:
    user_id: str

@dataclass
class MessageResponse:
    request_id: str
    ok: bool
    message: MessageRecord | None = None
    error: str | None = None

@dataclass
class MessagesResponse:
    request_id: str
    ok: bool
    messages: list[MessageRecord] = field(default_factory=list)
    error: str | None = None

@dataclass
class MessageEvent:
    kind: str
    message: MessageRecord
