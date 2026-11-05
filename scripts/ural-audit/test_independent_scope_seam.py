import hashlib,json,pathlib,struct,subprocess,sys,tempfile,unittest

SCRIPT=pathlib.Path(__file__).with_name('independent_scope_seam.py')

class ScopeSeamTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=pathlib.Path(self.tmp.name)
  base=[[18]*6 for _ in range(6)]; physical=[[17]*6 for _ in range(6)]; overlay=[x[:] for x in base]
  for y in range(1,5):overlay[y][1:3]=[19,19]
  for name,v in [('base',base),('physical',physical),('overlay',overlay)]:self.grid(name,v)
  (self.p/'divider').write_text(json.dumps([[3,6],[3,0]]))
  inputs={}
  for n in ['base_rows','base_runs','physical_rows','physical_runs','overlay_rows','overlay_runs','divider']:
   f=self.p/n.replace('_','-');inputs[n]={'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
  self.m={'candidate_revision':'synthetic','inputs':inputs,'config':{'width':6,'height':6,'west':0,'north':6,'step_degrees':1,'bounds':[1,1,5,5],'europe_code':19,'asia_code':18},'independent_europe_witness':[2,3],'physical_land_code':17}
 def tearDown(self):self.tmp.cleanup()
 def grid(self,name,vals):
  offsets=[0];runs=[]
  for r in vals:
   ends=[i for i in range(1,6) if r[i]!=r[i-1]]+[6];runs.extend((i,r[i-1]) for i in ends);offsets.append(len(runs))
  for suffix,values in [('rows',offsets),('runs',[v for pair in runs for v in pair])]:
   (self.p/(name+'-'+suffix)).write_bytes(struct.pack('<'+'I'*len(values),*values))
 def run_script(self,optimized=False):
  (self.p/'manifest.json').write_text(json.dumps(self.m));out=self.p/'result.json'
  cmd=[sys.executable]+(['-O'] if optimized else [])+[str(SCRIPT),'--manifest',str(self.p/'manifest.json'),'--output',str(out)]
  return subprocess.run(cmd,capture_output=True,text=True),out
 def test_detects_scope_seams_without_side_errors(self):
  r,p=self.run_script();self.assertEqual(r.returncode,0,r.stderr);x=json.loads(p.read_text());self.assertEqual(x['full_scope']['physical_land'],16);self.assertNotIn('ray_vs_actual_mismatches',x['full_scope']);self.assertEqual(x['counts']['west_after_mismatch'],4);self.assertEqual(x['counts']['north_after_mismatch'],2);self.assertEqual(x['counts']['south_after_mismatch'],2)
 def test_rejects_changed_input(self):
  self.m['inputs']['overlay_runs']['sha256']='0'*64;r,p=self.run_script();self.assertNotEqual(r.returncode,0);self.assertFalse(p.exists())
 def test_refuses_optimized_python(self):
  r,p=self.run_script(optimized=True);self.assertNotEqual(r.returncode,0);self.assertIn('optimized Python',r.stderr);self.assertFalse(p.exists())
if __name__=='__main__':unittest.main()
