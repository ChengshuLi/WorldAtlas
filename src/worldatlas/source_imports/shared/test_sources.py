"""Test how an import resolves and stages its catalog inputs."""

from contextlib import nullcontext
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.sources import acquire_sources


class SourceAcquisitionTests(unittest.TestCase):
    """Exercise verified file staging with catalog rows and in-memory R2 objects."""

    def test_files_arrive_in_request_order_without_downloading_evidence(self):
        payloads = {
            'first': b'first bytes',
            'second': b'second bytes',
            'evidence': b'supporting document',
        }
        database = Mock()
        database.execute.return_value = [
            (ident, 'test', ident, hashlib.sha256(raw).hexdigest(), len(raw))
            for ident, raw in payloads.items()
        ]
        storage = Mock()
        storage.get_object.side_effect = lambda **args: {'Body': io.BytesIO(payloads[args['Key']])}
        with (tempfile.TemporaryDirectory() as directory,
              patch('boto3.client', return_value=storage)):
            runtime = Runtime(connect=lambda: nullcontext(database),
                              recipe_id='test', method='watershed_boundary', arguments={},
                              work_dir=Path(directory))
            paths = acquire_sources(runtime, ['second', 'first'],
                                    evidence_source_ids=['evidence'])
            self.assertEqual([path.read_bytes() for path in paths],
                             [payloads['second'], payloads['first']])

        database.execute.assert_called_once()
        self.assertCountEqual(database.execute.call_args.args[1][0], payloads)
        self.assertEqual([call.kwargs['Key'] for call in storage.get_object.call_args_list],
                         ['second', 'first'])
