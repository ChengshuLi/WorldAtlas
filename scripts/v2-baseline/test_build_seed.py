import hashlib,json,tempfile,unittest
from pathlib import Path
import numpy as np
from build_seed import build

def pin(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def polygon(p,x0,y0,x1,y1):p.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':{'type':'Polygon','coordinates':[[[x0,y0],[x1,y0],[x1,y1],[x0,y1],[x0,y0]]]}}]}))
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.p=Path(self.t.name);self.i=self.p/'inputs';self.i.mkdir()
  np.asarray([0,3,4,5],'<u4').tofile(self.i/'cr');np.asarray([(0,4,10),(4,6,11),(7,8,99),(0,8,12),(0,8,13)],'<u4').tofile(self.i/'cv')
  polygon(self.i/'a.geojson',0,0,3,3);polygon(self.i/'b.geojson',2,0,5,3)
  self.c={'schema':'direct-region-seed-research-v1','grid':{'width':8,'height':3,'west':0,'north':3,'step':1,'crs':'EPSG:4326'},'component_rows':pin(self.i/'cr'),'component_runs':pin(self.i/'cv'),'regions':[{'id':'a','geometry':pin(self.i/'a.geojson'),'witnesses':[{'lon':1,'lat':1,'inside':True},{'lon':4,'lat':1,'inside':False}]},{'id':'b','geometry':pin(self.i/'b.geojson'),'witnesses':[]}], 'rules':[{'component_id':10,'region_id':'a','inside_code':19,'outside_code':18},{'component_id':11,'region_id':'b','inside_code':20,'outside_code':21},{'component_id':12,'region_id':None,'inside_code':17,'outside_code':17},{'component_id':13,'region_id':None,'inside_code':22,'outside_code':22}],'evidence':[],'strip_rows':2,'reserve_bytes':0}
 def tearDown(self):self.t.cleanup()
 def runbuild(self):
  f=self.i/'config.json';f.write_text(json.dumps(self.c));return build(f,self.p/'out')
 def test_complete_region_overlap_and_zero(self):
  r=self.runbuild();self.assertEqual(r['status'],'unreviewed-research-not-published');self.assertEqual(r['grid_crs'],'EPSG:4326');self.assertNotIn('crs',r['grid']);o=np.fromfile(self.p/'out/rows.u32le','<u4');v=np.fromfile(self.p/'out/runs.u32le','<u4').reshape(-1,2);self.assertEqual(o.tolist(),[0,5,6,7]);self.assertEqual(v.tolist(),[[3,19],[4,18],[5,20],[6,21],[8,0],[8,17],[8,22]])
 def test_bad_input_pin_fails_before_output(self):
  self.c['component_runs']['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'pin mismatch'):self.runbuild()
  self.assertFalse((self.p/'out').exists())
 def test_witness_failure(self):
  self.c['regions'][0]['witnesses'][0]['inside']=False
  with self.assertRaisesRegex(ValueError,'witness fails'):self.runbuild()
 def test_missing_root_never_succeeds(self):
  self.c['rules'][0]['component_id']=888
  with self.assertRaises(RuntimeError):self.runbuild()
  self.assertFalse((self.p/'out/report.json').exists())
 def test_duplicate_root_refused(self):
  self.c['rules'][1]['component_id']=10
  with self.assertRaisesRegex(ValueError,'root/code'):self.runbuild()
 def test_existing_output_refused(self):
  (self.p/'out').mkdir()
  with self.assertRaisesRegex(ValueError,'output exists'):self.runbuild()
 def test_default_disk_reserve_blocks_before_output(self):
  from unittest.mock import patch
  from collections import namedtuple
  self.c.pop('reserve_bytes')
  with patch('build_seed.shutil.disk_usage',return_value=namedtuple('Disk','total used free')(100,100,0)):
   with self.assertRaisesRegex(ValueError,'insufficient free space'):self.runbuild()
  self.assertFalse((self.p/'out').exists())
 def test_space_rechecked_per_strip(self):
  from unittest.mock import patch
  from collections import namedtuple
  disk=namedtuple('Disk','total used free');self.c['reserve_bytes']=1
  with patch('build_seed.shutil.disk_usage',side_effect=[disk(100,0,100),disk(100,0,100),disk(100,100,0)]):
   with self.assertRaisesRegex(ValueError,'insufficient free space'):self.runbuild()
  self.assertFalse((self.p/'out/report.json').exists())
 def test_input_output_directory_overlap_rejected(self):
  f=self.i/'config.json';f.write_text(json.dumps(self.c))
  with self.assertRaisesRegex(ValueError,'directories overlap'):build(f,self.i/'out')
 def test_big_endian_host_rejected(self):
  from unittest.mock import patch
  with patch('build_seed.sys.byteorder','big'):
   with self.assertRaisesRegex(ValueError,'little-endian'):self.runbuild()
 def test_boundary_witness_rejected(self):
  self.c['regions'][0]['witnesses'][0]={'lon':0,'lat':1,'inside':True}
  with self.assertRaisesRegex(ValueError,'witness fails'):self.runbuild()
 def test_changed_program_is_rejected_after_build(self):
  from unittest.mock import patch
  from build_seed import sha
  calls={}
  def altered(p):
   k=str(p);calls[k]=calls.get(k,0)+1
   if p.name=='seed_kernel.cpp' and calls[k]>1:return '0'*64
   return sha(p)
  with patch('build_seed.sha',side_effect=altered):
   with self.assertRaisesRegex(ValueError,'program changed'):self.runbuild()
  self.assertFalse((self.p/'out/report.json').exists())
 def test_changed_input_is_rejected_after_build(self):
  from unittest.mock import patch
  from build_seed import sha
  calls={}
  def altered(p):
   k=str(p);calls[k]=calls.get(k,0)+1
   if p.name=='a.geojson' and calls[k]>1:return '0'*64
   return sha(p)
  with patch('build_seed.sha',side_effect=altered):
   with self.assertRaisesRegex(ValueError,'pin mismatch'):self.runbuild()
  self.assertFalse((self.p/'out/report.json').exists())
 def test_grid_crs_rejected(self):
  self.c['grid']['crs']='EPSG:3857'
  with self.assertRaisesRegex(ValueError,'invalid grid'):self.runbuild()
 def test_polygon_crs_rejected(self):
  f=self.i/'a.geojson';j=json.loads(f.read_bytes());j['crs']={'type':'name','properties':{'name':'urn:ogc:def:crs:EPSG::3857'}};f.write_text(json.dumps(j));self.c['regions'][0]['geometry']=pin(f)
  with self.assertRaisesRegex(ValueError,'WGS84'):self.runbuild()
if __name__=='__main__':unittest.main()
