import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Add native-agent/src to sys.path
agent_src = Path(__file__).resolve().parent.parent.parent / "native-agent" / "src"
if str(agent_src) not in sys.path:
    sys.path.insert(0, str(agent_src))

from jobs.manager import JobManager
from messaging.handler import NativeMessageHandler


class TestNativeMessageHandler(unittest.TestCase):

    def setUp(self):
        self.job_manager = JobManager()
        self.events = []
        self.handler = NativeMessageHandler(
            job_manager=self.job_manager,
            event_callback=lambda msg: self.events.append(msg)
        )

    def test_handle_ping(self):
        self.handler.handle_message({"id": "req_1", "action": "ping"})
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0]["event"], "pong")
        self.assertEqual(self.events[0]["payload"]["status"], "ready")

    def test_handle_status(self):
        self.handler.handle_message({"id": "req_2", "action": "status"})
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0]["event"], "status")

    def test_invalid_url_rejection(self):
        self.handler.handle_message({
            "id": "req_3",
            "action": "get_formats",
            "payload": {"url": "invalid-url-string"}
        })
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0]["event"], "error")
        self.assertEqual(self.events[0]["payload"]["code"], "INVALID_URL")

    def test_command_injection_flag_rejection(self):
        self.handler.handle_message({
            "id": "req_4",
            "action": "download",
            "payload": {"url": "--exec calc.exe"}
        })
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0]["event"], "error")
        self.assertEqual(self.events[0]["payload"]["code"], "INVALID_URL")


if __name__ == "__main__":
    unittest.main()
