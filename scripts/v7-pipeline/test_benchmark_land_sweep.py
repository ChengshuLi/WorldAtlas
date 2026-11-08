"""Exercise the reusable complete-input sweep benchmark on pinned synthetic streams."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from benchmark_land_sweep import benchmark, STAGE2
from benchmark_stage import digest

sys.path.insert(0,str(STAGE2))
import preflight
import write_land_stream


class LandStreamBenchmarkTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.reference=self.root/'reference';self.reference.mkdir()
        self.inputs=self.reference/'inputs';self.inputs.mkdir()
        self.core=self.reference/'work/stage2-provisional-only/core';self.core.mkdir(parents=True)
        self.requests=self.core.parent/'core-requests';self.requests.mkdir()
        self.grid={'width':4,'height':1,'west':-180,'north':90,'step':90}
        self.pins={}
        def put(name,data):
            path=self.inputs/name
            path.write_bytes(data)
            self.pins[name]={'path':str(path),'sha256':digest(path)}
            return path
        u32=lambda *v:struct.pack('<'+'I'*len(v),*v)
        put('component_rows',u32(0,3));put('component_runs',u32(0,1,1,1,2,2,2,4,10))
        put('physical_rows',u32(0,1));put('physical_runs',u32(4,17))
        put('seed_rows',u32(0,3));put('seed_runs',u32(1,17,2,18,4,0))
        roots=put('hint_roots',u32(10));codes=self.inputs/'codes';codes.write_bytes(bytes([20]))
        seed={'seed_rules':[
            {'component_id_current_generation_only':1,'inside_code':17,'outside_code':17,'region_id':None},
            {'component_id_current_generation_only':2,'inside_code':18,'outside_code':18,'region_id':None}],
            'rule_population':{'1':{'inside_cells':1,'outside_cells':0},'2':{'inside_cells':1,'outside_cells':0}},
            'category_cell_counts':{'17':1,'18':1}}
        put('seed_report',json.dumps(seed).encode());put('decision_snapshot',b'{}')
        streams=[Path(self.pins[name]['path']) for name in (
            'component_rows','component_runs','physical_rows','physical_runs','seed_rows','seed_runs')]
        stage=self.reference/'stage2-provisional-only'
        write_land_stream.write_land_stream(4,1,*streams,roots,codes,[1,2],stage,disk_reserve_bytes=0)
        coverage=preflight.validate(4,1,*streams,[10],[1,2],required_codes=[17,18])
        np.savez(self.core/'checkpoint.npz',roots=np.array([10],dtype='<u4'),hints=np.array([20],dtype='u1'),
                 amb=np.array([False]),best=np.full((1,6),np.inf))
        config={'grid':self.grid,'inputs':self.pins}
        configpath=self.requests/'config.json';configpath.write_text(json.dumps(config))
        report={'config_sha256':digest(configpath),'checkpoint_sha256':digest(self.core/'checkpoint.npz'),
                'inputs_sha256':{name:pin['sha256'] for name,pin in self.pins.items()},
                'physical_coverage':coverage,'land_baseline_policy':{'tie_tolerance_metres':'0.00001'},
                'ties':[],'categories':{'17':'Africa','18':'Asia'}}
        report.update({'output_rows_sha256':digest(stage/'rows.u32le'),'output_runs_sha256':digest(stage/'runs.u32le')})
        (stage/'report.json').write_text(json.dumps(report))

    def test_complete_sweeps_and_expected_bytes_without_process_launches(self):
        with patch('ural_delta.compile_rule',return_value=None), patch('subprocess.Popen',side_effect=AssertionError('process launch')):
            result=benchmark(self.reference,self.root/'benchmark')
        self.assertEqual(result['status'],'all-complete-land-streams-and-coverage-identical')
        self.assertEqual(result['coverage']['land_cells'],4)
        self.assertGreaterEqual(result['writer_seconds'],0)
        self.assertTrue((self.root/'benchmark/comparison.json').is_file())

    def test_changed_source_is_rejected_before_output_creation(self):
        Path(self.pins['seed_runs']['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'input hash mismatch'):
            benchmark(self.reference,self.root/'benchmark')
        self.assertFalse((self.root/'benchmark').exists())

    def test_changed_reference_output_cannot_pass_comparison(self):
        (self.reference/'stage2-provisional-only/runs.u32le').write_bytes(b'changed')
        with patch('ural_delta.compile_rule',return_value=None):
            with self.assertRaisesRegex(ValueError,'reference land streams differ'):
                benchmark(self.reference,self.root/'benchmark')
        self.assertFalse((self.root/'benchmark/comparison.json').exists())


if __name__=='__main__':unittest.main()
