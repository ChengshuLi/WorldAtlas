import copy
import hashlib
import json
import unittest
from pathlib import Path

import resolve
from test_named_list1_integration import NamedList1Integration
from test_resolve import put


class LineIntegration(NamedList1Integration):
    def line_fixture(self):
        doc = self.fixture()
        a = doc['affiliations'][0]
        a['method'] = 'geonames_zip_line_side_component_v1'
        geometry = {'type': 'MultiLineString', 'coordinates': [[[-110, 24], [-110, 21]]]}
        digest = hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        line = {'line_id': 'fictional-line', 'source_id': 'p', 'source_version': '1',
                'geometry': geometry, 'geometry_sha256': digest, 'status': 'research'}
        # The fixture source version is not assumed to be a particular string.
        line['source_version'] = doc['sources'][0]['version']
        doc['line_observations'] = [line]
        doc['list1_entry_evidence_sources'] = [{'entry_id': 'entry', 'source_id': 'p',
                                                'source_version': line['source_version']}]
        a['evidence']['selector'].update({'line_id': line['line_id'], 'line_geometry_sha256': digest,
                                          'expected_side': 'west', 'minimum_separation_m': 10000})
        self.req['line_side_sha256'] = resolve.digest(Path(resolve.__file__).with_name('line_side.py'))
        self.req['snapshot'] = put(self.p/'combined.json', doc)
        return doc

    def test_line_end_to_end(self):
        self.line_fixture()
        result = resolve.resolve(self.req)
        self.assertEqual(result['claims'][0]['identity_check']['line_check']['side'], 'west')
        self.assertEqual(result['line_side_sha256'], self.req['line_side_sha256'])

    def test_wrong_side_fails(self):
        doc = self.line_fixture()
        doc['affiliations'][0]['evidence']['selector']['expected_side'] = 'east'
        self.req['snapshot'] = put(self.p/'combined.json', doc)
        with self.assertRaisesRegex(ValueError, 'unexpected side'):
            resolve.resolve(self.req)

    def test_line_hash_tamper_fails(self):
        doc = self.line_fixture()
        doc['line_observations'][0]['geometry']['coordinates'][0][0][0] += 1
        self.req['snapshot'] = put(self.p/'combined.json', doc)
        with self.assertRaisesRegex(ValueError, 'line geometry hash'):
            resolve.resolve(self.req)
    def test_line_code_tamper_fails(self):
        self.line_fixture(); self.req['line_side_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'line side code pin'):
            resolve.resolve(self.req)

    def test_unlinked_source_fails(self):
        doc = self.line_fixture(); doc['list1_entry_evidence_sources'] = []
        self.req['snapshot'] = put(self.p/'combined.json', doc)
        with self.assertRaisesRegex(ValueError, 'line source or entry evidence'):
            resolve.resolve(self.req)


if __name__ == '__main__':
    unittest.main()
