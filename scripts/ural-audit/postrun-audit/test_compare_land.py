import json,random,struct,subprocess,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
class Compare(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.binary=Path(cls.tmp.name)/'compare';subprocess.run(['c++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(HERE/'compare-land.cpp'),'-o',str(cls.binary)],check=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def write(self,p,name,grid):
  offsets=[0];records=[]
  for row in grid:
   for i,c in enumerate(row):
    if i==len(row)-1 or row[i+1]!=c:records.extend([i+1,c])
   offsets.append(len(records)//2)
  def pack(x):return struct.pack('<'+'I'*len(x),*x)
  (p/(name+'rows')).write_bytes(pack(offsets));(p/(name+'runs')).write_bytes(pack(records))
 def call(self,p,w,h):return subprocess.run([str(self.binary),str(w),str(h),*[str(p/(n+t)) for n in ('p','r','c') for t in ('rows','runs')]],capture_output=True,text=True)
 def test_random_cell_oracle_and_bad_physical(self):
  rng=random.Random(7711)
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)
   for _ in range(100):
    w=rng.randint(1,15);h=rng.randint(1,8);ph=[[rng.choice((1,17)) for x in range(w)] for y in range(h)];ref=[[rng.choice((1,2,10,17,18,19,20,21,22)) for x in range(w)] for y in range(h)];cand=[[0 if ph[y][x]==1 else rng.randint(17,22) for x in range(w)] for y in range(h)]
    for n,g in [('p',ph),('r',ref),('c',cand)]:self.write(p,n,g)
    run=self.call(p,w,h);self.assertEqual(run.returncode,0,run.stderr);out=json.loads(run.stdout);mat=[[0]*6 for i in range(6)];cw=rw=bw=0
    for y in range(h):
     for x in range(w):
      land=ph[y][x]==17;rl=ref[y][x]>=17
      if land and rl:mat[ref[y][x]-17][cand[y][x]-17]+=1
      elif land:rw+=1
      elif rl:cw+=1
      else:bw+=1
    self.assertEqual(out['reference_to_candidate_17_to_22'],mat);self.assertEqual((out['candidate_land_reference_water'],out['candidate_water_reference_land'],out['both_water']),(rw,cw,bw))
   ph=[[1]];ref=[[1]];cand=[[17]]
   for n,g in [('p',ph),('r',ref),('c',cand)]:self.write(p,n,g)
   self.assertNotEqual(self.call(p,1,1).returncode,0);self.assertNotEqual(self.call(p,0,1).returncode,0)
if __name__=='__main__':unittest.main()
