import contextlib, gzip, hashlib, json, sqlite3, struct, tempfile, unittest
from pathlib import Path
import numpy as np
from worldatlas.map_build.water import streaming_closed_water as s
from worldatlas.map_build.water.partition_json_stream import read_partition
from worldatlas.map_build.water.tests.test_closed_water_core import policy_snapshot
from worldatlas.map_build.water.tests.helpers import rle


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


class StreamingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.snap = policy_snapshot()
        p = np.full((180, 360), 17, dtype=np.uint32)
        q = p.copy()
        land = p.copy()
        for x in (5, 10, 15):
            p[89, x] = 1
            q[89, x] = 0
            land[89, x] = 0
        q[89, 6] = 18
        land[89, 6] = 18
        self.physical, self.prefill, self.land = rle(p), rle(q), rle(land)
        self.by = {89: [(5, 6, 1), (10, 11, 2), (15, 16, 3)]}
        self.inputs = {
            k: 'a' * 64
            for k in (
                'physical_rows_sha256',
                'physical_runs_sha256',
                'prefill_rows_sha256',
                'prefill_runs_sha256',
                'prefill_audit_sha256',
            )
        }
        self.part = {
            'schema': 'fresh-ocean-run-partition-v1',
            'grid': {'W': 360, 'H': 180},
            'inputs': {
                **self.inputs,
                'decision_snapshot_sha256': 's' * 64,
                'legacy_ocean_label_inheritance': False,
                'decision_revision': 'draft',
                'entity_revision': 'entities',
            },
            'unseeded_cell_count': 3,
            'components': [
                {
                    'component_root': r,
                    'ocean_code': None,
                    'cell_count': 1,
                    'source_barrier_contact_edge_count': 1 if r == 3 else 0,
                }
                for r in (1, 2, 3)
            ],
        }
        self.part['unseeded_span_count'] = 3
        self.rows = self.root / 'rows.u64'
        self.spans = self.root / 'spans.u32'
        self.cuts = self.root / 'cuts.u32'
        offsets = [0]
        records = []
        for y in range(180):
            records.extend(self.by.get(y, []))
            offsets.append(len(records))
        self.rows.write_bytes(struct.pack('<181Q', *offsets))
        self.spans.write_bytes(b''.join(struct.pack('<III', *z) for z in records))
        self.cuts.write_bytes(struct.pack('<III', 0, 89, 15))
        self.inputs['source_cut_edges_sha256'] = sha(self.cuts)
        self.part['inputs']['source_cut_edges_sha256'] = self.inputs['source_cut_edges_sha256']
        self.partition = self.root / 'partition.json'
        self.partition.write_text(json.dumps(self.part))

    def tearDown(self):
        self.tmp.cleanup()

    def run_stage(self, name='out', **kw):
        return s.run(
            self.snap,
            's' * 64,
            self.physical,
            self.prefill,
            self.land,
            self.partition,
            self.rows,
            self.spans,
            self.cuts,
            self.root / name,
            360,
            180,
            180,
            self.inputs,
            **kw
        )

    def test_streamed_direct_mixed_and_cut(self):
        m = self.run_stage()
        self.assertEqual((m['assigned_cells'], m['pending_cells']), (2, 1))
        self.assertEqual(m['status'], 'partial')
        with gzip.open(self.root / 'out/closed-water-assignments.jsonl.gz', 'rt') as f:
            z = json.loads(f.readline())
        self.assertEqual(
            [(x['start'], x['end'], x['code']) for x in z['spans']], [(5, 6, 1), (10, 11, 1)]
        )
        with gzip.open(self.root / 'out/pending-components.jsonl.gz', 'rt') as f:
            pending = json.loads(f.readline())
        self.assertEqual(pending['reason'], 'pending-source-cut-contact')
        self.assertEqual(sha(self.root / 'out/work.sqlite3'), m['work_database']['sha256'])

    def test_work_index_keeps_component_decisions(self):
        m = self.run_stage('indexed')
        timings = m['processing_stage_elapsed_seconds']
        self.assertEqual(
            set(timings),
            {
                'ingest_partition',
                'ingest_spans',
                'classify_boundaries',
                'mark_cut_contacts',
                'assign_components',
                'write_assignments',
            },
        )
        self.assertTrue(all(elapsed >= 0 for elapsed in timings.values()))
        self.assertGreaterEqual(m['processing_elapsed_seconds'], sum(timings.values()))
        with contextlib.closing(sqlite3.connect(self.root / 'indexed/work.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM spans').fetchone()[0], 3)
            methods = dict(db.execute('SELECT root,method FROM components'))
            self.assertEqual(methods, {1: 'mixed', 2: 'direct', 3: 'pending-source-cut-contact'})
        self.assertEqual((m['assigned_cells'], m['pending_cells']), (2, 1))

    def test_partition_pin_and_root_errors_fail_no_manifest(self):
        self.part['inputs']['physical_rows_sha256'] = 'b' * 64
        self.partition.write_text(json.dumps(self.part))
        with self.assertRaisesRegex(ValueError, 'partition input mismatch'):
            self.run_stage()
        self.assertFalse((self.root / 'out/manifest.json').exists())

    def test_component_size_unknown_root_and_overlap_fail_closed(self):
        self.part['components'][0]['cell_count'] = 2
        self.partition.write_text(json.dumps(self.part))
        with self.assertRaisesRegex(ValueError, 'size mismatch'):
            self.run_stage('bad-size')
        self.part['components'][0]['cell_count'] = 1
        self.partition.write_text(json.dumps(self.part))
        self.spans.write_bytes(struct.pack('<9I', 5, 6, 999, 10, 11, 2, 15, 16, 3))
        with self.assertRaisesRegex(ValueError, 'unknown roots'):
            self.run_stage('bad-root')
        self.spans.write_bytes(struct.pack('<9I', 5, 7, 1, 6, 7, 2, 15, 16, 3))
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            self.run_stage('bad-overlap')
        for name in ('bad-size', 'bad-root', 'bad-overlap'):
            self.assertFalse((self.root / name / 'manifest.json').exists())

    def test_malformed_offsets_fail_closed(self):
        data = list(struct.unpack('<181Q', self.rows.read_bytes()))
        data[89] = 2
        data[90] = 1
        self.rows.write_bytes(struct.pack('<181Q', *data))
        with self.assertRaisesRegex(ValueError, 'offsets'):
            self.run_stage('bad-offsets')
        self.assertFalse((self.root / 'bad-offsets/manifest.json').exists())

    def test_unsupported_policy_rejected_before_output(self):
        self.snap['policies'][0]['definition']['distance'] = 'unsupported'
        with self.assertRaisesRegex(ValueError, 'safety'):
            self.run_stage()
        self.assertFalse((self.root / 'out').exists())

    def test_mutation_callback_does_not_write_manifest(self):
        def changed():
            raise ValueError('input changed')

        with self.assertRaisesRegex(ValueError, 'input changed'):
            self.run_stage(verify_inputs=changed)
        self.assertFalse((self.root / 'out/manifest.json').exists())

    def test_cut_reconnected_same_root(self):
        # Root 1 consists of x=5,6; an internal cut still forces pending.
        p = np.full((180, 360), 17, dtype=np.uint32)
        q = p.copy()
        land = p.copy()
        for x in (5, 6, 10, 15):
            p[89, x] = 1
            q[89, x] = 0
            land[89, x] = 0
        q[89, 7] = 18
        land[89, 7] = 18
        from worldatlas.map_build.water.tests.helpers import rle

        self.physical, self.prefill, self.land = rle(p), rle(q), rle(land)
        records = [(5, 7, 1), (10, 11, 2), (15, 16, 3)]
        self.spans.write_bytes(b''.join(struct.pack('<III', *z) for z in records))
        self.part['unseeded_cell_count'] = 4
        self.part['components'][0]['cell_count'] = 2
        self.cuts.write_bytes(struct.pack('<6I', 0, 89, 5, 0, 89, 15))
        self.inputs['source_cut_edges_sha256'] = sha(self.cuts)
        self.part['inputs']['source_cut_edges_sha256'] = sha(self.cuts)
        self.partition.write_text(json.dumps(self.part))
        m = self.run_stage()
        self.assertEqual((m['assigned_cells'], m['pending_cells']), (1, 3))
        with gzip.open(self.root / 'out/pending-components.jsonl.gz', 'rt') as f:
            rows = [json.loads(z) for z in f]
        self.assertEqual({z['component_root'] for z in rows}, {1, 3})


class ParserTest(unittest.TestCase):
    def test_components_stream_and_nested(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'p'
            p.write_text(
                json.dumps(
                    {
                        'first': {'nested': [1, 2]},
                        'components': [{'root': 1}, {'root': 2}],
                        'after': 'x',
                    }
                )
            )
            found = []
            meta = read_partition(p, found.append)
            self.assertEqual(found, [{'root': 1}, {'root': 2}])
            self.assertEqual(meta['after'], 'x')

    def test_duplicate_and_truncated_json_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'p'
            p.write_text('{"components":[],"components":[]}')
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                read_partition(p, lambda x: None)
            p.write_text('{"components":[{"a":1}')
            with self.assertRaises(ValueError):
                read_partition(p, lambda x: None)

    def test_complete_large_components_and_metadata_are_read_without_size_caps(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'p'
            payload = 'x' * (2 * 1024 * 1024 + 1)
            p.write_text(json.dumps({'components': [{'a': payload}], 'metadata': payload * 2}))
            found = []
            meta = read_partition(p, found.append)
            self.assertEqual(found, [{'a': payload}])
            self.assertEqual(meta['metadata'], payload * 2)


if __name__ == '__main__':
    unittest.main()
