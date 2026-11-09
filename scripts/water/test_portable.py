import hashlib, json, pathlib, tempfile, unittest
from unittest.mock import patch
import numpy as np
import compose_full_water_grid as c

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f: f.write(b)
def json_file(p, obj): write(p,json.dumps(obj).encode())

class PortableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global TEST, ROOT
        cls.temp = tempfile.TemporaryDirectory(prefix='water-test-')
        TEST = pathlib.Path(cls.temp.name)
        ROOT = TEST / 'inputs'
        ROOT.mkdir()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_resolution_and_rejection(self):
        self.assertEqual(c.resolve_input(str(ROOT/'a/b'),ROOT,ROOT),ROOT/'a/b')
        with self.assertRaises(ValueError): c.resolve_input('/workspace/scratch/127991fc8b8e/a/b',ROOT,ROOT)
        with self.assertRaises(ValueError): c.resolve_input('/tmp/a/b',ROOT,ROOT)
        self.assertEqual(c.resolve_input('b',ROOT/'a',ROOT),ROOT/'a/b')
        with self.assertRaises(ValueError): c.resolve_input('/etc/passwd',ROOT,ROOT)
        with self.assertRaises(ValueError): c.resolve_input('../../escape',ROOT/'a',ROOT)
        with self.assertRaises(ValueError): c.resolve_input('/tmp/../../escape',ROOT,ROOT)
    def test_invalid_rle_envelopes_and_codes_fail_before_narrowing(self):
        with tempfile.TemporaryDirectory(prefix='rle-validation-') as tmp:
            root = pathlib.Path(tmp)
            rows, runs = root / 'rows', root / 'runs'
            with patch.object(c, 'W', 4), patch.object(c, 'H', 2):
                rows.write_bytes(np.array([0, 1, 2], dtype='<u4').tobytes())
                runs.write_bytes(np.array([4, 1, 4, 17], dtype='<u4').tobytes())
                rr, ru = c.open_validated_rle(rows, runs, 'physical')
                c.validate_rle_row(*c.rle_row(rr, ru, 0), 'physical', 0)
                for bad in ([0, 0, 2], [0, 1, 3], [1, 1, 2]):
                    rows.write_bytes(np.array(bad, dtype='<u4').tobytes())
                    with self.assertRaisesRegex(ValueError, 'offsets'):
                        c.open_validated_rle(rows, runs, 'physical')
                rows.write_bytes(b'\0')
                with self.assertRaisesRegex(ValueError, 'size'):
                    c.open_validated_rle(rows, runs, 'physical')
                for ends in ([0, 4], [3, 3, 4], [5]):
                    with self.assertRaisesRegex(ValueError, 'endpoints'):
                        c.validate_rle_row(np.array(ends), np.ones(len(ends)), 'physical', 0)
                for name, invalid in [('physical', 257), ('water', 257), ('land', 273)]:
                    with self.assertRaisesRegex(ValueError, 'code'):
                        c.validate_rle_row(np.array([4]), np.array([invalid]), name, 0)

    def test_pins_and_reads_tiles(self):
        tile=ROOT/'layer'/'tile.jsonl';write(tile,b'{"row":0,"spans":[{"start":0,"end":4,"code":7,"rule_id":"r","member_id":"m"}]}\n')
        m={'schema':'worldatlas-full-water-assignment-tiles-v1','status':'complete','grid':{'width':4,'height':2},'coverage':{'complete':True},'tiles':[{'path':'tile.jsonl','sha256':digest(tile),'row_start':0,'row_end_exclusive':2}]}
        mp=ROOT/'layer'/'manifest.json';json_file(mp,m)
        entry={'layer_id':'ocean','manifest_path':'layer/manifest.json','manifest_sha256':digest(mp),'priority':1,'overrides':[]}
        planpath=ROOT/'plan.json'
        with patch.object(c,'W',4),patch.object(c,'H',2),patch.object(c,'GRID',{'width':4,'height':2}):
            path, manifest = c.read_pinned_manifest(entry, planpath, ROOT)
            self.assertEqual(path, mp)
            manifest['_tiles'] = manifest['tiles']
            cursor = c.RowCursor(manifest, 0, 2, 'water')
            self.assertEqual(cursor.take(0), [(0, 0, 4, 7, 'r', 'm', None, None)])
            self.assertEqual(cursor.take(1), [])
            for bad in ({**entry,'manifest_sha256':'0'*64},{**entry,'manifest_sha256':None}):
                with self.assertRaises(ValueError): c.read_pinned_manifest(bad,planpath,ROOT)
            bad_m={**m,'tiles':[{**m['tiles'][0],'sha256':'0'*64}]}; bad_mp=ROOT/'layer'/'bad-manifest.json'; json_file(bad_mp,bad_m)
            with self.assertRaises(ValueError): c.read_pinned_manifest({**entry,'manifest_path':'layer/bad-manifest.json','manifest_sha256':digest(bad_mp)},planpath,ROOT)

if __name__=='__main__': unittest.main(verbosity=2)
