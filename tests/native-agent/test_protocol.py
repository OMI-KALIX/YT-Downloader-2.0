import io
import json
import struct
import sys
import unittest
from pathlib import Path

# Add native-agent/src to sys.path
agent_src = Path(__file__).resolve().parent.parent.parent / "native-agent" / "src"
if str(agent_src) not in sys.path:
    sys.path.insert(0, str(agent_src))

from messaging.protocol import NativeMessagingProtocol


class MockStream:
    def __init__(self, buffer):
        self.buffer = buffer


class TestNativeMessagingProtocol(unittest.TestCase):

    def test_send_message_framing(self):
        test_msg = {"id": "req_001", "action": "ping"}
        stdout_buf = io.BytesIO()
        mock_stdout = MockStream(stdout_buf)

        orig_stdout = sys.stdout
        try:
            sys.stdout = mock_stdout
            success = NativeMessagingProtocol.send_message(test_msg)
            self.assertTrue(success)
        finally:
            sys.stdout = orig_stdout

        stdout_buf.seek(0)
        raw_length = stdout_buf.read(4)
        length = struct.unpack("<I", raw_length)[0]
        data = stdout_buf.read(length)
        decoded = json.loads(data.decode("utf-8"))

        self.assertEqual(decoded["action"], "ping")
        self.assertEqual(decoded["id"], "req_001")

    def test_read_message_framing(self):
        payload = {"action": "status"}
        encoded_json = json.dumps(payload).encode("utf-8")
        raw_stream = struct.pack("<I", len(encoded_json)) + encoded_json

        stdin_buf = io.BytesIO(raw_stream)
        mock_stdin = MockStream(stdin_buf)

        orig_stdin = sys.stdin
        try:
            sys.stdin = mock_stdin
            msg = NativeMessagingProtocol.read_message()
            self.assertIsNotNone(msg)
            self.assertEqual(msg["action"], "status")
        finally:
            sys.stdin = orig_stdin


if __name__ == "__main__":
    unittest.main()
