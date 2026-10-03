import importlib.util,json,pathlib,tempfile,unittest,hashlib
spec=importlib.util.spec_from_file_location('aggregate',pathlib.Path(__file__).resolve().parents[1]/'scripts/compose-macro-install-proof.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,separators=(',',':')))
def fixture(stage):
 changed=[str(i)for i in range(6)];added=['new'+str(i)for i in range(34)];before=changed+['retained'];common={'geometry_stage_validated':True,'historical_claims_transferred':False,'removed_ids':[],'source_evidence':[{'url':'https://example.org','source_sha256':'a'*64}],'relationships':[]}
 write(stage/'reference-receipt.json',{'reference_only':True,'historical_claims_transferred':False,'before_hierarchy_sha256':'a'*64});write(stage/'composition.json',{'replacement_deltas':[{'id':i,'original_pre_reference_feature':{'id':i,'properties':{'name':'Original'}}}for i in changed]});write(stage/'independent-validation.json',{'verified':True});write(stage/'preparation-summary.json',{'published':False});write(stage/'replacement-migration/migration-receipt.json',{**common,'changed_ids':changed,'added_ids':[],'reused_ids':['retained'],'before_footprints_sha256':'a'*64,'after_footprints_sha256':'b'*64});write(stage/'replacement-migration/index.json',{'version':1});write(stage/'creation-migration/index.json',{'version':1});proofs=[]
 for i in added:
  file=stage/('creation-migration/sources/'+i+'.json');write(file,{'id':i});proofs.append({'location_id':i,'source':{'path':'sources/'+i+'.json','sha256':hashlib.sha256(file.read_bytes()).hexdigest()}})
 write(stage/'creation-migration/migration-receipt.json',{**common,'changed_ids':[],'added_ids':added,'reused_ids':before,'before_footprints_sha256':'b'*64,'after_footprints_sha256':'c'*64,'creation_proofs':proofs,'added_features':[{'id':i}for i in added]});write(stage/'creation/hierarchy.json',[])
class Aggregate(unittest.TestCase):
 def test_installed_original_names_are_preserved_not_post_reference_labels(self):
  with tempfile.TemporaryDirectory()as d:
   stage=pathlib.Path(d);fixture(stage);result=module.compose(stage);receipt=module.read(stage/'aggregate-source-receipt.json');self.assertEqual(result['added_ids'],34);self.assertEqual(receipt['archives'][0]['feature']['properties']['name'],'Original');self.assertTrue(all(p['source']['path'].startswith('creation-migration/')for p in receipt['creation_proofs']))
 def test_raw_source_tampering_rejected(self):
  with tempfile.TemporaryDirectory()as d:
   stage=pathlib.Path(d);fixture(stage);(stage/'creation-migration/sources/new0.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'wrapper'):module.compose(stage)
 def test_child_without_independent_validation_rejected(self):
  with tempfile.TemporaryDirectory()as d:
   stage=pathlib.Path(d);fixture(stage);p=stage/'creation-migration/migration-receipt.json';value=module.read(p);value['geometry_stage_validated']=False;write(p,value)
   with self.assertRaisesRegex(ValueError,'Unvalidated'):module.compose(stage)
if __name__=='__main__':unittest.main()
