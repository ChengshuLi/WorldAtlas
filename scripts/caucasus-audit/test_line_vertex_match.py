import unittest
from line_vertex_match import geometry_hash,line_coordinates,match_runs

class VertexMatchTests(unittest.TestCase):
    def test_forward_and_reverse_runs(self):
        source=[[0,0],[1,0],[2,0],[3,0]]
        self.assertEqual(match_runs([[9,9],[1,0],[2,0],[3,0]],source)['runs'][0],
                         {'selected_start':1,'source_start':1,'length':3,'source_direction':1})
        self.assertEqual(match_runs([[3,0],[2,0],[1,0]],source)['runs'][0]['source_direction'],-1)
    def test_duplicates_are_counted_as_ambiguous(self):
        result=match_runs([[0,0],[1,0]],[[0,0],[1,0],[0,0]])
        self.assertEqual(result['matched_selected_vertices'],2)
        self.assertEqual(result['ambiguous_selected_vertices'],1)
    def test_invalid_coordinates_fail_closed(self):
        for geometry in ({'type':'Point','coordinates':[0,0]},
                         {'type':'LineString','coordinates':[[0,0],[float('nan'),0]]},
                         {'type':'LineString','coordinates':[[0,0],[True,0]]}):
            with self.assertRaises(ValueError):line_coordinates(geometry)
    def test_integer_and_binary64_coordinates_hash_identically(self):
        first={'type':'LineString','coordinates':[[0,1],[2,3]]}
        second={'type':'LineString','coordinates':[[0.0,1.0],[2.0,3.0]]}
        self.assertEqual(geometry_hash(first),geometry_hash(second))

if __name__=='__main__':unittest.main()
