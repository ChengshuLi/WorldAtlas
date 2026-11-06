import importlib.util, json, unittest
from fractions import Fraction as F
from pathlib import Path
p=Path(__file__).with_name('validate_water_closure_v2.py'); spec=importlib.util.spec_from_file_location('validator',p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.WIDTH=131072; m.HEIGHT=54614; m.WEST=F(-180); m.NORTH=F(90); m.STEP=F(360,131072)
class Validation(unittest.TestCase):
 def setUp(self): m.WIDTH=131072; m.HEIGHT=54614; m.WEST=F(-180); m.NORTH=F(90); m.STEP=F(360,131072)
 def cells(self,*coords): return set(m.touched_segment(*map(F,coords)))
 def test_interior(self): self.assertEqual(self.cells(F(1,4),F(1,4),F(3,4),F(3,4)), {(0,0)})
 def test_corner(self): self.assertEqual(self.cells(F(1,2),F(1,2),F(3,2),F(3,2)), {(0,0),(1,0),(0,1),(1,1)})
 def test_vertical_edge(self): self.assertEqual(self.cells(1,F(1,4),1,F(7,4)), {(0,0),(1,0),(0,1),(1,1)})
 def test_horizontal_edge(self): self.assertEqual(self.cells(F(1,4),1,F(7,4),1), {(0,0),(1,0),(0,1),(1,1)})
 def test_reverse(self): self.assertEqual(self.cells(F(1,5),F(19,10),F(9,5),F(1,10)), self.cells(F(9,5),F(1,10),F(1,5),F(19,10)))
 def test_reject_180_cross(self):
  with self.assertRaisesRegex(ValueError,'dateline'): m.geom_and_points(json.dumps({'type':'LineString','coordinates':[[179,10],[-179,10]]}).encode())
 def test_reject_zero(self):
  with self.assertRaisesRegex(ValueError,'zero-length'): m.geom_and_points(b'{"type":"LineString","coordinates":[[1,1],[1,1]]}')
 def test_reject_duplicate_key(self):
  with self.assertRaisesRegex(ValueError,'duplicate'): m.geom_and_points(b'{"type":"LineString","type":"LineString","coordinates":[[1,1],[2,2]]}')
 def test_reject_extreme_precision(self):
  with self.assertRaisesRegex(ValueError,'precision'): m.geom_and_points(b'{"type":"LineString","coordinates":[[1e-10000,1],[2,2]]}')
 def test_reject_non_roundtrip_coordinate(self):
  with self.assertRaisesRegex(ValueError,'loses precision'): m.geom_and_points(b'{"type":"LineString","coordinates":[[1.00000000000000001,1],[2,2]]}')
 def test_reject_explicit_crs(self):
  with self.assertRaisesRegex(ValueError,'CRS'): m.geom_and_points(b'{"type":"Feature","crs":{},"geometry":{"type":"LineString","coordinates":[[1,1],[2,2]]}}')
 def test_reject_grid_edge(self):
  with self.assertRaisesRegex(ValueError,'edge'): m.geom_and_points(b'{"type":"LineString","coordinates":[[-180,1],[-179,1]]}')

class IndependentCrosscheck(unittest.TestCase):
 def test_exhaustive_half_grid_against_liang_barsky(self):
  # Independent clipping formulation, not the row-band algorithm under test.
  def intersect(x0,y0,x1,y1,x,y):
   lo,hi=F(0),F(1)
   for p,q in ((-(x1-x0),x0-x),((x1-x0),x+1-x0),(-(y1-y0),y0-y),((y1-y0),y+1-y0)):
    if p == 0:
     if q < 0: return False
    else:
     t=q/p
     if p < 0: lo=max(lo,t)
     else: hi=min(hi,t)
     if lo>hi: return False
   return True
  values=[F(i,2) for i in range(0,7)]
  for x0 in values:
   for y0 in values:
    for x1 in values:
     for y1 in values:
      got=set(m.touched_segment(x0,y0,x1,y1))
      want={(x,y) for x in range(-1,4) for y in range(-1,4) if intersect(x0,y0,x1,y1,x,y)}
      self.assertEqual(got,want,(x0,y0,x1,y1))

class ContractValidation(unittest.TestCase):
 def make(self):
  return {'schema':'physical-water-closure-contract-v1','grid':{'crs':'EPSG:4326','width':4,'height':3,'west':-2,'north':2,'step_numerator':1,'step_denominator':1},'physical':{'rows_sha256':'a'*64,'runs_sha256':'b'*64,'water_code':1,'land_code':17,'report_sha256':'c'*64,'encoding_evidence_sha256':'d'*64,'producer_code_path':'producer.py'},'resources':{'max_cell_visits':100}}
 def load(self,c,wrong=False):
  import hashlib,tempfile
  with tempfile.NamedTemporaryFile() as f:
   raw=json.dumps(c).encode();f.write(raw);f.flush();return m.load_contract(f.name,'0'*64 if wrong else hashlib.sha256(raw).hexdigest())
 def test_contract_valid_and_changes_grid(self):
  h,c=self.load(self.make());self.assertEqual((m.WIDTH,m.HEIGHT,m.WEST,m.NORTH,m.STEP),(4,3,F(-2),F(2),F(1)));self.assertEqual(len(h),64)
 def test_reject_bad_hash(self):
  with self.assertRaisesRegex(ValueError,'hash mismatch'): self.load(self.make(),True)
 def test_reject_grid_exceeding_globe(self):
  c=self.make();c['grid']['width']=999
  with self.assertRaisesRegex(ValueError,'bounds'): self.load(c)
 def test_reject_equal_codes(self):
  c=self.make();c['physical']['land_code']=1
  with self.assertRaisesRegex(ValueError,'differ'): self.load(c)
 def test_reject_oversized_index_before_hash(self):
  import tempfile
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);(base/'rows.u32le').write_bytes(b'x'*9);(base/'runs.u32le').write_bytes(b'')
   m.HEIGHT=1
   with self.assertRaisesRegex(ValueError,'invalid row index length'):m.Mask(base)
 def test_reject_zero_length_first_run(self):
  import hashlib,tempfile,struct
  with tempfile.TemporaryDirectory() as d:
   base=Path(d); rows=struct.pack('<II',0,2); runs=struct.pack('<IIII',0,1,4,1)
   (base/'rows.u32le').write_bytes(rows); (base/'runs.u32le').write_bytes(runs)
   m.WIDTH=4;m.HEIGHT=1;m.ROWS=hashlib.sha256(rows).hexdigest();m.RUNS=hashlib.sha256(runs).hexdigest();m.WATER=1;m.LAND=17
   mask=m.Mask(base)
   with self.assertRaisesRegex(ValueError,'invalid physical run values'):mask.code(0,0)
   mask.run.close()
 def test_report_and_producer_binding(self):
  import hashlib,tempfile
  with tempfile.TemporaryDirectory() as d:
   base=Path(d); raw=b'physical producer evidence'; (base/'producer.py').write_bytes(raw)
   report={'grid':{'width':4,'height':3,'west':-2,'north':2,'step':1},'output_sha256':{'rows.u32le':'a'*64,'runs.u32le':'b'*64}}
   report_bytes=json.dumps(report).encode(); (base/'report.json').write_bytes(report_bytes)
   c=self.make(); c['physical']['encoding_evidence_sha256']=hashlib.sha256(raw).hexdigest(); c['physical']['report_sha256']=hashlib.sha256(report_bytes).hexdigest()
   contract=base/'contract.json'; contract_bytes=json.dumps(c).encode(); contract.write_bytes(contract_bytes)
   m.load_contract(contract,hashlib.sha256(contract_bytes).hexdigest())
   self.assertEqual(m.verify_producer_code(contract,c),base/'producer.py')
   self.assertEqual(m.verify_physical_report(base,c),base/'report.json')
   (base/'producer.py').write_bytes(b'tampered')
   with self.assertRaisesRegex(ValueError,'producer evidence hash'): m.verify_producer_code(contract,c)
   report['grid']['width']=3; report_bytes=json.dumps(report).encode(); (base/'report.json').write_bytes(report_bytes); c['physical']['report_sha256']=hashlib.sha256(report_bytes).hexdigest()
   with self.assertRaisesRegex(ValueError,'grid mismatch'): m.verify_physical_report(base,c)
 def test_reject_excess_visits(self):
  c=self.make();c['resources']['max_cell_visits']=2000001
  with self.assertRaisesRegex(ValueError,'visit limit'): self.load(c)

if __name__=='__main__': unittest.main()
