import unittest
from verify_interval_lineage import verify

class IntervalTest(unittest.TestCase):
    def test_exact_interval_and_reject_mutation(self):
        a={'features':[{'properties':{'cut_id':'x'},'geometry':{'type':'LineString','coordinates':[[1,2],[3,4],[5,6],[7,8]]}}]}
        self.assertEqual(verify(a,[[3,4],[5,6]],'x')['start_positions_1based'],[2])
        self.assertFalse(verify(a,[[3,4],[5,7]],'x')['exact_match'])

if __name__=='__main__':unittest.main()
