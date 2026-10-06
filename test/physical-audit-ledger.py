"""Independent negative controls for complete artifact accounting."""
import copy
import importlib.util
import pathlib
import shutil
import subprocess
import json
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.immutable import canonical_json, descriptor, deterministic_gzip
spec = importlib.util.spec_from_file_location('ledger', ROOT / 'scripts/validate-physical-audit-evidence.py')
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)


class LedgerControls(unittest.TestCase):
    def setUp(self):
        self.out = ROOT / '.cache/physical-audit-ledger-controls'
        self.out.mkdir(parents=True, exist_ok=False)
        self.geometry = {'type': 'Polygon', 'coordinates': [[[-179, -59], [-178, -59], [-178, -58], [-179, -58], [-179, -59]]]}
        identity = 'physical-gap:0:0:' + ledger.digest(canonical_json(self.geometry))
        self.feature = {'type': 'Feature', 'id': identity, 'geometry': self.geometry,
                        'properties': {'tile': [-180, -60, -170, -50], 'original_planar_area': 1,
                                       'water_status': 'unverified', 'administrative_assignment': None, 'area_m2': None}}
        decoded = canonical_json({'type': 'FeatureCollection', 'features': [self.feature]})
        encoded = deterministic_gzip(decoded)
        name = self.out / 'candidates.geojson.gz'
        name.write_bytes(encoded)
        output = {**descriptor(str(name.relative_to(ROOT)), encoded),
                  'uncompressed_bytes': len(decoded), 'uncompressed_sha256': ledger.digest(decoded)}
        self.report = {'version': 'worldatlas-physical-land-before-water-v1', 'bounds': ledger.DOMAIN,
                       'tile_degrees': 10, 'status': 'declared-domain-detection-complete', 'tiles': [], 'candidate_fragments': 1, 'residues': 0,
                       'tiles_checked': 540, 'tiles_unchecked': 0, 'outputs': [output], 'residue_outputs': [],
                       'measured_candidate_area_m2': 0, 'measurement_errors': [{'fragment': identity}]}
        for i, bounds in enumerate(ledger.expected_tiles(10)):
            self.report['tiles'].append({'id': i, 'bounds': bounds, 'status': 'checked',
                                         'candidate_fragments': 1 if i == 0 else 0, 'residues': 0})

    def tearDown(self):
        shutil.rmtree(self.out)

    def test_complete_synthetic_domain_retains_unmeasured_shape(self):
        result = ledger.inventory(self.report, True)
        self.assertEqual((result['candidates'], result['measurement_unknowns'], result['tiles_checked']), (1, 1, 540))

    def test_missing_tile_cannot_claim_full_domain(self):
        self.report['tiles'].pop()
        with self.assertRaisesRegex(ValueError, 'domain accounting'):
            ledger.inventory(self.report, True)

    def test_missing_feature_cannot_reuse_reported_counts(self):
        self.report['outputs'] = []
        with self.assertRaisesRegex(ValueError, 'counts disagree'):
            ledger.inventory(self.report, True)

    def test_measurement_unknown_cannot_be_silently_cleared(self):
        self.report['measurement_errors'] = []
        with self.assertRaisesRegex(ValueError, 'uncertainty omitted'):
            ledger.inventory(self.report, True)

    def test_tampered_product_and_missing_code_are_rejected(self):
        self.report['outputs'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'product bytes changed'):
            ledger.inventory(self.report, True)
        with self.assertRaisesRegex(ValueError, 'execution-code closure'):
            ledger.require_code({'aliases': {}}, {'code_inputs': []}, ledger.SCIENCE_CODE)

    def test_source_unknowns_and_water_diagnostics_cannot_be_rehashed_away(self):
        inputs = {'invalid_land': [], 'invalid_locations': [], 'invalid_water': [
            {'id': 'invalid-lake', 'unchecked_bounds': [-180, -60, -170, -50]}],
            'location_count': 1, 'land_source': {}, 'water_source': {},
            'canonical_grid_sha256': 'a' * 64, 'release_index_sha256': 'b' * 64, 'release_ids': []}
        for a, b in [('invalid_land', 'invalid_land'), ('invalid_locations', 'invalid_locations'),
                     ('invalid_water_reference', 'invalid_water'), ('locations', 'location_count'),
                     ('physical_reference', 'land_source'), ('water_reference', 'water_source'),
                     ('canonical_grid_sha256', 'canonical_grid_sha256'),
                     ('release_index_sha256', 'release_index_sha256'), ('release_ids', 'release_ids')]:
            self.report[a] = inputs[b]
        for tile in self.report['tiles']:
            tile['invalid_water_diagnostics'] = ledger.blocked_sources(tile['bounds'], inputs['invalid_water'])
            tile['missing_geometry_sha256'] = 'c' * 64
        ledger.source_accounting(self.report, inputs)
        self.report['tiles'][0]['invalid_water_diagnostics'] = []
        with self.assertRaisesRegex(ValueError, 'invalid-water diagnostic'):
            ledger.source_accounting(self.report, inputs)
        self.report['invalid_water_reference'] = []
        with self.assertRaisesRegex(ValueError, 'source/release diagnostic'):
            ledger.source_accounting(self.report, inputs)
        self.report['status'] = 'partial-unknown-domain'
        with self.assertRaisesRegex(ValueError, 'status contradicts'):
            ledger.inventory(self.report, True)

    def test_rehashed_archived_code_cannot_replace_original_commit(self):
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
        path = 'scripts/evidence/immutable.py'
        raw = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)
        snapshot_path = self.out / 'code.bin'
        snapshot_path.write_bytes(raw)
        row = descriptor(path, raw)
        binding = {'original_commit': commit, 'original': row,
                   'snapshot': descriptor(str(snapshot_path.relative_to(ROOT)), raw)}
        report = {'executed_code_commit': commit, 'code_inputs': [row]}
        snapshot = {'aliases': {commit + ':' + path: binding}}
        ledger.require_code(snapshot, report, {path})
        changed = raw + b'\n# rehashed altered snapshot\n'
        snapshot_path.write_bytes(changed)
        report['code_inputs'] = [descriptor(path, changed)]
        binding['original'] = report['code_inputs'][0]
        binding['snapshot'] = descriptor(str(snapshot_path.relative_to(ROOT)), changed)
        with self.assertRaisesRegex(ValueError, 'Baseline input hash/size mismatch'):
            ledger.require_code(snapshot, report, {path})

    def test_same_issue_upstream_cannot_omit_original_descriptors(self):
        row = descriptor('original.json', b'original')
        envelope = {'entries': [{'original': row, 'encoded': descriptor('payload.gz', b'packed')}]}
        child = {'baseline': {'commit': 'a' * 40, 'files': []}, 'sources': [], 'outputs': []}
        with self.assertRaisesRegex(ValueError, 'complete original file descriptors'):
            ledger.upstream_closure(child, envelope, [None, None, None, {'baseline_commit': 'a' * 40}])

    def test_invented_rehashed_source_keys_are_rejected(self):
        original = {'id': 'original-location', 'input_path': 'original-part.json', 'name': 'Original'}
        rosters = {'land': {}, 'water': {}, 'locations': {original['id']: original}}
        feature = {'properties': {'stage': 'location-clipping', 'source': original}}
        ledger.source_keys(feature, rosters)
        feature['properties']['source'] = {**original, 'id': 'invented'}
        with self.assertRaisesRegex(ValueError, 'source key/metadata'):
            ledger.source_keys(feature, rosters)
        feature = {'properties': {'exact_location_contacts': [{**original, 'input_path': 'invented-part.json'}]}}
        with self.assertRaisesRegex(ValueError, 'source key/metadata'):
            ledger.source_keys(feature, rosters)

    def test_invalid_size_cannot_hang_validator(self):
        for size in [0, -1, float('nan'), float('inf'), True]:
            with self.assertRaisesRegex(ValueError, 'Invalid tile size'):
                ledger.expected_tiles(size)


if __name__ == '__main__':
    unittest.main()
