---
antik: 1
id: 01M86SC7F9W8X2VAGQYXK2NB3M
kind: task
project: 01M86SBGVGGJBN65GK80PBFVKE
created: 2026-11-24T12:44:31.593Z
title: Server socket implementation
---

# Server socket implementation

- phase: plan
- lane: learn
- scope: 

## Description

A socket endpoint for the backend of the chat application

## Plan

_No sections yet._

## Definition of done

_No criteria yet._


## Discussion

_No discussion yet._

## Notes

- 2026-11-24T12:45:12.843Z · Client draft:

import logging
import os
import socket
from threading import Thread
from typing import Any


def _set_logging_format():
    logging.basicConfig(format="[%(levelname)-.1s]: %(message)s", level=logging.DEBUG)


class Client:
    def __init__(self):
        super().__init__()
        my_host = socket.gethostname()
        my_ip = socket.gethostbyname(my_host)

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address: tuple[Any, int] | None = None

        self.logger = logging.getLogger(f"Client_{os.getpid()} ({my_ip})")
        self.logger.setLevel(logging.DEBUG)

        self.run()

    def discover_server(self, broadcast_ip: str, discovery_port: int, timeout_s: float) -> tuple[Any, int] | None:
        BUFFER_SIZE = 1024
        DISCOVERY_MESSAGE = ""  # TODO: Think of something.
        RESPONSE_PREFIX = "Funkloch_Server_Accept_Client"

        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_socket.settimeout(timeout_s)

        broadcast_socket.sendto(str.encode(DISCOVERY_MESSAGE), (broadcast_ip, discovery_port))

        try:
            while True:
                data, server_addr = broadcast_socket.recvfrom(BUFFER_SIZE)
                message = data.decode("utf-8")

                if message.startswith(f"{RESPONSE_PREFIX}:"):  # TODO: Think of better way to verify?
                    tcp_port = int(message.split(":")[1])  # TODO: Fixed port, or sent by server?
                    server_ip = server_addr[0]
                    return server_ip, tcp_port
        except TimeoutError:
            return None
        finally:
            broadcast_socket.close()

    def send(self):
        assert self.server_address is not None, "This should never occur!"
        self.client_socket.sendto(str.encode("message"), self.server_address)

    def receive(self):
        BUFFER_SIZE = 1024

        while True:
            print("e")
            try:
                msg = self.client_socket.recv(BUFFER_SIZE).decode("utf8")
                # TODO: Do something with message
            except OSError as e:
                self.logger.error(f"Receive-loop stopped: {e}")
                break

    def run(self):
        BROADCAST_IP = "192.168.0.255"  # TODO
        BROADCAST_PORT = 5972

        self.logger.info(f"Searching server at: {BROADCAST_IP}:{BROADCAST_PORT}")

        self.server_address = self.discover_server(BROADCAST_IP, BROADCAST_PORT, 5)

        if self.server_address is None:
            self.logger.error("No response from server!")  # TODO: needs to be reported to the frontend.
            return
        receive_thread = Thread(target=self.receive)
        receive_thread.start()

        # TODO: need possibility to quit


if __name__ == "__main__":
    _set_logging_format()
    client = Client()
