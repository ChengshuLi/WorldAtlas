"""Real Bering source bridge/resolver and writer, with unrelated stage2/claims mocked."""
import hashlib,importlib.util,json,struct,sys,unittest
from pathlib import Path
from unittest.mock import patch
from test_mixed_driver import DriverTests,js,binfile,U,P,T
import apply_selected_mixed as driver
class RealOuterTests(unittest.TestCase):
 def test_real_bering_sources_to_writer(self):
  t=DriverTests('runTest');t.setUp();self.addCleanup(t.doCleanups);root=Path(__file__).resolve().parent.parent;d=root/'bering-two-source-adapter-20261104';sys.path.insert(0,str(d))
  def load(name,p):
   spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
  fm=load('synthetic_bering_source_fixture',d/'test_resolver.py');f=fm.Tests('runTest');f.setUp();self.addCleanup(f.doCleanups);am=load('synthetic_bering_decision_fixture',d/'test_adapter_v3.py');a=am.Tests('runTest');a.setUp();b=t.src
  streams={'physical_rows':binfile(b/'pr2',U,[0,2,3,4,5]),'physical_runs':binfile(b/'pv2',P,[(4,17),(8,1),(8,1),(8,1),(8,1)]),'component_rows':binfile(b/'cr2',U,[0,4,4,4,4]),'component_runs':binfile(b/'cv2',T,[(0,1,1),(1,2,2),(2,3,3),(3,4,4)])};rows=binfile(b/'base_rows2',U,[0,2,3,4,5]);runs=binfile(b/'base_runs2',P,[(4,18),(8,0),(8,0),(8,0),(8,0)]);grid={'width':8,'height':4,'west':-180,'north':90,'step':45};stage=t.cfg['stage2'];stage.update(rows=rows,runs=runs,physical_rows=streams['physical_rows'],physical_runs=streams['physical_runs']);report_path=Path(stage['report']['path']);report=json.loads(report_path.read_text());report.update(grid=grid,output_rows_sha256=rows['sha256'],output_runs_sha256=runs['sha256'],inputs_sha256={k:v['sha256'] for k,v in streams.items()});w=js(b/'bering-witness',{});stage['derived_manifest']=js(b/'bering-derived',{'artifacts':{'resolution_report':w}});report['resolution_report_sha256']=w['sha256'];stage['report']=js(report_path,report)
  pins={'baseline_report_sha256':stage['report']['sha256'],'baseline_rows_sha256':rows['sha256'],'baseline_runs_sha256':runs['sha256'],'baseline_decision_snapshot_sha256':stage['snapshot']['sha256'],**{k+'_sha256':v['sha256'] for k,v in streams.items()}};t.cfg['policy_pins']=pins;reqpath=Path(t.cfg['point_request']['path']);req=json.loads(reqpath.read_text());req.update(streams);req['grid']=grid;sp=Path(req['snapshot']['path']);snap=json.loads(sp.read_text());snap['schema']='worldatlas-geography-decision-draft-evidence-v3';snap['unsupported_affiliation_source_ref_table_present']=False;snap['unsupported_point_methods_present']=False;snap['affiliation_source_refs']=[];snap['polygon_corroboration_refs']=[];snap['list1_policy'].update(pins);snap['list1_policy']['affiliation_ids'].append('bering');snap['list1_policy']['entry_ids'].append('eb');snap['list1_entries'].append({'entry_id':'eb','decision_revision':'r','title':'Bering','reason':'test','old_list1_refs':[],'execution_status':'selected_for_research','affiliation_ids':['bering']});ba=dict(a.s['affiliations'][0]);ba.update(affiliation_id='bering',entity_id=3);snap['affiliations'].append(ba)
  for name in ('sources','source_lineage_assets'):
   for v in a.s[name]:
    z=dict(v);input_spec=f.inputs['label' if z['source_id']=='label' else 'ecoregion'];z.update(sha256=input_spec['sha256'],size_bytes=input_spec['size_bytes']);snap[name].append(z)
  feature=dict(a.s['features'][0]);feature.update(source_feature_id='42',geometry_sha256=hashlib.sha256(json.dumps(f.geom,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest());snap['features'].append(feature);ref=dict(a.s['ecoregion_source_refs'][0]);ref['affiliation_id']='bering';ref['contract']=dict(ref['contract'],layer='epa',selector_property='CODE',name_property='NAME',expected_feature_count=1);snap['ecoregion_source_refs']=[ref];req['snapshot']=js(sp,snap);t.point.update(snapshot_sha256=req['snapshot']['sha256'],input_sha256={k:v['sha256'] for k,v in streams.items()});t.point['claims'][0]['component_id']=3;t.cfg['point_request']=js(reqpath,req);t.poly.update(grid=grid,input_sha256={k:v['sha256'] for k,v in streams.items()});t.poly['claims'][0].update(component_ids=[4],intersection={'per_feature_root_inside_cells':[{'4':1}]})
  t.cfg['bering_source_files']=[{'source_id':k,'version':'v',**f.inputs['label' if k=='label' else 'ecoregion']} for k in ('label','epa')];import pyproj;db=(Path(pyproj.datadir.get_data_dir())/'proj.db').resolve();t.cfg['bering_proj_db']={'path':str(db),'sha256':hashlib.sha256(db.read_bytes()).hexdigest()}
  label_path=Path(f.inputs['label']['path']);original=label_path.read_bytes();label_path.write_bytes(bytes([original[0]^1])+original[1:])
  with patch.dict('os.environ',{'PROJ_NETWORK':'OFF'}),patch.object(driver.bering_bridge,'protected_roots',return_value={99}):
   with self.assertRaisesRegex(ValueError,'input hash mismatch'):t.runv()
  self.assertFalse((t.b/'out').exists());label_path.write_bytes(original)
  with patch.dict('os.environ',{'PROJ_NETWORK':'OFF'}),patch.object(driver.bering_bridge,'protected_roots',return_value={1,99}):
   with self.assertRaisesRegex(ValueError,'empty or duplicate Bering roots'):t.runv()
  self.assertFalse((t.b/'out').exists())
  with patch.dict('os.environ',{'PROJ_NETWORK':'OFF'}),patch.object(driver.bering_bridge,'protected_roots',return_value={99}):t.runv()
  out=json.loads((t.b/'out/report.json').read_text());self.assertEqual(out['bering_resolution']['claims'][0]['component_ids'],[1]);self.assertEqual(out['bering_component_extents']['bering']['1']['ecoregion_inside_cells'],1);self.assertEqual(out['writer']['affiliation_statistics']['bering']['applied_cells'],1);self.assertEqual(out['writer']['changed_cells'],3)
if __name__=='__main__':unittest.main()
