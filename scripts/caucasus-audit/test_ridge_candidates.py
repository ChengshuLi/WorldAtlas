import unittest
import ridge_candidates as module
import sample_line
from geodesic_tools import GEOD
from unittest.mock import patch


class PeakTest(unittest.TestCase):
    def test_prominence_and_invalid_window(self):
        data = [{'offset_m': i, 'height_m': v, 'status': 'valid_mask_0'}
                for i, v in enumerate([0, 12, 1, 2, 18, 0])]
        peaks = module.profile_peaks(data, 10, 1)
        self.assertEqual([p['offset_m'] for p in peaks], [1, 4])
        data[0]['status'] = 'excluded_mask_or_nodata'
        self.assertEqual(module.profile_peaks(data, 10, 1), [])

    def test_ridge_offsets_and_old_sample_gate(self):
        line=[[1,1],[1.01,1]];doc=sample_line.generate(line,0,1,7,500,32631)
        def dummy(tiles,lon,lat,require_stack=False):
            return {'status':'valid_mask_0','longitude':lon,'latitude':lat,'height_m':100}
        with patch.object(module,'sample_point',side_effect=dummy):
            result=module.profiles(doc,line,7,0,1,0,500,32631,{},100,25,10,25)
        self.assertGreater(len(result),0)
        center=result[0]['center'];sample=result[0]['samples'][0]
        self.assertAlmostEqual(GEOD.inv(*center,sample['longitude'],sample['latitude'])[2],100,delta=1e-5)
        with self.assertRaisesRegex(ValueError,'regenerate'):
            module.profiles({'type':'FeatureCollection','features':doc['features']},line,7,0,1,0,500,32631,{},100,25,10,25)


if __name__ == '__main__':
    unittest.main()
