import gzip
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

from execution_state import pin
from manage_release import build_bundle, verify_object, version


class ColorCatalog:
    def execute(self, query, params):
        assert 'FROM atlas.geographic_entity_ids' in query
        assert 'color_rgb IS NOT NULL' in query
        assert params == ([42],)
        return [(42, '#E9B44C')]


class BundleTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        root = Path(work.name).resolve()
        self.run = root / 'run'
        self.viewer = root / 'viewer'
        self.output = root / 'bundle'
        for directory in (self.run / 'final', self.viewer, self.output):
            directory.mkdir(parents=True)
        request = root / 'config.json'
        self.snapshot = root / 'land.json'
        self.snapshot.write_text(json.dumps({
            'entities': [{'id': 42, 'name': 'Africa'}],
            'category_bindings': [
                {'code': 1, 'entity_id': 42, 'physical_class': 'water'},
                {'code': 17, 'entity_id': 42, 'physical_class': 'land'},
            ],
        }))
        snapshot_pin = pin(self.snapshot)
        request.write_text(json.dumps({
            'sources': {
                'land_config': {'json': {'grid': {'width': 2, 'height': 1, 'step': 180}}},
                'land_snapshot': snapshot_pin,
            },
        }))
        identity = self.run / 'run-identity.json'
        identity.write_text(json.dumps({'request': pin(request), 'source_pins': [snapshot_pin]}))
        (self.viewer / 'index.html').write_text('<html><head></head><body></body></html>')
        (self.viewer / 'config.json').write_text('{"water_rgb":[84,141,183]}')
        self.rows = struct.pack('<2I', 0, 2)
        self.runs = struct.pack('<4I', 1, 1, 2, 17)
        final = self.run / 'final'
        (final / 'rows.u32le').write_bytes(self.rows)
        (final / 'runs.u32le').write_bytes(self.runs)
        (final / 'report.json').write_text('{"counts":{"1":1,"17":1},"run_count":2}')
        self.report = self.run / 'report.json'
        self.report.write_text(json.dumps({
            'schema': 'worldatlas-end-to-end-report-v1', 'status': 'complete',
            'original_run_identity': pin(identity), 'request': pin(request), 'comparison': None,
            'final': {name: pin(final / filename) for name, filename in
                      [('rows', 'rows.u32le'), ('runs', 'runs.u32le'), ('report', 'report.json')]},
            'stages': {name: {'outputs_complete': True} for name in
                       ('physical', 'mainland', 'water', 'verification')},
        }))

    def test_bundle_uses_exact_output_files_and_one_asset_base(self):
        manifest = build_bundle('v9.0-rc.1', self.run, self.viewer, self.output, ColorCatalog())
        self.assertIn('<base href="/review/releases/v9.0-rc.1/">',
                      (self.output / 'index.html').read_text())
        self.assertEqual(gzip.decompress((self.output / 'rows.u32le.gz').read_bytes()), self.rows)
        self.assertEqual(gzip.decompress((self.output / 'runs.u32le.gz').read_bytes()), self.runs)
        config = json.loads((self.output / 'config.json').read_text())
        self.assertEqual(config['local_grid']['rows'], 'rows.u32le.gz')
        self.assertEqual(config['map_version'], 'v9.0')
        self.assertEqual(config['water_rgb'], [84, 141, 183])
        self.assertNotIn('counts', config)
        self.assertEqual(config['legend'], 'legend/continents.json')
        self.assertEqual(config['categories'], [
            {'id': 1, 'entity_id': 42, 'physical_class': 'water'},
            {'id': 17, 'entity_id': 42, 'physical_class': 'land'},
        ])
        self.assertEqual(json.loads((self.output / config['legend']).read_bytes()), [
            {'id': 42, 'name': 'Africa', 'color': [233, 180, 76], 'count': 2},
        ])
        self.assertIn(config['legend'], manifest['objects'])
        self.assertEqual(config['combined_sha256'], hashlib.sha256(self.rows + self.runs).hexdigest())
        self.assertEqual(manifest['decoded_sha256']['runs'], hashlib.sha256(self.runs).hexdigest())

    def test_changed_map_output_cannot_be_staged(self):
        (self.run / 'final/runs.u32le').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'checkpoint/input hash mismatch'):
            build_bundle('v9.0-rc.1', self.run, self.viewer, self.output, ColorCatalog())

    def test_source_cache_can_move_while_preserving_its_original_link(self):
        shared = self.snapshot.parent / 'shared'
        shared.mkdir()
        moved = shared / self.snapshot.name
        self.snapshot.rename(moved)
        self.snapshot.symlink_to(moved)
        build_bundle('v9.0-rc.1', self.run, self.viewer, self.output, ColorCatalog())

        moved.write_text('changed source')
        with self.assertRaisesRegex(ValueError, 'checkpoint/input hash mismatch'):
            build_bundle('v9.0-rc.2', self.run, self.viewer, self.output, ColorCatalog())

    def test_missing_land_color_blocks_staging(self):
        class EmptyCatalog:
            def execute(self, query, params):
                return []

        with self.assertRaisesRegex(ValueError, 'missing for land entities'):
            build_bundle('v9.0-rc.1', self.run, self.viewer, self.output, EmptyCatalog())

    def test_candidate_name_identifies_the_release(self):
        self.assertEqual(version('v9.0-rc.2'), 'v9.0')
        with self.assertRaises(ValueError):
            version('../v9.0')


class R2VerificationTests(unittest.TestCase):
    def test_matching_size_alone_cannot_pass_release_verification(self):
        class Storage:
            def get_object(self, **options):
                return {'ContentLength': 4, 'ContentType': 'text/html', 'Body': io.BytesIO(b'evil')}

        with self.assertRaisesRegex(ValueError, 'published bytes differ'):
            verify_object(Storage(), 'test', 'index.html',
                          {'size_bytes': 4, 'content_type': 'text/html',
                           'sha256': hashlib.sha256(b'good').hexdigest()})
