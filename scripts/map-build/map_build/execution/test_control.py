from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
import io
import threading
import unittest

from map_build.execution.control import check_cancelled, emit, stage


class StageControlTests(unittest.TestCase):
    def test_worker_observes_cancellation_and_the_context_is_released(self):
        cancelled = threading.Event()
        log = io.StringIO()
        with stage(cancelled, log), ThreadPoolExecutor(1) as workers:
            workers.submit(copy_context().run, emit, 'started').result()
            cancelled.set()
            with self.assertRaises(InterruptedError):
                workers.submit(copy_context().run, check_cancelled).result()
        self.assertEqual(log.getvalue(), 'started\n')
        check_cancelled()
