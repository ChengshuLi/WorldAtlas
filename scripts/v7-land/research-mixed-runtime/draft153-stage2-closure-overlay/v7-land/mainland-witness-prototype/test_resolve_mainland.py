import copy,hashlib,json,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import resolve_mainland as m

def put(p,x):
    raw=x if isinstance(x,bytes) else json.dumps(x,separators=(',',':')).encode();p.write_bytes(raw);return {'path':str(p),'sha256':hashlib.sha256(raw).hexdigest()}
def packed(fmt,rows):return b''.join(struct.pack(fmt,*x) for x in rows)

class MainlandWitnessTests(unittest.TestCase):
 def setUp(self):
    self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)
    self.mem=patch.object(m.helper,'available_memory_kib',return_value=4000000);self.mem.start();self.addCleanup(self.mem.stop)
    self.grid={'width':8,'height':4,'west':'-180','north':'90','step':'45'}
    self.points={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'id':i,'name':name},'geometry':{'type':'Point','coordinates':xy}} for i,name,xy in [('a','Alpha',[-112.5,22.5]),('b','Beta',[-67.5,22.5]),('c','Gamma',[67.5,22.5])]]}
    self.labels={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'id':'A','name':'MAINLAND','class':'Continent'},'geometry':{'type':'Polygon','coordinates':[[[-130,0],[-40,0],[-40,45],[-130,45],[-130,0]]]}},{'type':'Feature','properties':{'id':'B','name':'ISLAND','class':'Island'},'geometry':{'type':'Polygon','coordinates':[[[50,0],[90,0],[90,45],[50,45],[50,0]]]}}]}
    self.pp=put(self.p/'points',self.points);self.ip=put(self.p/'identity',self.labels)
    def source(id,pin):return {'source_id':id,'version':'1','sha256':pin['sha256'],'r2_bucket':'bucket','r2_key':id,'size_bytes':Path(pin['path']).stat().st_size}
    src=[source('points',self.pp),source('labels',self.ip)]
    assets=[dict(x,source_uri='https://example.org/'+x['source_id'],attribution='provider',license_name='test',license_uri='https://example.org/license',provider='provider',title='title',kind='raw',provenance={'representation':'provider_original'}) for x in src]
    features=[]
    for f in self.points['features']:
        features.append({'feature_id':'p'+f['properties']['id'],'source_id':'points','source_version':'1','source_feature_id':f['properties']['id'],'geometry_sha256':m.helper.geometry_sha(f['geometry'])})
    for f in self.labels['features']:
        features.append({'feature_id':'i'+f['properties']['id'],'source_id':'labels','source_version':'1','source_feature_id':f['properties']['id'],'geometry_sha256':m.helper.geometry_sha(f['geometry'])})
    def witness(id,name,identity,cls):
        return {'witness_id':id,'decision_revision':'d','method':'source_point_named_region_v1','execution_status':'selected_for_research','point_feature_id':'p'+id,'identity_feature_id':'i'+('A' if identity=='MAINLAND' else 'B'),'point_name':name,'identity_name':identity,'identity_class':cls,'id_property':'id','identity_id_property':'id','identity_name_property':'name','identity_class_property':'class','radius_cells':0,'max_water_cells':0,'rationale':'source-backed identity'}
    self.doc={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','decision_revision':{'id':'d','entity_revision':'e','status':'draft'},'entity_revision':{'id':'e','status':'draft'},'entities':[{'id':42,'name':'Continent','level':'continent'}],'category_bindings':[{'entity_id':42,'code':19,'physical_class':'land'}], 'sources':src,'source_lineage_assets':assets,'source_lineage_dependencies':[],'features':features,
      'mainland_witnesses':[witness('a','Alpha','MAINLAND','Continent'),witness('b','Beta','MAINLAND','Continent'),witness('c','Gamma','ISLAND','Island')],
      'mainland_witness_groups':[{'group_id':'main','decision_revision':'d','role':'mainland','execution_status':'selected_for_research','target_entity_ids':[42],'witness_ids':['a','b'],'rationale':'reviewed mainland identity'},{'group_id':'sentinel','decision_revision':'d','role':'sentinel','execution_status':'selected_for_research','target_entity_ids':[],'witness_ids':['c'],'rationale':'reviewed separation'}],
      'mainland_group_relations':[{'relation_id':'r','decision_revision':'d','execution_status':'selected_for_research','relation':'different','group_ids':['main','sentinel']}]}
    prows=put(self.p/'pr',packed('<I',[(0,),(5,),(10,),(15,),(20,)]));pruns=put(self.p/'ps',packed('<II',[(1,1),(3,17),(5,1),(7,17),(8,1)]*4));crows=put(self.p/'cr',packed('<I',[(0,),(2,),(4,),(6,),(8,)]));cruns=put(self.p/'cs',packed('<III',[(1,3,7),(5,7,9)]*4))
    cs=put(self.p/'component.cpp',b'component source');builder=put(self.p/'builder',b'builder');phys=put(self.p/'physical-report',{'status':'candidate-only','grid':self.grid,'output_sha256':{'rows.u32le':prows['sha256'],'runs.u32le':pruns['sha256']}})
    self.req={'schema':'mainland-witness-request-v1','grid':self.grid,'snapshot':put(self.p/'snapshot',self.doc),'physical_rows':prows,'physical_runs':pruns,'component_rows':crows,'component_runs':cruns,'component_source':cs,'source_files':[dict(source_id='points',version='1',**self.pp),dict(source_id='labels',version='1',**self.ip)]}
    self.manifest={'schema':'single-generation-component-manifest-v1','status':'complete-research','grid':self.grid,'component_source_sha256':cs['sha256'],'pins':{k:self.req[k] for k in ('physical_rows','physical_runs','component_rows','component_runs')},'physical_report':phys,'builder_binary':builder,'builder_binary_sha256':builder['sha256'],'compiler_version':'test','builder_output':'test'}
    self.req['component_manifest']=put(self.p/'manifest',self.manifest);self.req['code_sha256']={k:m.helper.digest(p) for k,p in {'resolver':Path(m.__file__).resolve(),'helper':m.HELPER.resolve(),'named_identity':m.NAMED.resolve(),'identity_watch':m.WATCH.resolve()}.items()}
 def save(self):self.req['snapshot']=put(self.p/'snapshot',self.doc)
 def change_component_runs(self,runs):
    self.req['component_runs']=put(self.p/'cs',packed('<III',runs*4));self.req['component_rows']=put(self.p/'cr',packed('<I',[(len(runs)*i,) for i in range(5)]));self.manifest['pins']['component_rows']=self.req['component_rows'];self.manifest['pins']['component_runs']=self.req['component_runs'];self.req['component_manifest']=put(self.p/'manifest',self.manifest)
 def test_selected_groups_resolve_without_fixed_decision_roots(self):
    out=m.resolve(self.req);self.assertEqual(out['status'],'selected-research-identity-claims-not-mainland-proof');self.assertFalse(out['publishable']);self.assertEqual({g['group_id']:g['component_id_current_generation_only'] for g in out['groups']},{'main':7,'sentinel':9})
 def test_same_group_mismatch_and_distinct_group_collision_fail(self):
    self.change_component_runs([(1,2,7),(2,3,8),(5,7,9)])
    with self.assertRaisesRegex(ValueError,'same-group witness mismatch'):m.resolve(self.req)
    self.change_component_runs([(1,3,7),(5,7,7)])
    with self.assertRaisesRegex(ValueError,'different-group witness mismatch'):m.resolve(self.req)
 def test_whole_row_mismatch_fails(self):
    self.change_component_runs([(1,3,7),(5,6,9)])
    with self.assertRaisesRegex(ValueError,'component row differs'):m.resolve(self.req)
 def test_invalid_selection_and_stale_revision_fail(self):
    self.doc['mainland_witnesses'][0]['execution_status']='proposed_not_selected';self.save()
    with self.assertRaisesRegex(ValueError,'unselected witness'):m.resolve(self.req)
    self.doc['mainland_witnesses'][0]['execution_status']='selected_for_research';self.doc['mainland_witness_groups'][0]['decision_revision']='old';self.save()
    with self.assertRaisesRegex(ValueError,'invalid or unselected group|group target mismatch'):m.resolve(self.req)
 def test_unrelated_fixed_root_and_missing_relations_fail(self):
    self.doc['mainland_witness_groups'][0]['component_id']=7;self.save()
    with self.assertRaisesRegex(ValueError,'invalid or unselected group|group target mismatch'):m.resolve(self.req)
    del self.doc['mainland_witness_groups'][0]['component_id'];self.doc['mainland_group_relations']=[];self.save()
    with self.assertRaisesRegex(ValueError,'incomplete different-group assertions'):m.resolve(self.req)
 def test_sentinel_target_and_source_tamper_fail(self):
    self.doc['mainland_witness_groups'][1]['target_entity_ids']=[42];self.save()
    with self.assertRaisesRegex(ValueError,'group target mismatch'):m.resolve(self.req)
    self.doc['mainland_witness_groups'][1]['target_entity_ids']=[];self.save();(self.p/'points').write_text('{}')
    with self.assertRaisesRegex(ValueError,'hash mismatch'):m.resolve(self.req)
 def test_source_feature_geometry_and_identity_fail(self):
    self.doc['features'][0]['geometry_sha256']='0'*64;self.save()
    with self.assertRaisesRegex(ValueError,'point identity or geometry'):m.resolve(self.req)
    self.doc['features'][0]['geometry_sha256']=m.helper.geometry_sha(self.points['features'][0]['geometry']);self.doc['mainland_witnesses'][0]['identity_name']='WRONG';self.save()
    with self.assertRaisesRegex(ValueError,'identity feature name or class mismatch'):m.resolve(self.req)
 def test_coastal_neighborhood_is_explicit(self):
    self.doc['mainland_witnesses'][2]['radius_cells']=1;self.doc['mainland_witnesses'][2]['max_water_cells']=2;self.save()
    with self.assertRaisesRegex(ValueError,'neighborhood is water or ambiguous'):m.resolve(self.req)
    self.doc['mainland_witnesses'][2]['max_water_cells']=3;self.save();out=m.resolve(self.req);sentinel=next(w for w in out['witnesses'] if w['witness_id']=='c');self.assertEqual(sentinel['water_cells'],3)
 def test_rejected_prior_seed_manifest_and_code_tamper(self):
    self.manifest['schema']='simple-v2-land-report-v1';self.req['component_manifest']=put(self.p/'manifest',self.manifest)
    with self.assertRaisesRegex(ValueError,'current independent component generation'):m.resolve(self.req)
    self.req['code_sha256']['helper']='0'*64
    with self.assertRaisesRegex(ValueError,'code pin mismatch'):m.resolve(self.req)
 def test_duplicate_category_codes_rejected(self):
    self.doc['entities'].append({'id':43,'name':'Other'});self.doc['category_bindings'].append({'entity_id':43,'code':19,'physical_class':'land'});self.doc['mainland_witness_groups'][0]['target_entity_ids'].append(43);self.save()
    with self.assertRaisesRegex(ValueError,'conflicting target entity'):m.resolve(self.req)
 def test_unreferenced_witness_and_wrong_revision_fails(self):
    self.doc['mainland_witness_groups'][0]['witness_ids']=['a'];self.save()
    with self.assertRaisesRegex(ValueError,'invalid or unselected group|group target mismatch'):m.resolve(self.req)
    self.doc['mainland_witness_groups'][0]['witness_ids']=['a','b'];self.doc['mainland_group_relations'][0]['decision_revision']='other';self.save()
    with self.assertRaisesRegex(ValueError,'invalid different-group assertion'):m.resolve(self.req)
 def test_coordinate_grid_boundary_fails(self):
    self.points['features'][0]['geometry']['coordinates']=[-90,22.5];self.pp=put(self.p/'points',self.points);self.doc['features'][0]['geometry_sha256']=m.helper.geometry_sha(self.points['features'][0]['geometry'])
    for x in self.doc['sources']+self.doc['source_lineage_assets']:
        if x['source_id']=='points':x['sha256']=self.pp['sha256'];x['size_bytes']=Path(self.pp['path']).stat().st_size
    self.req['source_files'][0].update(self.pp);self.save()
    with self.assertRaisesRegex(ValueError,'grid boundary'):m.resolve(self.req)

if __name__=='__main__':unittest.main()
