from protocol.framing import deserialize
from protocol.request import Heartbeat
from protocol.request import ChatMessage
from protocol.request import JoinGroupRequest
from protocol.request import LeaveGroupRequest
from protocol.request import DiscoverServerRequest
from protocol.request import RegisterNewUserRequest
from typing import Any


class MessageHandler:
    def __init__():
        print("Init-ing")

    def handle(self, msg: Any) -> Any:
        match deserialize(msg):
            case Heartbeat(ok=ok):
                return self.handle_heartbeat(ok)
            case ChatMessage(chat_id=chat_id, origin_id=origin_id, msg=msg):
                return self.handle_chat_message(chat_id, origin_id, msg)
            case JoinGroupRequest(chat_id=chat_id, origin_id=origin_id):
                return self.handle_join_group_request(chat_id, origin_id)
            case LeaveGroupRequest(chat_id=chat_id, origin_id=origin_id):
                return self.handle_leave_group_request(chat_id, origin_id)
            case DiscoverServerRequest(lat=lat, long=long):
                return self.handle_discover_server_request(lat, long)
            case RegisterNewUserRequest(username=username):
                return self.handle_register_user_request(username)

    def handle_heartbeat(self, ok: bool) -> Any:
        print(f"Is heartbeat: {ok}")

    def handle_chat_message(self, chat_id: str, origin_id: str, msg: str) -> Any:
        print(f"Is chat message: chat={
            chat_id}, origin_id={origin_id}, msg={msg}")

    def handle_join_group_request(self, chat_id: str, origin_id: str) -> Any:
        print(f"Is join group request: chat={chat_id}, origin_id={origin_id}")

    def handle_leave_group_request(self, chat_id: str, origin_id: str) -> Any:
        print(f"Is leave group request: chat={chat_id}, origin_id={origin_id}")

    def handle_discover_server_request(self, lat: float, long: float) -> Any:
        print(f"Is discover server request: lat={lat}, long={long}")

    def handle_register_user_request(self, username: str) -> Any:
        print(f"Is new user request: username={username}")

    # def send(self):
    #     assert self.server_address is not None, "This should never occur!"
    #     self.socket.sendto(str.encode("message"), self.server_address)
    #
    # def receive(self):
    #     while True:
    #         try:
    #             msg = self.socket.recv(
    #                 DEFAULT_BUFFER_SIZE).decode("utf8")
    #
    #             # Handle
    #             # self.handle_incoming_msg(msg)
    #         except OSError as e:
    #             self.logger.error(f"Receive-loop stopped: {e}")
    #             break
