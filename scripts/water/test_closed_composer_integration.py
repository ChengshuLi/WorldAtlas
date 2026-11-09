"""Synthetic closed-water output consumed by the actual direct composer."""
import contextlib,io,json,struct,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import streaming_closed_water as stream
from test_closed_water_core import policy_snapshot
from test_helpers import rle
HERE=Path(__file__).resolve().parent
REPLAY=HERE if (HERE/'build_prefill_plan.py').is_file() else HERE.parent/'worldatlas-pr4-resume/scripts/water';sys.path.append(str(REPLAY))
import compose_direct,compose_full_water_grid as c

class ComposerTest(unittest.TestCase):
 def test_closed_layer_composes_and_pending_layer_is_rejected(self):
  w,h=4,3;p=np.full((h,w),17,dtype=np.uint32);q=p.copy();land=p.copy();p[1,1]=1;q[1,1]=0;land[1,1]=1
  pr,pu=rle(p);qr,qu=rle(q);lr,lu=rle(land);snapshot=policy_snapshot();snapsha='a'*64
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);root=base/'inputs';root.mkdir()
   def put(name,data):
    f=root/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data);return f
   prp=put('physical-rows',pr.tobytes());pup=put('physical-runs',pu.tobytes());qrp=put('prefill-rows',qr.tobytes());qup=put('prefill-runs',qu.tobytes())
   preplan=put('prefill-plan.json',json.dumps({'land_input_kind':'direct-research','decision_revision_status':'draft',
       'decision_snapshot_sha256':snapsha,'decision_revision':'draft','entity_revision':'entities','research_shore_method':None}).encode())
   audit=put('prefill-audit.json',json.dumps({'schema':'worldatlas-prefill-class-rle-audit-v1','status':'staged-not-published',
      'land_input_kind':'direct-research','source_plan_sha256':stream.sha(preplan),'decision_snapshot_sha256':snapsha,'decision_revision':'draft',
      'entity_revision':'entities','research_shore_method':None,'output':{'rows_sha256':stream.sha(qrp),'runs_sha256':stream.sha(qup)}}).encode())
   cuts=put('barrier',b'');offsets=[0,0,1,1];rows=put('unseeded_rows.u64le',struct.pack('<4Q',*offsets));spans=put('unseeded_component_spans.u32le',struct.pack('<III',1,2,1))
   inputs={'physical_rows_sha256':stream.sha(prp),'physical_runs_sha256':stream.sha(pup),'prefill_rows_sha256':stream.sha(qrp),
      'prefill_runs_sha256':stream.sha(qup),'prefill_audit_sha256':stream.sha(audit),'source_cut_edges_sha256':stream.sha(cuts)}
   part={'schema':'fresh-ocean-run-partition-v1','grid':{'W':w,'H':h},'inputs':{**inputs,'decision_snapshot_sha256':snapsha,
        'decision_revision':'draft','entity_revision':'entities','legacy_ocean_label_inheritance':False},'unseeded_cell_count':1,
        'unseeded_span_count':1,'components':[{'component_root':1,'ocean_code':None,'cell_count':1,'source_barrier_contact_edge_count':0}]}
   partition=put('partition.json',json.dumps(part).encode());closed=root/'closed'
   m=stream.run(snapshot,snapsha,(pr,pu),(qr,qu),(lr,lu),partition,rows,spans,cuts,closed,w,h,180,inputs,allow_selected_research=True)
   self.assertTrue(m['coverage']['complete']);self.assertEqual(m['source']['decision_snapshot_sha256'],snapsha)
   spec={}
   for key,path in [('rows',qrp),('runs',qup),('audit',audit),('plan',preplan)]:spec[key+'_path']=path.name;spec[key+'_sha256']=stream.sha(path)
   final={'schema':'worldatlas-direct-final-plan-v1','grid':{'width':w,'height':h},'decision_snapshot_sha256':snapsha,
      'decision_revision':'draft','decision_revision_status':'draft','entity_revision':'entities','prefill':spec,
      'water_layers':[{'layer_id':'closed','priority':1,'overrides':[],'allowed_codes':[1,2,3,4,5,6],
                       'manifest_path':'closed/manifest.json','manifest_sha256':stream.sha(closed/'manifest.json')}]}
   fp=put('final-plan.json',json.dumps(final).encode());argv=['compose','--plan',str(fp),'--input-root',str(root),'--out',str(base/'final'),
       '--allow-unverified-snapshot','--allow-draft-snapshot']
   with patch.object(c,'W',w),patch.object(c,'H',h),patch.object(c,'GRID',{'width':w,'height':h}),patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):
    compose_direct.main()
   self.assertTrue((base/'final/report.json').exists())
   # An unresolved component is never presented as complete to the composer.
   m['status']='partial';m['coverage']['complete']=False;(closed/'manifest.json').write_text(json.dumps(m))
   final['water_layers'][0]['manifest_sha256']=stream.sha(closed/'manifest.json');fp.write_text(json.dumps(final));argv[argv.index(str(base/'final'))]=str(base/'bad')
   with patch.object(c,'W',w),patch.object(c,'H',h),patch.object(c,'GRID',{'width':w,'height':h}),patch.object(sys,'argv',argv):
    with self.assertRaisesRegex(ValueError,'not a completed candidate'):compose_direct.main()

if __name__=='__main__':unittest.main()
