import contextlib, hashlib, io, json, pathlib, sys, tempfile, unittest
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
        cls.temp = tempfile.TemporaryDirectory(prefix='v7-replay-test-')
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
        with tempfile.TemporaryDirectory(prefix='v7-rle-validation-') as tmp:
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
                for name, invalid in [('physical', 257), ('v2', 257), ('v6', 273)]:
                    with self.assertRaisesRegex(ValueError, 'code'):
                        c.validate_rle_row(np.array([4]), np.array([invalid]), name, 0)

    def test_pins_tiles_and_compose(self):
        tile=ROOT/'layer'/'tile.jsonl';write(tile,b'{"row":0,"spans":[{"start":0,"end":4,"code":7,"rule_id":"r","member_id":"m"}]}\n')
        m={'schema':'worldatlas-full-water-assignment-tiles-v1','status':'complete','grid':{'width':4,'height':2},'coverage':{'complete':True},'tiles':[{'path':'tile.jsonl','sha256':digest(tile),'row_start':0,'row_end_exclusive':2}]}
        mp=ROOT/'layer'/'manifest.json';json_file(mp,m)
        entry={'layer_id':'ocean','manifest_path':'layer/manifest.json','manifest_sha256':digest(mp),'priority':1,'overrides':[]}
        planpath=ROOT/'plan.json'
        with patch.object(c,'W',4),patch.object(c,'H',2),patch.object(c,'GRID',{'width':4,'height':2}):
            self.assertEqual(c.read_pinned_manifest(entry,planpath,ROOT)[0],mp)
            for bad in ({**entry,'manifest_sha256':'0'*64},{**entry,'manifest_sha256':None}):
                with self.assertRaises(ValueError): c.read_pinned_manifest(bad,planpath,ROOT)
            bad_m={**m,'tiles':[{**m['tiles'][0],'sha256':'0'*64}]}; bad_mp=ROOT/'layer'/'bad-manifest.json'; json_file(bad_mp,bad_m)
            with self.assertRaises(ValueError): c.read_pinned_manifest({**entry,'manifest_path':'layer/bad-manifest.json','manifest_sha256':digest(bad_mp)},planpath,ROOT)
            rows=np.asarray([0,1,2],dtype='<u4').tobytes()
            for name,values in [('physical',[4,1,4,17]),('v2',[4,7,4,17]),('v6',[4,7,4,17])]:
                write(ROOT/f'{name}-rows',rows);write(ROOT/f'{name}-runs',np.asarray(values,dtype='<u4').tobytes())
            rles={name:{'rows_path':f'{name}-rows','runs_path':f'{name}-runs','rows_sha256':digest(ROOT/f'{name}-rows'),'runs_sha256':digest(ROOT/f'{name}-runs')} for name in ('physical','v2','v6')}
            json_file(planpath,{'schema':'worldatlas-v7-full-grid-composition-plan-v1','grid':{'width':4,'height':2},'rle_inputs':rles,'water_layers':[entry]})
            out=TEST/'new-output'
            argv=['compose','--plan',str(planpath),'--input-root',str(ROOT),'--out',str(out)]
            with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()): c.main()
            self.assertEqual(np.fromfile(out/'rows.u32le',dtype='<u4').tolist(),[0,1,2])
            self.assertEqual(np.fromfile(out/'runs.u32le',dtype='<u4').tolist(),[4,7,4,17])
            before=(out/'runs.u32le').read_bytes()
            with patch.object(sys,'argv',argv),self.assertRaises(FileExistsError): c.main()
            self.assertEqual((out/'runs.u32le').read_bytes(),before)
            argv[-1]=str(ROOT/'forbidden-output')
            with patch.object(sys,'argv',argv),self.assertRaises(ValueError): c.main()
            self.assertFalse((ROOT/'forbidden-output').exists())

if __name__=='__main__': unittest.main(verbosity=2)
