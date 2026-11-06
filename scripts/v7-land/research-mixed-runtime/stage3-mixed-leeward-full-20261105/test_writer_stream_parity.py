"""Golden-byte test for stage-3 binary RLE output serialization."""
import array
import hashlib
import sys
import pathlib
import struct
import tempfile
import unittest

import writer

U = struct.Struct('<I')
PAIR = struct.Struct('<II')
TRIPLE = struct.Struct('<III')


def write_rows(row_path, run_path, rows, run_struct):
    offset = 0
    with row_path.open('wb') as row_file, run_path.open('wb') as run_file:
        row_file.write(U.pack(0))
        for runs in rows:
            for run in runs:
                run_file.write(run_struct.pack(*run))
            offset += len(runs)
            row_file.write(U.pack(offset))


class WriterParity(unittest.TestCase):
    def test_array_byteswap_reverses_each_u32_word(self):
        values = [1, 0x10203040, 0xffffffff]
        packed = array.array('I', values)
        self.assertEqual(packed.itemsize, 4)
        native = packed.tobytes()
        packed.byteswap()
        swapped = packed.tobytes()
        self.assertEqual(swapped, b''.join(native[i:i + 4][::-1] for i in range(0, len(native), 4)))
        if sys.byteorder == 'little':
            packed.byteswap()
            self.assertEqual(packed.tobytes(), b''.join(struct.pack('<I', value) for value in values))

    def test_serialized_output_matches_golden_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            inputs, outputs = root / 'inputs', root / 'outputs'
            inputs.mkdir(); outputs.mkdir()
            width, height = 20, 128
            pr, ps, cr, cs, br, bs = [inputs / name for name in ('pr', 'ps', 'cr', 'cs', 'br', 'bs')]
            write_rows(pr, ps, [[(1, 1), (20, 17)] for _ in range(height)], PAIR)
            write_rows(cr, cs, [[(1, 20, y + 1)] for y in range(height)], TRIPLE)
            write_rows(br, bs, [[(1, 0), (20, 17)] for _ in range(height)], PAIR)
            output = outputs / 'run'
            report = writer.write_streams(
                grid={'width': width, 'height': height}, physical_rows=pr, physical_runs=ps,
                component_rows=cr, component_runs=cs, baseline_rows=br, baseline_runs=bs,
                component_claims={}, mainland_roots={999}, region_rows=lambda _y: [],
                output=output, guard=lambda: None, disk_reserve_bytes=2 * 1024**3)
            expected = {
                'rows.u32le': b''.join(U.pack(2 * i) for i in range(height + 1)),
                'runs.u32le': (PAIR.pack(1, 0) + PAIR.pack(width, 17)) * height,
                'changes.jsonl': b'',
            }
            for name, payload in expected.items():
                self.assertEqual((output / name).read_bytes(), payload)
            self.assertEqual(report['output_rows_sha256'], hashlib.sha256(expected['rows.u32le']).hexdigest())
            self.assertEqual(report['output_runs_sha256'], hashlib.sha256(expected['runs.u32le']).hexdigest())
            self.assertEqual(report['changes_sha256'], hashlib.sha256(expected['changes.jsonl']).hexdigest())


if __name__ == '__main__':
    unittest.main()
