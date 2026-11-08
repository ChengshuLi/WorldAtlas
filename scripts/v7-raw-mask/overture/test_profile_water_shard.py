import ctypes
import json
import subprocess
import unittest
from unittest import mock

import profile_water_shard as profile
import test_rasterize_water_shard as fixture


class WaterProfileTests(unittest.TestCase):
    setUp=fixture.WaterShardTests.setUp
    tearDown=fixture.WaterShardTests.tearDown
    fixture=fixture.WaterShardTests.fixture

    def test_profile_uses_python_apis_and_matches_complete_reference(self):
        source,digest=self.fixture();reference=self.path/'reference';output=self.path/'profile'
        with mock.patch.object(subprocess,'Popen',side_effect=AssertionError('unexpected subprocess')), \
                mock.patch.object(ctypes,'CDLL',side_effect=AssertionError('unexpected ctypes bridge')):
            profile.benchmark.build.run(source,digest,reference,self.config,engine='python')
            report=profile.run(source,digest,self.config,reference,output)
        self.assertEqual(report['status'],'profiled-input-matches-pinned-reference')
        self.assertEqual(report['different_pixels'],0)
        self.assertTrue((output/'profile.pstats').is_file())
        self.assertTrue(any('Geometry_IsValid' in row['function'] for row in report['functions']))
        self.assertEqual(json.loads((output/'profile.json').read_bytes())['source_sha256'],digest)

    def test_changed_reference_fails_before_processing(self):
        source,digest=self.fixture();reference=self.path/'reference'
        profile.benchmark.build.run(source,digest,reference,self.config)
        (reference/'water.tif').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'reference identity mismatch'):
            profile.run(source,digest,self.config,reference,self.path/'not-created')
        self.assertFalse((self.path/'not-created').exists())


if __name__=='__main__':unittest.main()
