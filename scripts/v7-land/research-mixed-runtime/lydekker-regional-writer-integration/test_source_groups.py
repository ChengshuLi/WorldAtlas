import hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
from source_groups import resolve_feature_windows

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class SourceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();d=Path(self.tmp.name);self.osm=d/'osm.zip';self.osm.write_bytes(b'osm');self.big=d/'gazette.pdf';self.big.write_bytes(b'gazette');self.geo=d/'id.zip'
  fields=['101','Island One','Island One','','1.5','2.5','T','ISL','ID']+['']*10
  with zipfile.ZipFile(self.geo,'w') as z:z.writestr('ID.txt','\t'.join(fields)+'\n')
  self.sources={'osm-land-polygons-split-4326':{'path':str(self.osm),'shapefile':str(d/'land_polygons.shp'),'version':'osm-v','sha256':sha(self.osm)},'geonames-country-id':{'path':str(self.geo),'version':'geo-v','sha256':sha(self.geo)},'indonesia-big-national-gazetteer':{'path':str(self.big),'version':'big-v','sha256':sha(self.big)}}
  self.inputs={}
  for n in ('physical_rows','physical_runs','component_rows','component_runs'):
   f=d/n;f.write_bytes(n.encode());self.inputs[n]={'path':str(f),'sha256':sha(f)}
  self.policy={'sources':[{'source_id':k,'version':v['version'],'sha256':v['sha256']} for k,v in self.sources.items()],'evidence':{'component_rows_sha256':self.inputs['component_rows']['sha256'],'component_runs_sha256':self.inputs['component_runs']['sha256']},'regional_groups':[{'group_id':'g','target_code':18,'mode':'complete_source_feature','osm_feature_ids':['1','2'],'named_witnesses':[{'source':'geonames-country-id','id':'101'},{'source':'indonesia-big-national-gazetteer','name':'Island Two','point_lon_lat':[5.5,6.5]}],'source_section':'reference','limitation':'interpreted'}],'source_feature_pins':[{'source_id':'osm-land-polygons-split-4326','source_version':'osm-v','source_feature_id':i,'geometry_sha256':i*64} for i in ('1','2')],'named_small_island_anchor_ids':['101'],'anchor_discovery':{'official_reef_anchors':['Island Two']}}
  self.region={10:{'total':2,'in_scope':2},20:{'total':1,'in_scope':1},30:{'total':3,'in_scope':3}}
 def tearDown(self):self.tmp.cleanup()
 def resolve(self,*,partial=False,inside=True):
  def extract(path,shp,source_sha,specs,guard):return [({'fid':s['source_feature_id']},{'source_feature_id':s['source_feature_id'],'geometry_sha256':s['geometry_sha256'],'source_sha256':source_sha}) for s in specs]
  def intersect(geoms,grid,*args):
   fid=geoms[0]['fid'];return ([10,30],{'per_feature_root_inside_cells':[{'10':1 if partial else 2,'30':1}]}) if fid=='1' else ([20],{'per_feature_root_inside_cells':[{'20':1}]})
  def point_inside(g,x,y):return inside
  def component_at(rows,runs,grid,x,y):return 10 if x==2.5 else 20
  return resolve_feature_windows(self.policy,self.region,{},self.inputs,self.sources,extract=extract,intersect=intersect,point_inside=point_inside,component_at=component_at,guard=lambda:None)
 def test_whole_feature_roots_and_named_anchors(self):
  out=self.resolve();self.assertEqual(set(out['windows'][0]['components']),{10,20});self.assertEqual(set(out['anchors']),{10,20});self.assertEqual(out['source_trace'][0]['partial_roots_current_generation_only'],[30])
 def test_partial_named_witness_fails_closed(self):
  with self.assertRaisesRegex(ValueError,'not fully covered'):self.resolve(partial=True)
 def test_point_outside_source_polygon_fails(self):
  with self.assertRaisesRegex(ValueError,'outside selected'):self.resolve(inside=False)
 def test_changed_source_bytes_fail(self):
  self.big.write_bytes(b'tampered')
  with self.assertRaisesRegex(ValueError,'source bytes mismatch'):self.resolve()
