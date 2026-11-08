import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import stage_land_sweep_inputs as staging


def sha(data):return hashlib.sha256(data).hexdigest()


class Client:
    def __init__(self, data):self.data=data;self.gets=[]
    def get_object(self, Bucket, Key):
        self.gets.append((Bucket,Key));data=self.data[Key]
        return {'ContentLength':len(data),'Body':io.BytesIO(data)}
    def get_paginator(self, name):return self
    def paginate(self, **kwargs):return [{'Contents':[]}]


class StagingTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.data={name:name.encode() for name in (*staging.METADATA,*staging.STREAMS)}
        self.data['fresh-stage2-land-report']=json.dumps({'checkpoint_sha256':'a'*64}).encode()
        config={'grid':{'width':8,'height':2,'west':-180,'north':90,'step':45},
                'inputs':{name:{'path':'/original/'+source,'sha256':sha(self.data[source])} for name,source in staging.INPUTS.items()}}
        self.data['fresh-stage2-core-config']=json.dumps(config).encode()
        self.catalog=self.root/'catalog.json';self.config=self.root/'core.json';self.out=self.root/'out'
        self.config.write_bytes(self.data['fresh-stage2-core-config'])
        rows=[{'source_id':name,'version':'test','r2_bucket':'bucket','r2_key':name,
               'sha256':sha(data),'size_bytes':str(len(data))} for name,data in self.data.items()]
        self.catalog.write_text(json.dumps(rows));self.client=Client(self.data)

    def test_metadata_only_never_fetches_global_streams_and_reuses_exact_bytes(self):
        with patch('subprocess.Popen',side_effect=AssertionError('process launch')):
            result=staging.stage(self.catalog,self.config,self.out,self.client)
        self.assertEqual(result['checkpoint_candidates'],[])
        self.assertEqual({key for bucket,key in self.client.gets},set(staging.METADATA))
        self.client.gets.clear();staging.stage(self.catalog,self.config,self.out,self.client)
        self.assertEqual(self.client.gets,[])
        self.assertEqual((self.out/'fresh-stage2-core-config').read_bytes(),self.config.read_bytes())

    def test_full_streams_are_pinned_and_partial_tamper_fails(self):
        result=staging.stage(self.catalog,self.config,self.out,self.client,stage_streams=True)
        self.assertEqual(set(result['inputs']),set(staging.INPUTS))
        # A later metadata-only inventory stays deterministic after bulk staging.
        staging.stage(self.catalog,self.config,self.out,self.client)
        staging.stage(self.catalog,self.config,self.out,self.client)
        (self.out/'fresh-stage2-seed-runs').write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError,'staged input differs'):
            staging.stage(self.catalog,self.config,self.out,self.client,stage_streams=True)

    def test_cloud_corruption_has_no_success_marker(self):
        self.client.data=dict(self.data);self.client.data['fresh-stage2-core-config']=b'wrong'
        with self.assertRaisesRegex(ValueError,'cloud input .* differs'):
            staging.stage(self.catalog,self.config,self.out,self.client)
        self.assertFalse((self.out/'metadata-staged.json').exists())

    def test_catalog_core_mismatch_fails_before_output_creation(self):
        value=json.loads(self.catalog.read_bytes());value[0]['source_id']='duplicate'
        self.catalog.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'catalog entry required'):
            staging.stage(self.catalog,self.config,self.out,self.client)
        self.assertFalse(self.out.exists())

    def test_identity_change_is_rejected_without_rewriting_sources(self):
        staging.stage(self.catalog,self.config,self.out,self.client)
        identity=(self.out/'plan.json').read_bytes()
        self.catalog.write_text(self.catalog.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'identity changed'):
            staging.stage(self.catalog,self.config,self.out,self.client)
        self.assertEqual((self.out/'plan.json').read_bytes(),identity)


if __name__=='__main__':unittest.main()
