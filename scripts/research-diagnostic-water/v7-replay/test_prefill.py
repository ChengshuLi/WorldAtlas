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
            argv = ['build_prefill', '--allow-unverified-snapshot', '--allow-historical-v6', '--plan', str(pp), '--input-root', str(root), '--out', str(out)]
            with patch.object(c, 'W', 4), patch.object(c, 'H', 2), patch.object(c, 'GRID', {'width': 4, 'height': 2}), patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
                no_history=[x for x in argv if x!='--allow-historical-v6']
                with patch.object(sys,'argv',no_history):
                    with self.assertRaisesRegex(ValueError,'historical V6 replay requires explicit opt-in'):prefill.main()
                self.assertFalse(out.exists())
                # Actual CLI gate: obsolete and unknown methods are rejected
                # even with opt-in; the WGS84 method requires that opt-in.
                for method in ('spherical-grid-edge-v1','',False):
                    plan['research_shore_method']=method;pp.write_text(json.dumps(plan))
                    with patch.object(sys,'argv',argv+['--allow-research-shore']):
                        with self.assertRaisesRegex(ValueError,'retired or unknown'):prefill.main()
                    self.assertFalse(out.exists())
                manifest['source']={'assignment_method':'shared_nearest_assigned_shore'}
                manifest['nearest_assignment_audit']={'shore_method':'spherical-grid-edge-v1'}
                mp.write_text(json.dumps(manifest));layer['manifest_sha256']=digest(mp)
                plan['research_shore_method']='wgs84-coastal-4neighbor-center-v2';pp.write_text(json.dumps(plan))
                with self.assertRaisesRegex(ValueError,'explicit opt-in'):prefill.main()
                with patch.object(sys,'argv',argv+['--allow-research-shore']):
                    with self.assertRaisesRegex(ValueError,'does not bind'):prefill.main()
                manifest['nearest_assignment_audit']['shore_method']='wgs84-coastal-4neighbor-center-v2 (research, not an approved decision)'
                mp.write_text(json.dumps(manifest));layer['manifest_sha256']=digest(mp);pp.write_text(json.dumps(plan))
                with patch.object(sys,'argv',argv+['--allow-research-shore']):prefill.main()
                self.assertTrue((out/'prefill-rows.u32le').exists())
                import shutil
                shutil.rmtree(out);plan.pop('research_shore_method');pp.write_text(json.dumps(plan))
                with self.assertRaisesRegex(ValueError,'does not bind'):prefill.main()
                manifest.pop('source');manifest.pop('nearest_assignment_audit');mp.write_text(json.dumps(manifest));layer['manifest_sha256']=digest(mp);pp.write_text(json.dumps(plan))
                prefill.main()
                self.assertEqual(np.fromfile(out / 'prefill-rows.u32le', dtype='<u4').tolist(), [0, 2, 3])
                self.assertEqual(np.fromfile(out / 'prefill-runs.u32le', dtype='<u4').tolist(), [2, 2, 4, 0, 4, 18])
                with self.assertRaises(FileExistsError):
                    prefill.main()
                argv[-1] = str(root / 'bad')
                prefill.main()
                self.assertEqual((root/'bad/prefill-runs.u32le').read_bytes(),(out/'prefill-runs.u32le').read_bytes())
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


class DiagnosticWaterEncodingTests(unittest.TestCase):
 def test_pinned_run7_contract_and_untrusted_contract(self):
  r={'schema':'stage3-provisional-diagnostic-land-report-v1','status':'provisional-profiling-only-not-publishable','writer':{'schema':'stage3-land-writer-result-v1'},'policy':{'policy':{'physical_water_policy':'preserve_unassigned'}},'limitations':['Water cells stay unassigned.']};line={'status':'diagnostic-provisional-lineage-bound'}
  self.assertEqual(prefill.direct_land_water_code(r,prefill.DIAGNOSTIC_RUN7_SHA,line),0)
  with self.assertRaisesRegex(ValueError,'unsupported diagnostic'):prefill.direct_land_water_code(r,'0'*64,line)
  r['policy']['policy']['physical_water_policy']='other'
  with self.assertRaisesRegex(ValueError,'unsupported diagnostic'):prefill.direct_land_water_code(r,prefill.DIAGNOSTIC_RUN7_SHA,line)
 def test_every_cell_encoding_is_checked(self):
  def run(p,l):return prefill.validate_row_codes(np.array([p]),np.array([l]),np.array([False]),np.array([0]),np.array([0]),np.array([4]),0,0)
  run(1,0);run(17,18)
  for p,l,err in [(1,1,'physical water'),(17,0,'unassigned final land'),(7,0,'unexpected physical')]:
   with self.assertRaisesRegex(ValueError,err):run(p,l)

class DiagnosticPrefillIntegrationTests(unittest.TestCase):
 def test_pinned_diagnostic_water_and_land_validation(self):
  with tempfile.TemporaryDirectory() as t:
   base=Path(t);root=base/'inputs';root.mkdir();rows=np.array([0,1,2],dtype='<u4').tobytes();(root/'rows').write_bytes(rows);(root/'physical').write_bytes(np.array([4,1,4,17],dtype='<u4').tobytes());(root/'land').write_bytes(np.array([4,0,4,18],dtype='<u4').tobytes())
   report={'schema':'stage3-provisional-diagnostic-land-report-v1','status':'provisional-profiling-only-not-publishable','writer':{'schema':'stage3-land-writer-result-v1'},'policy':{'policy':{'physical_water_policy':'preserve_unassigned'}},'limitations':['Water cells stay unassigned.']};(root/'report').write_text(json.dumps(report));rh=digest(root/'report');line={'status':'diagnostic-provisional-lineage-bound'}
   spec=lambda name:{'rows_path':'rows','rows_sha256':digest(root/'rows'),'runs_path':name,'runs_sha256':digest(root/name)}
   plan={'schema':'worldatlas-v7-full-grid-composition-plan-v1','grid':{'width':4,'height':2},'rle_inputs':{'physical':spec('physical'),'land':{**spec('land'),'report_path':'report','report_sha256':rh}},'water_layers':[],'land_lineage':line,'land_input_kind':'direct-research','decision_revision_status':'draft'};pp=root/'plan';pp.write_text(json.dumps(plan));out=base/'out';argv=['build_prefill','--allow-unverified-snapshot','--allow-draft-snapshot','--plan',str(pp),'--input-root',str(root),'--out',str(out)]
   with patch.object(c,'W',4),patch.object(c,'H',2),patch.object(c,'GRID',{'width':4,'height':2}),patch.object(sys,'argv',argv),patch.object(prefill,'validate_land_report',return_value=line),patch.object(prefill,'DIAGNOSTIC_RUN7_SHA',rh),contextlib.redirect_stdout(io.StringIO()):
    prefill.main();self.assertEqual(np.fromfile(out/'prefill-runs.u32le',dtype='<u4').tolist(),[4,0,4,18])
    for i,values in enumerate(([4,1,4,18],[4,0,4,0])):
     (root/'land').write_bytes(np.array(values,dtype='<u4').tobytes());plan['rle_inputs']['land']['runs_sha256']=digest(root/'land');pp.write_text(json.dumps(plan));argv[-1]=str(base/f'bad-{i}')
     with self.assertRaises(ValueError):prefill.main()
