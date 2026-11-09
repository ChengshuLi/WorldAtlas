"""Connect actual research ocean partition, closed-water classifier, and composer."""
import contextlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'stages'/'ocean'))
import ocean_fill_runner as ocean
import streaming_closed_water as closed
import compose_direct,compose_full_water_grid as common
from test_closed_water_core import policy_snapshot
from test_helpers import rle

class OceanClosedPipeline(unittest.TestCase):
 def test_actual_partition_to_closed_and_composer(self):
  w,h=12,5; physical=np.full((h,w),17,dtype=np.uint32); prefill=physical.copy();land=physical.copy()
  for x in (0,3,6,9):physical[0,x]=1;prefill[0,x]=0;land[0,x]=1
  physical[2,1]=1;prefill[2,1]=0;land[2,1]=1
  pr,pu=rle(physical);qr,qu=rle(prefill);lr,lu=rle(land);snapshot=policy_snapshot();snapsha='a'*64
  snapshot.update({'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','entity_revision':{'id':'entities','status':'draft'}})
  snapshot['endpoints']=[{'endpoint_id':'rtop','longitude':'-30','latitude':'90'},{'endpoint_id':'rbottom','longitude':'-30','latitude':'-60'}];snapshot['routes']=[{'route_id':'r0','route_type':'meridian','parameters':{},'points':[{'ordinal':0,'endpoint_id':'rtop'},{'ordinal':1,'endpoint_id':'rbottom'}]}];snapshot['ocean_seeds']=[]
  for i,x in enumerate((0,3,6,9)):
   eid=100+i;sid=f's{i}';snapshot['endpoints'].append({'endpoint_id':sid,'longitude':str(-180+(x+0.5)*30),'latitude':'75'})
   snapshot['ocean_seeds'].append({'seed_id':sid,'endpoint_id':sid,'entity_id':eid});snapshot['category_bindings'].append({'code':7+i,'entity_id':eid,'physical_class':'water'})
  snapshot['policies'].append({'id':'ocean','kind':'ocean_fill','evidence':{'execution_status':'selected_for_research'},'definition':{'connectivity':4,'wrap_longitude':True,'barrier_tie_rule':'left-of-oriented-route','unseeded_policy':'report-only','route_ids':['r0'],'seed_ids':['s0','s1','s2','s3']}})
  with tempfile.TemporaryDirectory() as td:
   base=Path(td);root=base/'in';root.mkdir()
   def put(name,data):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return path
   prp=put('physical-rows',pr.tobytes());pup=put('physical-runs',pu.tobytes());qrp=put('prefill-rows',qr.tobytes());qup=put('prefill-runs',qu.tobytes())
   preplan=put('prefill-plan.json',json.dumps({'land_input_kind':'direct-research','decision_revision_status':'draft','decision_snapshot_sha256':snapsha,'decision_revision':'draft','entity_revision':'entities','research_shore_method':None}).encode())
   audit=put('prefill-audit.json',json.dumps({'schema':'worldatlas-prefill-class-rle-audit-v1','status':'staged-not-published','land_input_kind':'direct-research','source_plan_sha256':closed.sha(preplan),'decision_snapshot_sha256':snapsha,'decision_revision':'draft','entity_revision':'entities','research_shore_method':None,'output':{'rows_sha256':closed.sha(qrp),'runs_sha256':closed.sha(qup)}}).encode())
   inputs={'physical_rows_sha256':closed.sha(prp),'physical_runs_sha256':closed.sha(pup),'prefill_rows_sha256':closed.sha(qrp),'prefill_runs_sha256':closed.sha(qup),'prefill_audit_sha256':closed.sha(audit)}
   ocean_out=root/'ocean';ocean.run(snapshot,snapsha,prp,pup,qrp,qup,ocean_out,w,h,inputs,tile_height=2,allow_draft=True)
   cuts=ocean_out/'barrier_edges.u32le';partition=ocean_out/'partition'/'manifest.json';rows=ocean_out/'partition'/'unseeded_rows.u64le';spans=ocean_out/'partition'/'unseeded_component_spans.u32le';inputs['source_cut_edges_sha256']=closed.sha(cuts)
   result=closed.run(snapshot,snapsha,(pr,pu),(qr,qu),(lr,lu),partition,rows,spans,cuts,root/'closed',w,h,180,inputs,allow_selected_research=True)
   self.assertEqual(result['assigned_cells'],1);self.assertEqual(result['pending_cells'],0)
   spec={}
   for key,path in [('rows',qrp),('runs',qup),('audit',audit),('plan',preplan)]:spec[key+'_path']=path.name;spec[key+'_sha256']=closed.sha(path)
   plan={'schema':'worldatlas-direct-final-plan-v1','grid':{'width':w,'height':h},'decision_snapshot_sha256':snapsha,'decision_revision':'draft','decision_revision_status':'draft','entity_revision':'entities','prefill':spec,'water_layers':[
     {'layer_id':'ocean','priority':1,'overrides':[],'allowed_codes':[7,8,9,10],'manifest_path':'ocean/ocean-layer-manifest.json','manifest_sha256':closed.sha(ocean_out/'ocean-layer-manifest.json')},
     {'layer_id':'closed','priority':2,'overrides':[],'allowed_codes':[1,2,3,4,5,6],'manifest_path':'closed/manifest.json','manifest_sha256':closed.sha(root/'closed/manifest.json')}]}
   fp=put('final-plan.json',json.dumps(plan).encode());argv=['compose','--plan',str(fp),'--input-root',str(root),'--out',str(base/'final'),'--allow-unverified-snapshot','--allow-draft-snapshot']
   with patch.object(common,'W',w),patch.object(common,'H',h),patch.object(common,'GRID',{'width':w,'height':h}),patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):compose_direct.main()
   report=json.loads((base/'final/report.json').read_text());self.assertEqual(sum(report['counts'][str(i)] for i in range(7,11)),4);self.assertEqual(report['counts']['1'],1)
if __name__=='__main__':unittest.main()
