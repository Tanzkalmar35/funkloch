import logging
import os
import socket
from threading import Thread
from typing import Any


def _set_logging_format():
    logging.basicConfig(format="[%(levelname)-.1s] %(name)s: %(message)s", level=logging.DEBUG)


class Client:
    def __init__(self):
        super().__init__()
        my_host = socket.gethostname()
        my_ip = socket.gethostbyname(my_host)

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.logger = logging.getLogger(f"Client_{os.getpid()} ({my_ip})")
        self.logger.setLevel(logging.DEBUG)

        self.run()

    def discover_server(self, broadcast_ip: str, discovery_port: int, timeout_s: float) -> tuple[Any, int] | None:
        BUFFER_SIZE = 1024
        DISCOVERY_MESSAGE = "Hi"  # TODO: Think of something.
        RESPONSE_PREFIX = "Funkloch_Server_Accept_Client"

        self.logger.info(f"Broadcasting server discovery {broadcast_ip}:{discovery_port} (timeout = {timeout_s} s)")

        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_socket.settimeout(timeout_s)

        broadcast_socket.sendto(str.encode(DISCOVERY_MESSAGE), (broadcast_ip, discovery_port))

        try:
            while True:
                data, server_addr = broadcast_socket.recvfrom(BUFFER_SIZE)
                message = data.decode()
                print(message)

                if message.startswith(f"{RESPONSE_PREFIX}:"):  # TODO: Think of better way to verify?
                    self.logger.debug(f"Broadcast response from {server_addr}: {message}")
                    tcp_port = int(message.split(":")[1])  # TODO: Fixed port, or sent by server?
                    server_ip = server_addr[0]
                    return server_ip, tcp_port
        except TimeoutError:
            self.logger.debug("Timeout for broadcast response.")
            return None
        finally:
            broadcast_socket.close()

    def send(self):
        self.client_socket.sendall(str.encode("message"))

    def receive(self):
        BUFFER_SIZE = 1024

        while True:
            try:
                data = self.client_socket.recv(BUFFER_SIZE)
                if len(data) > 0:
                    self.logger.info(f"Server Response: {data.decode()}")
                # TODO: Do something with message
            except OSError as e:
                self.logger.error(f"Receive-loop stopped: {e}")
                break

    def start_tcp_connection(self, address: tuple[str, int]):
        self.logger.info(f"Establishing TCP connection: {address[0]}:{address[1]}")

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TODO: with socket.socje ...
        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.client_socket.connect(address)

    def run(self):
        BROADCAST_IP = "192.168.0.255"  # TODO
        BROADCAST_PORT = 5000

        self.logger.info(f"Searching server at: {BROADCAST_IP}:{BROADCAST_PORT}")
        server_address = self.discover_server(BROADCAST_IP, BROADCAST_PORT, 5)

        if server_address is None:
            self.logger.error("No response from server!")  # TODO: needs to be reported to the frontend.
            return

        self.logger.info(f"Discovered server at: {server_address[0]}:{server_address[1]}")

        self.start_tcp_connection(server_address)

        receive_thread = Thread(target=self.receive)
        receive_thread.start()

        self.send()

        # TODO: need possibility to quit


if __name__ == "__main__":
    _set_logging_format()
    client = Client()
