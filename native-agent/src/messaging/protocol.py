import json
import struct
import sys
from typing import Any, Dict, Optional


class NativeMessagingProtocol:
    """Implements Chrome/Edge Native Messaging stdin/stdout protocol.
    Reads/writes 4-byte uint32 little-endian length prefix followed by UTF-8 encoded JSON payload.
    """

    @staticmethod
    def read_message() -> Optional[Dict[str, Any]]:
        try:
            raw_length = sys.stdin.buffer.read(4)
            if not raw_length or len(raw_length) < 4:
                return None
            length = struct.unpack("<I", raw_length)[0]
            if length == 0:
                return None
            raw_data = sys.stdin.buffer.read(length)
            if len(raw_data) < length:
                return None
            return json.loads(raw_data.decode("utf-8"))
        except Exception:
            return None

    @staticmethod
    def send_message(message: Dict[str, Any]) -> bool:
        try:
            encoded_payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
            length_prefix = struct.pack("<I", len(encoded_payload))
            sys.stdout.buffer.write(length_prefix)
            sys.stdout.buffer.write(encoded_payload)
            sys.stdout.buffer.flush()
            return True
        except Exception:
            return False
