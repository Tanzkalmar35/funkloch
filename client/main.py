import copy
import logging
import os
import socket
import uuid
from collections.abc import Callable
from queue import Empty, Queue
from threading import Lock, Thread
from typing import Any

from protocol import framing, request, response

REQUEST_TIMEOUT = 5.0


def _set_logging_format():
    logging.basicConfig(format="[%(levelname)-.1s] %(name)s: %(message)s", level=logging.DEBUG)


class Client:
    def __init__(self, username: str, lat: int, lon: int):
        super().__init__()
        my_host = socket.gethostname()
        my_ip = socket.gethostbyname(my_host)

        self.logger = logging.getLogger(f"Client_{os.getpid()} ({my_ip})")
        self.logger.setLevel(logging.DEBUG)

        self.lat = f"{lat}"
        self.lon = f"{lon}"
        self.username = username

        self.client_tcp_socket: socket.socket | None = None

        self.on_message_callback: Callable[[request.ChatMessage], None] | None = None
        self.on_message_event_callback: Callable[[response.MessageEvent], None] | None = None

        # TODO: necessary?
        self.chat_message_queue: list[request.ChatMessage] = []
        self.message_queue_lock: Lock = Lock()

        self._pending: dict[str, Queue] = {}
        self._pending_lock = Lock()
        self._send_lock = Lock()

    def _discover_server(self, broadcast_ip: str, discovery_port: int, timeout_s: float) -> response.DiscoverServerResponse:
        BUFFER_SIZE = 1024

        self.logger.info(f"Broadcasting server discovery {broadcast_ip}:{discovery_port} (timeout = {timeout_s} s)")

        discovery_message = framing.serialize(request.DiscoverServerRequest(self.lat, self.lon))

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as broadcast_socket:
            broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            broadcast_socket.settimeout(timeout_s)

            broadcast_socket.sendto(discovery_message, (broadcast_ip, discovery_port))

            try:
                while True:
                    data, (server_ip, server_port) = broadcast_socket.recvfrom(BUFFER_SIZE)

                    try:
                        discovery_response: response.DiscoverServerResponse = framing.deserialize(data)
                        self.logger.debug(
                            f"Broadcast response from {server_ip}:{server_port}: "
                            f"{discovery_response.remote_addr}:{discovery_response.port}: "
                            f"{'OK' if discovery_response.ok else 'NOK'}"
                        )
                        return discovery_response
                    except ValueError:
                        self.logger.debug(f"Unrecognized response during discovery from {server_ip}:{server_port}")

            except TimeoutError:
                self.logger.debug("Timeout for broadcast response.")
                return response.DiscoverServerResponse(False, "", 0)

    def _handle_received_frame(self, frame):
        if isinstance(frame, request.ChatMessage):
            if self.on_message_callback is not None:
                self.on_message_callback(frame)
            with self.message_queue_lock:
                self.chat_message_queue.append(frame)
        elif isinstance(frame, response.MessageEvent):
            if self.on_message_event_callback is not None:
                self.on_message_event_callback(frame)
        elif isinstance(frame, (response.MessageResponse, response.MessagesResponse)):
            with self._pending_lock:
                pending = self._pending.get(frame.request_id)
            if pending is not None:
                pending.put(frame)
            else:
                self.logger.warning(f"Unexpected response: {frame}")
        else:
            self.logger.warning(f"Frame handling not implemented for {frame}.")

    def _receive_loop(self):
        assert self.client_tcp_socket is not None, "Socket not initialized. No TCP connection established."

        while True:
            try:
                frame = framing.recv_frame(self.client_tcp_socket)
            except Exception as e:
                self.logger.error(f"Receive-loop stopped: {e}")  # TODO: propagate error
                break

            try:
                self.logger.info(f"Server Response: {frame}")
                self._handle_received_frame(frame)
            except Exception as e:
                self.logger.error(f"Unexpected failure in receive-loop: {e}")  # TODO: propagate error

    def _send_frame(self, frame: Any):
        assert self.client_tcp_socket is not None, "Socket not initialized. No TCP connection established."
        with self._send_lock:
            self.client_tcp_socket.sendall(framing.serialize(frame))

    def _request(self, frame: Any) -> Any:
        request_id = uuid.uuid4().hex
        frame.request_id = request_id
        reply: Queue = Queue()

        with self._pending_lock:
            self._pending[request_id] = reply

        try:
            self._send_frame(frame)
            try:
                return reply.get(timeout=REQUEST_TIMEOUT)
            except Empty as exc:
                raise TimeoutError(f"Request {request_id} timed out") from exc
        finally:
            with self._pending_lock:
                self._pending.pop(request_id, None)

    def send(self, chat_id: str, message: str):
        self._send_frame(request.ChatMessage(chat_id, self.username, message))

    def create_message(self, chat_id: str, message: str) -> request.MessageRecord:
        reply = self._request(
            request.CreateMessageRequest("", chat_id, self.username, message)
        )
        if not reply.ok or reply.message is None:
            raise RuntimeError(reply.error or "create_message failed")
        return reply.message

    def get_messages(self, chat_id: str) -> list[request.MessageRecord]:
        reply = self._request(request.GetMessagesRequest("", chat_id))
        if not reply.ok:
            raise RuntimeError(reply.error or "get_messages failed")
        return reply.messages

    def update_message(self, message_id: str, message: str) -> request.MessageRecord:
        reply = self._request(
            request.UpdateMessageRequest("", message_id, self.username, message)
        )
        if not reply.ok or reply.message is None:
            raise RuntimeError(reply.error or "update_message failed")
        return reply.message

    def delete_message(self, message_id: str) -> request.MessageRecord:
        reply = self._request(
            request.DeleteMessageRequest("", message_id, self.username)
        )
        if not reply.ok or reply.message is None:
            raise RuntimeError(reply.error or "delete_message failed")
        return reply.message

    def get_latest_messages(self) -> list[request.ChatMessage]:  # TODO: Add callback function?
        """If no callback is registered: deepcopy, return and clear and all received messages since the last call."""

        queue_copy = []
        with self.message_queue_lock:
            queue_copy = copy.deepcopy(self.chat_message_queue)
            self.chat_message_queue.clear()
        return queue_copy

    def add_message_callback(self, on_message: Callable[[request.ChatMessage], None]):
        """Add a function to be called after the reception of a chat message."""

        self.on_message_callback = on_message

    def add_message_event_callback(self, on_event: Callable[[response.MessageEvent], None]):
        """Add a function to be called after a message is created, updated or deleted."""

        self.on_message_event_callback = on_event

    def _start_tcp_connection(self, server_ip: str, port: int):
        self.logger.info(f"Establishing TCP connection: {server_ip}:{port}")

        self.client_tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client_tcp_socket.connect((server_ip, port))

        receive_thread = Thread(target=self._receive_loop)
        receive_thread.start()

    def join_group_request(self, group_id: str):
        raise Exception("Not implemented")  # TODO: implement

    def leave_group_request(self, group_id: str):
        raise Exception("Not implemented")  # TODO: implement

    def register_user(self, username: str):
        raise Exception("Not implemented")  # TODO: implement

    def start(self):
        """Start the client: Boradcast server-discovery, establishment of a TCP connection and the reveival-loop-thread."""

        BROADCAST_IP = "255.255.255.255"
        BROADCAST_PORT = 5000

        self.logger.info(f"Searching server at: {BROADCAST_IP}:{BROADCAST_PORT}")
        discovery_response = self._discover_server(BROADCAST_IP, BROADCAST_PORT, 5)

        if not discovery_response.ok:
            self.logger.error("Server discovery failed.")  # TODO: propagate error
            return

        self.logger.info(f"Discovered server at: {discovery_response.remote_addr}:{discovery_response.port}")

        self._start_tcp_connection(discovery_response.remote_addr, discovery_response.port)

    def stop(self):
        if self.client_tcp_socket:
            try:
                self.client_tcp_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.client_tcp_socket.close()


if __name__ == "__main__":
    _set_logging_format()
    client = Client("Tester", 0, 0)
    client.add_message_callback(print)
    client.start()

    client.send("chat", "testmessage")

    # client.stop()

    # print(client.get_latest_messages())
