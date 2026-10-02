"""#503 source conservation, unknown attributes, exact archival safety and fail-closed pins."""
import gzip,hashlib,importlib.util,json,os,pathlib,shutil,tempfile,unittest,sys
sys.dont_write_bytecode=True
from shapely import from_wkb
ROOT=pathlib.Path(__file__).resolve().parents[1]
PACK=ROOT/'data/macro-improvements/three-island-restoration'
BASE=pathlib.Path(os.environ.get('WORLDATLAS503_BASELINE_ROOT',ROOT))
def read(p):return json.loads(p.read_bytes())
class Restoration(unittest.TestCase):
 def test_every_source_and_derivative_pin(self):
  for file,pin in read(PACK/'manifest.json')['files'].items():self.assertEqual(hashlib.sha256((PACK/file).read_bytes()).hexdigest(),pin['sha256'],file)
 def test_dry_land_preserves_mapped_water_holes(self):
  p=read(PACK/'proposal.json')
  for row in p['locations']:
   dry=from_wkb(gzip.decompress((PACK/(row['slug']+'-dry-land.wkb.gz')).read_bytes()));water=from_wkb(gzip.decompress((PACK/(row['slug']+'-water-mask.wkb.gz')).read_bytes()))
   self.assertTrue(dry.is_valid);self.assertTrue(water.is_valid);self.assertGreater(dry.area,0);self.assertEqual(dry.intersection(water).area,0)
   for g in water.geoms if hasattr(water,'geoms') else [water]:self.assertFalse(dry.covers(g.representative_point()))
 def test_named_new_islands_not_retired_identity_resurrection(self):
  p=read(PACK/'proposal.json');ids={x['id'] for x in p['locations']};old={x['id'] for x in read(PACK/'identity-review.json')['entities']}
  self.assertEqual(ids,{'atlas:island:geonames:3420645','atlas:island:geonames:3421886','atlas:island:geonames:3370905'});self.assertFalse(ids&old)
  self.assertFalse(p['history_transfer']);self.assertFalse(p['modern_attribute_assignments']);self.assertFalse(p['regional_interior_approval'])
  self.assertEqual([r['water_count'] for r in p['locations']],[350,10,1])
 @unittest.skipUnless((BASE/'data/world-index.json').exists(),'Requires pinned real baseline; set WORLDATLAS503_BASELINE_ROOT')
 def test_replay_actual_baseline_without_mutation(self):
  with tempfile.TemporaryDirectory(prefix='worldatlas503test-') as tmp:
   spec=importlib.util.spec_from_file_location('islands503',PACK/'prepare.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
   out=pathlib.Path(tmp)/'candidate';result=module.prepare(BASE,out);self.assertEqual(result['old_count'],49589);self.assertEqual(result['new_count'],49592)
   preservation=read(out/'preservation.json');self.assertGreater(preservation['all_archived_entities_exhaustively_checked'],80000)
   for feature in read(out/'candidate-patch.json')['added_features']:
    self.assertIsNone(feature['properties']['reference_owner']);self.assertNotIn('reference_owner_id',feature['properties']['metadata']);self.assertFalse(feature['properties']['metadata']['historical_claims_transferred'])
   for part in read(BASE/'data/world-index.json')['parts']:self.assertEqual(hashlib.sha256((BASE/'data'/part).read_bytes()).digest(),hashlib.sha256((out/'after'/part).read_bytes()).digest())
 @unittest.skipUnless((BASE/'data/world-index.json').exists(),'Requires pinned real baseline; set WORLDATLAS503_BASELINE_ROOT')
 def test_tampered_source_and_bad_parent_are_rejected(self):
  with tempfile.TemporaryDirectory(prefix='worldatlas503bad-') as tmp:
   pack=pathlib.Path(tmp)/'pack';shutil.copytree(PACK,pack);spec=importlib.util.spec_from_file_location('bad503',pack/'prepare.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
   source=pack/'disko-dry-land.wkb.gz';raw=source.read_bytes();source.write_bytes(raw+b'changed')
   with self.assertRaisesRegex(ValueError,'Evidence changed'):module.prepare(BASE,pathlib.Path(tmp)/'out1')
   source.write_bytes(raw);proposal=read(pack/'proposal.json');proposal['locations'][0]['parent_chain'][0]='province:unverified';(pack/'proposal.json').write_text(json.dumps(proposal));manifest=read(pack/'manifest.json');manifest['files']['proposal.json']['sha256']=hashlib.sha256((pack/'proposal.json').read_bytes()).hexdigest();(pack/'manifest.json').write_text(json.dumps(manifest))
   with self.assertRaisesRegex(ValueError,'Incomplete reviewed adjacent-tier chain'):module.prepare(BASE,pathlib.Path(tmp)/'out2')
if __name__=='__main__':unittest.main()
