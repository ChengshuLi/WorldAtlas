import unittest
import ridge_candidates as module


class PeakTest(unittest.TestCase):
    def test_prominence_and_invalid_window(self):
        data = [{'offset_m': i, 'height_m': v, 'status': 'valid_mask_0'}
                for i, v in enumerate([0, 12, 1, 2, 18, 0])]
        peaks = module.profile_peaks(data, 10, 1)
        self.assertEqual([p['offset_m'] for p in peaks], [1, 4])
        data[0]['status'] = 'excluded_mask_or_nodata'
        self.assertEqual(module.profile_peaks(data, 10, 1), [])


if __name__ == '__main__':
    unittest.main()
