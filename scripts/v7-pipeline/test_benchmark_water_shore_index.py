import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmark_water_shore_index import run,point_fingerprint
import benchmark_water_shore_index as benchmark
from test_verified_water_inputs import encode


class GlobalShoreQATests(unittest.TestCase):
    def fixture(self,root):
        physical=[[17,17,1,1,17,17,17,1],[17,1,1,1,1,17,1,1],[1,1,17,17,1,1,1,1]]
        land=[[18 if value==17 else 0 for value in row] for row in physical]
        specifications={}
        for role,grid in (('physical',physical),('land',land)):
            for kind,data in zip(('rows','runs'),encode(grid)):
                path=root/(role+'_'+kind);path.write_bytes(data)
                specifications[role+'_'+kind]={'path':path.name,'sha256':hashlib.sha256(data).hexdigest()}
        request=root/'request.json';request.write_text(json.dumps({'schema':'worldatlas-shore-index-global-qa-request-v1',
            'grid':{'width':8,'height':3},'inputs':specifications,'scope':'synthetic fixture only'}))
        return request

    def test_all_points_both_orders_with_explicit_preparation_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request=self.fixture(root)
            for first in (False,True):
                result=run(request,root/str(first),rows_per_block=2,candidate_first=first)
                self.assertEqual(result['status'],'every-global-coastal-point-and-category-byte-identical')
                self.assertGreater(result['coastal_cells'],0)
                self.assertEqual(len(result['blocks']),2)
                self.assertEqual(result['request_scope'],'synthetic fixture only')
                self.assertGreater(result['generation_preparation_seconds'],0)
                self.assertGreater(result['generation_exit_verification_seconds'],0)

    def test_coordinate_change_is_not_hidden_by_equal_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request=self.fixture(root)
            original=benchmark.coastal_shore_index.CoastalShoreIndex.centers_for_crop
            def wrong(self,*args,**kwargs):
                result=original(self,*args,**kwargs);result['lon']=result['lon']+.001;return result
            with patch.object(benchmark.coastal_shore_index.CoastalShoreIndex,'centers_for_crop',wrong):
                with self.assertRaisesRegex(ValueError,'point bytes differ'):run(request,root/'out')
            self.assertFalse((root/'out/report.json').exists())

    def test_empty_query_encoding_has_no_shape_or_cast_error(self):
        result=point_fingerprint(None)
        self.assertEqual(result['cells'],0)
        self.assertEqual(set(result['sha256'].values()),{hashlib.sha256(b'').hexdigest()})


if __name__=='__main__':unittest.main()
