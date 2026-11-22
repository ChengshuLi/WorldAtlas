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

    def test_mixed_requests_preserve_file_and_part_order_without_downloading_evidence(self):
        payloads = {
            'first': b'first bytes',
            'second': b'second bytes',
            'standalone': b'one whole file',
            'evidence': b'supporting document',
        }
        database = Mock()
        database.execute.return_value = [
            (ident, 'test', ident, hashlib.sha256(raw).hexdigest(), len(raw))
            for ident, raw in payloads.items()
        ]
        storage = Mock()
        storage.get_object.side_effect = lambda **args: {'Body': io.BytesIO(payloads[args['Key']])}
        parts = ['second', 'first']
        combined = b''.join(payloads[ident] for ident in parts)
        multipart = dict(parts=parts, sha256=hashlib.sha256(combined).hexdigest(),
                         size_bytes=len(combined), filename='terrain.tif')
        with (tempfile.TemporaryDirectory() as directory,
              patch('boto3.client', return_value=storage)):
            runtime = Runtime(connect=lambda: nullcontext(database),
                              recipe_id='test', method='watershed_boundary', arguments={},
                              work_dir=Path(directory))
            paths = acquire_sources(runtime, ['standalone', multipart],
                                    evidence_source_ids=['evidence'])
            self.assertEqual([path.read_bytes() for path in paths],
                             [payloads['standalone'], combined])
            self.assertEqual(paths[1].name, 'terrain.tif')

        database.execute.assert_called_once()
        self.assertCountEqual(database.execute.call_args.args[1][0], payloads)
        self.assertCountEqual([call.kwargs['Key'] for call in storage.get_object.call_args_list],
                              ['standalone', 'first', 'second'])
