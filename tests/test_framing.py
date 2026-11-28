import socket
import unittest

from protocol import framing, request, response


class FramingTests(unittest.TestCase):
    def test_existing_round_trip(self):
        frame = request.DiscoverServerRequest()
        self.assertEqual(framing.deserialize(framing.serialize(frame)), frame)

    def test_crud_frames_round_trip(self):
        record = request.MessageRecord("m1", "chat", "user", "hello", 1, 1)
        frames = [
            request.CreateMessageRequest("r1", "chat", "user", "hello"),
            request.GetMessagesRequest("r2", "chat"),
            request.UpdateMessageRequest("r3", "m1", "user", "bye"),
            request.DeleteMessageRequest("r4", "m1", "user"),
            response.MessageResponse("r1", True, record),
            response.MessagesResponse("r2", True, [record]),
            response.MessageEvent("created", record),
        ]
        for frame in frames:
            with self.subTest(frame=type(frame).__name__):
                self.assertEqual(framing.deserialize(framing.serialize(frame)), frame)

    def test_recv_frame_handles_fragmentation(self):
        frame = request.CreateMessageRequest("r1", "chat", "user", "hello")
        data = framing.serialize(frame)
        sender, receiver = socket.socketpair()
        with sender, receiver:
            for start in range(0, len(data), 3):
                sender.sendall(data[start : start + 3])
            self.assertEqual(framing.recv_frame(receiver), frame)

    def test_recv_frame_handles_large_payload(self):
        frame = request.CreateMessageRequest("r1", "chat", "user", "x" * 5000)
        sender, receiver = socket.socketpair()
        with sender, receiver:
            sender.sendall(framing.serialize(frame))
            self.assertEqual(framing.recv_frame(receiver), frame)

    def test_recv_frame_handles_concatenation(self):
        frames = [
            request.CreateMessageRequest("r1", "chat", "user", "one"),
            request.GetMessagesRequest("r2", "chat"),
        ]
        sender, receiver = socket.socketpair()
        with sender, receiver:
            sender.sendall(b"".join(framing.serialize(frame) for frame in frames))
            self.assertEqual(framing.recv_frame(receiver), frames[0])
            self.assertEqual(framing.recv_frame(receiver), frames[1])

    def test_recv_frame_rejects_oversized_frame(self):
        sender, receiver = socket.socketpair()
        with sender, receiver:
            sender.sendall(
                framing.HEADER + str(framing.MAX_FRAME_SIZE + 1).encode("ascii") + b":"
            )
            with self.assertRaisesRegex(ValueError, "Frame too large"):
                framing.recv_frame(receiver)

    def test_recv_frame_rejects_invalid_header(self):
        sender, receiver = socket.socketpair()
        with sender, receiver:
            sender.sendall(b"NotFunkloch:1:x")
            with self.assertRaisesRegex(ValueError, "Invalid frame header"):
                framing.recv_frame(receiver)


if __name__ == "__main__":
    unittest.main()
