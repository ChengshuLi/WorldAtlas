import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from build_seavox_basin import contiguous_spans, validate_source, grid_bounds, selected_basin


class BasinTest(unittest.TestCase):
    def test_selection_uses_stable_entity_bindings(self):
        data={'category_bindings':[{'entity_id':101,'code':6,'physical_class':'water'}],
              'basins':[{'id':'b1','source_id':'s1','source_version':'v1','source_feature_id':'123',
                         'geometry_sha256':'a'*64,'assignment_method':'single_continent_named_basin','participant_entity_ids':[101]}],
              'sources':[{'source_id':'s1','version':'v1','sha256':'b'*64}]}
        self.assertEqual(selected_basin(data,'b1')[2],6)
        with self.assertRaisesRegex(ValueError,'exactly one selected'): selected_basin(data,'missing')
        data['category_bindings'].append({'entity_id':101,'code':5,'physical_class':'water'})
        with self.assertRaisesRegex(ValueError,'unique V7 water binding'): selected_basin(data,'b1')

    def test_span_extraction_and_geometry_bounds(self):
        self.assertEqual(contiguous_spans(np.array([False,True,True,False,True]),10),[(11,13),(14,15)])
        self.assertEqual(grid_bounds({'geometry':{'coordinates':[[[0,0],[45,45]]]}}),(65536,81920,16384,32768))

    def test_pinned_feature_identity_and_geometry(self):
        geom={'type':'Polygon','coordinates':[[[1,1],[2,1],[1,2],[1,1]]]}
        obj={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'mrgid_sr':'123'},'geometry':geom}]}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'source.json';path.write_text(json.dumps(obj));fsha=hashlib.sha256(path.read_bytes()).hexdigest()
            gsha=hashlib.sha256(json.dumps(geom,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
            self.assertEqual(validate_source(path,fsha,gsha,'123')['properties']['mrgid_sr'],'123')
            with self.assertRaisesRegex(ValueError,'source file hash'): validate_source(path,'0'*64,gsha,'123')
            with self.assertRaisesRegex(ValueError,'geometry hash'): validate_source(path,fsha,'0'*64,'123')
            with self.assertRaisesRegex(ValueError,'selected SeaVoX feature'): validate_source(path,fsha,gsha,'999')


if __name__ == '__main__': unittest.main()
