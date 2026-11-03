import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import build_prefill as prefill
import compose_full_water_grid as c


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PrefillTests(unittest.TestCase):
    def test_small_prefill_pins_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='v7-prefill-') as tmp:
            base = Path(tmp)
            root = base / 'inputs'
            root.mkdir()
            def put(name, data):
                p = root / name
                p.write_bytes(data)
                return p
            rows = np.array([0, 1, 2], dtype='<u4').tobytes()
            rles = {}
            for name, values in [('physical', [4, 1, 4, 17]), ('v6', [4, 8, 4, 18])]:
                rp = put(name + '-rows', rows)
                up = put(name + '-runs', np.array(values, dtype='<u4').tobytes())
                rles[name] = {'rows_path': rp.name, 'runs_path': up.name,
                              'rows_sha256': digest(rp), 'runs_sha256': digest(up)}
            tile = put('coast.jsonl', b'{"row":0,"spans":[{"start":0,"end":2,"code":2,"rule_id":"coast","member_id":"m"}]}\n')
            manifest = {'schema': 'worldatlas-full-water-assignment-tiles-v1',
                        'status': 'complete', 'grid': {'width': 4, 'height': 2},
                        'coverage': {'complete': True}, 'tiles': [{'path': tile.name,
                        'sha256': digest(tile), 'row_start': 0, 'row_end_exclusive': 2}]}
            mp = put('coast.json', json.dumps(manifest).encode())
            layer = {'layer_id': 'coast', 'manifest_path': mp.name,
                     'manifest_sha256': digest(mp), 'priority': 1, 'overrides': []}
            plan = {'schema': 'worldatlas-v7-full-grid-composition-plan-v1',
                    'grid': {'width': 4, 'height': 2}, 'rle_inputs': rles, 'water_layers': [layer]}
            pp = put('plan.json', json.dumps(plan).encode())
            out = base / 'output'
            argv = ['build_prefill', '--plan', str(pp), '--input-root', str(root), '--out', str(out)]
            with patch.object(c, 'W', 4), patch.object(c, 'H', 2), patch.object(c, 'GRID', {'width': 4, 'height': 2}), patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
                prefill.main()
                self.assertEqual(np.fromfile(out / 'prefill-rows.u32le', dtype='<u4').tolist(), [0, 2, 3])
                self.assertEqual(np.fromfile(out / 'prefill-runs.u32le', dtype='<u4').tolist(), [2, 2, 4, 0, 4, 18])
                with self.assertRaises(FileExistsError):
                    prefill.main()
                argv[-1] = str(root / 'bad')
                with self.assertRaises(ValueError):
                    prefill.main()
                self.assertFalse((root / 'bad').exists())
                plan['water_layers'][0]['manifest_sha256'] = '0' * 64
                pp.write_text(json.dumps(plan))
                argv[-1] = str(base / 'bad-pin')
                with self.assertRaises(ValueError):
                    prefill.main()
                self.assertFalse((base / 'bad-pin').exists())
                plan['water_layers'][0]['manifest_sha256'] = digest(mp)
                bad_physical = root / 'physical-runs'
                bad_physical.write_bytes(np.array([4, 257, 4, 17], dtype='<u4').tobytes())
                plan['rle_inputs']['physical']['runs_sha256'] = digest(bad_physical)
                pp.write_text(json.dumps(plan))
                argv[-1] = str(base / 'bad-code')
                with self.assertRaisesRegex(ValueError, 'physical' ):
                    prefill.main()


if __name__ == '__main__':
    unittest.main()
