import random,unittest
from compose_direct import compose_row

class ComposeTests(unittest.TestCase):
 def test_composes_exact_root_without_touching_other_seed(self):
  self.assertEqual(compose_row([(2,17),(5,0),(7,0),(10,18)],[(2,4,20),(4,7,21)],[(2,7)],10),[(2,17),(4,20),(7,21),(10,18)])
 def test_empty_root_leaves_seed_unchanged(self):
  self.assertEqual(compose_row([(2,17),(5,0)],[],[],5),[(2,17),(5,0)])
 def test_overlapping_seed_rejected(self):
  with self.assertRaisesRegex(ValueError,'overlaps another seed'):compose_row([(5,17)],[(2,4,20)],[(2,4)],5)
 def test_missing_and_extra_cells_rejected(self):
  for spans in ([(2,3,20)],[(1,4,20)]):
   with self.subTest(spans=spans),self.assertRaisesRegex(ValueError,'exactly cover'):compose_row([(5,0)],spans,[(2,4)],5)
 def test_overlapping_split_and_invalid_codes_rejected(self):
  for spans in ([(1,3,20),(2,4,21)],[(1,4,99)]):
   with self.subTest(spans=spans),self.assertRaises(ValueError):compose_row([(5,0)],spans,[(1,4)],5)
 def test_randomized_against_cellwise_composition(self):
  rng=random.Random(8742)
  def end_runs(values):
   out=[]
   for i,v in enumerate(values,1):
    if out and out[-1][1]==v:out[-1]=(i,v)
    else:out.append((i,v))
   return out
  def spans(values,skip):
   out=[]
   for i,v in enumerate(values):
    if v==skip:continue
    if out and out[-1][1]==i and out[-1][2]==v:out[-1]=(out[-1][0],i+1,v)
    else:out.append((i,i+1,v))
   return out
  for _ in range(1000):
   width=rng.randrange(1,45);chosen=[rng.choice((False,True)) for _ in range(width)]
   base=[0 if flag else rng.choice((0,17,18)) for flag in chosen]
   split=[rng.choice((20,21)) if flag else 0 for flag in chosen]
   root=[(a,b) for a,b,_ in spans([1 if flag else 0 for flag in chosen],0)]
   self.assertEqual(compose_row(end_runs(base),spans(split,0),root,width),end_runs([s or b for s,b in zip(split,base)]))
 def test_invalid_base_and_root_rejected(self):
  for base,root in (([(4,0)],[]), ([(5,99)],[]), ([(5,0)],[(1,3),(2,4)])):
   with self.subTest(base=base,root=root),self.assertRaises(ValueError):compose_row(base,[],root,5)
if __name__=='__main__':unittest.main()
