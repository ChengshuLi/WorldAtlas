from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from contextlib import redirect_stdout
import io
import threading
import unittest

from worldatlas.map_build.execution.control import check_cancelled, emit, stage


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

    def test_progress_can_be_printed_outside_a_worker_context(self):
        log = io.StringIO()
        with redirect_stdout(log):
            emit('started')
        self.assertEqual(log.getvalue(), 'started\n')
