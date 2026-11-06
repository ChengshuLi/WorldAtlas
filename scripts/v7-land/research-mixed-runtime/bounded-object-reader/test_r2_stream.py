import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import r2_stream
from r2_stream import R2Reader, R2StreamError


class FakeProcess:
    def __init__(self, data=b'abc', rc=0):
        self.stdout = io.BytesIO(data)
        self.returncode = None
        self.rc = rc
        self.killed = False

    def wait(self, timeout=None):
        self.returncode = -9 if self.killed else self.rc
        return self.returncode

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9


class StreamTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cli = self.root / 'wrangler'; self.cli.write_text('fixture')
        self.cfg = self.root / 'config'; self.cfg.write_text('fixture')
        self.processes = []
        self.cmd = None
        read_patch = patch.object(r2_stream, '_read_once', side_effect=lambda raw, count, timeout: raw.read(count))
        kill_patch = patch.object(r2_stream, '_kill_group', side_effect=self.fake_kill_group)
        read_patch.start(); kill_patch.start()
        self.addCleanup(read_patch.stop); self.addCleanup(kill_patch.stop)

    def fake_kill_group(self, process):
        if process.poll() is None:
            process.kill()
        process.wait()

    def launch(self, cmd, **kwargs):
        self.cmd = cmd
        self.assertIs(kwargs['stdout'], subprocess.PIPE)
        self.assertIs(kwargs['stderr'], subprocess.DEVNULL)
        self.assertFalse(kwargs['shell'])
        self.assertTrue(kwargs['start_new_session'])
        self.assertEqual(kwargs['env'], {'HOME': str(self.root)})
        proc = FakeProcess(); self.processes.append(proc)
        return proc

    def reader(self, **kw):
        return R2Reader(self.cli, self.cfg, 'example-bucket', {'parts/a'},
                        {'HOME': str(self.root)}, launcher=self.launch, **kw)

    def test_reads_bounded_stream_through_eof(self):
        with self.reader(read_limit=2).open_part('parts/a') as stream:
            self.assertEqual(stream.read(2), b'ab')
            self.assertEqual(stream.read(2), b'c')
            self.assertEqual(stream.read(1), b'')
        self.assertEqual(self.processes[0].returncode, 0)
        self.assertEqual(self.cmd[1:5], ['r2', 'object', 'get', 'example-bucket/parts/a'])
        self.assertIn('--pipe', self.cmd)

    def test_unapproved_key_rejected_before_launch(self):
        with self.assertRaisesRegex(R2StreamError, 'not authorized'):
            with self.reader().open_part('parts/b'):
                pass
        self.assertFalse(self.processes)

    def test_early_exit_kills_reader_and_fails(self):
        with self.assertRaisesRegex(R2StreamError, 'not consumed'):
            with self.reader().open_part('parts/a') as stream:
                self.assertEqual(stream.read(1), b'a')
        self.assertTrue(self.processes[0].killed)

    def test_nonzero_reader_exit_rejected_after_eof(self):
        def fail(cmd, **kwargs):
            p = FakeProcess(b'', 7); self.processes.append(p); return p
        with patch.object(self, 'launch', fail):
            with self.assertRaisesRegex(R2StreamError, 'reader failed'):
                with self.reader().open_part('parts/a') as stream:
                    self.assertEqual(stream.read(1), b'')

    def test_caller_exception_cleans_up_process(self):
        with self.assertRaisesRegex(ValueError, 'callback'):
            with self.reader().open_part('parts/a'):
                raise ValueError('callback')
        self.assertTrue(self.processes[0].killed)

    def test_oversized_or_invalid_reads_fail(self):
        for n in (0, -1, True, 3):
            with self.subTest(n=n), self.assertRaisesRegex(R2StreamError, 'bounded read'):
                with self.reader(read_limit=2).open_part('parts/a') as stream:
                    stream.read(n)

    def test_unsafe_keys_rejected_at_configuration(self):
        for key in ('../a', '/a', 'a//b', 'a\nb', ''):
            with self.subTest(key=key), self.assertRaises(R2StreamError):
                R2Reader(self.cli, self.cfg, 'example-bucket', {key}, {'HOME': str(self.root)})

class RealProcessLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cli = self.root / 'cli'; self.cli.write_text('fixture')
        self.cfg = self.root / 'config'; self.cfg.write_text('fixture')
        self.processes = []

    def reader(self, script, **options):
        import sys
        def launch(cmd, **kwargs):
            process = subprocess.Popen([sys.executable, '-I', '-S', '-c', script], **kwargs)
            self.processes.append(process)
            return process
        return R2Reader(self.cli, self.cfg, 'example-bucket', {'parts/a'},
                        {}, launcher=launch, **options)

    def test_stalled_read_times_out_and_reaps(self):
        import time
        start = time.monotonic()
        with self.assertRaisesRegex(R2StreamError, 'timed out'):
            with self.reader('import time; time.sleep(5)', idle_timeout=.2, object_timeout=2).open_part('parts/a') as stream:
                stream.read(1)
        self.assertLess(time.monotonic() - start, 2)
        self.assertIsNotNone(self.processes[0].poll())

    def test_descendant_is_terminated_on_abort(self):
        import sys, time
        marker = self.root / 'descendant-ran'
        child = "import time,pathlib; time.sleep(.7); pathlib.Path(%r).write_text('bad')" % str(marker)
        script = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',%r]); print('ready',flush=True); time.sleep(5)" % child
        with self.assertRaises(ValueError):
            with self.reader(script, idle_timeout=1, object_timeout=3).open_part('parts/a') as stream:
                self.assertTrue(stream.read(16))
                raise ValueError('abort')
        time.sleep(.9)
        self.assertFalse(marker.exists())
        self.assertIsNotNone(self.processes[0].poll())

    def test_remote_failure_does_not_leak_raw_log(self):
        script = "import sys; sys.stderr.write('certificate failure; secret fixture'); sys.exit(1)"
        with self.assertRaisesRegex(R2StreamError, 'object reader failed') as caught:
            with self.reader(script, idle_timeout=1, object_timeout=3).open_part('parts/a') as stream:
                self.assertEqual(stream.read(1), b'')
        self.assertNotIn('secret fixture', str(caught.exception))

class MoreLifecycle(RealProcessLifecycle):
    def test_success_reaps_descendant_that_closed_stdout(self):
        import time
        marker = self.root / 'surviving-descendant'
        child = "import time,pathlib; time.sleep(.7); pathlib.Path(%r).write_text('bad')" % str(marker)
        script = "import subprocess,sys; subprocess.Popen([sys.executable,'-c',%r],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print('ok',flush=True)" % child
        with self.reader(script, idle_timeout=1, object_timeout=3).open_part('parts/a') as stream:
            self.assertTrue(stream.read(16)); self.assertEqual(stream.read(1), b'')
        time.sleep(.9)
        self.assertFalse(marker.exists())

    def test_noisy_stderr_does_not_block_or_fill_a_temporary_file(self):
        script = "import os; os.write(2,b'x'*5000000); os.write(1,b'ok')"
        with self.reader(script, idle_timeout=2, object_timeout=4).open_part('parts/a') as stream:
            self.assertEqual(stream.read(2), b'ok'); self.assertEqual(stream.read(1), b'')


if __name__ == '__main__':
    unittest.main(verbosity=2)
