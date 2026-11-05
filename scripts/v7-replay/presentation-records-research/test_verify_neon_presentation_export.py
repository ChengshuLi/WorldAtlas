import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import verify_neon_presentation_export as v

class NeonExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        records={'schema':'worldatlas-island-presentation-v1','source':{'revision':'fictional'},'groups':[],'leaves':[]}
        rr=v.canonical_records(records)
        (self.root/'presentation-records-local.json').write_bytes(rr)
        assets={};pins={};cols={}
        manifest={'schema':'worldatlas-presentation-parity-manifest-v2','release_id':'fictional','assets':{'records':hashlib.sha256(rr).hexdigest()}}
        for i,(name,(filename,prefix)) in enumerate(v.ASSET_FILES.items()):
            raw=('fictional-'+name).encode()
            (self.root/filename).write_bytes(raw)
            asset={'source_id':'s'+str(i),'version':'v1','r2_bucket':'b','r2_key':'k'+str(i),'sha256':hashlib.sha256(raw).hexdigest(),'size_bytes':len(raw)}
            assets[name]=asset
            pins[name]=dict(asset)
            cols[prefix+'_source_id']=asset['source_id'];cols[prefix+'_source_version']=asset['version']
            manifest['assets'][name]=asset['sha256']
        manifest['sources']=pins
        self.manifest=self.root/'manifest'
        self.manifest.write_text(json.dumps(manifest))
        self.manifest_sha=hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        release={**cols,'release_id':'fictional','release_kind':'historical_review_presentation','manifest_sha256':self.manifest_sha,'records_sha256':hashlib.sha256(rr).hexdigest(),'source_pins':pins,'records':records}
        self.snapshot={'schema':'worldatlas-neon-presentation-export-v1','origin':{'project_id':'p','branch_id':'b','database':'d'},'release':release,'assets':assets}
        self.path=self.root/'snapshot'
        self.write_snapshot()
        self.mock=patch.object(v.parity,'verify',return_value={'status':'parity-verified-not-deployed','limitations':[]})
        self.mock.start();self.addCleanup(self.mock.stop)
    def write_snapshot(self):
        self.path.write_text(json.dumps(self.snapshot))
        self.snap_sha=hashlib.sha256(self.path.read_bytes()).hexdigest()
    def check(self):
        return v.verify(self.path,self.snap_sha,self.manifest,self.manifest_sha,self.root,'p','b','d')
    def test_matching_export(self):
        self.assertEqual(self.check()['status'],'presentation-export-parity-verified-not-authenticated-or-deployed')
    def test_wrong_origin_rejected(self):
        self.snapshot['origin']['branch_id']='other';self.write_snapshot()
        with self.assertRaisesRegex(ValueError,'wrong Neon origin'):self.check()
    def test_missing_or_modified_asset_rejected(self):
        self.snapshot['assets']['proposal']['r2_key']='other';self.write_snapshot()
        with self.assertRaisesRegex(ValueError,'asset row and release pin disagree'):self.check()
    def test_bad_fk_rejected(self):
        self.snapshot['release']['proposal_source_id']='other';self.write_snapshot()
        with self.assertRaisesRegex(ValueError,'asset foreign key mismatch'):self.check()
    def test_changed_row_and_pin_still_fail_trusted_manifest(self):
        self.snapshot['assets']['proposal']['r2_key']='other'
        self.snapshot['release']['source_pins']['proposal']['r2_key']='other'
        self.write_snapshot()
        with self.assertRaisesRegex(ValueError,'manifest/source identity mismatch'):self.check()
    def test_modified_r2_readback_rejected(self):
        (self.root/'proposal.json').write_bytes(b'not-the-source')
        with self.assertRaisesRegex(ValueError,'R2 readback mismatch'):self.check()
    def test_jsonb_semantic_change_rejected(self):
        self.snapshot['release']['records']['groups'].append({'id':'altered'});self.write_snapshot()
        with self.assertRaisesRegex(ValueError,'canonical JSONB records mismatch'):self.check()
    def test_numeric_record_rejected(self):
        with self.assertRaisesRegex(ValueError,'only strings'):v.canonical_records({'value':1})
        with self.assertRaisesRegex(ValueError,'only strings'):v.canonical_records({'value':True})
    def test_boolean_size_is_not_integer(self):
        bad=dict(self.snapshot['release']['source_pins']['proposal'])
        bad['size_bytes']=True
        self.assertFalse(v.valid_pin(bad))
        self.snapshot['release']['source_pins']['proposal']=bad
        self.write_snapshot()
        with self.assertRaisesRegex(ValueError,'invalid typed source pin'):self.check()
    def test_wrong_snapshot_hash_rejected(self):
        with self.assertRaisesRegex(ValueError,'Neon export hash mismatch'):
            v.verify(self.path,'0'*64,self.manifest,self.manifest_sha,self.root,'p','b','d')

if __name__=='__main__':unittest.main()

