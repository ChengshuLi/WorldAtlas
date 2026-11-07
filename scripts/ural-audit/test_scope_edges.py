import os, subprocess, sys, tempfile, unittest
import numpy as np
from delta_divider_apply import apply, sides, update_row

CFG={'width':4,'height':4,'step_degrees':1,'west':0,'north':4,
     'land_codes':[18,19,20,21], 'asia_code':18, 'europe_code':19,
     'bounds':[.5,.5,3.5,3.5], 'europe_witness':[1,2], 'asia_witness':[3,2]}
LINE=[[2,4],[2,0]]

def encode(values):
    offsets=[0]; pairs=[]
    for row in values:
        last=None
        for x,v in enumerate(row):
            if last is not None and v!=last: pairs.append((x,last))
            last=v
        pairs.append((len(row),last)); offsets.append(len(pairs))
    return np.array(offsets,dtype='<u4'),np.array(pairs,dtype='<u4').ravel()

def run(old,physical,d):
    a,b=encode(old);c,e=encode(physical)
    return apply(a,b,c,e,LINE,CFG,os.path.join(d,'rows'),os.path.join(d,'runs'))

class ScopeEdgeTests(unittest.TestCase):
    def test_verifier_refuses_optimized_mode(self):
        p=subprocess.run([sys.executable,'-O',os.path.join(os.path.dirname(__file__),'verify_pipeline.py')],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('optimized Python disables verifier assertions',p.stderr)

    def test_all_edges_and_corners_reject_physical_or_candidate_land(self):
        for x,y in [(0,1),(3,1),(1,0),(1,3),(0,0),(3,0),(0,3),(3,3)]:
            for candidate,physical in [(18,17),(0,17),(18,0)]:
                with self.subTest(x=x,y=y,candidate=candidate,physical=physical), tempfile.TemporaryDirectory() as d:
                    old=np.zeros((4,4),dtype=int); mask=np.zeros((4,4),dtype=int)
                    old[y,x]=candidate;mask[y,x]=physical
                    with self.assertRaisesRegex(ValueError,'land center on scope boundary'):run(old,mask,d)
    def test_water_on_edges_and_other_land_labels_preserved_and_reported(self):
        old=np.zeros((4,4),dtype=int);mask=np.zeros((4,4),dtype=int)
        old[1,1],old[2,2]=20,21;mask[1,1]=mask[2,2]=17
        with tempfile.TemporaryDirectory() as d:
            counts=run(old,mask,d)
            self.assertEqual(counts['other_land_labels'],2)
            self.assertEqual(counts['other_land_labels_by_code'],{'20':1,'21':1})
            self.assertEqual(counts['europe_to_asia']+counts['asia_to_europe'],0)
            actual=np.fromfile(os.path.join(d,'runs'),dtype='<u4')
            self.assertTrue(np.array_equal(actual,encode(old)[1]))
    def test_near_edge_candidate_land_is_not_silently_ignored(self):
        bounds=(0,0,4,2);e,a=sides([(2,-1),(2,3)],bounds,(1,1),(3,1))
        with self.assertRaisesRegex(ValueError,'land center on scope boundary'):
            update_row(np.array([18]),np.array([0]),np.array([1e-13]),1,e,a,bounds,CFG)

    def test_interior_masks_must_agree(self):
        old=np.zeros((4,4),dtype=int);mask=np.zeros((4,4),dtype=int)
        old[1,1]=20
        with tempfile.TemporaryDirectory() as d, self.assertRaisesRegex(ValueError,'physical land masks differ'):
            run(old,mask,d)

if __name__=='__main__':unittest.main()
