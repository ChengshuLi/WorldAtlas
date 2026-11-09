"""Synthetic real tile -> assembler -> actual shared prefill planner contract."""
import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import build_coastal_tile as tile
import assemble_coastal_tiles as combine
from test_coastal_core import snap
from test_helpers import rle

HERE=Path(__file__).resolve().parent
REPLAY=HERE if (HERE/'build_prefill_plan.py').is_file() else HERE.parent/'worldatlas-pr4-resume/scripts/water'
sys.path.append(str(REPLAY))
import build_prefill_plan as planner
import compose_full_water_grid as c

class CoastPlannerIntegration(unittest.TestCase):
 def test_real_tiles_assemble_into_planner_and_reject_unselected(self):
  width,height=360,180;grid={'width':width,'height':height,'step':1.0,'west':-180,'north':90}
  p=np.ones((height,width),dtype=np.uint32);land=np.ones_like(p);p[89,4]=p[89,6]=17;land[89,4]=17;land[89,6]=18
  pr,pu=rle(p);lr,lu=rle(land)
  snapshot=snap();snapshot.update(schema='worldatlas-geography-decision-draft-evidence-v1',source='neon-export',
      entity_revision={'id':'entities','status':'draft'},basins=[{'id':'b1','source_id':'src','source_version':'v1','source_feature_id':'1',
      'geometry_sha256':'a'*64,'assignment_method':'single_continent_named_basin','participant_entity_ids':[1]}],
      sources=[{'source_id':'src','version':'v1','sha256':'b'*64}])
  snapshot['policies'].append({'id':'order','kind':'layer_precedence','evidence':{'execution_status':'selected_for_research'},
    'definition':{'priorities':{'coastal-band':1,'named-b1':2},'allowed_overrides':[]}})
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'inputs';root.mkdir();sp=root/'snapshot.json';sp.write_text(json.dumps(snapshot));ph=tile.sha(sp)
   def put(name,data):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return path
   prp=put('physical/rows.u32le',pr.tobytes());pup=put('physical/runs.u32le',pu.tobytes())
   lrp=put('land-build/land/rows.u32le',lr.tobytes());lup=put('land-build/land/runs.u32le',lu.tobytes())
   physical_report={'status':'candidate-only','grid':grid,'output_sha256':{'rows.u32le':tile.sha(prp),'runs.u32le':tile.sha(pup)}}
   pp=put('physical-report.json',json.dumps(physical_report).encode())
   land_cfg={'grid':grid,'snapshot':{'sha256':ph},'physical_rows':{'sha256':tile.sha(prp)},'physical_runs':{'sha256':tile.sha(pup)}}
   lc=put('land-build/config.json',json.dumps(land_cfg).encode())
   builder=put('land-build/component-builder',b'builder');cr=put('land-build/verified-component-rows.u32le',b'component-rows');cu=put('land-build/verified-component-runs.u32le',b'component-runs')
   land_report={'schema':'direct-neon-land-build-report-v1','status':'unverified-research-not-published','config_sha256':tile.sha(lc),
     'snapshot_sha256':ph,'decision_revision':'draft','decision_revision_asserted_status':'draft','entity_revision':'entities',
     'component_verification':{'builder_source_sha256':'1'*64,'builder_binary_sha256':tile.sha(builder),'compiler_version':'test','builder_output':'test',
                               'rows_sha256':tile.sha(cr),'runs_sha256':tile.sha(cu)},
     'compiler_report':{'schema':'land-decision-compiler-prototype-report-v1','input_sha256':{'physical_rows':tile.sha(prp),'physical_runs':tile.sha(pup),
                          'component_rows':tile.sha(cr),'component_runs':tile.sha(cu)},'output_rows_sha256':tile.sha(lrp),'output_runs_sha256':tile.sha(lup)}}
   lp=put('land-build/report.json',json.dumps(land_report).encode())
   pins={'physical_rows_sha256':tile.sha(prp),'physical_runs_sha256':tile.sha(pup),'physical_report_sha256':tile.sha(pp),
         'land_rows_sha256':tile.sha(lrp),'land_runs_sha256':tile.sha(lup),'land_report_sha256':tile.sha(lp)}
   entries=[]
   for i,(x0,x1) in enumerate(((0,180),(180,360))):
    out=root/f'coast-tile-{i}';tile.run(snapshot,ph,(pr,pu),(lr,lu),out,width,height,[x0,x1,0,height],180,pins,allow_selected_research=True)
    entries.append({'manifest_path':f'coast-tile-{i}/manifest.json','manifest_sha256':tile.sha(out/'manifest.json')})
   coast=root/'coast.json';coast.write_text(json.dumps(combine.assemble(snapshot,ph,entries,root,coast,width,height,allow_selected_research=True)))
   basin_file=put('basin.jsonl',b'');basin_manifest={'schema':'worldatlas-full-water-assignment-tiles-v1','status':'complete',
      'grid':{'width':width,'height':height},'coverage':{'complete':True},'tiles':[{'core_rows':[0,height],'core_cols':[0,width],
      'span_file':{'path':basin_file.name,'sha256':tile.sha(basin_file)}}],
      'source':{'decision_id':'b1','assignment_method':'single_continent_named_basin','source_id':'src','source_version':'v1','source_feature_id':'1',
       'source_file_sha256':'b'*64,'canonical_geometry_sha256':'a'*64,'physical_rows_sha256':tile.sha(prp),'physical_runs_sha256':tile.sha(pup),
       'policy_sha256':ph,'decision_revision':'draft','entity_revision':'entities'}}
   bm=put('basin.json',json.dumps(basin_manifest).encode())
   config={'rle_inputs':{'physical':{'rows_path':str(prp),'runs_path':str(pup),'rows_sha256':tile.sha(prp),'runs_sha256':tile.sha(pup),
                                     'report_path':str(pp),'report_sha256':tile.sha(pp)},
                         'land':{'rows_path':str(lrp),'runs_path':str(lup),'rows_sha256':tile.sha(lrp),'runs_sha256':tile.sha(lup),
                                 'report_path':str(lp),'report_sha256':tile.sha(lp)}},
      'coastal_band':{'manifest_path':str(coast),'manifest_sha256':tile.sha(coast)},
      'basins':[{'decision_id':'b1','manifest_path':str(bm),'manifest_sha256':tile.sha(bm)}]}
   cfg=put('config.json',json.dumps(config).encode())
   with patch.object(c,'W',width),patch.object(c,'H',height),patch.object(c,'GRID',{'width':width,'height':height}):
    plan=planner.assemble(config,cfg,root,snapshot,sp,Path(d)/'plan.json',allow_draft=True)
    self.assertEqual([z['layer_id'] for z in plan['water_layers']],['coastal-band','named-b1'])
    bad=copy.deepcopy(snapshot);bad['policies'][0]['evidence']['execution_status']='research_only_not_selected'
    with self.assertRaisesRegex(ValueError,'research selection'):planner.coastline_policy(bad)
    bad_coast=json.loads(coast.read_text());bad_coast['source']['land_report_sha256']='0'*64;coast.write_text(json.dumps(bad_coast))
    config['coastal_band']['manifest_sha256']=tile.sha(coast)
    with self.assertRaisesRegex(ValueError,'lineage mismatch'):planner.assemble(config,cfg,root,snapshot,sp,Path(d)/'bad.json',allow_draft=True)

if __name__=='__main__':unittest.main()
