"""Runtime identity requires Python bindings, not an obsolete build compiler."""
import importlib.util
import os
import unittest
from unittest.mock import patch

import run_pipeline as pipeline


class RuntimePrerequisiteTests(unittest.TestCase):
    def test_validation_and_identity_work_without_executable_search_path(self):
        with patch.dict(os.environ, {'PATH': '', 'PROJ_NETWORK': 'OFF'}), \
             patch.object(pipeline.shutil, 'which', side_effect=AssertionError('no external tool lookup')):
            pipeline.validate_runtime()
            identity = pipeline.runtime_identity()
        self.assertNotIn('tools', identity)
        self.assertFalse(identity['proj_network_enabled'])
        for field in ('numpy', 'scipy', 'pyproj', 'proj', 'gdal', 'pyarrow',
                      'binary_sha256', 'proj_database'):
            self.assertIn(field, identity)
        self.assertEqual(len(identity['proj_database']['sha256']), 64)

    def test_missing_python_binding_remains_an_explicit_error(self):
        original = importlib.util.find_spec
        def find(name):
            return None if name == 'osgeo' else original(name)
        with patch.object(pipeline.importlib.util, 'find_spec', side_effect=find), \
             patch.object(pipeline.shutil, 'which', side_effect=AssertionError('no compiler lookup')):
            with self.assertRaisesRegex(ValueError, 'runtime prerequisites missing.*osgeo'):
                pipeline.validate_runtime()


if __name__ == '__main__':
    unittest.main()
