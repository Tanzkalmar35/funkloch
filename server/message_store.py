import time
import uuid
from dataclasses import replace
from threading import Lock

from protocol.request import MessageRecord


class InMemoryMessageStore:
    def __init__(self):
        self._messages: dict[str, MessageRecord] = {}
        self._lock = Lock()

    def create_message(self, chat_id: str, origin_id: str, msg: str) -> MessageRecord:
        now = time.time_ns() // 1_000_000
        record = MessageRecord(uuid.uuid4().hex, chat_id, origin_id, msg, now, now)
        with self._lock:
            self._messages[record.message_id] = record
        return replace(record)

    def get_messages(self, chat_id: str) -> list[MessageRecord]:
        with self._lock:
            messages = [
                replace(record)
                for record in self._messages.values()
                if record.chat_id == chat_id and record.deleted_at is None
            ]
        return sorted(messages, key=lambda record: (record.created_at, record.message_id))

    def update_message(self, message_id: str, origin_id: str, msg: str) -> MessageRecord | None:
        with self._lock:
            record = self._messages.get(message_id)
            if record is None or record.deleted_at is not None or record.origin_id != origin_id:
                return None
            updated = replace(record, msg=msg, updated_at=time.time_ns() // 1_000_000)
            self._messages[message_id] = updated
            return replace(updated)

    def delete_message(self, message_id: str, origin_id: str) -> MessageRecord | None:
        with self._lock:
            record = self._messages.get(message_id)
            if record is None or record.origin_id != origin_id:
                return None
            if record.deleted_at is None:
                now = time.time_ns() // 1_000_000
                record = replace(record, updated_at=now, deleted_at=now)
                self._messages[message_id] = record
            return replace(record)
