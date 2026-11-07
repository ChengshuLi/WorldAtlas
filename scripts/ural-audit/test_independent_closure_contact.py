import hashlib,json,pathlib,struct,subprocess,sys,tempfile,unittest
SCRIPT=pathlib.Path(__file__).with_name('independent_closure_contact.py')
class ClosureTest(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.p=pathlib.Path(self.t.name)
  self.points=[[.5,3.5],[3.5,.5]]
 def tearDown(self):self.t.cleanup()
 def prepare(self,landcell):
  grid=[[1]*4 for _ in range(4)];x,y=landcell;grid[y][x]=17;offsets=[0];runs=[]
  for row in grid:
   ends=[i for i in range(1,4) if row[i]!=row[i-1]]+[4];runs.extend((i,row[i-1]) for i in ends);offsets.append(len(runs))
  for n,vals in [('physical-rows',offsets),('physical-runs',[v for pair in runs for v in pair])]:
   (self.p/n).write_bytes(struct.pack('<'+'I'*len(vals),*vals))
  (self.p/'closure').write_text(json.dumps(self.points));inputs={}
  for n in ['physical_rows','physical_runs','closure']:
   f=self.p/n.replace('_','-');inputs[n]={'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
  geom={'type':'LineString','coordinates':self.points};raw=json.dumps(geom,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
  m={'inputs':inputs,'geometry_sha256':hashlib.sha256(raw).hexdigest(),'config':{'width':4,'height':4,'west':0,'north':4,'step_degrees':1,'physical_land_code':17,'physical_water_code':1},'allow_land_at_start':False,'allow_land_at_end':True}
  (self.p/'manifest').write_text(json.dumps(m))
 def run_case(self,optimized=False):
  dest=self.p/'out';cmd=[sys.executable]+(['-O'] if optimized else [])+[str(SCRIPT),'--manifest',str(self.p/'manifest'),'--output',str(dest)]
  r=subprocess.run(cmd,capture_output=True,text=True);return r,dest
 def test_terminal_land_allowed(self):
  self.prepare((3,3));r,p=self.run_case();self.assertEqual(r.returncode,0,r.stderr);x=json.loads(p.read_text());self.assertTrue(x['terminal_policy_satisfied']);self.assertEqual(x['code_counts']['17'],1)
 def test_interior_land_is_reported_as_failure(self):
  self.prepare((1,1));r,p=self.run_case();self.assertEqual(r.returncode,0,r.stderr);self.assertFalse(json.loads(p.read_text())['terminal_policy_satisfied'])
 def test_rejects_optimized_python(self):
  self.prepare((3,3));r,p=self.run_case(True);self.assertNotEqual(r.returncode,0);self.assertIn('optimized Python',r.stderr);self.assertFalse(p.exists())
if __name__=='__main__':unittest.main()
