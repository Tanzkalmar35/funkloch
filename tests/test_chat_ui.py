import time
import tkinter as tk
import unittest

from client.main import Client
from main import ChatUI
from server.main import FunklochServer
from server.message_store import InMemoryMessageStore


class ChatUITests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
            self.root.withdraw()
        except tk.TclError as exc:
            self.skipTest(f"Tk display unavailable: {exc}")

        self.store = InMemoryMessageStore()
        self.server = FunklochServer(self.store, host="127.0.0.1", udp_port=0, tcp_port=0)
        self.server.start()

        self.alice = Client("alice")
        self.alice._start_tcp_connection("127.0.0.1", self.server.tcp_port)

        self.bob = Client("bob")
        self.bob._start_tcp_connection("127.0.0.1", self.server.tcp_port)

        self.ui = ChatUI(
            self.root,
            username="alice",
            chat_id="general",
            client=self.alice,
            auto_connect=False,
        )

    def tearDown(self):
        if hasattr(self, "ui"):
            self.ui.close()
        if hasattr(self, "bob"):
            self.bob.stop()
        if hasattr(self, "alice"):
            self.alice.stop()
        if hasattr(self, "server"):
            self.server.stop()

    def _pump_until(self, predicate, timeout: float = 2.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.ui.drain_ui_queue()
            self.root.update()
            if predicate():
                return
            time.sleep(0.02)
        self.ui.drain_ui_queue()
        self.root.update()
        self.assertTrue(predicate(), "Timed out waiting for UI condition")

    def _chat_text(self) -> str:
        return self.ui.chat.get("1.0", tk.END)

    def test_send_receive_update_and_delete_events(self):
        # Seed history before UI loads it
        self.bob.create_message("general", "history message")
        self.ui._on_connected(self.alice.get_messages("general"))
        self.assertIn("history message", self._chat_text())

        # Send from UI
        self.ui.entry.insert(0, "hello from alice")
        self.ui.send_message()
        self._pump_until(lambda: "hello from alice" in self._chat_text())

        # Incoming message from another client in same chat vs different chat
        bob_msg = self.bob.create_message("general", "hi alice")
        self.bob.create_message("random", "wrong room")
        self._pump_until(lambda: "hi alice" in self._chat_text())
        self.assertNotIn("wrong room", self._chat_text())

        # Update and delete events reflected in UI
        self.bob.update_message(bob_msg.message_id, "hi alice (edited)")
        self._pump_until(lambda: "hi alice (edited)" in self._chat_text())

        self.bob.delete_message(bob_msg.message_id)
        self._pump_until(lambda: "hi alice (edited)" not in self._chat_text())


if __name__ == "__main__":
    unittest.main()
