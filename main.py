import argparse
from datetime import datetime
import getpass
from queue import Empty, SimpleQueue
from threading import Thread
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from client.main import Client
from protocol.request import MessageRecord
from protocol.response import MessageEvent


class ChatUI:
    def __init__(
        self,
        root: tk.Misc,
        username: str | None = None,
        chat_id: str = "general",
        client: Client | None = None,
        auto_connect: bool = True,
    ):
        self.root = root
        self.chat_id = chat_id
        self.username = username or getpass.getuser()
        self.client = client or Client(self.username)
        self._messages: list[MessageRecord] = []
        self._seen_ids: set[str] = set()
        self._connected = False
        self._closed = False
        self._ui_queue: SimpleQueue[tuple] = SimpleQueue()

        root.title(f"Funkloch - {self.username} ({self.chat_id})")
        root.geometry("650x550")
        root.configure(bg="#111b21")

        # Header
        header = tk.Frame(root, bg="#202c33")
        header.pack(fill="x", padx=10, pady=(10, 0))

        tk.Label(
            header,
            text="Funkloch",
            font=("Arial", 18, "bold"),
            bg="#202c33",
            fg="white",
        ).pack(side="left", padx=10, pady=8)

        self.status_label = tk.Label(
            header,
            text="Connecting..." if auto_connect else "Offline",
            font=("Arial", 10),
            bg="#202c33",
            fg="#8696a0",
        )
        self.status_label.pack(side="right", padx=10)

        # Chat history
        self.chat = ScrolledText(
            root,
            bg="#111b21",
            fg="white",
            font=("Arial", 12),
            wrap="word",
            state="disabled",
        )
        self.chat.pack(fill="both", expand=True, padx=10, pady=10)

        self.chat.tag_config("own", foreground="#53bdeb", justify="right")
        self.chat.tag_config("other", foreground="white", justify="left")
        self.chat.tag_config("system", foreground="#8696a0", justify="center")

        # Input area
        frame = tk.Frame(root, bg="#202c33")
        frame.pack(fill="x", padx=10, pady=(0, 10))

        self.entry = tk.Entry(frame, font=("Arial", 12))
        self.entry.pack(side="left", fill="x", expand=True, padx=(8, 0), pady=6)
        self.entry.bind("<Return>", self.send_message)

        self.send_button = tk.Button(
            frame,
            text="Senden",
            command=self.send_message,
            bg="#005c4b",
            fg="white",
            state="disabled" if auto_connect else "normal",
        )
        self.send_button.pack(side="right", padx=10, pady=6)

        self.entry.focus_set()
        self.client.add_message_event_callback(self._on_client_event)

        if isinstance(root, tk.Tk):
            root.protocol("WM_DELETE_WINDOW", self.close)

        self._poll_ui_queue()

        if auto_connect:
            self._start_connection()

    def _schedule_ui(self, func, *args):
        if not self._closed:
            self._ui_queue.put((func, args))

    def drain_ui_queue(self):
        while not self._closed:
            try:
                func, args = self._ui_queue.get_nowait()
            except Empty:
                break
            func(*args)

    def _poll_ui_queue(self):
        if self._closed:
            return
        self.drain_ui_queue()
        try:
            self.root.after(25, self._poll_ui_queue)
        except tk.TclError:
            pass

    def _set_status(self, text: str, color: str = "#8696a0"):
        self.status_label.configure(text=text, fg=color)

    def _start_connection(self):
        def worker():
            try:
                self.client.start()
                history = self.client.get_messages(self.chat_id)
            except Exception as exc:
                self._schedule_ui(self._on_connect_failed, str(exc))
                return
            self._schedule_ui(self._on_connected, history)

        Thread(target=worker, daemon=True).start()

    def _on_connected(self, history: list[MessageRecord]):
        self._connected = True
        self._set_status(f"Connected ({self.username})", "#25d366")
        self.send_button.configure(state="normal")
        self._messages = [m for m in history if m.chat_id == self.chat_id and m.deleted_at is None]
        self._seen_ids = {m.message_id for m in self._messages}
        self._rerender_chat()

    def _on_connect_failed(self, error: str):
        self._connected = False
        self._set_status("Connection failed", "#f15c6d")
        self.add_system_message(f"Could not connect to server: {error}")

    def _on_client_event(self, event: MessageEvent):
        self._schedule_ui(self.handle_message_event, event)

    def handle_message_event(self, event: MessageEvent):
        record = event.message
        if record.chat_id != self.chat_id:
            return

        if event.kind == "created":
            if record.message_id not in self._seen_ids:
                self._messages.append(record)
                self._seen_ids.add(record.message_id)
                self._append_record(record)
        elif event.kind == "updated":
            for idx, existing in enumerate(self._messages):
                if existing.message_id == record.message_id:
                    self._messages[idx] = record
                    break
            self._rerender_chat()
        elif event.kind == "deleted":
            self._messages = [m for m in self._messages if m.message_id != record.message_id]
            self._seen_ids.discard(record.message_id)
            self._rerender_chat()

    def _format_timestamp(self, timestamp_ms: int | None) -> str:
        if timestamp_ms is None:
            return datetime.now().strftime("%H:%M")
        return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%H:%M")

    def _append_record(self, record: MessageRecord):
        own = record.origin_id == self.username
        self.add_message(
            record.origin_id,
            record.msg,
            own=own,
            timestamp=self._format_timestamp(record.created_at),
        )

    def _rerender_chat(self):
        self.chat.configure(state="normal")
        self.chat.delete("1.0", tk.END)
        self.chat.configure(state="disabled")
        for record in self._messages:
            self._append_record(record)

    def add_message(
        self,
        user_name: str,
        message: str,
        own: bool = False,
        timestamp: str | None = None,
    ):
        time_str = timestamp or datetime.now().strftime("%H:%M")
        tag = "own" if own else "other"

        self.chat.configure(state="normal")
        self.chat.insert(tk.END, f"{user_name} ({time_str})\n{message}\n\n", tag)
        self.chat.configure(state="disabled")
        self.chat.see(tk.END)

    def add_system_message(self, message: str):
        self.chat.configure(state="normal")
        self.chat.insert(tk.END, f"{message}\n\n", "system")
        self.chat.configure(state="disabled")
        self.chat.see(tk.END)

    def send_message(self, event=None):
        message = self.entry.get().strip()
        if not message or not self._connected:
            return

        self.entry.delete(0, tk.END)

        def worker():
            try:
                record = self.client.create_message(self.chat_id, message)
            except Exception as exc:
                self._schedule_ui(self.add_system_message, f"Failed to send message: {exc}")
                return
            self._schedule_ui(self._on_message_sent, record)

        Thread(target=worker, daemon=True).start()

    def _on_message_sent(self, record: MessageRecord):
        if record.message_id not in self._seen_ids:
            self._messages.append(record)
            self._seen_ids.add(record.message_id)
            self._append_record(record)

    def close(self):
        self._closed = True
        try:
            self.client.stop()
        finally:
            if isinstance(self.root, tk.Tk):
                self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="Funkloch Tkinter chat client")
    parser.add_argument("--username", "-u", default=None, help="Display name / origin_id")
    parser.add_argument("--chat", "-c", default="general", help="Chat room ID")
    args = parser.parse_args()

    root = tk.Tk()
    ChatUI(root, username=args.username, chat_id=args.chat)
    root.mainloop()


if __name__ == "__main__":
    main()
