import unittest
import numpy as np
import delta_core as d
class Delta(unittest.TestCase):
 def setUp(self):
  # Root 1 affects 4 cells; root 2 affects 1, with gaps and an empty row.
  self.cr=np.array([0,0,3,4],dtype=np.uint32);self.cv=np.array([[0,2,1],[4,6,1],[7,8,2],[3,4,2]],dtype=np.uint32)
  # Two rows of labels plus empty first row, each candidate/reference fully covers width 8.
  self.rows=np.array([0,1,5,7],dtype=np.uint32)
  self.base=np.array([[8,0],[2,17],[4,0],[6,18],[8,17],[3,0],[8,18]],dtype=np.uint32)
  self.ref=np.array([[8,1],[1,17],[2,18],[4,1],[6,18],[8,17],[3,1],[4,17],[8,1]],dtype=np.uint32)
  self.rr=np.array([0,1,6,9],dtype=np.uint32)
 def test_full_component_and_new_mismatch(self):
  spans,counts=d.selected_spans(self.cr,self.cv,8,{1:18,2:17},chunk=2)
  self.assertEqual(counts,{1:4,2:2})
  out=d.compare_delta(spans,{1:18,2:17},self.rows,self.base,self.rr,self.ref,8,{17,18},{1})['total']
  self.assertEqual(out,{'affected_cells':6,'reference_water_cells':0,'old_mismatch':2,'new_mismatch':1,'new_mismatch_from_match':1,'resolved_mismatch':2,'unchanged_mismatch':0})
 def test_bad_rows_and_missing_root(self):
  with self.assertRaises(ValueError):d.selected_spans(self.cr,self.cv,8,{3:17})
  corrupt=self.cv.copy();corrupt[1,0]=1
  with self.assertRaises(ValueError):d.selected_spans(self.cr,corrupt,8,{1:17})
 def test_candidate_water_rejected(self):
  spans,_=d.selected_spans(self.cr,self.cv,8,{1:18})
  bad=self.base.copy();bad[1,1]=0
  with self.assertRaisesRegex(ValueError,'candidate water'):d.compare_delta(spans,{1:18},self.rows,bad,self.rr,self.ref,8,{17,18},{1})

class RandomDifferential(unittest.TestCase):
 def test_random_against_per_cell_ground_truth(self):
  import random
  q=random.Random(277)
  for _ in range(200):
   width=30;height=8;targets={1:17,2:18};crow=[0];cruns=[];brow=[0];bruns=[];rrow=[0];rruns=[];cells=[]
   for y in range(height):
    roots=[q.randrange(0,4) for _ in range(width)];base=[q.choice([17,18]) if r else 0 for r in roots];ref=[q.choice([1,17,18]) for _ in roots];cells.extend(zip(roots,base,ref))
    i=0
    while i<width:
     j=i+1
     while j<width and roots[j]==roots[i]:j+=1
     if roots[i]:cruns.append([i,j,roots[i]])
     i=j
    crow.append(len(cruns))
    for a,runs,rows in ((base,bruns,brow),(ref,rruns,rrow)):
     for i in range(width):
      if i==width-1 or a[i]!=a[i+1]:runs.append([i+1,a[i]])
     rows.append(len(runs))
   if not all(any(r==k for r,_,_ in cells) for k in targets):continue
   arrays=[np.array(z,dtype=np.uint32) for z in (crow,cruns,brow,bruns,rrow,rruns)];c,cc,br,bb,rr,rb=arrays
   spans,counts=d.selected_spans(c,cc,width,targets,chunk=5);out=d.compare_delta(spans,targets,br,bb,rr,rb,width,{17,18},{1})['total']
   subset=[(r,b,v) for r,b,v in cells if r in targets];self.assertEqual(out['affected_cells'],len(subset));self.assertEqual(out['reference_water_cells'],sum(v==1 for r,b,v in subset));self.assertEqual(out['old_mismatch'],sum(v!=1 and b!=v for r,b,v in subset));self.assertEqual(out['new_mismatch'],sum(v!=1 and targets[r]!=v for r,b,v in subset));self.assertEqual(out['new_mismatch_from_match'],sum(v!=1 and b==v and targets[r]!=v for r,b,v in subset))

class LimitTests(unittest.TestCase):
 def test_overflow_rejected(self):
  rows=np.array([0,2],dtype=np.uint32);runs=np.array([[0,1,1],[2,3,1]],dtype=np.uint32)
  with self.assertRaisesRegex(ValueError,'invalid targets'):d.selected_spans(rows,runs,3,{2**32:17})
 def test_reject_overlapping_caller_spans(self):
  rows=np.array([0,1],dtype=np.uint32);b=np.array([[5,17]],dtype=np.uint32);r=np.array([[5,18]],dtype=np.uint32)
  with self.assertRaisesRegex(ValueError,'overlapping'):d.compare_delta({0:[(0,3,1),(2,5,1)]},{1:18},rows,b,rows,r,5,{17,18},{1})
 def test_reference_water_is_excluded(self):
  rows=np.array([0,1],dtype=np.uint32);b=np.array([[5,17]],dtype=np.uint32);r=np.array([[5,1]],dtype=np.uint32)
  x=d.compare_delta({0:[(0,5,1)]},{1:18},rows,b,rows,r,5,{17,18},{1})['total'];self.assertEqual((x['affected_cells'],x['reference_water_cells'],x['old_mismatch'],x['new_mismatch']),(5,5,0,0))

class WidthTests(unittest.TestCase):
 def test_uint32_width_bound(self):
  rows=np.array([0,1],dtype=np.uint32);runs=np.array([[2,17]],dtype=np.uint32)
  with self.assertRaisesRegex(ValueError,'width'):d.compare_delta({0:[(0,1,1)]},{1:17},rows,runs,rows,runs,2**32,{17},{1})

class TypeTests(unittest.TestCase):
 def test_boolean_categories_rejected(self):
  rows=np.array([0,1],dtype=np.uint32);v=np.array([[5,17]],dtype=np.uint32)
  with self.assertRaisesRegex(ValueError,'categories'):d.compare_delta({0:[(0,5,1)]},{1:17},rows,v,rows,v,5,{17},{True})
 def test_non_integer_streams_rejected(self):
  rows=np.array([0,1],dtype=np.uint32);v=np.array([[5.0,17.0]])
  with self.assertRaisesRegex(ValueError,'dtype'):d.compare_delta({0:[(0,5,1)]},{1:17},rows,v,rows,v,5,{17},{1})

class RootZeroTests(unittest.TestCase):
 def test_valid_root_zero(self):
  cr=np.array([0,1],dtype=np.uint32);cv=np.array([[0,5,0]],dtype=np.uint32);rows=np.array([0,1],dtype=np.uint32);candidate=np.array([[5,17]],dtype=np.uint32);reference=np.array([[5,18]],dtype=np.uint32)
  spans,counts=d.selected_spans(cr,cv,5,{0:18});self.assertEqual(counts,{0:5});result=d.compare_delta(spans,{0:18},rows,candidate,rows,reference,5,{17,18},{1});self.assertEqual((result['total']['old_mismatch'],result['total']['new_mismatch']),(5,0))

if __name__=='__main__': unittest.main()
