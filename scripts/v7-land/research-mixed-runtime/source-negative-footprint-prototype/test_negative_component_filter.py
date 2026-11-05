import unittest
from negative_component_filter import exclude_footprint

class NegativeFootprintTest(unittest.TestCase):
    def test_excludes_entire_intersecting_roots_and_sorts(self):
        result = exclude_footprint([9, 4, 2], [9, 11])
        self.assertEqual(result['selected_roots'], [2, 4])
        self.assertEqual(result['excluded_roots'], [9])
        self.assertEqual(result['negative_roots_outside_positive'], 1)
    def test_empty_input(self):
        self.assertEqual(exclude_footprint([], [])['selected_roots'], [])
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError): exclude_footprint([1, 1], [])
        with self.assertRaises(ValueError): exclude_footprint([], [3, 3])
    def test_invalid_root_rejected(self):
        for value in [True, -1, 0xffffffff, '2', None, 1.0]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError): exclude_footprint([value], [])
    def test_invalid_collection_rejected(self):
        for value in [None, {'root': 1}, '123']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError): exclude_footprint(value, [])

if __name__ == '__main__': unittest.main()
