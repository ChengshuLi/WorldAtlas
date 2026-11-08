import contextlib, gzip, hashlib, io, json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import verify_basin_coverage as v


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


class CoverageTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        # Two rows, width 4; the physical land cell is row 0, column 1.
        np.array([0,3,4],dtype='<u4').tofile(self.root/'rows')
        np.array([1,1,2,17,4,1,4,1],dtype='<u4').tofile(self.root/'runs')
        np.array([[1,1,0,0],[0,1,1,0]],dtype='u1').tofile(self.root/'source-mask.dat')
        self.records=[{'row':0,'spans':[{'start':0,'end':1,'code':6}]},
                      {'row':1,'spans':[{'start':1,'end':3,'code':6}]}]
        self.write_spans()
        self.policy={'schema':'worldatlas-geography-decision-export-v1','source':'neon-export',
                     'decision_revision':{'id':'d','entity_revision':'e','status':'accepted'},
                     'entity_revision':{'id':'e','status':'accepted'},
                     'category_bindings':[{'entity_id':6,'physical_class':'water','code':6}],
                     'basins':[{'id':'b','source_id':'s','source_version':'v','source_feature_id':'1',
                                'geometry_sha256':'g'*64,'assignment_method':'single_continent_named_basin','participant_entity_ids':[6]}],
                     'sources':[{'source_id':'s','version':'v','sha256':'a'*64}]}
        (self.root/'policy.json').write_text(json.dumps(self.policy))
        self.doc={'grid':{'width':4,'height':2},'source':{'physical_rows_sha256':sha(self.root/'rows'),
                 'physical_runs_sha256':sha(self.root/'runs'),'policy_sha256':sha(self.root/'policy.json'),
                 'decision_revision':'d','entity_revision':'e','decision_status':'accepted','decision_id':'b',
                 'source_id':'s','source_version':'v','source_feature_id':'1','canonical_geometry_sha256':'g'*64,
                 'source_file_sha256':'a'*64,'assignment_method':'single_continent_named_basin'},
                  'rasterization':{'bounds_columns_rows':[0,4,0,2],'source_mask_sha256':sha(self.root/'source-mask.dat')},
                  'tiles':[{'core_rows':[0,2],'core_cols':[0,4],'span_file':{'path':'assign.gz','sha256':sha(self.root/'assign.gz')}}],
                  'physical_water_cells':3,'span_count':2}
        self.write_manifest()

    def tearDown(self): self.tmp.cleanup()
    def write_spans(self):
        with gzip.open(self.root/'assign.gz','wt') as f:
            for rec in self.records:f.write(json.dumps(rec)+'\n')
    def write_manifest(self): (self.root/'manifest.json').write_text(json.dumps(self.doc))
    def repin_spans(self):
        self.write_spans();self.doc['tiles'][0]['span_file']['sha256']=sha(self.root/'assign.gz');self.write_manifest()
    def run_verifier(self,manifest_hash=None,shared_inputs=None):
        p=self.root/'manifest.json'
        argv=['verify','--manifest',str(p),'--manifest-sha256',manifest_hash or sha(p),
              '--physical-rows',str(self.root/'rows'),'--physical-runs',str(self.root/'runs'),
              '--policy',str(self.root/'policy.json'),'--policy-sha256',sha(self.root/'policy.json')]
        with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):v.main(shared_inputs=shared_inputs)

    def test_match(self): self.run_verifier()
    def test_verified_shared_generation_is_used_without_rehashing_mutable_paths(self):
        from verified_water_inputs import VerifiedWaterInputs
        land_rows=self.root/'land-rows';land_runs=self.root/'land-runs'
        land_rows.write_bytes((self.root/'rows').read_bytes())
        np.asarray([1,0,2,18,4,0,4,0],dtype='<u4').tofile(land_runs)
        specs={}
        for name,path in [('physical_rows',self.root/'rows'),('physical_runs',self.root/'runs'),('land_rows',land_rows),('land_runs',land_runs)]:
            specs[name]={'path':path,'sha256':sha(path)}
        with VerifiedWaterInputs(specs,4,2,work_root=self.root) as verified:
            original_sha=v.sha
            def reject_rehash(path):
                if path in (self.root/'rows',self.root/'runs'):raise AssertionError('must reuse snapshot')
                return original_sha(path)
            with patch.object(v,'sha',side_effect=reject_rehash):self.run_verifier(shared_inputs=verified)
    def test_missing_and_extra_cells(self):
        self.records[1]['spans'][0]['end']=2;self.repin_spans()
        with self.assertRaisesRegex(ValueError,'coverage mismatch'):self.run_verifier()
        self.records[1]['spans'][0]['end']=4;self.repin_spans()
        with self.assertRaisesRegex(ValueError,'coverage mismatch'):self.run_verifier()
    def test_invalid_spans_and_rows(self):
        self.records[0]['spans'][0]['end']=5;self.repin_spans()
        with self.assertRaisesRegex(ValueError,'invalid span'):self.run_verifier()
        self.records[0]['spans'][0]['end']=1;self.records[0]['spans'][0]['code']=2;self.repin_spans()
        with self.assertRaisesRegex(ValueError,'invalid span'):self.run_verifier()
        self.records[0]['spans'][0]['code']=6;self.records.reverse();self.repin_spans()
        with self.assertRaisesRegex(ValueError,'coverage mismatch|unordered'):self.run_verifier()
    def test_tampered_hashes(self):
        with self.assertRaisesRegex(ValueError,'manifest hash'):self.run_verifier('0'*64)
        with (self.root/'runs').open('ab') as f:f.write(b'!')
        with self.assertRaisesRegex(ValueError,'physical hash'):self.run_verifier()
    def test_decision_mismatch_rejected(self):
        self.doc['source']['canonical_geometry_sha256']='h'*64;self.write_manifest()
        with self.assertRaisesRegex(ValueError,'does not match'):self.run_verifier()
        self.doc['source']['canonical_geometry_sha256']='g'*64
        self.doc['source']['policy_sha256']='0'*64;self.write_manifest()
        with self.assertRaisesRegex(ValueError,'does not match'):self.run_verifier()
    def test_tampered_raster_and_assignment(self):
        with (self.root/'source-mask.dat').open('ab') as f:f.write(b'!')
        with self.assertRaisesRegex(ValueError,'raster size or hash'):self.run_verifier()
        np.array([[1,1,0,0],[0,1,1,0]],dtype='u1').tofile(self.root/'source-mask.dat')
        with (self.root/'assign.gz').open('ab') as f:f.write(b'!')
        with self.assertRaisesRegex(ValueError,'assignment path or hash'):self.run_verifier()

if __name__=='__main__': unittest.main()
