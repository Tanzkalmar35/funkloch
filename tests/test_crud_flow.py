import logging
import socket
import time
import unittest

from client.main import Client
from protocol import framing, request
from server.main import FunklochServer
from server.message_store import InMemoryMessageStore


class CrudFlowTests(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

        self.server = FunklochServer(
            InMemoryMessageStore(), host="127.0.0.1", udp_port=0, tcp_port=0
        )
        self.addCleanup(self.server.stop)
        self.server.start()

        self.alice = Client("alice")
        self.addCleanup(self.alice.stop)
        self.bob = Client("bob")
        self.addCleanup(self.bob.stop)

        self.alice._start_tcp_connection("127.0.0.1", self.server.tcp_port)
        self.bob._start_tcp_connection("127.0.0.1", self.server.tcp_port)

        self.bob_events = []
        self.bob.add_message_event_callback(self.bob_events.append)

    def _wait_for_events(self, count, timeout=2):
        deadline = time.monotonic() + timeout
        while len(self.bob_events) < count and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertGreaterEqual(len(self.bob_events), count)

    def test_crud_flow_and_events(self):
        created = self.alice.create_message("chat", "hello")
        self.assertEqual(created.origin_id, "alice")
        self.assertEqual(created.msg, "hello")
        self.assertIsNone(created.deleted_at)

        self._wait_for_events(1)
        self.assertEqual(self.bob_events[0].kind, "created")
        self.assertEqual(self.bob_events[0].message.message_id, created.message_id)

        self.assertEqual(
            [message.message_id for message in self.alice.get_messages("chat")],
            [created.message_id],
        )

        with self.assertRaisesRegex(RuntimeError, "not found or not owned"):
            self.bob.update_message(created.message_id, "hacked")

        updated = self.alice.update_message(created.message_id, "bye")
        self.assertEqual(updated.msg, "bye")
        self._wait_for_events(2)
        self.assertEqual(self.bob_events[1].kind, "updated")
        self.assertEqual(self.bob_events[1].message.msg, "bye")

        deleted = self.alice.delete_message(created.message_id)
        self.assertIsNotNone(deleted.deleted_at)
        self.assertEqual(self.alice.get_messages("chat"), [])
        self._wait_for_events(3)
        self.assertEqual(self.bob_events[2].kind, "deleted")

    def test_slow_client_does_not_block_other_clients(self):
        self.server._send_timeout = 0.5

        # Connects but never reads, with a tiny receive window.
        stalled = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        stalled.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024)
        self.addCleanup(stalled.close)
        stalled.connect(("127.0.0.1", self.server.tcp_port))

        # Far larger than the send buffer, so the broadcast to the client that
        # never reads blocks until the send timeout drops it.
        self.alice.create_message("chat", "x" * (8 * 1024 * 1024))

        started = time.monotonic()
        reply = self.alice.create_message("chat", "still alive")
        elapsed = time.monotonic() - started

        self.assertEqual(reply.msg, "still alive")
        self.assertLess(elapsed, 3)
        self._wait_for_events(2)
        deadline = time.monotonic() + 2
        while len(self.server._clients) > 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(len(self.server._clients), 2)

    def test_get_messages_filters_chat_and_deleted(self):
        first = self.alice.create_message("chat-a", "one")
        second = self.alice.create_message("chat-b", "two")

        self.assertEqual(
            [message.message_id for message in self.alice.get_messages("chat-a")],
            [first.message_id],
        )
        self.assertEqual(
            [message.message_id for message in self.alice.get_messages("chat-b")],
            [second.message_id],
        )

        self.alice.delete_message(first.message_id)
        self.assertEqual(self.alice.get_messages("chat-a"), [])

    def test_discovery(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.settimeout(2)
            udp.sendto(
                framing.serialize(request.DiscoverServerRequest()),
                ("127.0.0.1", self.server.udp_port),
            )
            data, _ = udp.recvfrom(1024)

        discovery = framing.deserialize(data)
        self.assertTrue(discovery.ok)
        self.assertEqual(discovery.remote_addr, "127.0.0.1")
        self.assertEqual(discovery.port, self.server.tcp_port)

    def test_discovery_advertises_reachable_address(self):
        server = FunklochServer(
            InMemoryMessageStore(), host="0.0.0.0", udp_port=0, tcp_port=0
        )
        self.addCleanup(server.stop)
        server.start()

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.bind(("127.0.0.1", 0))
            udp.settimeout(2)
            udp.sendto(
                framing.serialize(request.DiscoverServerRequest()),
                ("127.0.0.1", server.udp_port),
            )
            data, _ = udp.recvfrom(1024)

        discovery = framing.deserialize(data)
        self.assertTrue(discovery.ok)
        self.assertEqual(discovery.remote_addr, "127.0.0.1")
        self.assertEqual(discovery.port, server.tcp_port)


if __name__ == "__main__":
    unittest.main()
