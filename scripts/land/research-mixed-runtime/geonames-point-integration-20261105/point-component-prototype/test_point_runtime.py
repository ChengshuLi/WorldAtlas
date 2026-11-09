import copy
import hashlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

import geonames_extract
import point_runtime
import resolve
from test_geonames_integration import GeoNamesIntegration
from test_resolve import packed, put


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def geometry(lon, lat):
    value = {'type': 'Point', 'coordinates': [float(lon), float(lat)]}
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def row(record_id, name, country='ZZ', lon='12.5', lat='22.5'):
    return ('\t'.join([record_id, name, name, '', lat, lon, 'T', 'ISL', country,
                       '', '', '', '', '', '0', '', '', 'Pacific/Test', '2020-01-01']) + '\n').encode()


def archive(members):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as source:
        for name, data in members:
            source.writestr(name, data)
    return output.getvalue()


class ExtractBatchTests(unittest.TestCase):
    def setUp(self):
        self.selections = [('1', 'First', 'ZZ', geometry('12.5', '22.5')),
                           ('2', 'Second', 'ZZ', geometry('-12.5', '-22.5'))]
        self.raw = archive([('ZZ.txt', row('1', 'First') + row('9', 'Other')
                             + row('2', 'Second', lon='-12.5', lat='-22.5'))])

    def extract(self, raw=None, selections=None):
        raw = self.raw if raw is None else raw
        return point_runtime.extract_many(raw, sha(raw), self.selections if selections is None else selections,
                                          geonames_extract.extract)

    def test_exact_reviewed_results_with_one_archive_open(self):
        expected = [geonames_extract.extract(self.raw, sha(self.raw), *item) for item in self.selections]
        with patch.object(point_runtime.zipfile, 'ZipFile', wraps=zipfile.ZipFile) as opened:
            self.assertEqual(self.extract(), expected)
            self.assertEqual(opened.call_count, 1)

    def test_two_country_members_and_repeated_selection(self):
        raw = archive([('ZZ.txt', row('1', 'First')), ('AA.txt', row('2', 'Second', 'AA'))])
        selections = [self.selections[0], ('2', 'Second', 'AA', geometry('12.5', '22.5')), self.selections[0]]
        self.assertEqual(self.extract(raw, selections),
                         [geonames_extract.extract(raw, sha(raw), *item) for item in selections])

    def test_selection_iterator_keeps_every_result(self):
        self.assertEqual(self.extract(selections=iter(self.selections)), self.extract())

    def test_original_checker_is_not_mutated(self):
        original = geonames_extract.extract.__globals__['zipfile']
        self.extract()
        self.assertIs(geonames_extract.extract.__globals__['zipfile'], original)

    def test_late_duplicate_is_rejected(self):
        raw = archive([('ZZ.txt', row('1', 'First') + row('9', 'Other') * 30 + row('1', 'First'))])
        with self.assertRaisesRegex(ValueError, 'record not unique'):
            self.extract(raw, [self.selections[0]])

    def test_late_bad_utf8_is_rejected(self):
        raw = archive([('ZZ.txt', row('1', 'First') + b'9\t\xff\n')])
        with self.assertRaisesRegex(ValueError, 'invalid archive'):
            self.extract(raw, [self.selections[0]])

    def test_late_long_line_is_rejected(self):
        raw = archive([('ZZ.txt', row('1', 'First') + b'x' * (1024 * 1024 + 1))])
        with self.assertRaisesRegex(ValueError, 'record too long'):
            self.extract(raw, [self.selections[0]])

    def test_missing_record_and_wrong_geometry_still_use_reviewed_checks(self):
        for selection, error in [(('3', 'Missing', 'ZZ', '0' * 64), 'record not unique'),
                                 (('1', 'First', 'ZZ', '0' * 64), 'geometry hash'),
                                 (('1', 'Wrong', 'ZZ', self.selections[0][3]), 'island identity mismatch')]:
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                self.extract(selections=[selection])

    def test_bad_archive_and_hash_and_selection(self):
        with self.assertRaisesRegex(ValueError, 'invalid archive'):
            self.extract(b'x')
        with self.assertRaisesRegex(ValueError, 'source hash'):
            point_runtime.extract_many(self.raw, '0' * 64, self.selections, geonames_extract.extract)
        with self.assertRaisesRegex(ValueError, 'selection'):
            self.extract(selections=[('0', 'First', 'ZZ', '0' * 64)])


class IdentityBatchTests(unittest.TestCase):
    def setUp(self):
        # All tests use a persistent workspace scratch root selected by TMPDIR.
        import tempfile
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'identity.json'
        self.source.write_text('{"value":42}')
        self.request = {'identity_path': str(self.source), 'identity_sha256': sha(self.source.read_bytes()),
                        'point_geometry': {'type': 'Point', 'coordinates': [1, 2]},
                        'island_identity': 'Island', 'spec': {}}

    def test_single_child_reuses_source_parse_and_preserves_order(self):
        checker = b'''def check(source, point, identity, spec):
    source['calls'] = source.get('calls', 0) + 1
    return {'value': source['value'], 'call': source['calls'], 'point': point}
'''
        requests = [copy.deepcopy(self.request) for _ in range(3)]
        for index, request in enumerate(requests):
            request['point_geometry']['coordinates'][0] = index
        with patch.object(point_runtime.subprocess, 'run', wraps=point_runtime.subprocess.run) as process:
            results = point_runtime.run_identity(checker, requests)
            self.assertEqual(process.call_count, 1)
            self.assertIn('-I', process.call_args.args[0])
            self.assertNotIn('timeout', process.call_args.kwargs)
        self.assertEqual([item['call'] for item in results], [1, 2, 3])
        self.assertEqual([item['point']['coordinates'][0] for item in results], [0, 1, 2])

    def test_per_item_size_does_not_limit_total_batch(self):
        checker = b"def check(source, point, identity, spec): return {'ok':True}"
        request = {**self.request, 'island_identity': 'x' * 40000}
        self.assertEqual(len(point_runtime.run_identity(checker, [request, request, request])), 3)
        with self.assertRaisesRegex(ValueError, 'request too large'):
            point_runtime.run_identity(checker, [{**request, 'island_identity': 'x' * 70000}])

    def test_source_pin_and_end_of_batch_change_detection(self):
        checker = b"def check(source, point, identity, spec): return {'ok':True}"
        with self.assertRaisesRegex(ValueError, 'source pin mismatch'):
            point_runtime.run_identity(checker, [{**self.request, 'identity_sha256': '0' * 64}])
        modifying_checker = ('def check(source, point, identity, spec):\n'
                            '    open(' + repr(str(self.source)) + ", 'w').write('{}')\n"
                            "    return {'ok':True}\n").encode()
        with self.assertRaisesRegex(ValueError, 'source changed during worker run'):
            point_runtime.run_identity(modifying_checker, [self.request])

    def test_same_path_with_conflicting_hash_is_not_accepted_from_cache(self):
        checker = b"def check(source, point, identity, spec): return {'ok':True}"
        with self.assertRaisesRegex(ValueError, 'source pin mismatch'):
            point_runtime.run_identity(checker, [self.request, {**self.request, 'identity_sha256': '0' * 64}])

    def test_later_check_failure_rejects_entire_batch(self):
        checker = b"def check(source, point, identity, spec):\n    if identity == 'Bad': raise ValueError('later failure')\n    return {'ok':True}"
        with self.assertRaisesRegex(ValueError, 'later failure'):
            point_runtime.run_identity(checker, [self.request, {**self.request, 'island_identity': 'Bad'}])


class RuntimeResolverTests(GeoNamesIntegration):
    def fixture(self):
        result = super().fixture()
        path = Path(point_runtime.__file__)
        self.req['runtime'] = {'path': str(path), 'sha256': resolve.digest(path)}
        return result

    def test_runtime_and_reviewed_resolution_are_exact_except_declared_provenance(self):
        self.fixture()
        result = resolve.resolve(self.req)
        request = {key: value for key, value in self.req.items() if key != 'runtime'}
        expected = resolve.resolve(request)
        provenance = result.pop('equivalent_runtime')
        self.assertEqual(result, expected)
        self.assertFalse(provenance['geographic_policy_changed'])
        self.assertEqual(provenance['code'], self.req['runtime'])

    def test_multiple_claims_share_archive_and_identity_process(self):
        snapshot = self.fixture()
        raw = archive([('ZZ.txt', row('123', 'Test place', lon='-112.5')
                        + row('124', 'Second place', lon='-89.5'))])
        pin = put(self.p / 'source.zip', raw)
        self.req['source_files'][0].update(pin)
        for source in snapshot['sources'] + snapshot['source_lineage_assets']:
            if source['source_id'] == 'p':
                source.update(sha256=pin['sha256'], size_bytes=len(raw))
        feature = copy.deepcopy(snapshot['features'][0])
        feature.update(feature_id='second-feature', source_feature_id='124', geometry_sha256=geometry('-89.5', '22.5'))
        snapshot['features'].append(feature)
        affiliation = copy.deepcopy(snapshot['affiliations'][0])
        affiliation.update(affiliation_id='b', feature_id='second-feature')
        affiliation['evidence']['selector']['point_name'] = 'Second place'
        snapshot['affiliations'].append(affiliation)
        reference = copy.deepcopy(snapshot['affiliation_feature_refs'][0])
        reference['affiliation_id'] = 'b'
        snapshot['affiliation_feature_refs'].append(reference)
        self.req['snapshot'] = put(self.p / 'combined.json', snapshot)
        self.req['component_rows'] = put(self.p / 'cr', packed('<I', [(0,), (2,), (4,), (6,), (8,)]))
        self.req['component_runs'] = put(self.p / 'cs', packed('<III', [(1, 2, 7), (2, 4, 8)] * 4))
        for key in ('component_rows', 'component_runs'):
            self.manifest['pins'][key] = self.req[key]
        self.req['component_manifest'] = put(self.p / 'manifest', self.manifest)
        with patch.object(point_runtime.subprocess, 'run', wraps=point_runtime.subprocess.run) as process:
            result = resolve.resolve(self.req)
            self.assertEqual(process.call_count, 1)
        expected = resolve.resolve({key: value for key, value in self.req.items() if key != 'runtime'})
        result.pop('equivalent_runtime')
        self.assertEqual(result, expected)
        self.assertEqual([claim['component_id'] for claim in result['claims']], [7, 8])

    def test_runtime_pin_and_canonical_path_are_required(self):
        self.fixture()
        self.req['runtime']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'file hash mismatch'):
            resolve.resolve(self.req)
        path = Path(point_runtime.__file__)
        self.req['runtime'] = put(self.p / 'alternate.py', path.read_bytes())
        with self.assertRaisesRegex(ValueError, 'unsupported point runtime'):
            resolve.resolve(self.req)


if __name__ == '__main__':
    unittest.main()
