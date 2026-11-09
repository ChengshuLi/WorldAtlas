import hashlib,json,tempfile,unittest
from pathlib import Path
import verify_physical_lineage as v
class LineageTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=Path(self.tmp.name);self.grid={'width':8,'height':4,'west':-180,'north':90,'step':45};self.files=[];self.shards=[];self.entries=[];self.union=[]
  for i in range(32):
   name=f'part-{i:05d}-fixture.zstd.parquet';sha=format(i+1,'064x');out=format(i+100,'064x');f={'path':'water/'+name,'key':'release/water/'+name,'sha256':sha,'size':1,'provider_sha256_composite':'ok','computed_sha256_composite':'ok'};self.files.append(f)
   r={'status':'candidate-only','source':'/raw/'+name,'source_sha256':sha,'script_sha256':'a'*64,'grid':self.grid,'output_sha256':out,'counts':{'rows':1}};self.shards.append({'index':i,**self.write('s'+str(i),r)});self.entries.append({'index':i,'status':'candidate-only','output_sha256':out,'counts':{'rows':1}});self.union.append({'index':i,'sha256':out})
  self.readback=self.write('readback',[{'key':'path/'+Path(f['path']).name,'size':f['size'],'sha256':f['sha256']} for f in self.files])
  manifest={'source':'Overture Maps Foundation','theme':'base','type':'water','file_count':32,'total_bytes':32,'files':self.files};self.man=self.write('manifest',manifest);summary={'status':'candidate-only','manifest_sha256':self.man['sha256'],'rasterizer_sha256':'a'*64,'shards':self.entries};self.sump=self.write('summary',summary);un={'status':'candidate-only','source_summary_sha256':self.sump['sha256'],'shard_hashes':self.union,'union_sha256':'b'*64};self.unp=self.write('union',un)
  names=['README.txt','land_polygons.cpg','land_polygons.dbf','land_polygons.prj','land_polygons.shp','land_polygons.shx'];self.members=[{'name':'osm/'+x,'sha256':format(i+200,'064x')} for i,x in enumerate(names)];self.receipt=self.write('receipt',{'archive_sha256':'c'*64,'archive_bytes':123,'source_url':'https://example.org/land.zip','files':self.members});self.land=self.write('land',{'status':'candidate-only','source_files':[{'path':'/x/'+Path(x['name']).name,'sha256':x['sha256']} for x in self.members],'candidate_sha256':'d'*64});self.physical=self.write('physical',{'status':'candidate-only','grid':self.grid,'inputs':{'land':{'sha256':'d'*64},'water':{'sha256':'b'*64}},'output_sha256':{'rows.u32le':'e'*64,'runs.u32le':'f'*64}})
  self.req={'schema':'stage1-reported-lineage-request-v1','inputs':{'overture_manifest':self.man,'overture_readback':self.readback,'osm_receipt':self.receipt,'shard_summary':self.sump,'water_union':self.unp,'land_report':self.land,'physical_report':self.physical},'shard_reports':self.shards};self.request=self.d/'request';self.save()
 def write(self,name,obj):
  p=self.d/name;p.write_text(json.dumps(obj,sort_keys=True));return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 def save(self):self.request.write_text(json.dumps(self.req,sort_keys=True))
 def check(self):return v.validate(self.request,self.physical['sha256'],'e'*64,'f'*64,self.grid)
 def test_valid_report_chain(self):self.assertEqual(self.check()['status'],'reported-lineage-verified-not-rerasterized')
 def test_tampered_shard_even_with_new_pin_fails(self):
  report=json.loads((self.d/'s0').read_text());report['source_sha256']='0'*64;self.req['shard_reports'][0]={'index':0,**self.write('s0',report)};self.save()
  with self.assertRaisesRegex(ValueError,'shard report chain mismatch'):self.check()
 def test_missing_or_duplicate_shard_fails(self):
  self.req['shard_reports'][1]['index']=0;self.save()
  with self.assertRaisesRegex(ValueError,'duplicate or missing'):self.check()
 def test_source_member_mismatch_even_with_new_pin_fails(self):
  receipt=json.loads((self.d/'receipt').read_text());receipt['files'][0]['sha256']='0'*64;self.req['inputs']['osm_receipt']=self.write('receipt',receipt);self.save()
  with self.assertRaisesRegex(ValueError,'OSM member chain mismatch'):self.check()
 def test_wrong_physical_output_fails(self):
  with self.assertRaisesRegex(ValueError,'physical report chain mismatch'):v.validate(self.request,self.physical['sha256'],'0'*64,'f'*64,self.grid)
 def test_missing_matching_land_values_cannot_pass(self):
  land=json.loads((self.d/'land').read_text());land.pop('candidate_sha256');self.req['inputs']['land_report']=self.write('land',land)
  physical=json.loads((self.d/'physical').read_text());physical['inputs']['land'].pop('sha256');self.physical=self.write('physical',physical);self.req['inputs']['physical_report']=self.physical;self.save()
  with self.assertRaisesRegex(ValueError,'missing land or water output hash'):self.check()
 def test_missing_matching_rasterizer_hash_cannot_pass(self):
  summary=json.loads((self.d/'summary').read_text());summary.pop('rasterizer_sha256');self.sump=self.write('summary',summary);self.req['inputs']['shard_summary']=self.sump
  union=json.loads((self.d/'union').read_text());union['source_summary_sha256']=self.sump['sha256'];self.req['inputs']['water_union']=self.write('union',union);self.save()
  with self.assertRaisesRegex(ValueError,'missing rasterizer hash'):self.check()
 def test_missing_matching_shard_outputs_cannot_pass(self):
  report=json.loads((self.d/'s0').read_text());report.pop('output_sha256');self.req['shard_reports'][0]={'index':0,**self.write('s0',report)}
  summary=json.loads((self.d/'summary').read_text());summary['shards'][0].pop('output_sha256');self.sump=self.write('summary',summary);self.req['inputs']['shard_summary']=self.sump
  union=json.loads((self.d/'union').read_text());union['source_summary_sha256']=self.sump['sha256'];union['shard_hashes'][0].pop('sha256');self.req['inputs']['water_union']=self.write('union',union);self.save()
  with self.assertRaisesRegex(ValueError,'missing shard output hash'):self.check()
 def test_missing_grid_cannot_pass(self):
  physical=json.loads((self.d/'physical').read_text());physical.pop('grid');self.physical=self.write('physical',physical);self.req['inputs']['physical_report']=self.physical;self.save()
  with self.assertRaisesRegex(ValueError,'physical grid mismatch'):self.check()
 def neon_snapshot(self):
  entries=[];sources=[];assets=[]
  def add(role,ordinal,sha,size,name):
   sid=role+str(ordinal);version='1';entry={'decision_revision':'rev','role':role,'ordinal':ordinal,'source_id':sid,'source_version':version,'execution_status':'selected_for_research'};src={'source_id':sid,'version':version,'sha256':sha,'size_bytes':size,'r2_bucket':'raw','r2_key':'path/'+name};entries.append(entry);sources.append(src);assets.append({**src,'kind':'raw','source_uri':'https://example.org/'+name,'provenance':{}})
  add('physical_land',0,'c'*64,123,'land.zip')
  for i,f in enumerate(self.files):add('inland_water',i,f['sha256'],f['size'],Path(f['path']).name)
  return {'decision_revision':{'id':'rev'},'stage1_source_inputs':entries,'sources':sources,'source_lineage_assets':assets,'source_lineage_dependencies':[]}
 def test_selected_neon_sources_match_report_chain(self):
  snap=self.neon_snapshot();r=v.validate_neon_sources(snap,'a'*64,self.request);self.assertEqual((r['status'],len(r['selected_sources'])),('selected-source-records-match-reported-lineage',33))
  snap['stage1_source_inputs'][0]['execution_status']='draft'
  with self.assertRaisesRegex(ValueError,'invalid selected'):v.validate_neon_sources(snap,'a'*64,self.request)
 def test_selected_source_mismatch_and_missing_fail(self):
  snap=self.neon_snapshot();snap['sources'][5]['sha256']='0'*64;snap['source_lineage_assets'][5]['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'differs from report chain|R2 key differs'):v.validate_neon_sources(snap,'a'*64,self.request)
  snap=self.neon_snapshot();snap['stage1_source_inputs'].pop()
  with self.assertRaisesRegex(ValueError,'missing selected'):v.validate_neon_sources(snap,'a'*64,self.request)
if __name__=='__main__':unittest.main()
