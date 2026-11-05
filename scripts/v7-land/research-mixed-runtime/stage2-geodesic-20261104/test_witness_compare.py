import copy
import hashlib
import json
import unittest
import witness_compare as w


def dump(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':')).encode()

class Compare(unittest.TestCase):
    def setUp(self):
        self.req = {'schema':'mainland-witness-request-v1', 'grid':{'width':8,'height':4,'west':-180,'north':90,'step':45},
          'source_files':[{'source_id':'s','version':'1','path':'/s','sha256':'a'*64}],
          'code_sha256':{k:'a'*64 for k in w.CODE_NAMES}}
        self.req.update({k:{'path':'/'+k,'sha256':'b'*64} for k in w.PIN_NAMES})
        self.report = {'schema':'mainland-witness-resolution-v1','status':'selected-research-identity-claims-not-mainland-proof','publishable':False,
          'decision_revision':'r','entity_revision':'e','snapshot_sha256':'b'*64,'component_manifest_sha256':'b'*64,
          'component_lineage_mode':'fresh','grid':copy.deepcopy(self.req['grid']),
          'input_sha256':{k:'b'*64 for k in ('physical_rows','physical_runs','component_rows','component_runs')},
          'code_sha256':copy.deepcopy(self.req['code_sha256']), 'groups':[{'group_id':'g','component_id_current_generation_only':42}],
          'witnesses':[{'row':1,'identity_check':{'strict_contains':True,'gdal_version':'x'}}],
          'relations_checked':[],'limitations':['not a build'], 'request_sha256':hashlib.sha256(dump(self.req)).hexdigest()}
        self.new_req=copy.deepcopy(self.req);self.new_req['code_sha256']['helper']='c'*64
        self.new_report=copy.deepcopy(self.report);self.new_report['code_sha256']=copy.deepcopy(self.new_req['code_sha256']);self.new_report['request_sha256']=hashlib.sha256(dump(self.new_req)).hexdigest()
    def check(self):return w.compare_witness_resolutions(dump(self.req),dump(self.report),dump(self.new_req),dump(self.new_report))
    def rebind(self):self.new_report['request_sha256']=hashlib.sha256(dump(self.new_req)).hexdigest()
    def test_code_changes_only_match(self):
        out=self.check();self.assertEqual(out['status'],'matched');self.assertEqual(out['new_report_sha256'],hashlib.sha256(dump(self.new_report)).hexdigest())
    def test_source_or_path_change_rejected(self):
        self.new_req['source_files'][0]['path']='/different';self.rebind()
        with self.assertRaisesRegex(ValueError,'requests differ'):self.check()
    def test_nested_identity_and_root_changes_rejected(self):
        for field,value in [('strict_contains',False),('gdal_version','other')]:
            old=self.new_report['witnesses'][0]['identity_check'][field];self.new_report['witnesses'][0]['identity_check'][field]=value
            with self.assertRaisesRegex(ValueError,'resolutions differ'):self.check()
            self.new_report['witnesses'][0]['identity_check'][field]=old
        self.new_report['groups'][0]['component_id_current_generation_only']=43
        with self.assertRaisesRegex(ValueError,'resolutions differ'):self.check()
    def test_type_mismatch_rejected(self):
        self.new_report['witnesses'][0]['row']=True
        with self.assertRaisesRegex(ValueError,'resolutions differ'):self.check()
    def test_request_or_report_tampering_rejected(self):
        self.new_report['request_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.check()
        self.new_report['request_sha256']=hashlib.sha256(dump(self.new_req)).hexdigest();self.new_report['code_sha256']['helper']='f'*64
        with self.assertRaisesRegex(ValueError,'code pin mismatch'):self.check()
    def test_report_request_input_mismatch_rejected(self):
        self.new_report['input_sha256']['physical_rows']='f'*64
        with self.assertRaisesRegex(ValueError,'input binding'):self.check()
    def test_unknown_schema_and_keys_rejected(self):
        self.new_report['future_field']=1
        with self.assertRaisesRegex(ValueError,'report schema'):self.check()
        del self.new_report['future_field'];self.new_req['future']=1;self.rebind()
        with self.assertRaisesRegex(ValueError,'request schema'):self.check()
    def test_duplicate_keys_and_nonfinite_rejected(self):
        with self.assertRaises(ValueError):w._load(b'{"x":1,"x":2}')
        with self.assertRaises(ValueError):w._load(b'{"x":1e999}')
    def test_nested_additions_and_order_rejected(self):
        self.new_report['witnesses'][0]['identity_check']['unknown']=1
        with self.assertRaisesRegex(ValueError,'resolutions differ'):self.check()
        del self.new_report['witnesses'][0]['identity_check']['unknown'];self.new_report['limitations'].append('other')
        with self.assertRaisesRegex(ValueError,'resolutions differ'):self.check()

if __name__ == '__main__':unittest.main()
