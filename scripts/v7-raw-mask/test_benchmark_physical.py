import ctypes
import io
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

import benchmark_physical as benchmark
import test_build_physical as fixture


class PhysicalBenchmarkTests(unittest.TestCase):
    setUp=fixture.PipelineTests.setUp
    tearDown=fixture.PipelineTests.tearDown

    def test_complete_land_pair_uses_python_apis_and_restores_environment(self):
        checkout=Path(benchmark.__file__).resolve().parents[2]
        before=os.environ.get('TMPDIR');original=sys.modules['build']
        with mock.patch.object(subprocess,'Popen',side_effect=AssertionError('unexpected subprocess')), \
                mock.patch.object(ctypes,'CDLL',side_effect=AssertionError('unexpected ctypes bridge')):
            report=benchmark.run('land',self.land_cfg,checkout,self.root/'land-benchmark',2,discard=True)
        self.assertEqual(report['execution_mode'],'in-process-python-api')
        self.assertEqual(len(report['results']),2)
        self.assertEqual([item['different_pixels'] for item in report['results']],[0,0])
        self.assertEqual(os.environ.get('TMPDIR'),before)
        self.assertIs(sys.modules['build'],original)
        for item in report['results']:
            for run in item['runs'].values():
                self.assertIn('build',run['helper_sha256'])
                self.assertTrue(run['started_at_utc'].endswith('+00:00'))
                self.assertFalse((Path(run['output'])/'land.tif').exists())

    def test_selected_helper_isolated_from_cached_caller_and_restored(self):
        code=self.root/'api';code.mkdir();(code/'build.py').write_text('VALUE = "selected helper"\n')
        (code/'rasterize_land.py').write_text('from build import VALUE\ndef run(config, output):\n return VALUE\n')
        original=sys.modules['build']
        value,pins=benchmark.invoke(code,'rasterize_land.py',None,None,io.StringIO())
        self.assertEqual(value,'selected helper');self.assertIn('build',pins)
        self.assertIs(sys.modules['build'],original)

    def test_complete_composition_pair_preserves_all_stream_bytes(self):
        checkout=Path(benchmark.__file__).resolve().parents[2]
        with mock.patch.object(subprocess,'Popen',side_effect=AssertionError('unexpected subprocess')), \
                mock.patch.object(ctypes,'CDLL',side_effect=AssertionError('unexpected ctypes bridge')):
            fixture.b.run(self.config,self.root/'physical')
            report=benchmark.run('compose',self.root/'physical/configs/compose.json',checkout,self.root/'composition-benchmark',1)
        entry=report['results'][0]
        self.assertEqual(entry['different_pixels'],0)
        self.assertEqual(entry['output_sha256']['baseline'],entry['output_sha256']['candidate'])
        self.assertEqual(set(entry['output_sha256']['candidate']),{'physical-dry.tif','rows.u32le','runs.u32le'})

    def test_cli_only_stage_does_not_fall_back_to_a_process(self):
        code=self.root/'cli';code.mkdir();(code/'rasterize_land.py').write_text('VALUE = 1\n')
        original=sys.modules['build']
        with mock.patch.object(subprocess,'Popen',side_effect=AssertionError('unexpected subprocess')):
            with self.assertRaisesRegex(TypeError,'Python stage API'):
                benchmark.invoke(code,'rasterize_land.py',None,None,io.StringIO())
        self.assertIs(sys.modules['build'],original)


if __name__=='__main__':unittest.main()
