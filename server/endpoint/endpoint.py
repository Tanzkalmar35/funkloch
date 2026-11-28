import logging
import socket
import os
import handler
from threading import Thread

DEFAULT_BUFFER_SIZE = 1024


def _set_logging_format():
    logging.basicConfig(
        format="[%(levelname)-.1s]: %(message)s", level=logging.DEBUG)


class ServerSocketEndpoint:
    def __init__(self):
        super().__init__()
        my_host = socket.gethostname()
        my_ip = socket.gethostbyname(my_host)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.handler = handler.MessageHandler()

        self.logger = logging.getLogger(f"server_{os.getpid()} ({my_ip})")
        self.logger.setLevel(logging.DEBUG)

        self.run()

    def run(self):
        """
        Accepts a new socket connection, receives a message and passes that to
        the message handler in a new thread. The incoming message must fit into
        a 1024 sized buffer.
        """
        while True:
            conn, addr = self.socket.accept()
            print("Incoming message from " + addr[0] + ":" + str(addr[1]))

            try:
                msg = socket.recv(
                    DEFAULT_BUFFER_SIZE).decode("utf8")

                # Spawn msg handler in new thread
                thread = Thread(target=self.handle_request(msg))
                thread.start()
            except OSError as e:
                self.logger.error(
                    f"Unable to receive or handle incomin message: {e}")
                break

    def handle_request(self, msg):
        resp = self.handler.handle(msg)
        self.socket.
