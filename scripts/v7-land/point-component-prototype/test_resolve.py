# Synthetic fixtures only; no project geographic records.
import copy, hashlib, json, struct, tempfile, unittest, sys
from pathlib import Path
from unittest.mock import patch
import resolve
import adapter

def put(p,data):
    p.write_bytes(data if isinstance(data,bytes) else json.dumps(data,separators=(',',':')).encode());return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

def packed(fmt,records):return b''.join(struct.pack(fmt,*r) for r in records)

class ResolverTests(unittest.TestCase):
 def setUp(self):
    self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);p=Path(self.t.name);self.p=p;self.out=tempfile.TemporaryDirectory();self.addCleanup(self.out.cleanup);self.outdir=Path(self.out.name);self.mem=patch.object(resolve,'available_memory_kib',return_value=4000000);self.mem.start();self.addCleanup(self.mem.stop)
    self.g={'width':8,'height':4,'west':'-180','north':'90','step':'45'}
    self.point={'type':'Feature','properties':{'id':'a','name':'Test place'},'geometry':{'type':'Point','coordinates':[-112.5,22.5]}}
    self.feature={'type':'FeatureCollection','features':[self.point]}
    self.pointpin=put(p/'point.json',self.feature);self.docpin=put(p/'identity.txt',b'Independent claimed-island identity evidence')
    self.sources=[{'source_id':'p','version':'1','sha256':self.pointpin['sha256'],'uri':'https://example.org/point','attribution':'provider','license':'test','r2_bucket':'b','r2_key':'p','license_uri':'https://example.org/license','provider':'provider','title':'title','size_bytes':(p/'point.json').stat().st_size,'kind':'raw','provenance':{'representation':'provider_original'}}, {'source_id':'i','version':'1','sha256':self.docpin['sha256'],'uri':'https://example.org/identity','attribution':'provider','license':'test','r2_bucket':'b','r2_key':'i','license_uri':'https://example.org/license','provider':'provider','title':'title','size_bytes':(p/'identity.txt').stat().st_size,'kind':'raw','provenance':{'representation':'provider_original'}}]
    self.decision={'affiliation_id':'a','method':'source_point_component_v1','execution_status':'selected_for_research','entity_id':42,'island_identity':'Test island','point_name':'Test place','point_source_id':'p','point_source_version':'1','identity_source_id':'i','identity_source_version':'1','source_feature_id':'a','id_property':'id','geometry_sha256':resolve.geometry_sha(self.point['geometry'])}
    self.snap={'schema':'point-component-decision-snapshot-v1','source':'neon-export','status':'draft','revision':'draft-1','sources':self.sources,'target_entities':[{'id':42,'name':'Continent','physical_class':'land'},{'id':43,'name':'Other','physical_class':'land'}],'decisions':[self.decision]}
    self.snapref=put(p/'snapshot.json',self.snap)
    # Each row spans [0,1) water [1,4) land [4,8) water; same component 7.
    prows=put(p/'pr',packed('<I',[(0,),(3,),(6,),(9,),(12,)]));pruns=put(p/'ps',packed('<II',[(1,1),(4,17),(8,1)]*4))
    crows=put(p/'cr',packed('<I',[(0,),(1,),(2,),(3,),(4,)]));cruns=put(p/'cs',packed('<III',[(1,4,7)]*4))
    self.req={'resolver_sha256':resolve.digest(resolve.__file__),'schema':'point-component-request-v1','grid':self.g,'snapshot':self.snapref,'physical_rows':prows,'physical_runs':pruns,'component_rows':crows,'component_runs':cruns,'source_files':[dict(source_id='p',version='1',**self.pointpin),dict(source_id='i',version='1',**self.docpin)]}
    cs=put(p/'component.cpp',b'synthetic component source');builder=put(p/'builder',b'synthetic binary')
    physical_report=put(p/'physical-report',{'status':'candidate-only','grid':self.g,'output_sha256':{'rows.u32le':prows['sha256'],'runs.u32le':pruns['sha256']}})
    self.manifest={'schema':'single-generation-component-manifest-v1','status':'complete-research','grid':self.g,'component_source_sha256':cs['sha256'],'pins':{k:self.req[k] for k in ('physical_rows','physical_runs','component_rows','component_runs')},'physical_report':physical_report,'builder_binary':builder,'builder_binary_sha256':builder['sha256'],'compiler_version':'test','builder_output':'test'}
    self.req['component_source']=cs;self.req['component_manifest']=put(p/'manifest',self.manifest)
 def save_snap(self):self.req['snapshot']=put(self.p/'snapshot.json',self.snap)
 def save_point(self):
    self.pointpin=put(self.p/'point.json',self.feature);self.sources[0]['sha256']=self.pointpin['sha256'];self.sources[0]['size_bytes']=(self.p/'point.json').stat().st_size;self.req['source_files'][0].update(self.pointpin);self.decision['geometry_sha256']=resolve.geometry_sha(self.point['geometry']);self.save_snap()
 def use_combined_export(self):
    def source(name,pin):return {'source_id':name,'version':'1','sha256':pin['sha256'],'r2_bucket':'bucket','r2_key':name,'size_bytes':Path(pin['path']).stat().st_size}
    sources=[source('p',self.pointpin),source('i',self.docpin)];assets=[dict(x,source_uri='https://example.org/'+x['source_id'],attribution='provider',license_name='test',license_uri='https://example.org/license',provider='provider',title='title',kind='raw',provenance={'representation':'provider_original'}) for x in sources]
    d={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','decision_revision':{'id':'draft-1','entity_revision':'ent-1','status':'draft'},'entity_revision':{'id':'ent-1','status':'draft'},'sources':sources,'source_lineage_assets':assets,'source_lineage_dependencies':[],'features':[{'feature_id':'f','source_id':'p','source_version':'1','source_feature_id':'a','geometry_sha256':resolve.geometry_sha(self.point['geometry'])}],'affiliations':[{'affiliation_id':'a','method':'source_point_component_v1','scope':'land','relationship':'affiliation','rationale':'independent evidence','feature_id':'f','entity_id':42,'evidence':{'execution_status':'selected_for_research','selector':{'island_identity':'Test island','point_name':'Test place','id_property':'id'}}}],'affiliation_source_refs':[{'affiliation_id':'a','role':'identity_evidence','source_id':'i','source_version':'1'}],'entities':[{'id':42,'name':'Continent'}],'category_bindings':[{'entity_id':42,'physical_class':'land','code':18}]}
    self.req['snapshot']=put(self.p/'combined.json',d);self.req['adapter_sha256']=resolve.digest(adapter.__file__);return d
 def use_named_export(self):
    d=self.use_combined_export();geom={'type':'Polygon','coordinates':[[[-150,0],[-80,0],[-80,45],[-150,45],[-150,0]]]};identity={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'NE_ID':8,'NAME':'TEST ISLAND','FEATURECLA':'Island'},'geometry':geom}]};ip=put(self.p/'identity.txt',identity);self.req['source_files'][1].update(ip)
    for row in d['sources']+d['source_lineage_assets']:
     if row['source_id']=='i':row['sha256']=ip['sha256'];row['size_bytes']=Path(ip['path']).stat().st_size
    d['features'].append({'feature_id':'identity-feature','source_id':'i','source_version':'1','source_feature_id':'8','geometry_sha256':resolve.geometry_sha(geom)});a=d['affiliations'][0];a['method']='source_point_named_region_component_v1';a['evidence']['selector'].update({'identity_id_property':'NE_ID','identity_name_property':'NAME','identity_class_property':'FEATURECLA','identity_class_value':'Island'});d['affiliation_source_refs']=[];d['affiliation_feature_refs']=[{'affiliation_id':'a','role':'identity_polygon','feature_id':'identity-feature'}];self.req['snapshot']=put(self.p/'combined.json',d);self.req['named_identity_sha256']=resolve.digest(Path(resolve.__file__).resolve().parent.parent/'named-identity-prototype'/'named_identity.py');self.req['identity_watch_sha256']=resolve.digest(Path(resolve.__file__).resolve().parent.parent/'named-identity-prototype'/'identity_watch.py');return d,identity
 def use_wgs84_lineage(self):
    comp_source=self.req['component_source'];builder=self.manifest['builder_binary'];physical=self.manifest['physical_report'];pins={k:self.req[k] for k in ('physical_rows','physical_runs','component_rows','component_runs')}
    identity={'config_sha256':'a'*64,'grid':self.g,'component_rows_sha256':pins['component_rows']['sha256'],'component_runs_sha256':pins['component_runs']['sha256'],'code_sha256':{'build_components.cpp':comp_source['sha256']}}
    cp={'payload':{'schema':'simple-v2-query-checkpoint-v1','identity':identity,'next_row':self.g['height'],'queries':13,'best':{}}};checkpoint=put(self.p/'spherical-checkpoint',cp)
    sr={'schema':'simple-v2-land-report-v1','status':'research-not-published','grid':self.g,'component_generation':'independent-recompute','config_sha256':'a'*64,'queries':13,'checkpoint_sha256':checkpoint['sha256'],'component_builder_binary_sha256':builder['sha256'],'code_sha256':{'build_components.cpp':comp_source['sha256']},'inputs':{k:pins[k] for k in ('physical_rows','physical_runs')}};sphere=put(self.p/'spherical-report',sr)
    report={'schema':'simple-v2-land-report-v1','status':'research-not-published','grid':self.g,'component_topology_provenance':'Prior independent build; WGS84 did not regenerate topology.','inputs':{**pins,'physical_report':physical,'component_builder_source':comp_source,'component_builder_binary':builder,'spherical_report':sphere,'spherical_checkpoint':checkpoint}}
    self.req['component_manifest']=put(self.p/'wgs84-report',report);return report,sr,cp
 def test_wgs84_prior_independent_lineage(self):
    self.use_wgs84_lineage();out=resolve.resolve(self.req);self.assertEqual(out['component_lineage_mode'],'wgs84-report-with-prior-independent-component-build')
 def test_wgs84_checkpoint_component_mismatch(self):
    report,sr,cp=self.use_wgs84_lineage();cp['payload']['identity']['component_rows_sha256']='0'*64;checkpoint=put(self.p/'spherical-checkpoint',cp);sr['checkpoint_sha256']=checkpoint['sha256'];sphere=put(self.p/'spherical-report',sr);report['inputs']['spherical_report']=sphere;report['inputs']['spherical_checkpoint']=checkpoint;self.req['component_manifest']=put(self.p/'wgs84-report',report)
    with self.assertRaisesRegex(ValueError,'prior checkpoint component identity mismatch'):resolve.resolve(self.req)
 def test_wgs84_builder_provenance_mismatch(self):
    report,sr,cp=self.use_wgs84_lineage();sr['component_generation']='not-verified';report['inputs']['spherical_report']=put(self.p/'spherical-report',sr);self.req['component_manifest']=put(self.p/'wgs84-report',report)
    with self.assertRaisesRegex(ValueError,'prior component build provenance'):resolve.resolve(self.req)
 def test_named_identity_end_to_end(self):
    self.use_named_export();out=resolve.resolve(self.req);self.assertEqual(out['claims'][0]['method'],'source_point_named_region_component_v1');self.assertTrue(out['claims'][0]['identity_check']['strict_contains']);self.assertEqual(out['claims'][0]['source_crs_scope'],'collection_feature_geometry');self.assertEqual(out['claims'][0]['identity_feature_id'],'identity-feature')
 def test_named_identity_code_pin_mismatch(self):
    self.use_named_export();self.req['named_identity_sha256']='0'*64
    with self.assertRaisesRegex(ValueError,'named identity code pin'):resolve.resolve(self.req)
 def test_named_watchdog_pin_mismatch(self):
    self.use_named_export();self.req['identity_watch_sha256']='0'*64
    with self.assertRaisesRegex(ValueError,'watchdog code pin'):resolve.resolve(self.req)
 def test_named_identity_outside_fails(self):
    d,identity=self.use_named_export();identity['features'][0]['geometry']['coordinates']=[[[-80,0],[-50,0],[-50,45],[-80,45],[-80,0]]];ip=put(self.p/'identity.txt',identity);self.req['source_files'][1].update(ip)
    for row in d['sources']+d['source_lineage_assets']:
     if row['source_id']=='i':row['sha256']=ip['sha256'];row['size_bytes']=Path(ip['path']).stat().st_size
    d['features'][-1]['geometry_sha256']=resolve.geometry_sha(identity['features'][0]['geometry']);self.req['snapshot']=put(self.p/'combined.json',d)
    with self.assertRaisesRegex(ValueError,'strictly inside'):resolve.resolve(self.req)
 def test_combined_neon_export(self):
    self.use_combined_export();out=resolve.resolve(self.req);self.assertEqual(out['snapshot_schema'],'worldatlas-geography-decision-draft-evidence-v1');self.assertEqual(out['claims'][0]['entity_code'],18);self.assertEqual(out['claims'][0]['feature_id'],'f');self.assertEqual(out['claims'][0]['identity_source']['r2_key'],'i');self.assertEqual(out['adapter_sha256'],self.req['adapter_sha256'])
 def test_combined_adapter_pin_mismatch(self):
    self.use_combined_export();self.req['adapter_sha256']='0'*64
    with self.assertRaisesRegex(ValueError,'adapter code pin'):resolve.resolve(self.req)
 def test_combined_rejects_wrong_identity_role(self):
    d=self.use_combined_export();d['affiliation_source_refs'][0]['role']='wrong';self.req['snapshot']=put(self.p/'combined.json',d)
    with self.assertRaisesRegex(ValueError,'unsupported source role'):resolve.resolve(self.req)
 def test_valid(self):
    out=resolve.resolve(self.req);self.assertEqual(out['claims'][0]['component_id'],7);self.assertEqual(out['claims'][0]['affiliation_id'],'a');self.assertEqual(out['status'],'research-only-not-a-build')
 def test_source_digest_mismatch(self):
    (self.p/'point.json').write_text('{}')
    with self.assertRaisesRegex(ValueError,'hash mismatch'):resolve.resolve(self.req)
 def test_identity_document_mismatch(self):
    (self.p/'identity.txt').write_text('other')
    with self.assertRaisesRegex(ValueError,'hash mismatch'):resolve.resolve(self.req)
 def test_duplicate_feature(self):
    self.feature['features'].append(copy.deepcopy(self.point));self.save_point()
    with self.assertRaisesRegex(ValueError,'unique'):resolve.resolve(self.req)
 def test_geometry_pin_mismatch(self):
    self.decision['geometry_sha256']='0'*64;self.save_snap()
    with self.assertRaisesRegex(ValueError,'geometry hash'):resolve.resolve(self.req)
 def test_feature_name_mismatch(self):
    self.decision['point_name']='Other';self.save_snap()
    with self.assertRaisesRegex(ValueError,'name mismatch'):resolve.resolve(self.req)
 def test_boundary_fails(self):
    self.point['geometry']['coordinates']=[-90.0,22.5];self.save_point()
    with self.assertRaisesRegex(ValueError,'grid boundary'):resolve.resolve(self.req)
 def test_point_crs84_accepted(self):
    self.feature['crs']={'type':'name','properties':{'name':'urn:ogc:def:crs:OGC:1.3:CRS84'}};self.save_point();self.assertEqual(resolve.resolve(self.req)['claims'][0]['source_crs']['point'],'OGC:CRS84')
 def test_point_bad_crs_fails(self):
    self.feature['crs']={'type':'name','properties':{'name':'EPSG:3857'}};self.save_point()
    with self.assertRaisesRegex(ValueError,'source CRS'):resolve.resolve(self.req)
 def test_nested_point_feature_crs_fails(self):
    self.point['crs']={'type':'name','properties':{'name':'EPSG:3857'}};self.save_point()
    with self.assertRaisesRegex(ValueError,'nested feature CRS'):resolve.resolve(self.req)
 def test_nested_point_geometry_crs_fails(self):
    self.point['geometry']['crs']={'type':'name','properties':{'name':'EPSG:3857'}};self.save_point()
    with self.assertRaisesRegex(ValueError,'nested geometry CRS'):resolve.resolve(self.req)
 def test_water_fails(self):
    self.point['geometry']['coordinates']=[-157.5,22.5];self.save_point()
    with self.assertRaisesRegex(ValueError,'exactly one physical land'):resolve.resolve(self.req)
 def test_unknown_status(self):
    self.decision['execution_status']='pending';self.save_snap()
    with self.assertRaisesRegex(ValueError,'unselected'):resolve.resolve(self.req)
 def test_multiple_component_claims_fail(self):
    duplicate=copy.deepcopy(self.decision);duplicate['affiliation_id']='b';duplicate['entity_id']=43;self.snap['decisions'].append(duplicate);self.save_snap()
    with self.assertRaisesRegex(ValueError,'multiple or conflicting'):resolve.resolve(self.req)
 def test_invalid_row(self):
    ref=put(self.p/'ps',packed('<II',[(1,1),(1,17),(8,1)]*4));self.req['physical_runs']=ref;self.manifest['pins']['physical_runs']=ref;report=json.loads((self.p/'physical-report').read_bytes());report['output_sha256']['runs.u32le']=ref['sha256'];self.manifest['physical_report']=put(self.p/'physical-report',report);self.req['component_manifest']=put(self.p/'manifest',self.manifest)
    with self.assertRaisesRegex(ValueError,'invalid physical'):resolve.resolve(self.req)
 def test_missing_feature_id_cannot_match_literal_none(self):
    del self.point['properties']['id'];self.decision['source_feature_id']='None';self.save_point()
    with self.assertRaisesRegex(ValueError,'unique'):resolve.resolve(self.req)
 def test_invalid_global_grid(self):
    self.g['west']='-179';self.manifest['grid']=self.g;report=json.loads((self.p/'physical-report').read_bytes());report['grid']=self.g;self.manifest['physical_report']=put(self.p/'physical-report',report);self.req['component_manifest']=put(self.p/'manifest',self.manifest);self.save_snap()
    with self.assertRaisesRegex(ValueError,'global grid'):resolve.resolve(self.req)
 def test_code_pin_mismatch(self):
    self.req['resolver_sha256']='0'*64
    with self.assertRaisesRegex(ValueError,'code pin'):resolve.resolve(self.req)
 def test_point_parse_requires_headroom(self):
    with patch.object(resolve,'available_memory_kib',return_value=resolve.MEMORY_FLOOR_KIB+1000):
     with self.assertRaisesRegex(ValueError,'headroom for point parsing'):resolve.resolve(self.req)
 def test_point_source_byte_cap(self):
    with (self.p/'point.json').open('wb') as f:f.truncate(1024*1024+1)
    self.pointpin={'path':str(self.p/'point.json'),'sha256':resolve.digest(self.p/'point.json')};self.sources[0]['sha256']=self.pointpin['sha256'];self.sources[0]['size_bytes']=1024*1024+1;self.req['source_files'][0].update(self.pointpin);self.save_snap()
    with self.assertRaisesRegex(ValueError,'point source exceeds bounded size'):resolve.resolve(self.req)
 def test_bounded_source_reader(self):
    p=self.p/'large';
    with p.open('wb') as f:f.truncate(8*1024*1024+1)
    with self.assertRaisesRegex(ValueError,'exceeds bounded size'):resolve.read_bounded(p,'source')
 def test_cli_does_not_overwrite_existing(self):
    request=put(self.p/'request',self.req);out=self.outdir/'existing';out.write_text('preserve')
    with patch.object(sys,'argv',['resolve.py',request['path'],str(out)]):
     with self.assertRaises(FileExistsError):resolve.main()
    self.assertEqual(out.read_text(),'preserve')
 def test_cli_rejects_output_overlapping_input(self):
    request=put(self.p/'request',self.req);out=Path(self.req['physical_rows']['path']);original=out.read_bytes()
    with patch.object(sys,'argv',['resolve.py',request['path'],str(out)]):
     with self.assertRaisesRegex(ValueError,'overlaps an input'):resolve.main()
    self.assertEqual(out.read_bytes(),original)
 def test_cli_detects_changed_request(self):
    request=put(self.p/'request',self.req);out=self.outdir/'new-report'
    def mutate(_):
     (self.p/'request').write_text('{}');return {}
    with patch.object(resolve,'resolve',side_effect=mutate), patch.object(sys,'argv',['resolve.py',request['path'],str(out)]):
     with self.assertRaisesRegex(ValueError,'request changed'):resolve.main()
    self.assertFalse(out.exists())
 def test_memory_floor(self):
    with patch.object(resolve,'available_memory_kib',return_value=1000000):
     with self.assertRaisesRegex(ValueError,'memory below safety floor'):resolve.resolve(self.req)
 def test_excessive_row_count_rejected_before_allocation(self):
    self.req['component_rows']=put(self.p/'cr',packed('<I',[(0,),(1000000,),(1000000,),(1000000,),(1000000,)]));self.manifest['pins']['component_rows']=self.req['component_rows'];self.req['component_manifest']=put(self.p/'manifest',self.manifest)
    with self.assertRaisesRegex(ValueError,'excessive run count'):resolve.resolve(self.req)
 def test_output_in_input_directory_rejected(self):
    request=put(self.p/'request',self.req);out=self.p/'new-report'
    with patch.object(sys,'argv',['resolve.py',request['path'],str(out)]):
     with self.assertRaisesRegex(ValueError,'input directory'):resolve.main()
    self.assertFalse(out.exists())
 def test_component_manifest_mismatch(self):
    self.manifest['component_source_sha256']='0'*64;self.req['component_manifest']=put(self.p/'manifest',self.manifest)
    with self.assertRaisesRegex(ValueError,'manifest identity'):resolve.resolve(self.req)
 def test_source_size_rejected(self):
    self.sources[0]['size_bytes']+=1;self.save_snap()
    with self.assertRaisesRegex(ValueError,'size mismatch'):resolve.resolve(self.req)
 def test_nonraw_source_rejected(self):
    self.sources[0]['kind']='derived';self.save_snap()
    with self.assertRaisesRegex(ValueError,'non-raw'):resolve.resolve(self.req)
 def test_unregistered_target(self):
    self.decision['entity_id']=99;self.save_snap()
    with self.assertRaisesRegex(ValueError,'unselected or malformed'):resolve.resolve(self.req)
 def test_component_sentinel_rejected(self):
    self.req['component_runs']=put(self.p/'cs',packed('<III',[(1,4,0xffffffff)]*4));self.manifest['pins']['component_runs']=self.req['component_runs'];self.req['component_manifest']=put(self.p/'manifest',self.manifest)
    with self.assertRaisesRegex(ValueError,'invalid component row'):resolve.resolve(self.req)
 def test_component_row_mismatch(self):
    self.req['component_runs']=put(self.p/'cs',packed('<III',[(1,3,7)]*4));self.manifest['pins']['component_runs']=self.req['component_runs'];self.req['component_manifest']=put(self.p/'manifest',self.manifest)
    with self.assertRaisesRegex(ValueError,'differs from physical'):resolve.resolve(self.req)
 def test_same_identity_and_point_source_rejected(self):
    self.decision['identity_source_id']='p';self.save_snap()
    with self.assertRaisesRegex(ValueError,'missing point or identity'):resolve.resolve(self.req)
 def test_unverified_export(self):
    self.snap['source']='local';self.save_snap()
    with self.assertRaisesRegex(ValueError,'Neon export'):resolve.resolve(self.req)
 def test_duplicate_source(self):
    self.snap['sources'].append(copy.deepcopy(self.sources[0]));self.save_snap()
    with self.assertRaisesRegex(ValueError,'duplicate source'):resolve.resolve(self.req)
 def test_changed_input_after_resolution(self):
    original=resolve.digest;path=self.req['physical_rows']['path'];count=0
    def fake(p):
     nonlocal count
     value=original(p)
     if str(p)==path:
      count+=1
      if count==2:return '0'*64
     return value
    with patch.object(resolve,'digest',side_effect=fake):
     with self.assertRaisesRegex(ValueError,'changed during'):resolve.resolve(self.req)
 def test_snapshot_asset_pin_disagreement(self):
    self.req['source_files'][0]['sha256']='0'*64
    with self.assertRaisesRegex(ValueError,'snapshot pin mismatch'):resolve.resolve(self.req)
if __name__=='__main__':unittest.main()
