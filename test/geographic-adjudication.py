"""Synthetic differential decisions against immutable retained native water.

The envelope here is a test carrier, NOT GitHub authority or factual approval.
Separate adapter/workflow/merge controls must verify those trust boundaries.
"""
import base64
import copy
import gzip
import hashlib
import importlib.util
import json
import pathlib
import sys
import unittest

from shapely.geometry import box, mapping, shape

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import geographic_adjudication as water
from evidence.immutable import canonical_json

spec = importlib.util.spec_from_file_location('detector', ROOT / 'scripts/check-geographic-regression.py')
detector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(detector)
SOURCE = 'coordination/engineering/coverage-gaps-907-20261005-local01/sources/natural-earth-lakes.geojson.gz'
DOSSIER = 'coordination/engineering/synthetic-water-control/dossier.json'
NATIVE = 1159112991


class Adjudication(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT / SOURCE).read_bytes()
        original = gzip.decompress(self.raw)
        self.assertEqual(hashlib.sha256(original).hexdigest(),
                         '2d036f53dedec578001c5c30c2959ee7d4eebc1306900fa4367c49929ec8f2d9')
        native = [f for f in json.loads(original)['features'] if f['properties'].get('ne_id') == NATIVE]
        self.assertEqual(len(native), 1)
        self.native = native[0]
        self.lake = shape(self.native['geometry'])
        self.ref = {'source_id': 'retained-ne-native-lakes', 'path': SOURCE,
                    'sha256': hashlib.sha256(self.raw).hexdigest(),
                    'decoded_sha256': hashlib.sha256(original).hexdigest(),
                    'native_identity': {'property': 'ne_id', 'value': NATIVE},
                    'native_geometry_sha256': water.digest(self.native['geometry']),
                    'native_role': {'property': 'featurecla', 'value': 'Lake'}}
        self.loss = box(-87.5, 47.7, -87.49, 47.71)

    def proposal(self, losses=None):
        losses = losses or [self.loss]
        extent = box(-87.6, 47.6, -87.3, 47.85)
        if not all(extent.contains(loss) for loss in losses):
            west, south, east, north = losses[0].bounds
            extent = box(west-.05, south-.05, east+.05, north+.05)
        before = {'synthetic:a': {'type': 'Feature', 'geometry': mapping(extent)}}
        after = copy.deepcopy(before)
        after['synthetic:a']['geometry']['coordinates'] = [mapping(extent)['coordinates'][0],
                                                         *[mapping(loss)['coordinates'][0] for loss in losses]]
        return self.differential(before, after)

    def differential(self, before, after):
        result = detector.compare(before, after)
        self.assertEqual(result['status'], 'regressions-found')
        def inventory(features):
            raw = canonical_json(features)
            oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            return [{'path': 'data/geography/synthetic.json', 'mode': '100644', 'git_blob_oid': oid}]
        return {'status': result['status'], 'regressions': result['regressions'],
                'trusted_code_inventory_sha256': 'a'*64,
                'baseline_input_inventory': inventory(before), 'candidate_input_inventory': inventory(after),
                'differential_report': result}

    def dossier(self, report, selection=None):
        selected = selection if selection is not None else report['differential_report']['findings']['features']
        return {'version': 1, 'method_id': water.VERSION, 'target_context': water.TARGET,
                'context': water.context(report), 'findings': [{'sha256': water.digest(f), 'feature': f} for f in selected],
                'source_refs': [self.ref], 'rationale': 'Synthetic interior water-loss proposal; no real jurisdiction or live correction.'}

    def carrier(self, dossier):
        raw = canonical_json(dossier)
        decision = {'dossier_path': DOSSIER, 'dossier_sha256': hashlib.sha256(raw).hexdigest(),
                    'target_context': water.TARGET, 'target_water': 'supported',
                    'physical_provenance': 'accepted', 'temporal_suitability': 'accepted',
                    'resolution_suitability': 'accepted', 'target_uncertainty': 'resolved-for-this-target',
                    'source_limits': ['Coarse modern reference; synthetic target only, no fine/dated shoreline certificate.'],
                    'source_refs_sha256': water.digest(dossier['source_refs']),
                    'finding_sha256s': sorted(row['sha256'] for row in dossier['findings'])}
        envelope = {'version': 1, 'method_id': water.VERSION, 'status': 'reviewed', 'authority_sha256': 'b'*64,
                    'review': {'scope': 'Synthetic authority carrier only; not an actual source review'},
                    'dossiers': [{'path': DOSSIER, 'sha256': decision['dossier_sha256'],
                                  'bytes_base64': base64.b64encode(raw).decode(), 'decision': decision}]}
        files = {SOURCE: self.raw, DOSSIER: raw}
        return envelope, files

    def test_actual_detector_loss_inside_retained_native_water(self):
        report = self.proposal()
        self.assertTrue(self.lake.covers(self.loss))
        envelope, files = self.carrier(self.dossier(report))
        result = water.adjudicate(report, envelope, files.__getitem__)
        self.assertEqual(result['status'], 'all-findings-supported-and-reviewed')
        self.assertEqual(result['unresolved_findings'], 0)

    def test_centroid_water_cannot_approve_partly_unsupported_loss(self):
        loss = box(-84.508983, 46.463515, -84.488983, 46.483515)
        self.assertTrue(self.lake.contains(loss.centroid))
        self.assertFalse(self.lake.covers(loss))
        report = self.proposal([loss])
        envelope, files = self.carrier(self.dossier(report))
        with self.assertRaisesRegex(ValueError, 'Whole proposed loss') as caught:
            water.adjudicate(report, envelope, files.__getitem__)
        self.assertFalse(shape(caught.exception.unsupported_geometry).is_empty)

    def test_additional_combined_finding_remains_blocked(self):
        report = self.proposal([self.loss, box(-87.45, 47.7, -87.44, 47.71)])
        self.assertEqual(report['regressions'], 2)
        envelope, files = self.carrier(self.dossier(report, report['differential_report']['findings']['features'][:1]))
        with self.assertRaisesRegex(ValueError, 'additional combined'):
            water.adjudicate(report, envelope, files.__getitem__)

    def test_unknown_target_suitability_remains_blocked(self):
        report = self.proposal(); envelope, files = self.carrier(self.dossier(report))
        envelope['dossiers'][0]['decision']['resolution_suitability'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'Unknown or rejected'):
            water.adjudicate(report, envelope, files.__getitem__)

    def test_source_bytes_cannot_be_replaced_under_reviewed_hash(self):
        report = self.proposal(); envelope, files = self.carrier(self.dossier(report))
        files[SOURCE] += b'changed'
        with self.assertRaisesRegex(ValueError, 'source bytes changed'):
            water.adjudicate(report, envelope, files.__getitem__)

    def test_native_role_cannot_be_relabelled(self):
        report = self.proposal(); dossier = self.dossier(report)
        dossier['source_refs'][0]['native_role']['value'] = 'Country outline'
        envelope, files = self.carrier(dossier)
        with self.assertRaisesRegex(ValueError, 'physical role differs'):
            water.adjudicate(report, envelope, files.__getitem__)

    def test_native_geometry_cannot_be_replaced_under_original_source(self):
        report = self.proposal(); dossier = self.dossier(report)
        dossier['source_refs'][0]['native_geometry_sha256'] = '0'*64
        envelope, files = self.carrier(dossier)
        with self.assertRaisesRegex(ValueError, 'native water geometry differs'):
            water.adjudicate(report, envelope, files.__getitem__)

    def test_changed_consumed_neighbor_input_requires_new_review(self):
        report = self.proposal(); envelope, files = self.carrier(self.dossier(report))
        report['candidate_input_inventory'][0]['git_blob_oid'] = 'c'*40
        with self.assertRaisesRegex(ValueError, 'Consumed geography'):
            water.adjudicate(report, envelope, files.__getitem__)

    def test_changed_trusted_method_requires_new_review(self):
        report = self.proposal(); envelope, files = self.carrier(self.dossier(report))
        report['trusted_code_inventory_sha256'] = 'c'*64
        with self.assertRaisesRegex(ValueError, 'Consumed geography'):
            water.adjudicate(report, envelope, files.__getitem__)

    def test_duplicate_exact_finding_is_not_a_blanket_decision(self):
        report = self.proposal(); dossier = self.dossier(report)
        dossier['findings'].append(copy.deepcopy(dossier['findings'][0]))
        envelope, files = self.carrier(dossier)
        with self.assertRaisesRegex(ValueError, 'Duplicate exact'):
            water.adjudicate(report, envelope, files.__getitem__)

    def test_author_approval_field_is_not_supported(self):
        report = self.proposal(); dossier = self.dossier(report); dossier['approved'] = True
        envelope, files = self.carrier(dossier)
        with self.assertRaisesRegex(ValueError, 'author-approved'):
            water.adjudicate(report, envelope, files.__getitem__)

    def test_changed_dossier_is_not_covered_by_previous_review(self):
        report = self.proposal(); envelope, files = self.carrier(self.dossier(report))
        files[DOSSIER] += b'\n'
        with self.assertRaisesRegex(ValueError, 'dossier differs'):
            water.adjudicate(report, envelope, files.__getitem__)

    def test_invalid_native_water_cannot_be_repaired_into_approval(self):
        report = self.proposal(); dossier = self.dossier(report)
        invalid = copy.deepcopy(self.native)
        invalid['geometry'] = {'type': 'Polygon', 'coordinates': [[
            [-87.6,47.6],[-87.3,47.85],[-87.6,47.85],[-87.3,47.6],[-87.6,47.6]]]}
        original = canonical_json({'type': 'FeatureCollection', 'features': [invalid]})
        self.raw = gzip.compress(original, mtime=0)
        ref = dossier['source_refs'][0]
        ref['sha256'] = hashlib.sha256(self.raw).hexdigest()
        ref['decoded_sha256'] = hashlib.sha256(original).hexdigest()
        ref['native_geometry_sha256'] = water.digest(invalid['geometry'])
        envelope, files = self.carrier(dossier)
        with self.assertRaisesRegex(ValueError, 'Invalid|invalid'):
            water.adjudicate(report, envelope, files.__getitem__)

    def test_actual_new_overlap_inside_water_is_never_waived(self):
        before = {'synthetic:a': {'type':'Feature','geometry':mapping(box(-87.6,47.6,-87.45,47.85))},
                  'synthetic:b': {'type':'Feature','geometry':mapping(box(-87.45,47.6,-87.3,47.85))}}
        after = copy.deepcopy(before)
        after['synthetic:a']['geometry'] = mapping(box(-87.6,47.6,-87.44,47.85))
        report = self.differential(before, after)
        features = report['differential_report']['findings']['features']
        self.assertEqual([f['properties']['kind'] for f in features], ['new-pair-overlap'])
        self.assertTrue(self.lake.covers(shape(features[0]['geometry'])))
        envelope, files = self.carrier(self.dossier(report))
        with self.assertRaisesRegex(ValueError, 'overlap.*cannot'):
            water.adjudicate(report, envelope, files.__getitem__)


def receipt_run(directory):
    class Result(unittest.TextTestResult):
        def addSuccess(self, test):
            super().addSuccess(test)
            self.successes = getattr(self, 'successes', []) + [test._testMethodName]
    result = unittest.TextTestRunner(resultclass=Result, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Adjudication))
    if not result.wasSuccessful() or result.skipped:
        return 1
    directory = pathlib.Path(directory)
    if any(p.is_symlink() for p in [directory, *directory.absolute().parents]):
        raise ValueError('Symlink receipt destination')
    directory.mkdir()
    paths = ['scripts/geographic_adjudication.py', 'scripts/check-geographic-regression.py',
             'scripts/evidence/immutable.py', 'scripts/evidence/geometry.py',
             'scripts/ellipsoidal_area.py', 'test/geographic-adjudication.py', SOURCE]
    files = [{'path': name, 'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest()} for name in paths]
    sample = Adjudication()
    sample.setUp()
    negative = box(-84.508983,46.463515,-84.488983,46.483515)
    if not sample.lake.covers(sample.loss) or not sample.lake.contains(negative.centroid) or sample.lake.covers(negative):
        raise ValueError('Native physical source controls changed')
    summary = {'method_id': 'scoped-water-adjudication', 'outcome': 'passed', 'tests': result.testsRun,
               'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
               'controls': sorted(result.successes), 'executed_files': files,
               'native_source_binding': sample.ref,
               'limits': ['Synthetic candidate losses against an original retained coarse current lake. No real territory edit, source suitability approval, hosted authority or publication.']}
    (directory / 'results.json').write_bytes(canonical_json(summary))
    for kind in ['positive-control', 'negative-control']:
        selected = [name for name in summary['controls'] if (name == 'test_actual_detector_loss_inside_retained_native_water') == (kind == 'positive-control')]
        diagnostic = {'whole_loss': mapping(sample.loss), 'whole_shape_supported': True} if kind == 'positive-control' else {
            'whole_loss': mapping(negative), 'centroid_inside_water': True, 'whole_shape_supported': False,
            'unsupported_geometry': mapping(negative.difference(sample.lake))}
        (directory / (kind + '.json')).write_bytes(canonical_json({**summary, 'kind': kind,
                                                               'controls': selected, 'diagnostic': diagnostic}))
    return 0


if __name__ == '__main__':
    if '--receipts' in sys.argv:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--receipts', required=True)
        raise SystemExit(receipt_run(parser.parse_args().receipts))
    unittest.main()
