import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from write_land_stream import write_land_stream
from ural_delta import SCHEMA as URAL_DELTA_SCHEMA, split_scope

U = lambda *v: struct.pack('<' + 'I' * len(v), *v)

class WriterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.p = Path(self.tmp.name)
        # Four mainland roots, one spans two mainland codes. Seed boundaries
        # deliberately cross adjacent component boundaries.
        self.comp = [[(0,2,1),(2,4,2),(5,7,10)], [(0,2,3),(2,4,4),(4,6,10),(7,8,11)]]
        self.phys = [[(4,17),(5,1),(7,17),(8,1)], [(6,17),(7,1),(8,17)]]
        self.seed = [[(3,17),(4,18),(8,0)], [(4,19),(8,0)]]
        self.roots = [10,11]
        self.codes = [20,20]
    def tearDown(self): self.tmp.cleanup()
    def pair(self, name, rows):
        offsets = [0]; flat = []
        for r in rows: flat.extend(r); offsets.append(len(flat))
        (self.p/(name+'rows')).write_bytes(U(*offsets))
        (self.p/(name+'runs')).write_bytes(b''.join(U(*r) for r in flat))
        return self.p/(name+'rows'), self.p/(name+'runs')
    def run_writer(self, **overrides):
        a,b = self.pair('c',self.comp); c,d = self.pair('p',self.phys); e,f = self.pair('s',self.seed)
        (self.p/'roots').write_bytes(U(*self.roots)); (self.p/'codes').write_bytes(bytes(self.codes))
        params = dict(width=8,height=2,component_rows=a,component_runs=b,physical_rows=c,physical_runs=d,mainland_rows=e,mainland_runs=f,roots=self.p/'roots',codes=self.p/'codes',mainland_roots=[1,2,3,4],output_dir=self.p/'out',disk_reserve_bytes=0)
        params.update(overrides)
        return write_land_stream(**params)
    def output(self):
        b = (self.p/'out/runs.u32le').read_bytes()
        return [struct.unpack_from('<II',b,i) for i in range(0,len(b),8)]
    def test_boundaries_coalescing_and_report(self):
        r = self.run_writer()
        self.assertEqual(self.output(), [(3,17),(4,18),(5,0),(7,20),(8,0),(4,19),(6,20),(7,0),(8,20)])
        self.assertEqual((self.p/'out/rows.u32le').read_bytes(),U(0,5,9))
        self.assertEqual(r['land_cells'], 13)
        self.assertEqual(json.loads((self.p/'out/report.json').read_text()),r)
        self.assertEqual(r['rows_sha256'],hashlib.sha256((self.p/'out/rows.u32le').read_bytes()).hexdigest())
        self.assertEqual(r['runs_sha256'],hashlib.sha256((self.p/'out/runs.u32le').read_bytes()).hexdigest())
        self.assertFalse((self.p/'out/assignment-seen.partial').exists())
    def test_ural_delta_overrides_seed_by_cell_center_side(self):
        # A seeded mainland component is split across a synthetic divider.
        # The writer must apply the bounded override at cell-center granularity.
        self.seed[0] = [(2,19),(4,18),(8,0)]
        bounds = [-130,30,40,80]
        line, europe_ring, asia_ring = split_scope(
            [[-50,90],[-60,40],[-130,40]], bounds, [-100,60], [20,60])
        rule = {
            'schema': URAL_DELTA_SCHEMA, 'revision': 'synthetic',
            'boundary_id': 'ural_kara_coast_to_caspian', 'boundary_sha256': '0'*64,
            'route_id': 'europe_caspian_closure_v1', 'route_sha256': '1'*64,
            'scope_bounds': bounds, 'europe_witness': [-100,60], 'asia_witness': [20,60],
            'europe_code': 19, 'asia_code': 18,
            'grid': {'width': 8, 'height': 2, 'west': -180, 'north': 90, 'step': 45},
            'line_scope_vertices': line, 'europe_ring': europe_ring, 'asia_ring': asia_ring,
        }
        result = self.run_writer(delta_rule=rule)
        out = self.output()
        row0 = [next(code for end,code in out[:5] if x < end) for x in range(8)]
        self.assertEqual(row0[2], 19)
        self.assertEqual(row0[3], 18)
        self.assertEqual(result['ural_delta']['counts'], {
            'land_centers': 3, 'other_land_labels': 0,
            'europe_to_asia': 0, 'asia_to_europe': 1,
        })
        self.assertEqual(result['land_cells'], 13)
    def test_ural_delta_rejects_land_cell_center_on_scope_edge(self):
        self.seed[0] = [(4,19),(8,0)]
        rule = {
            'schema': URAL_DELTA_SCHEMA,
            'scope_bounds': [-130, 30, 40, 67.5],
            'europe_code': 19, 'asia_code': 18,
            'grid': {'width': 8, 'height': 2, 'west': -180, 'north': 90, 'step': 45},
        }
        with self.assertRaisesRegex(ValueError, 'scope edge'):
            self.run_writer(delta_rule=rule, output_dir=self.p/'edge')
    def test_adjacent_same_assignment_coalesces(self):
        self.comp[0] = [(0,2,1),(2,4,2),(5,6,10),(6,7,11)]
        self.run_writer()
        self.assertIn((7,20),self.output())
    def test_missing_and_extra_assignments(self):
        for roots,codes,msg in [([10],[20],'no assignment'),([10,11,12],[20,20,21],'unused assignment'),([10,10],[20,20],'duplicate'),([11,10],[20,20],'unsorted'),([10,11],[20,16],'invalid')]:
            with self.subTest(roots=roots,codes=codes):
                self.roots,self.codes=roots,codes
                with self.assertRaisesRegex(ValueError,msg): self.run_writer(output_dir=self.p/('o'+str(roots)+str(codes)))
    def test_variable_mainland_root_counts(self):
        # One root and five roots both preserve seed classifications.
        self.comp = [[(0,2,1),(2,4,1),(5,7,10)], [(0,2,1),(2,4,1),(4,6,10),(7,8,11)]]
        result = self.run_writer(mainland_roots=[1])
        self.assertEqual(result['mainland_roots'], [1])
        self.comp[0] = [(0,1,1),(1,2,5),(2,4,2),(5,7,10)]
        self.comp[1] = [(0,2,3),(2,4,4),(4,6,10),(7,8,11)]
        result = self.run_writer(mainland_roots=[1,2,3,4,5], output_dir=self.p/'out5')
        self.assertEqual(result['mainland_roots'], [1,2,3,4,5])
        for roots in ([], [1,1], [1,-1], [1, 1 << 32], [True]):
            with self.subTest(roots=roots):
                with self.assertRaisesRegex(ValueError, 'mainland roots'):
                    self.run_writer(mainland_roots=roots, output_dir=self.p/'invalid')

    def test_seed_mismatch(self):
        for seed,msg in [([[(2,17),(8,0)],self.seed[1]],'seed gap'),([[(4,17),(5,0),(6,18),(8,0)],self.seed[1]],'overlaps'),([[(4,17),(5,18),(8,0)],self.seed[1]],'on water')]:
            with self.subTest(msg=msg):
                self.seed=seed
                with self.assertRaisesRegex(ValueError,msg): self.run_writer(output_dir=self.p/msg.replace(' ',''))
    def test_physical_mismatch_and_overlapping_components(self):
        self.phys[0]=[(3,17),(5,1),(7,17),(8,1)]
        with self.assertRaisesRegex(ValueError,'coverage'): self.run_writer()
        self.phys[0]=[(4,17),(5,1),(7,17),(8,1)]
        self.comp[0]=[(0,3,1),(2,4,2)]
        with self.assertRaisesRegex(ValueError,'overlapping'): self.run_writer(output_dir=self.p/'other')
    def test_malformed_full_row_and_missing_seed_root(self):
        self.seed[0]=[(7,0)]
        with self.assertRaises(ValueError): self.run_writer()
        self.seed[0]=[(3,17),(4,18),(8,0)]
        self.comp[1] = [(0,2,3),(2,4,10),(4,6,10),(7,8,11)]
        self.seed[1] = [(2,19),(8,0)]
        with self.assertRaisesRegex(ValueError,'missing designated'): self.run_writer(mainland_roots=[1,2,3,999],output_dir=self.p/'other')
    def test_invalid_offsets_and_truncated_runs(self):
        # Patch the row encoder to corrupt the first input after generation.
        original=self.pair
        def corrupt(name, rows):
            a,b=original(name,rows)
            if name=='c': a.write_bytes(U(0,99,99))
            return a,b
        self.pair=corrupt
        with self.assertRaisesRegex(ValueError,'offset'): self.run_writer()
        self.assertFalse((self.p/'out/report.json').exists())
        self.assertTrue((self.p/'out/rows.u32le').exists())
    def test_bad_input_lengths_codes_and_existing_output(self):
        self.phys[0] = [(8, 2)]
        with self.assertRaisesRegex(ValueError, 'physical'): self.run_writer()
        self.assertFalse((self.p/'out/report.json').exists())
        self.phys[0] = [(4,17),(5,1),(7,17),(8,1)]
        with self.assertRaises(FileExistsError): self.run_writer()
        original = self.pair
        def truncate(name, rows):
            a,b=original(name,rows)
            if name == 's': b.write_bytes(b.read_bytes()[:-1])
            return a,b
        self.pair=truncate
        with self.assertRaisesRegex(ValueError, 'length'): self.run_writer(output_dir=self.p/'truncated')
        self.assertFalse((self.p/'truncated').exists())

    def test_resource_guards(self):
        with patch('write_land_stream.shutil.disk_usage') as usage:
            usage.return_value=type('D',(),{'free':0})()
            with self.assertRaisesRegex(RuntimeError,'disk'): self.run_writer()
        self.run_writer(output_dir=self.p/'without_memory_guard')
        self.assertTrue((self.p/'without_memory_guard/report.json').exists())

if __name__ == '__main__': unittest.main()
