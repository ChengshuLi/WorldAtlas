import copy
import hashlib
import importlib.util
import json
import unittest
import tempfile
from pathlib import Path

from point_claim_validator import claims_for, load_line_side
from test_named_list1_claim import NamedList1Claims

PATH = Path(__file__).resolve().parent.parent/'point-integration/point-component-prototype/line_side.py'
spec = importlib.util.spec_from_file_location('synthetic_line_side', PATH)
line_side = importlib.util.module_from_spec(spec); spec.loader.exec_module(line_side)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class LineClaims(NamedList1Claims):
    def setUp(self):
        super().setUp()
        method = 'geonames_zip_line_side_component_v1'
        self.snap['affiliations'][0]['method'] = self.claim['method'] = method
        geom = {'type': 'Point', 'coordinates': [9, 3]}
        self.feature['geometry_sha256'] = self.claim['geonames_extraction']['geometry_sha256'] = digest(geom)
        self.claim['geonames_extraction']['geometry'] = geom
        linegeom = {'type':'MultiLineString','coordinates':[[[10,4],[10,2]]]}
        line = {'line_id':'fictional-line','source_id':'x','source_version':'v',
                'geometry':linegeom,'geometry_sha256':digest(linegeom),'status':'research'}
        self.snap['line_observations'] = [line]
        self.snap['list1_entry_evidence_sources'] = [{'entry_id':'entry','source_id':'x','source_version':'v'}]
        self.sel.update({'line_id':'fictional-line','line_geometry_sha256':digest(linegeom),
                         'expected_side':'west','minimum_separation_m':10000})
        self.claim['identity_check']['line_check'] = line_side.check(line, geom['coordinates'], 'west', 10000)
        self.res['line_side_sha256'] = hashlib.sha256(PATH.read_bytes()).hexdigest()

    def test_line_claim_and_tampering(self):
        self.assertIn(10, claims_for(self.comp,self.snap,self.res))
        for field in ('line_check','geometry','code'):
            bad = copy.deepcopy(self.res)
            if field == 'line_check': bad['claims'][0]['identity_check']['line_check']['side'] = 'east'
            elif field == 'geometry': bad['claims'][0]['geonames_extraction']['geometry']['coordinates'][0] = 11
            else: bad['line_side_sha256'] = '0'*64
            with self.subTest(field=field), self.assertRaises(ValueError):
                claims_for(self.comp,self.snap,bad)

    def test_evidence_link_tampering(self):
        bad = copy.deepcopy(self.snap); bad['list1_entry_evidence_sources'] = []
        with self.assertRaises(ValueError): claims_for(self.comp,bad,self.res)

    def test_oversized_code_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'oversized.py'; path.write_bytes(b' ' * ((1<<20)+1))
            with self.assertRaisesRegex(ValueError, 'exceeds limit'):
                load_line_side(path, hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == '__main__': unittest.main()
