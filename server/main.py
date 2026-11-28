import logging
import os
import socket
import struct
from threading import Event, Lock, Thread

from protocol import framing, request, response
from server.message_store import InMemoryMessageStore

logger = logging.getLogger(__name__)
SEND_TIMEOUT_S = 2.0


class FunklochServer:
    def __init__(
        self,
        store: InMemoryMessageStore,
        host: str = "0.0.0.0",
        udp_port: int = 5000,
        tcp_port: int = 5001,
    ):
        self.store = store

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((host, udp_port))
        self.udp_socket.settimeout(0.2)
        self.udp_port = self.udp_socket.getsockname()[1]

        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind((host, tcp_port))
        self.tcp_socket.settimeout(0.2)
        self.tcp_socket.listen()
        self.tcp_port = self.tcp_socket.getsockname()[1]

        self._clients: dict[socket.socket, Lock] = {}
        self._clients_lock = Lock()
        self._send_timeout = SEND_TIMEOUT_S
        self._running = False
        self._threads: list[Thread] = []

    def start(self):
        self._running = True
        for target in (self._serve_udp, self._serve_tcp):
            thread = Thread(target=target, daemon=True)
            thread.start()
            self._threads.append(thread)

    def stop(self):
        self._running = False
        self.udp_socket.close()
        self.tcp_socket.close()
        with self._clients_lock:
            clients = list(self._clients)
            self._clients.clear()
        for client in clients:
            client.close()
        for thread in self._threads:
            thread.join(timeout=1)

    def _serve_udp(self):
        while self._running:
            try:
                data, address = self.udp_socket.recvfrom(1024)
            except TimeoutError:
                continue
            except OSError:
                break
            try:
                framing.deserialize(data)
            except ValueError as exc:
                logger.debug("Invalid discovery datagram from %s: %s", address, exc)
                continue
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                    probe.connect(address)
                    advertise_host = probe.getsockname()[0]
            except OSError as exc:
                logger.debug("Could not determine local address for %s: %s", address, exc)
                continue
            self.udp_socket.sendto(
                framing.serialize(
                    response.DiscoverServerResponse(True, advertise_host, self.tcp_port)
                ),
                address,
            )

    def _set_send_timeout(self, client_socket: socket.socket):
        try:
            if os.name == "nt":
                client_socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_SNDTIMEO, int(self._send_timeout * 1000)
                )
            else:
                timeout_us = int(self._send_timeout * 1_000_000)
                client_socket.setsockopt(
                    socket.SOL_SOCKET,
                    socket.SO_SNDTIMEO,
                    struct.pack("ll", timeout_us // 1_000_000, timeout_us % 1_000_000),
                )
        except (OSError, TypeError):
            pass

    def _serve_tcp(self):
        while self._running:
            try:
                client_socket, address = self.tcp_socket.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            self._set_send_timeout(client_socket)
            with self._clients_lock:
                self._clients[client_socket] = Lock()
            Thread(target=self._handle_client, args=(client_socket, address), daemon=True).start()

    def _handle_client(self, client_socket: socket.socket, address: tuple[str, int]):
        logger.info("Client connected: %s:%s", *address)
        try:
            while self._running:
                try:
                    frame = framing.recv_frame(client_socket)
                except Exception as exc:
                    logger.debug("Client %s:%s disconnected: %s", *address, exc)
                    break
                try:
                    self._handle_frame(client_socket, frame)
                except Exception:
                    logger.exception("Failed to handle frame from %s:%s", *address)
        finally:
            self._remove_client(client_socket)
        logger.info("Client disconnected: %s:%s", *address)

    def _handle_frame(self, client_socket: socket.socket, frame):
        if isinstance(frame, request.CreateMessageRequest):
            record = self.store.create_message(frame.chat_id, frame.origin_id, frame.msg)
            self._reply_mutation(client_socket, frame.request_id, "created", record)
        elif isinstance(frame, request.GetMessagesRequest):
            records = self.store.get_messages(frame.chat_id)
            self._send(client_socket, response.MessagesResponse(frame.request_id, True, records))
        elif isinstance(frame, request.UpdateMessageRequest):
            record = self.store.update_message(frame.message_id, frame.origin_id, frame.msg)
            self._reply_mutation(client_socket, frame.request_id, "updated", record)
        elif isinstance(frame, request.DeleteMessageRequest):
            record = self.store.delete_message(frame.message_id, frame.origin_id)
            self._reply_mutation(client_socket, frame.request_id, "deleted", record)
        else:
            logger.warning("Unsupported frame from client: %r", frame)

    def _reply_mutation(self, client_socket, request_id: str, kind: str, record):
        if record is None:
            self._send(
                client_socket,
                response.MessageResponse(
                    request_id, False, error="message not found or not owned"
                ),
            )
            return
        self._send(client_socket, response.MessageResponse(request_id, True, record))
        self._broadcast(response.MessageEvent(kind, record), exclude=client_socket)

    def _send_bytes(self, client_socket: socket.socket, data: bytes):
        with self._clients_lock:
            send_lock = self._clients.get(client_socket)
        if send_lock is None:
            return
        try:
            with send_lock:
                client_socket.sendall(data)
        except OSError:
            self._remove_client(client_socket)

    def _send(self, client_socket: socket.socket, frame):
        self._send_bytes(client_socket, framing.serialize(frame))

    def _broadcast(self, frame, exclude: socket.socket | None = None):
        data = framing.serialize(frame)
        with self._clients_lock:
            clients = [client for client in self._clients if client is not exclude]
        for client in clients:
            self._send_bytes(client, data)

    def _remove_client(self, client_socket: socket.socket):
        with self._clients_lock:
            send_lock = self._clients.pop(client_socket, None)
        if send_lock is not None:
            client_socket.close()


def main():
    logging.basicConfig(level=logging.INFO, format="[%(levelname)-.1s] %(name)s: %(message)s")
    server = FunklochServer(InMemoryMessageStore())
    server.start()
    logger.info("Listening on UDP %s and TCP %s", server.udp_port, server.tcp_port)
    try:
        Event().wait()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
