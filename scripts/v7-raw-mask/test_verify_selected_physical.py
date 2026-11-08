import json
import ctypes
from pathlib import Path
import subprocess
import unittest
import zipfile
from unittest import mock

import test_build_physical as fixture
import verify_selected_physical as verify


class PhysicalParityTests(unittest.TestCase):
    setUp=fixture.PipelineTests.setUp
    tearDown=fixture.PipelineTests.tearDown

    def selection(self):
        source=self.raw/'water.parquet'
        value={'schema':'worldatlas-end-to-end-pipeline-v1','selection_notes':'complete synthetic inputs',
            'sources':{'land_config':{'json':json.loads(self.land_cfg.read_bytes())},
                'water_config':{'json':json.loads(self.water_cfg.read_bytes())},
                'raw_manifest':{'json':{'file_count':1,'files':[{'path':'raw/water.parquet','sha256':fixture.b.sha(source)}]}}},
            'physical_controls':{'minimum_free_bytes':0,'union_rows_per_block':2,'physical_rows_per_block':2}}
        path=self.root/'selected.json';path.write_text(json.dumps(value));return path

    def test_complete_inputs_produce_identical_final_streams_without_processes(self):
        selection=self.selection();water=self.root/'water-parity';out=self.root/'physical-parity'
        with mock.patch.object(subprocess,'Popen',side_effect=AssertionError('unexpected subprocess')), \
                mock.patch.object(ctypes,'CDLL',side_effect=AssertionError('unexpected ctypes bridge')):
            verify.benchmark_selected_water.run(selection,water)
            report=verify.run(selection,water,self.root,out)
        self.assertEqual(report['status'],'complete-physical-pixels-and-streams-identical')
        self.assertEqual(report['different_physical_cells'],0)
        self.assertEqual(report['grid_cells'],32)
        self.assertEqual(report['raw_shard_count'],1)
        self.assertEqual(report['raw_source_rows'],1)
        for name in ('rows.u32le','runs.u32le'):
            self.assertEqual(fixture.b.sha(out/'physical-python'/name),fixture.b.sha(out/'physical-gdal'/name))
        self.assertFalse(list(out.rglob('*.so')))

    def test_incomplete_water_receipt_fails_before_processing(self):
        selection=self.selection();water=self.root/'incomplete';water.mkdir()
        (water/'benchmark.json').write_text(json.dumps({'status':'in-progress'}))
        with self.assertRaisesRegex(ValueError,'complete matching all-shard'):
            verify.run(selection,water,self.root,self.root/'not-created')
        self.assertFalse((self.root/'not-created').exists())

    def test_foreign_cached_stage_module_fails_before_processing(self):
        with mock.patch.object(verify.aggregate_compare,'__file__',str(self.root/'foreign.py')):
            with self.assertRaisesRegex(ValueError,'module resolved outside selected checkout'):
                verify.run(self.root/'not-read.json',self.root/'not-read',self.root,self.root/'not-created')
        self.assertFalse((self.root/'not-created').exists())

    def test_archive_cache_pins_and_unsafe_member_paths(self):
        source=self.land_dir/'land.geojson';temporary=self.root/'land.zip';member='land/land.geojson'
        with zipfile.ZipFile(temporary,'w') as archive:archive.writestr(member,source.read_bytes())
        digest=fixture.b.sha(temporary);folder=self.root/'inputs'/digest;folder.mkdir(parents=True)
        archive=folder/'land.zip';temporary.rename(archive);cached=folder/member;cached.parent.mkdir()
        cached.write_bytes(source.read_bytes())
        entry={'archive':{'r2_key':'sources/land.zip','sha256':digest,'size_bytes':archive.stat().st_size},
               'member':member,'sha256':fixture.b.sha(source),'size_bytes':source.stat().st_size}
        cfg={'sources':{'land_config':{'json':{'land':[{'dataset':entry,'files':[entry]}]}}}}
        result,pins=verify.cached_land_configuration(cfg,self.root/'selected.json',self.root)
        self.assertEqual(result['land'][0]['dataset'],str(cached))
        self.assertEqual(pins[str(archive)],digest)
        entry['member']='../outside'
        with self.assertRaisesRegex(ValueError,'unsafe land archive member'):
            verify.cached_land_configuration(cfg,self.root/'selected.json',self.root)


if __name__=='__main__':unittest.main()
