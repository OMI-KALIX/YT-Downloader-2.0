import os
import sys
from pathlib import Path

# Add src to sys.path to allow execution both via python main.py and PyInstaller bundle
src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from messaging.protocol import NativeMessagingProtocol
from messaging.handler import NativeMessageHandler
from jobs.manager import JobManager


def main():
    """Main entrypoint for downloader-agent executable."""
    job_manager = JobManager()

    def send_event(msg):
        NativeMessagingProtocol.send_message(msg)

    handler = NativeMessageHandler(job_manager=job_manager, event_callback=send_event)

    while True:
        message = NativeMessagingProtocol.read_message()
        if message is None:
            # Stdin closed or EOF reached (browser extension disconnected)
            break
        handler.handle_message(message)


if __name__ == "__main__":
    main()
