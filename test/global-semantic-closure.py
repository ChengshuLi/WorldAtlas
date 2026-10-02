"""Meaningful review-publication gates: completeness cannot be inferred from counts."""
import contextlib,gzip,importlib.util,io,json,pathlib,tempfile,unittest
from shapely.geometry import Polygon
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('closure',ROOT/'scripts/review-global-semantic-closure.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ReviewGates(unittest.TestCase):
 def test_supported_boundary_with_unresolved_child_is_not_complete(self):
  self.assertEqual(m.semantic_status({'boundary':m.check('supported','sourced')},False),'open')
 def test_unknown_source_evidence_is_not_supported(self):
  self.assertEqual(m.semantic_status({'purpose':m.check('open','independent purpose missing')}),'open')
  self.assertEqual(m.semantic_status({'purpose':m.check('attention','city fragment')}),'open')
 def test_supported_complete_rubric_can_close(self):
  self.assertEqual(m.semantic_status({'purpose':m.check('supported','independent evidence'),'islands':m.check('not-applicable','no islands')}),'supported')
 def test_duplicate_missing_and_unexpected_ids_fail(self):
  for actual in [['a','a'],['a'],['a','b','c']]:
   with self.assertRaises(ValueError):m.assert_complete_inventory(['a','b'],actual,'fixtures')
  m.assert_complete_inventory(['a','b'],['b','a'],'fixtures')
 def test_source_atoms_survive_changed_physical_source_id(self):
  atoms=m.source_atom_resolver({'atlas:physical:one':{'metadata':{'source_id':'resolve:722','source_member_ids':['gb:ARE:ADM1:one']}}},{})
  self.assertEqual(atoms('atlas:physical:one'),('gb:ARE:ADM1:one',))
  self.assertEqual(atoms('gb:ARE:ADM1:one'),('gb:ARE:ADM1:one',))
  cycle=m.source_atom_resolver({'a':{'metadata':{'source_member_ids':['b']}},'b':{'metadata':{'source_member_ids':['a']}}},{})
  with self.assertRaises(ValueError):cycle('a')
 def test_data_resolution_requires_current_geometry_and_real_source(self):
  original={'disconnected_territories':m.check('attention','three islands')}
  record={'island':{'footprint_sha256':'current','checks':{'disconnected_territories':{'status':'supported','rationale':'named archipelago','evidence':[{'url':'https://source.example/islands','inspected_fact':'All three islands are named members'}]}}}}
  self.assertEqual(m.apply_resolutions('island',original,record,'current')['disconnected_territories']['status'],'supported')
  with self.assertRaises(ValueError):m.apply_resolutions('island',original,record,'old')
  record['island']['checks']['disconnected_territories']['evidence']=[]
  with self.assertRaises(ValueError):m.apply_resolutions('island',original,record,'current')
 def test_data_resolution_cannot_override_invalid_geometry(self):
  record={'land':{'footprint_sha256':'current','checks':{'valid_land_footprint':{'status':'supported','rationale':'override','evidence':[{'url':'https://source.example','inspected_fact':'claim'}]}}}}
  with self.assertRaises(ValueError):m.apply_resolutions('land',{'valid_land_footprint':m.check('attention','invalid')},record,'current')
 def test_actual_complete_fixture_keeps_semantics_open(self):
  with tempfile.TemporaryDirectory() as directory:
   data=pathlib.Path(directory);(data/'geographic-decisions').mkdir()
   write=lambda path,value:path.write_text(json.dumps(value))
   features=[];units=[];owners=[]
   for i,name in enumerate(['Africa','Asia','Europe','North America','Oceania','South America']):
    ids=[f'{i}:{level}' for level in m.LEVELS];owner=f'owner{i}'
    geometry={'type':'Polygon','coordinates':[[[i*3,0],[i*3+1,0],[i*3+1,1],[i*3,1],[i*3,0]]]}
    features.append({'id':ids[0],'geometry':geometry,'properties':{'name':f'County{i}','parent_id':ids[1],'reference_owner':owner,'metadata':{'source_role':'County','source_id':'fixture','source_url':'https://source.example/counties','license':'Public Domain','reference_year':2026}}})
    for j,level in enumerate(m.LEVELS[1:],1):units.append({'id':ids[j],'name':name if level=='continent' else f'{level}{i}','level':level,'parent_id':ids[j+1] if j<5 else None,'metadata':{}})
    owners.append({'owner':owner,'iso':f'FIX{i}','sources':[]})
    write(data/'geographic-decisions'/f'{i}.json',{'location_review':[{'ids':[ids[0]],'status':'open','rationale':'purpose not independently sourced'}]})
   for filename,value in [('world-index.json',{'parts':['world.json']}),('world.json',{'features':features}),('hierarchy.json',units),('location-policy.json',{'countries':{}}),('world-review.json',{'territories':owners}),('coverage-report.json',{}),('global-refinement-report.json',{}),('semantic-report.json',{'changes':[]})]:write(data/filename,value)
   with contextlib.redirect_stdout(io.StringIO()):m.main(data)
   result=json.loads(gzip.decompress((data/'global-semantic-closure.json.gz').read_bytes()))
   self.assertTrue(result['audit_complete']);self.assertTrue(result['structural_complete']);self.assertFalse(result['semantic_complete'])
   self.assertEqual(result['counts']['locations'],6);self.assertEqual(result['counts']['groups'],30)
   units[0]['parent_id']=ids[-1];write(data/'hierarchy.json',units)
   with self.assertRaises(ValueError):m.main(data)
 def test_source_adm_numbers_are_not_semantic_roles(self):
  self.assertTrue(m.BAD_ROLE.search('ADM2'))
  self.assertTrue(m.BAD_ROLE.search('Unknown'))
  self.assertFalse(m.BAD_ROLE.search('Municipality'))
 def test_holes_are_excluded_from_land_measurement(self):
  outer=[(0,0),(2,0),(2,2),(0,2),(0,0)];hole=[(.5,.5),(1.5,.5),(1.5,1.5),(.5,1.5),(.5,.5)]
  self.assertAlmostEqual(m.measured_area(Polygon(outer,[hole])),m.measured_area(Polygon(outer))-m.measured_area(Polygon(hole)),places=6)
 def test_antimeridian_diagnostic_does_not_measure_nearly_whole_world(self):
  cross=Polygon([(179,0),(-179,0),(-179,1),(179,1),(179,0)])
  equivalent=Polygon([(-1,0),(1,0),(1,1),(-1,1),(-1,0)])
  self.assertAlmostEqual(m.measured_area(cross),m.measured_area(equivalent),places=6)

if __name__=='__main__':unittest.main()
