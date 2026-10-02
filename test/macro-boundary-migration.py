import copy,gzip,hashlib,importlib.util,json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('migration',ROOT/'scripts/apply-macro-boundary-decisions.py');migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
def fixture():
 units={}
 for prefix,name in [('eu','Europe'),('as','Asia')]:
  parent=None
  for level in ['continent','subcontinent','region','area','province']:
   id=prefix+'-'+level;units[id]={'id':id,'name':name+' '+level if level!='continent' else name,'level':level,'parent_id':parent,'metadata':{'original_marker':True}};parent=id
 def feature(id,parent):return {'type':'Feature','id':id,'properties':{'id':id,'name':id,'parent_id':parent,'metadata':{'historical_record_reference':'preserved-reference'}},'geometry':{'type':'Polygon','coordinates':[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}}
 fs=[feature('moving','eu-province'),feature('staying','eu-province'),feature('existing-asian','as-province')];chains={x['level']:x['id'] for x in migration.chain(fs[0],units)}
 proof={'first_continent':'Europe','second_continent':'Asia','first_share':.2,'second_share':.7,'outside_surveyed_share':.1,'source_uncertainty_share':.01,'proposed_continent':'Asia','current_chain':chains,'divide':'synthetic source reach','method':'Synthetic strict whole-land majority fixture'}
 d={'sources':{'s':{'url':'https://example.org/physical-reference','inspected_fact':'Explicit source fact','sha256':'0'*64}},'group_changes':[],'location_changes':[{'id':'moving','current_name':'moving','current_parent_id':'eu-province','parent_id':'new-province','geometry_sha256':migration.digest(fs[0]['geometry']),'evidence':proof}],'new_groups':[{'id':'new-province','name':'geographic portion','level':'province','parent_id':'as-area','role':'sourced geographic reference portion','derived_from_id':'eu-province'}],'groups':[{'id':'eu-continent','convention':'Explicit geographic convention','source_ids':['s'],'convention_status':'documented','boundary_status':'supported-convention','semantic_status':'open','descendant_completion':'not implied','definition_method':'explicit convention'}]}
 d['sources']['physical-rivers']=copy.deepcopy(d['sources']['s'])
 r={'geometry_stage_validated':True,'changed_ids':[],'removed_ids':[],'added_ids':[]};return d,units,fs,r
class MigrationTests(unittest.TestCase):
 def test_one_parent_complete_chains_and_evidence_preserved(self):
  d,u,f,r=fixture();original=copy.deepcopy(f);new,after,receipt=migration.apply(d,u,f,r);self.assertEqual(new['new-province']['metadata']['derived_from_id'],'eu-province');self.assertEqual(after[0]['properties']['parent_id'],'new-province');self.assertEqual(after[0]['properties']['metadata']['historical_record_reference'],'preserved-reference');self.assertEqual([x['geometry'] for x in after],[x['geometry'] for x in original]);self.assertFalse(receipt['historical_claims_transferred']);self.assertEqual(receipt['summary']['geometry_changes'],0);self.assertEqual(f,original)
 def test_unvalidated_and_overlapping_source_repairs_rejected(self):
  d,u,f,r=fixture();r['geometry_stage_validated']=False
  with self.assertRaisesRegex(ValueError,'independently validated'):migration.apply(d,u,f,r)
  r['geometry_stage_validated']=True;r['changed_ids']=['moving']
  with self.assertRaisesRegex(ValueError,'intersects'):migration.apply(d,u,f,r)
 def test_missing_or_stale_identity_cannot_be_ignored(self):
  d,u,f,r=fixture();d['location_changes'][0]['id']='missing'
  with self.assertRaisesRegex(ValueError,'Missing proposal'):migration.apply(d,u,f,r)
  d,u,f,r=fixture();d['location_changes'][0]['current_name']='wrong'
  with self.assertRaisesRegex(ValueError,'Stale macro location'):migration.apply(d,u,f,r)
 def test_changed_geometry_and_nonadjacent_parent_rejected(self):
  d,u,f,r=fixture();f[0]['geometry']['coordinates'][0][1][0]=1.1
  with self.assertRaisesRegex(ValueError,'changed an assigned footprint'):migration.apply(d,u,f,r)
  d,u,f,r=fixture();d['new_groups'][0]['parent_id']='as-continent'
  with self.assertRaisesRegex(ValueError,'Non-adjacent'):migration.apply(d,u,f,r)
 def test_uncertainty_and_partial_coverage_do_not_manufacture_majority(self):
  d,u,f,r=fixture();e=d['location_changes'][0]['evidence'];e['second_share']=.51;e['source_uncertainty_share']=.02
  with self.assertRaisesRegex(ValueError,'conservative strict'):migration.apply(d,u,f,r)
 def test_own_boundary_support_does_not_close_descendants(self):
  d,u,f,r=fixture();new,_,_=migration.apply(d,u,f,r);review=new['eu-continent']['metadata']['semantic_review'];self.assertEqual(review['boundary_status'],'supported');self.assertEqual(review['semantic_status'],'open');self.assertEqual(review['descendant_completion'],'not implied')
 def test_complete_staged_dataset_and_git_archive(self):
  stage=ROOT/'.cache/macro-boundary-repair-stage';_,_,u,fs=migration.load_data(stage/'after');receipt=migration.read(ROOT/'data/macro-boundary-migration.json.gz');self.assertEqual(len(fs),49589);self.assertEqual(receipt['summary']['direct_location_parent_changes'],30);self.assertEqual(receipt['summary']['geometry_changes'],0);self.assertEqual(receipt['summary']['historical_records_touched'],0)
  before={f['properties']['id']:f['geometry'] for f in migration.load_data(stage/'before')[3]};self.assertEqual(set(before),{f['properties']['id'] for f in fs})
  for f in fs:self.assertEqual(f['geometry'],before[f['properties']['id']]);self.assertEqual(len(migration.chain(f,u)),5)
  self.assertEqual(migration.digest([u,fs]),receipt['after_sha256']);self.assertEqual(receipt['source_repair_disjointness']['intersection'],[]);self.assertEqual(len(receipt['new_group_ids']),9);self.assertTrue(all(i in u for i in receipt['new_group_ids']))
  source=receipt['retained_physical_geometry'];self.assertEqual(hashlib.sha256(gzip.decompress((ROOT/source['path']).read_bytes())).hexdigest(),source['uncompressed_sha256'])
if __name__=='__main__':unittest.main()
