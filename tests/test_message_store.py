import unittest

from server.message_store import InMemoryMessageStore


class MessageStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryMessageStore()

    def test_create_and_get_by_chat(self):
        created = self.store.create_message("chat", "alice", "hello")
        self.store.create_message("other", "bob", "elsewhere")

        self.assertTrue(created.message_id)
        self.assertEqual(created.created_at, created.updated_at)
        self.assertIsNone(created.deleted_at)
        self.assertEqual(self.store.get_messages("chat"), [created])
        self.assertEqual(self.store.get_messages("missing"), [])

    def test_update_requires_owner(self):
        created = self.store.create_message("chat", "alice", "hello")

        self.assertIsNone(self.store.update_message(created.message_id, "bob", "hacked"))

        updated = self.store.update_message(created.message_id, "alice", "bye")
        self.assertIsNotNone(updated)
        self.assertEqual(updated.msg, "bye")
        self.assertEqual(updated.origin_id, "alice")
        self.assertGreaterEqual(updated.updated_at, created.updated_at)
        self.assertEqual(self.store.get_messages("chat"), [updated])

    def test_delete_is_soft_and_requires_owner(self):
        created = self.store.create_message("chat", "alice", "hello")

        self.assertIsNone(self.store.delete_message(created.message_id, "bob"))

        deleted = self.store.delete_message(created.message_id, "alice")
        self.assertIsNotNone(deleted)
        self.assertIsNotNone(deleted.deleted_at)
        self.assertEqual(self.store.get_messages("chat"), [])
        self.assertIsNone(self.store.update_message(created.message_id, "alice", "after delete"))

    def test_returned_records_are_copies(self):
        created = self.store.create_message("chat", "alice", "hello")
        created.msg = "mutated"

        self.assertEqual(self.store.get_messages("chat")[0].msg, "hello")


if __name__ == "__main__":
    unittest.main()
