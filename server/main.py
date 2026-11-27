import logging
import socket
from threading import Event, Lock, Thread

from protocol import framing, request, response
from server.message_store import InMemoryMessageStore

logger = logging.getLogger(__name__)


class FunklochServer:
    def __init__(
        self,
        store: InMemoryMessageStore,
        host: str = "0.0.0.0",
        udp_port: int = 5000,
        tcp_port: int = 5001,
    ):
        self.store = store
        self.host = host
        self._advertise_host = (
            host if host != "0.0.0.0" else socket.gethostbyname(socket.gethostname())
        )

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

        self._clients: set[socket.socket] = set()
        self._clients_lock = Lock()
        self._send_lock = Lock()
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
            self.udp_socket.sendto(
                framing.serialize(
                    response.DiscoverServerResponse(True, self._advertise_host, self.tcp_port)
                ),
                address,
            )

    def _serve_tcp(self):
        while self._running:
            try:
                client_socket, address = self.tcp_socket.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            with self._clients_lock:
                self._clients.add(client_socket)
            Thread(target=self._handle_client, args=(client_socket, address), daemon=True).start()

    def _handle_client(self, client_socket: socket.socket, address: tuple[str, int]):
        logger.info("Client connected: %s:%s", *address)
        with client_socket:
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
        self._remove_client(client_socket)
        logger.info("Client disconnected: %s:%s", *address)

    def _handle_frame(self, client_socket: socket.socket, frame):
        if isinstance(frame, request.CreateMessageRequest):
            record = self.store.create_message(frame.chat_id, frame.origin_id, frame.msg)
            self._send(client_socket, response.MessageResponse(frame.request_id, True, record))
            self._broadcast(response.MessageEvent("created", record), exclude=client_socket)
        elif isinstance(frame, request.GetMessagesRequest):
            records = self.store.get_messages(frame.chat_id)
            self._send(client_socket, response.MessagesResponse(frame.request_id, True, records))
        elif isinstance(frame, request.UpdateMessageRequest):
            record = self.store.update_message(frame.message_id, frame.origin_id, frame.msg)
            if record is None:
                self._send(
                    client_socket,
                    response.MessageResponse(
                        frame.request_id, False, error="message not found or not owned"
                    ),
                )
                return
            self._send(client_socket, response.MessageResponse(frame.request_id, True, record))
            self._broadcast(response.MessageEvent("updated", record), exclude=client_socket)
        elif isinstance(frame, request.DeleteMessageRequest):
            record = self.store.delete_message(frame.message_id, frame.origin_id)
            if record is None:
                self._send(
                    client_socket,
                    response.MessageResponse(
                        frame.request_id, False, error="message not found or not owned"
                    ),
                )
                return
            self._send(client_socket, response.MessageResponse(frame.request_id, True, record))
            self._broadcast(response.MessageEvent("deleted", record), exclude=client_socket)
        elif isinstance(frame, request.ChatMessage):
            record = self.store.create_message(frame.chat_id, frame.origin_id, frame.msg)
            self._send(client_socket, request.ChatMessage("*", "Server", f"OK:{frame}"))
            self._broadcast(response.MessageEvent("created", record), exclude=client_socket)
        else:
            logger.warning("Unsupported frame from client: %r", frame)

    def _send(self, client_socket: socket.socket, frame) -> bool:
        try:
            with self._send_lock:
                client_socket.sendall(framing.serialize(frame))
            return True
        except OSError:
            self._remove_client(client_socket)
            return False

    def _broadcast(self, frame, exclude: socket.socket | None = None):
        data = framing.serialize(frame)
        with self._clients_lock:
            clients = [client for client in self._clients if client is not exclude]
        for client in clients:
            try:
                with self._send_lock:
                    client.sendall(data)
            except OSError:
                self._remove_client(client)

    def _remove_client(self, client_socket: socket.socket):
        with self._clients_lock:
            self._clients.discard(client_socket)
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
