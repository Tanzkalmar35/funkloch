from dataclasses import dataclass

@dataclass
class StatusResponse:
    ok: bool
    msg: str

@dataclass
class DiscoverServerResponse:
    remote_addr: str
    port: int

@dataclass
class RegisterNewUserResponse:
    user_id: str
