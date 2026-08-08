import sys
import unittest
from pathlib import Path

# Add native-agent/src to sys.path
agent_src = Path(__file__).resolve().parent.parent.parent / "native-agent" / "src"
if str(agent_src) not in sys.path:
    sys.path.insert(0, str(agent_src))

from jobs.manager import JobManager
from jobs.models import JobState


class TestJobManager(unittest.TestCase):

    def test_job_lifecycle(self):
        manager = JobManager()
        job = manager.create_job("job_100", "https://youtube.com/watch?v=123", "1080p")
        self.assertEqual(job.state, JobState.STARTING)

        manager.update_state("job_100", JobState.DOWNLOADING)
        self.assertEqual(manager.get_job("job_100").state, JobState.DOWNLOADING)

        manager.update_progress("job_100", percent=45.5, speed="2.1MiB/s", eta="00:15")
        updated = manager.get_job("job_100")
        self.assertEqual(updated.progress.percent, 45.5)
        self.assertEqual(updated.progress.speed, "2.1MiB/s")

        manager.update_state("job_100", JobState.COMPLETED)
        self.assertEqual(manager.get_job("job_100").state, JobState.COMPLETED)


if __name__ == "__main__":
    unittest.main()
