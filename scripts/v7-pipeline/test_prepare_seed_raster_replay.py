import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from osgeo import ogr
import prepare_seed_raster_replay as replay


class SeedRegionReplayTests(unittest.TestCase):
    def test_physical_equivalence_covers_supported_report_shapes_and_grid_changes(self):
        for width,height in ((8,2),(3600,100)):
            grid={'width':width,'height':height,'step':360/width,'west':-180,'north':90}
            current={'status':'candidate-only','grid':grid,'output_sha256':{'rows.u32le':'a'*64,'runs.u32le':'b'*64}}
            prior={'status':'stage1-complete','grid':grid,'physical_output_sha256':{'rows.u32le':'a'*64,'runs.u32le':'b'*64}}
            replay.physical_equivalence(current,prior,grid,'a'*64,'b'*64)
            prior['physical_output_sha256']['runs.u32le']='c'*64
            with self.assertRaisesRegex(ValueError,'not byte-equivalent'):
                replay.physical_equivalence(current,prior,grid,'a'*64,'b'*64)

    def test_contract_uses_selected_grid_and_read_only_encoding_pin(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            source=Path(temp)/'encoding.py';source.write_text('WATER=1\nLAND=17\n')
            for width in (8,3600):
                grid={'width':width,'height':2,'step':360/width,'west':-180,'north':90}
                result=replay.closure_contract(grid,'a'*64,'b'*64,'c'*64,source)
                self.assertEqual(result['grid']['step_denominator'],width)
                self.assertEqual(result['physical']['encoding_evidence_sha256'],replay.digest(source))
                self.assertEqual(result['physical']['producer_code_path'],str(source.resolve()))

    def test_normal_producer_modules_use_python_api_and_restore_caller_cache(self):
        wrong=types.ModuleType('regions');wrong.__file__='/wrong/regions.py'
        with patch.dict(sys.modules,{'regions':wrong}),patch('subprocess.Popen',side_effect=AssertionError('process launch')),patch('ctypes.CDLL',side_effect=AssertionError('ctypes binding')):
            with replay.producer_modules() as (modules,pins):
                self.assertEqual(set(modules),{'regions','closure_client','export_adapter','region_client'})
                self.assertIsNot(modules['regions'],wrong)
                self.assertTrue(callable(modules['region_client'].execute))
                self.assertEqual(len(pins),4)
            self.assertIs(sys.modules['regions'],wrong)


if __name__=='__main__':unittest.main()
