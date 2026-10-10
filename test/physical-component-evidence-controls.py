"""Compact semantic controls and retained whole-world custody fixtures.

Semantic cases call the actual validator predicates with small original records.
The separate full-world positive and custody tests retain complete-byte coverage.
"""
import gzip
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('component_validator', ROOT / 'scripts/validate-physical-component-evidence.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
from evidence.immutable import canonical_json, descriptor, sha256
from physical_component_custody import describe


class Fixture:
    def __init__(self, root):
        self.root = root
        self.index = json.loads((ROOT / validator.INDEX).read_bytes())
        self.aliases = {a['original']['path']: a for a in self.index['aliases']}
        self.complete = [g for g in self.index['generations'] if g['status'] == 'complete']
        self.reports = {g['prefix']: json.loads(self.raw(g['prefix'] + '/report.json')) for g in self.complete}
        paths = {p['path'] for p in self.index['payloads']}
        paths.update(p['path'] for p in next(iter(self.reports.values()))['inputs'])
        for path in paths:
            destination = root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.link(ROOT / path, destination)
        self.changed = {}

    def raw(self, original):
        target = self.aliases[original]['payload']
        return self.changed[target] if hasattr(self, 'changed') and target in self.changed else (ROOT / target).read_bytes()

    def alter_rows(self, family, change, select=lambda rows: True):
        report = next(iter(self.reports.values()))
        for entry in report['outputs'][family]:
            target = self.aliases[entry['path']]['payload']
            body = json.loads(gzip.decompress(self.raw(entry['path'])))
            rows = body['features'] if isinstance(body, dict) else body
            if select(rows):
                change(rows)
                self.changed[target] = gzip.compress(canonical_json(body), mtime=0)
                return
        raise AssertionError('Control did not find its required world example')

    def finalize(self):
        for prefix, report in self.reports.items():
            for entries in report['outputs'].values():
                for number, entry in enumerate(entries):
                    # Preserve original descriptors for unchanged payloads. The
                    # real scientific validator still authenticates every
                    # byte; fixture construction only rebinds altered outputs.
                    if self.aliases[entry['path']]['payload'] in self.changed:
                        entries[number] = describe(entry['path'], self.raw(entry['path']))
            self.changed[self.aliases[prefix + '/report.json']['payload']] = canonical_json(report)
        # A shared payload may also belong to the preserved failed trial. Its
        # immutable trial receipt must accurately reflect the changed control.
        for generation in self.index['generations']:
            if generation['status'] == 'complete':
                continue
            path = generation['prefix'] + '/incomplete-export-receipt.json'
            receipt = json.loads(self.raw(path))
            for number, entry in enumerate(receipt['outputs_preserved']):
                if self.aliases[entry['path']]['payload'] not in self.changed:
                    continue
                row = describe(entry['path'], self.raw(entry['path']))
                if 'uncompressed_sha256' not in entry:
                    row = {k: v for k, v in row.items() if not k.startswith('uncompressed_')}
                receipt['outputs_preserved'][number] = row
            self.changed[self.aliases[path]['payload']] = canonical_json(receipt)
        for target, raw in self.changed.items():
            path = self.root / target
            path.unlink()  # detach hard link before replacing bytes
            path.write_bytes(raw)
        for payload in self.index['payloads']:
            if payload['path'] in self.changed:
                payload.update(descriptor(payload['path'], self.changed[payload['path']]))
        for alias in self.index['aliases']:
            if alias['payload'] in self.changed:
                alias['original'] = describe(alias['original']['path'], self.changed[alias['payload']])
        path = self.root / validator.INDEX
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json(self.index))


class FixtureBindingControls(unittest.TestCase):
    def test_changed_shared_payload_rebinds_complete_and_failed_receipts_without_touching_original(self):
        from physical_component_custody import validate
        with tempfile.TemporaryDirectory(prefix='physical-fixture-binding-') as directory:
            f = Fixture(pathlib.Path(directory))
            f.alter_rows('new_contacts', lambda rows: rows.clear())
            changed = next(iter(f.changed))
            original = (ROOT / changed).read_bytes()
            f.finalize()
            self.assertEqual((ROOT / changed).read_bytes(), original)
            self.assertNotEqual((f.root / changed).read_bytes(), original)
            # Real whole-byte validation checks every alias and both successful
            # runs, plus any shared payload in the preserved failed trial.
            validate(f.root, f.index)

    def test_unchanged_bad_descriptor_is_not_repaired_into_apparent_validity(self):
        from physical_component_custody import validate
        with tempfile.TemporaryDirectory(prefix='physical-fixture-rejection-') as directory:
            f = Fixture(pathlib.Path(directory))
            entry = next(iter(next(iter(f.reports.values()))['outputs'].values()))[0]
            entry['sha256'] = '0' * 64
            f.finalize()
            with self.assertRaisesRegex(ValueError, 'Missing or changed original output'):
                validate(f.root, f.index)


class CompactFixture:
    """All required failure conditions in six new fragments, without world copies."""
    def __init__(self):
        from copy import deepcopy
        from shapely.geometry import box, mapping
        from geographic_components import components
        from physical_gap_crosswalk import crosswalk, membership

        def feature(identity, bounds, area=1):
            return {'type': 'Feature', 'id': identity, 'geometry': mapping(box(*bounds)),
                    'properties': {'area_m2': area, 'exact_location_contacts': []}}

        self.old = [feature('old-overlap', (0, 0, 2, 1), None),
                    feature('old-unlinked', (10, 10, 11, 11))]
        self.new = [feature('new-a', (0, 0, 1, 1)),
                    feature('new-edge', (1, 0, 2, 1)),
                    feature('new-point', (2, 1, 3, 2)),
                    feature('new-east', (179, 3, 180, 4)),
                    feature('new-west', (-180, 3, -179, 4)),
                    feature('new-unlinked', (15, 15, 16, 16))]
        bounds = [-180, -60, 180, 85]
        blocked = {'bounds': [20, 20, 21, 21], 'status': 'blocked-original-water'}
        self.old_records, _ = components(self.old, [blocked], bounds)
        new_records, contacts = components(self.new, [blocked], bounds)
        for row in new_records:
            row['id'] = 'physical-component:' + row['id'].split(':', 1)[1]
        members = membership(self.new, new_records)
        for contact in contacts:
            contact['components'] = [members[i] for i in contact['fragments']]
        assert {c['kind'] for c in contacts} == {'shared-edge', 'point-only-ambiguous'}
        assert any(c['dateline'] for c in contacts)
        self.rows = crosswalk(self.old, self.new, self.old_records, new_records)
        self.rows.update(new_components=new_records, new_contacts=contacts)
        self.old_report = {'candidate_fragments': len(self.old), 'tiles_blocked': [blocked]}
        self.new_report = {'candidate_fragments': len(self.new), 'residues': 0,
                           'tiles': [blocked], 'bounds': bounds}
        self.component_report = {'component_count': len(self.old_records)}
        report = {name: len(self.rows[name]) for name in
                  ['old_fragments', 'new_fragments', 'new_components', 'fragment_pairs', 'component_links']}
        report.update(old_components=len(self.old_records), new_remnants_preserved_in_original_bundles=0,
                      unmeasured_original_ids=['old-overlap'], unmeasured_new_ids=[],
                      original_blocked_domains=[{'original': deepcopy(blocked), 'new': deepcopy(blocked)}],
                      overlay_unknowns=[], difference_unknowns=[], status='complete-exact-correspondence-accounting')
        self.reports = {'compact-control': report}
        # Match actual decoded JSON representations, including coordinate arrays.
        self.__dict__ = json.loads(canonical_json(self.__dict__))

    def alter_rows(self, family, change, select=lambda rows: True):
        rows = self.rows[family]
        assert select(rows), 'Control is missing its required failure condition'
        change(rows)

    def validate(self):
        report = self.reports['compact-control']
        validator.validate_accounting(report, self.old_report, self.component_report, self.new_report,
                                      self.old, self.new, [], self.old_records, self.rows)
        return validator.validate_reconstruction(self.new, self.new_report,
                                                self.rows['new_components'], self.rows['new_contacts'])


class Controls(unittest.TestCase):
    def control(self, tamper, message):
        fixture = CompactFixture()
        self.assertEqual(fixture.validate()['source_contact_unknowns'], 0)
        tamper(fixture)
        # No stale file hash can short-circuit these actual semantic predicates.
        # Full-file authentication is exercised separately with retained evidence.
        with self.assertRaisesRegex(ValueError, message):
            fixture.validate()

    def test_missing_fragment_with_self_consistent_reported_count(self):
        def tamper(f):
            f.alter_rows('old_fragments', lambda rows: rows.pop())
            for report in f.reports.values():
                report['old_fragments'] -= 1
        self.control(tamper, 'Complete reported count differs: old_fragments')

    def test_original_unmeasured_area_cannot_be_fabricated(self):
        def change(rows):
            row = next(r for r in rows if r['unmeasured_original'])
            row['original_area_m2'], row['unmeasured_original'] = 0, False
        self.control(lambda f: f.alter_rows('old_fragments', change,
                     lambda rows: any(r['unmeasured_original'] for r in rows)),
                     'Original measurement uncertainty changed')

    def test_unlinked_component_cannot_disappear(self):
        def change(rows):
            rows.remove(next(r for r in rows if not r['component_link_numbers']))
        self.control(lambda f: f.alter_rows('components', change,
                     lambda rows: any(not r['component_link_numbers'] for r in rows)),
                     'Original unlinked components erased')

    def test_original_blocked_tile_binding_cannot_be_redirected(self):
        def tamper(f):
            for report in f.reports.values():
                report['original_blocked_domains'][0]['new']['bounds'][0] += 1
        self.control(tamper, 'Old blocked domain binding changed')

    def test_pair_cannot_claim_another_component(self):
        def change(rows):
            rows[0]['old_component'] = 'invented-component'
        self.control(lambda f: f.alter_rows('fragment_pairs', change), 'Pair membership differs')

    def test_component_link_cannot_omit_a_pair(self):
        self.control(lambda f: f.alter_rows('component_links', lambda rows: rows[0]['pair_numbers'].pop()),
                     'Component relationship omitted/duplicated')

    def test_edge_point_dateline_contacts_cannot_be_erased(self):
        self.control(lambda f: f.alter_rows('new_contacts', lambda rows: rows.clear()),
                     'Complete original edge/point/dateline contact roster changed')


if __name__ == '__main__':
    unittest.main(defaultTest='Controls', verbosity=2, failfast=True)
