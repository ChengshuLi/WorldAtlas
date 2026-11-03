import contextlib, hashlib, io, json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import compose_direct as direct
import compose_full_water_grid as c


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

class DirectCompositionTest(unittest.TestCase):
    def test_final_grid_rejects_gaps_changes_and_overlaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root=base/'inputs';root.mkdir()
            def put(name, contents):
                p=root/name;p.write_bytes(contents);return p
            rows=put('rows',np.array([0,3,4],dtype='<u4').tobytes())
            runs=put('runs',np.array([1,2,3,0,4,0,4,18],dtype='<u4').tobytes())
            decision='a'*64
            preplan=put('prefill-plan',json.dumps({'land_input_kind':'direct-research','decision_revision_status':'draft',
                'decision_snapshot_sha256':decision,'decision_revision':'d1','entity_revision':'e1'}).encode())
            audit=put('audit',json.dumps({'schema':'worldatlas-v7-prefill-class-rle-audit-v1','status':'staged-not-published','land_input_kind':'direct-research',
                'source_plan_sha256':sha(preplan),'decision_snapshot_sha256':decision,'decision_revision':'d1','entity_revision':'e1',
                'output':{'rows_sha256':sha(rows),'runs_sha256':sha(runs)}}).encode())
            source={'prefill_rows_sha256':sha(rows),'prefill_runs_sha256':sha(runs),'decision_snapshot_sha256':decision,
                    'decision_revision':'d1','entity_revision':'e1'}
            tile=put('water.jsonl',b'{"row":0,"spans":[{"start":1,"end":4,"code":7,"rule_id":"ocean","member_id":"o"}]}\n')
            manifest={'schema':'worldatlas-full-water-assignment-tiles-v1','status':'complete','grid':{'width':4,'height':2},
                      'coverage':{'complete':True},'source':source,
                      'tiles':[{'path':tile.name,'sha256':sha(tile),'row_start':0,'row_end_exclusive':2}]}
            mp=put('water.json',json.dumps(manifest).encode())
            spec={}
            for name,p in [('rows',rows),('runs',runs),('audit',audit),('plan',preplan)]:
                spec[name+'_path']=p.name;spec[name+'_sha256']=sha(p)
            plan={'schema':'worldatlas-direct-final-plan-v1','grid':{'width':4,'height':2},'decision_revision_status':'draft',
                  'decision_snapshot_sha256':decision,'decision_revision':'d1','entity_revision':'e1','prefill':spec,
                  'water_layers':[{'layer_id':'ocean','manifest_path':mp.name,'manifest_sha256':sha(mp),
                                   'priority':1,'overrides':[],'allowed_codes':[7]}]}
            pp=root/'final-plan.json';pp.write_text(json.dumps(plan))
            def run(out, draft=True):
                argv=['compose','--allow-unverified-snapshot','--plan',str(pp),'--input-root',str(root),'--out',str(out)]
                if draft:argv.append('--allow-draft-snapshot')
                with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):direct.main()
            with patch.object(c,'W',4),patch.object(c,'H',2),patch.object(c,'GRID',{'width':4,'height':2}):
                with self.assertRaisesRegex(ValueError,'draft plan'):run(base/'no-draft',False)
                run(base/'out')
                self.assertEqual(np.fromfile(base/'out/runs.u32le',dtype='<u4').tolist(),[1,2,4,7,4,18])
                report=json.loads((base/'out/report.json').read_text());self.assertEqual(report['counts']['7'],3)
                # Removing the only layer must not leave residual water silently unclassified.
                bad={**plan,'water_layers':[]};pp.write_text(json.dumps(bad))
                with self.assertRaisesRegex(ValueError,'unassigned water'):run(base/'gap')
                self.assertFalse((base/'gap/report.json').exists())
                # Overlapping prefill water cannot be overwritten.
                tile.write_bytes(b'{"row":0,"spans":[{"start":0,"end":4,"code":7,"rule_id":"ocean","member_id":"o"}]}\n')
                manifest['tiles'][0]['sha256']=sha(tile);mp.write_text(json.dumps(manifest))
                plan['water_layers'][0]['manifest_sha256']=sha(mp);pp.write_text(json.dumps(plan))
                with self.assertRaisesRegex(ValueError,'already assigned'):run(base/'overlap')
                self.assertFalse((base/'overlap/report.json').exists())
                manifest['source']['decision_revision']='other';mp.write_text(json.dumps(manifest))
                plan['water_layers'][0]['manifest_sha256']=sha(mp);pp.write_text(json.dumps(plan))
                with self.assertRaisesRegex(ValueError,'not bound'):run(base/'bad-revision')
                self.assertFalse((base/'bad-revision').exists())

if __name__=='__main__':unittest.main()
