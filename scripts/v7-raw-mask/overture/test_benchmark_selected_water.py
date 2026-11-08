import json
from pathlib import Path
import subprocess
import unittest
from unittest import mock

import benchmark_selected_water as benchmark
import test_rasterize_water_shard as fixture


class SelectedWaterTests(unittest.TestCase):
    setUp=fixture.WaterShardTests.setUp
    tearDown=fixture.WaterShardTests.tearDown
    fixture=fixture.WaterShardTests.fixture

    def selection(self,missing=False):
        source,digest=self.fixture();water=json.loads(self.config.read_bytes())
        entry={'path':'missing/'+source.name if missing else source.name,'sha256':digest,
               'size':source.stat().st_size,'r2_bucket':'test','r2_key':'water/'+source.name}
        selection=self.inputs/'selected.json'
        selection.write_text(json.dumps({'schema':'worldatlas-end-to-end-pipeline-v1',
            'sources':{'water_config':{'json':water},'raw_manifest':{'json':{'file_count':1,'files':[entry]}}},
            'physical_controls':{'source_staging':{'mode':'r2-s3','endpoint_url':'https://'+'a'*32+'.r2.cloudflarestorage.com'}}}))
        return selection,source

    def test_complete_manifest_runs_both_python_backends_without_processes(self):
        selection,source=self.selection()
        with mock.patch.object(subprocess,'Popen',side_effect=AssertionError('unexpected subprocess')):
            report=benchmark.run(selection,self.path/'all')
        self.assertEqual(report['scope'],'complete-manifest')
        self.assertEqual(report['status'],'all-selected-inputs-pixels-and-diagnostics-identical')
        self.assertEqual(set(report['processing_seconds']),{'python','gdal'})
        self.assertTrue(source.exists())

    def test_owned_staged_source_is_verified_and_removed_only_after_success(self):
        selection,source=self.selection(missing=True);data=source.read_bytes();written=[]
        def download(endpoint,entry,path):path.write_bytes(data);written.append(path)
        with mock.patch.object(benchmark,'download_r2',side_effect=download):
            report=benchmark.run(selection,self.path/'staged')
        self.assertEqual(len(written),1);self.assertFalse(written[0].exists());self.assertTrue(source.exists())
        self.assertEqual(report['results'][0]['discarded_owned_source']['bytes'],len(data))


if __name__=='__main__':unittest.main()
