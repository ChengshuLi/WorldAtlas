"""Complete in-process land replay derives decisions before reading expected labels."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from replay_land_sweep import replay
import replay_land_sweep as driver
from stage_land_sweep_inputs import INPUTS, METADATA, STREAMS


def packed(*values):return struct.pack('<'+'I'*len(values),*values)
def sha(data):return hashlib.sha256(data).hexdigest()


class ReplayTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2])
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.stage=self.root/'inputs';self.stage.mkdir()
        data={name:name.encode() for name in (*METADATA,*STREAMS)}
        data['fresh-components-rows']=packed(0,6,7)
        data['fresh-components-runs']=packed(*[value for x in range(6) for value in (x,x+1,x+1)],0,1,10)
        data['fresh-physical-rows']=packed(0,2,4);data['fresh-physical-runs']=packed(6,17,8,1,1,17,8,1)
        data['fresh-stage2-seed-rows']=packed(0,7,8)
        data['fresh-stage2-seed-runs']=packed(*[value for x in range(6) for value in (x+1,17+x)],8,0,8,0)
        data['fresh-stage2-hint-roots']=packed(10);data['fresh-stage2-hints']=bytes([17])
        data['fresh-stage2-land-rows']=packed(0,7,9)
        data['fresh-stage2-land-runs']=packed(*[value for x in range(6) for value in (x+1,17+x)],8,0,1,17,8,0)
        seed={'seed_rules':[{'component_id_current_generation_only':root,'inside_code':root+16,
            'outside_code':root+16,'region_id':None} for root in range(1,7)],
            'rule_population':{str(root):{'inside_cells':1,'outside_cells':0} for root in range(1,7)},
            'category_cell_counts':{str(code):1 for code in range(17,23)}}
        data['fresh-stage2-seed-report']=json.dumps(seed).encode()
        grid={'width':8,'height':2,'west':-180,'north':90,'step':45}
        config={'grid':grid,'inputs':{name:{'path':'/immutable/'+source,'sha256':sha(data[source])} for name,source in INPUTS.items()},
            'controls':{'minimum_free_bytes':0,'numerical_guard_metres':1000,'chunk_columns':1024,
                        'checkpoint_seconds':30,'block_records':10000}}
        tile=b''.join(packed(0,x,x+1,17+x) for x in range(6))
        extra={'representatives':np.asarray([[0,0,0,x,17+x] for x in range(6)],dtype='<u4').tobytes(),
               'tile_manifest':f'0 0 6 63 {sha(tile)}\n'.encode(),'decision_snapshot':b'{}'}
        for name,value in extra.items():config['inputs'][name]={'path':'/immutable/'+name,'sha256':sha(value)}
        data['fresh-stage2-core-config']=json.dumps(config).encode()
        coverage={'land_cells':7,'nonseed_roots':1,'seed_roots':list(range(1,7)),
                  'seed_codes':list(range(17,23)),'seed_category_cells':{str(code):1 for code in range(17,23)}}
        report={'config_sha256':sha(data['fresh-stage2-core-config']),
            'inputs_sha256':{name:pin['sha256'] for name,pin in config['inputs'].items()},
            'output_rows_sha256':sha(data['fresh-stage2-land-rows']),
            'output_runs_sha256':sha(data['fresh-stage2-land-runs']),
            'physical_coverage':coverage,'categories':{str(code):str(code) for code in range(17,23)},
            'land_baseline_policy':{'tie_tolerance_metres':'0.00001'},'ties':[]}
        data['fresh-stage2-land-report']=json.dumps(report).encode()
        plan={'schema':'worldatlas-land-sweep-staging-plan-v1','grid':grid,'core_config_sha256':report['config_sha256'],
              'assets':{name:{'sha256':sha(value),'size_bytes':len(value)} for name,value in data.items()}}
        for name,value in data.items():(self.stage/name).write_bytes(value)
        (self.stage/'plan.json').write_text(json.dumps(plan))
        pins={}
        for name,value in extra.items():
            path=self.stage/name;path.write_bytes(value)
            pins[name]={'path':str(path),'sha256':sha(value),'size_bytes':len(value)}
        (self.stage/'search-inputs.json').write_text(json.dumps({'parent_plan_sha256':sha((self.stage/'plan.json').read_bytes()),'inputs':pins}))

    def test_complete_coverage_without_processes(self):
        with patch('subprocess.Popen',side_effect=AssertionError('process launch')):
            result=replay(self.stage,self.root/'out')
        self.assertEqual(result['coverage']['land_cells'],7)
        self.assertEqual(result['status'],'complete-global-preflight-identical')
        self.assertIn('started_at_utc',result['phase_utc']['preflight'])
        self.assertIn('completed_at_utc',result)

    def test_fresh_source_search_and_writer_match_all_expected_bytes(self):
        with patch('subprocess.Popen',side_effect=AssertionError('process launch')),patch('ctypes.CDLL',side_effect=AssertionError('ctypes binding')),patch('ural_delta.compile_rule',return_value=None):
            result=replay(self.stage,self.root/'out',search=True)
        self.assertEqual(result['status'],'complete-source-bound-search-and-land-streams-identical')
        self.assertEqual((self.root/'out/codes.u8').read_bytes(),bytes([17]))
        self.assertTrue((self.root/'out/checkpoint.npz').is_file())

    def test_search_inputs_are_rechecked_after_writing(self):
        original=driver.land_writer.write_land_stream
        def write_then_change(*args,**kwargs):
            result=original(*args,**kwargs)
            (self.stage/'decision_snapshot').write_bytes(b'changed')
            return result
        with patch('ural_delta.compile_rule',return_value=None),patch.object(driver.land_writer,'write_land_stream',side_effect=write_then_change):
            with self.assertRaisesRegex(ValueError,'search input changed'):
                replay(self.stage,self.root/'out',search=True)
        self.assertFalse((self.root/'out/comparison.json').exists())

    def test_staging_identity_is_byte_bound_until_completion(self):
        original=driver.preflight.validate
        def check_then_change(*args,**kwargs):
            result=original(*args,**kwargs)
            path=self.stage/'plan.json';path.write_text(path.read_text()+' ')
            return result
        with patch.object(driver.preflight,'validate',side_effect=check_then_change):
            with self.assertRaisesRegex(ValueError,'staging plan changed'):
                replay(self.stage,self.root/'out')
        self.assertFalse((self.root/'out/comparison.json').exists())

    def test_corrupt_staged_stream_is_rejected_before_output_creation(self):
        (self.stage/'fresh-stage2-seed-runs').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'size/hash mismatch'):
            replay(self.stage,self.root/'out')
        self.assertFalse((self.root/'out').exists())


if __name__=='__main__':unittest.main()
