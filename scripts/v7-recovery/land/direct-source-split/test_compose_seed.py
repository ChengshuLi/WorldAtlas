"""Synthetic test intervals and category codes only."""
import unittest
from compose_seed import compose_streams

class ComposeStreamsTest(unittest.TestCase):
 def test_complete_stream_and_exact_cover(self):
  outputs=[];guards=[]
  partial=lambda y:[(1,11),(3,0),(5,12)]
  component=lambda y:[(1,3,7)]
  direct=lambda y:[(1,2,31),(2,3,32)]
  result=compose_streams(partial,direct,component,7,5,2,{11,12,31,32},lambda y,row:outputs.append(row),lambda:guards.append(1))
  self.assertEqual(result['selected_cells'],4);self.assertEqual(outputs,[[(1,11),(2,31),(3,32),(5,12)]]*2);self.assertTrue(guards)
 def test_mismatched_or_overlapping_output_fails(self):
  partial=lambda y:[(5,0)];component=lambda y:[(1,3,7)]
  with self.assertRaisesRegex(ValueError,'exactly cover'):compose_streams(partial,lambda y:[(1,2,31)],component,7,5,1,{31},lambda *_:None,lambda:None)
  with self.assertRaisesRegex(ValueError,'invalid component'):compose_streams(partial,lambda y:[],lambda y:[(1,3,7),(2,4,8)],7,5,1,{31},lambda *_:None,lambda:None)
if __name__=='__main__':unittest.main()
