"""Runtime identity requires Python bindings, not an obsolete build compiler."""

import os
import unittest
from unittest.mock import patch

from worldatlas.map_build import build as pipeline


class RuntimePrerequisiteTests(unittest.TestCase):
    def test_identity_works_without_executable_search_path(self):
        with patch.dict(os.environ, {'PATH': ''}), patch.object(
            pipeline.shutil, 'which', side_effect=AssertionError('no external tool lookup')
        ):
            identity = pipeline.runtime_identity()
        self.assertNotIn('tools', identity)
        for field in (
            'numpy',
            'scipy',
            'pyproj',
            'proj',
            'gdal',
            'pyarrow',
            'binary_sha256',
            'proj_database',
        ):
            self.assertIn(field, identity)
        self.assertEqual(len(identity['proj_database']['sha256']), 64)

if __name__ == '__main__':
    unittest.main()
