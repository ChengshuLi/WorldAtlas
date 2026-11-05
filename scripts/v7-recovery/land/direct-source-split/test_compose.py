"""Synthetic row fixtures; categories are arbitrary test values."""
import random, unittest
from compose import compose_row

class ComposeTest(unittest.TestCase):
 def test_dynamic_codes_and_exact_cover(self):
  self.assertEqual(compose_row([(2,11),(5,0),(8,12)],[(2,4,31),(4,5,32)],[(2,5)],8,{11,12,31,32}),[(2,11),(4,31),(5,32),(8,12)])
 def test_overlap_gaps_and_wrong_codes_fail(self):
  with self.assertRaisesRegex(ValueError,'overlaps'):compose_row([(5,11)],[(1,3,31)],[(1,3)],5,{11,31})
  with self.assertRaisesRegex(ValueError,'exactly cover'):compose_row([(5,0)],[(1,2,31)],[(1,3)],5,{31})
  with self.assertRaisesRegex(ValueError,'invalid split code'):compose_row([(5,0)],[(1,3,99)],[(1,3)],5,{31})
 def test_random_rows_against_dense_reference(self):
  rng=random.Random(1234)
  for _ in range(100):
   width=40;selected={x for x in range(width) if rng.random()<0.3};base=[0 if x in selected else rng.choice([0,11,12]) for x in range(width)];split={x:rng.choice([31,32]) for x in selected}
   def rle(vals):
    result=[]
    for i,v in enumerate(vals):
     if i and v!=vals[i-1]:result.append((i,vals[i-1]))
    result.append((len(vals),vals[-1]));return result
   intervals=[];spans=[]
   for x in sorted(selected):
    if intervals and intervals[-1][1]==x:intervals[-1]=(intervals[-1][0],x+1)
    else:intervals.append((x,x+1))
    if spans and spans[-1][1]==x and spans[-1][2]==split[x]:spans[-1]=(spans[-1][0],x+1,split[x])
    else:spans.append((x,x+1,split[x]))
   got=compose_row(rle(base),spans,intervals,width,{11,12,31,32});expected=[split.get(x,base[x]) for x in range(width)];self.assertEqual(got,rle(expected))
if __name__=='__main__':unittest.main()
