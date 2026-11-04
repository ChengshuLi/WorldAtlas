import contextlib, hashlib, io, json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import build_prefill as prefill
import build_prefill_plan as plans
import compose_full_water_grid as c


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


class PrefillPlanTest(unittest.TestCase):
    def test_selected_layers_connect_to_prefill(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp); root=base/'inputs'; root.mkdir()
            def put(path, data):
                p=root/path; p.write_bytes(data); return p
            rows=np.array([0,1,2],dtype='<u4').tobytes(); rles={}
            for key,values in [('physical',[4,1,4,17]),('v6',[4,8,4,18])]:
                rp=put(key+'-rows',rows); up=put(key+'-runs',np.array(values,dtype='<u4').tobytes())
                rles[key]={'rows_path':rp.name,'runs_path':up.name,'rows_sha256':sha(rp),'runs_sha256':sha(up)}
            policy={'schema':'worldatlas-geography-decision-export-v1','source':'neon-export',
                    'decision_revision':{'id':'d1','status':'accepted','entity_revision':'e1'},
              'entity_revision':{'id':'e1','status':'accepted'},
                    'category_bindings':[{'entity_id':101,'code':6,'physical_class':'water'}],
                    'basins':[{'id':'b1','source_id':'s1','source_version':'v1','source_feature_id':'123','geometry_sha256':'a'*64,'assignment_method':'single_continent_named_basin','participant_entity_ids':[101]}],
                    'sources':[{'source_id':'s1','version':'v1','sha256':'b'*64},{'source_id':'coast-src','version':'v1','sha256':'c'*64}],
                    'policies':[{'id':'p1','kind':'layer_precedence','definition':{
                        'priorities':{'coastal-band':1,'named-b1':10},
                        'allowed_overrides':[{'winner':'named-b1','loser':'coastal-band'}]}},
                        {'id':'coast-policy','kind':'coastline_assignment','definition':{'source_id':'coast-src','source_version':'v1','method':'nearest','parameters':{'distance':12}}}]}
            policy_path=base/'snapshot.json';policy_path.write_text(json.dumps(policy));policy_hash=sha(policy_path)
            def layer(name,spans,source=None):
                tile=put(name+'.jsonl',(json.dumps({'row':0,'spans':spans})+'\n').encode())
                m={'schema':'worldatlas-full-water-assignment-tiles-v1','status':'complete','grid':{'width':4,'height':2},
                   'coverage':{'complete':True},'tiles':[{'path':tile.name,'sha256':sha(tile),'row_start':0,'row_end_exclusive':2}]}
                m['source']={'decision_id':'coast-policy','source_id':'coast-src','source_version':'v1','source_file_sha256':'c'*64,'assignment_method':'nearest','parameters':{'distance':12},'physical_rows_sha256':rles['physical']['rows_sha256'],'physical_runs_sha256':rles['physical']['runs_sha256'],'policy_sha256':policy_hash,'decision_revision':'d1','entity_revision':'e1'}
                if source: m['source']={'decision_id':'b1','assignment_method':'single_continent_named_basin','source_id':'s1','source_version':'v1','source_feature_id':'123','source_file_sha256':'b'*64,
                    'physical_rows_sha256':rles['physical']['rows_sha256'],'physical_runs_sha256':rles['physical']['runs_sha256'],
                    'canonical_geometry_sha256':'a'*64,'policy_sha256':policy_hash,'decision_revision':'d1','entity_revision':'e1'}
                mp=put(name+'.json',json.dumps(m).encode());return {'manifest_path':mp.name,'manifest_sha256':sha(mp)}
            coast=layer('coast',[{'start':0,'end':2,'code':2,'rule_id':'coast','member_id':'coast'}])
            basin=layer('basin',[{'start':1,'end':3,'code':6,'rule_id':'basin','member_id':'b1'}],True);basin['decision_id']='b1'
            config={'rle_inputs':rles,'coastal_band':coast,'basins':[basin]};config_path=put('inputs.json',json.dumps(config).encode())
            plan_path=base/'plan.json'
            with patch.object(c,'W',4),patch.object(c,'H',2),patch.object(c,'GRID',{'width':4,'height':2}):
                with self.assertRaisesRegex(ValueError,'historical V6 replay requires explicit opt-in'):
                    plans.assemble(config,config_path,root,policy,policy_path,base/'historical-default')
                result=plans.assemble(config,config_path,root,policy,policy_path,plan_path,allow_historical_v6=True);plan_path.write_text(json.dumps(result))
                output=base/'prefill';argv=['build_prefill','--allow-unverified-snapshot','--allow-historical-v6','--plan',str(plan_path),'--input-root',str(root),'--out',str(output)]
                with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()): prefill.main()
                self.assertEqual(np.fromfile(output/'prefill-runs.u32le',dtype='<u4').tolist(),[1,2,3,6,4,0,4,18])
                audit=json.loads((output/'prefill-audit.json').read_text())
                self.assertEqual((audit['decision_revision'],audit['entity_revision'],audit['decision_snapshot_sha256']),('d1','e1',policy_hash))
                for invalid in ([],[basin,basin],[{**basin,'decision_id':'bad'}]):
                    with self.assertRaisesRegex(ValueError,'exactly match'):
                        plans.assemble({**config,'basins':invalid},config_path,root,policy,policy_path,base/'bad',allow_historical_v6=True)
                bad_coast_path=root/'bad-coast.json'; bad_coast=json.loads((root/'coast.json').read_text())
                bad_coast['source']['parameters']['distance']=13; bad_coast_path.write_text(json.dumps(bad_coast))
                with self.assertRaisesRegex(ValueError,'coastal manifest source or assignment decision mismatch'):
                    plans.assemble({**config,'coastal_band':{'manifest_path':bad_coast_path.name,'manifest_sha256':sha(bad_coast_path)}},config_path,root,policy,policy_path,base/'bad-coast-plan',allow_historical_v6=True)
                for definition in ({'priorities':{'coastal-band':1},'allowed_overrides':[]},
                                   {'priorities':{'coastal-band':1,'named-b1':10},'allowed_overrides':[{'winner':'coastal-band','loser':'named-b1'}]},
                                   {'priorities':{'coastal-band':1,'named-b1':10},'allowed_overrides':[{'winner':'named-b1','loser':'coastal-band'}]*2}):
                    bad_policy={**policy,'policies':[{'kind':'layer_precedence','definition':definition},policy['policies'][1]]}
                    with self.assertRaises(ValueError): plans.assemble(config,config_path,root,bad_policy,policy_path,base/'bad-precedence',allow_historical_v6=True)
                # Shared-nearest tie decisions are not implemented by the candidate generator.
                unsupported=json.loads(json.dumps(policy))
                unsupported['basins'][0]['assignment_method']='shared_nearest_assigned_shore'
                unsupported['basins'][0]['tie_rules']={'method':'within_minimum_distance_tolerance', 'tolerance_metres':'0.00001'}
                with self.assertRaisesRegex(ValueError,'shared shoreline metric requires explicit draft research opt-in'):
                    plans.assemble(config,config_path,root,unsupported,policy_path,base/'unsupported',allow_historical_v6=True)
                # A manifest built with a different geographic rule is not interchangeable.
                bad_method_path=root/'bad-method.json'; bad_method=json.loads((root/'basin.json').read_text())
                bad_method['source']['assignment_method']='shared_nearest_assigned_shore'
                bad_method_path.write_text(json.dumps(bad_method))
                bad_method_basin={**basin,'manifest_path':bad_method_path.name,'manifest_sha256':sha(bad_method_path)}
                with self.assertRaisesRegex(ValueError,'manifest source does not match'):
                    plans.assemble({**config,'basins':[bad_method_basin]},config_path,root,policy,policy_path,base/'method-plan',allow_historical_v6=True)
                # A pinned but partial layer must not silently omit ungenerated cells.
                partial_path=root/'partial.json'; partial=json.loads((root/'basin.json').read_text())
                partial['coverage']={'complete':False}; partial_path.write_text(json.dumps(partial))
                partial_basin={**basin,'manifest_path':partial_path.name,'manifest_sha256':sha(partial_path)}
                with self.assertRaisesRegex(ValueError,'complete coverage'):
                    plans.assemble({**config,'basins':[partial_basin]},config_path,root,policy,policy_path,base/'partial-plan',allow_historical_v6=True)
                # Direct land must bind the same physical inputs and decision snapshot.
                ld=root/'land-build';(ld/'land').mkdir(parents=True)
                lr=ld/'land/rows.u32le';lu=ld/'land/runs.u32le'
                lr.write_bytes(rows);lu.write_bytes(np.array([4,1,4,18],dtype='<u4').tobytes())
                report={'schema':'direct-neon-land-build-report-v1','status':'unverified-research-not-published',
                    'snapshot_sha256':policy_hash,'decision_revision':'d1','decision_revision_asserted_status':'accepted',
                    'entity_revision':'e1','component_verification':{'builder_source_sha256':'a'*64,'builder_binary_sha256':'b'*64,
                        'compiler_version':'test','builder_output':'test','rows_sha256':'c'*64,'runs_sha256':'d'*64},
                    'compiler_report':{'schema':'land-decision-compiler-prototype-report-v1',
                        'input_sha256':{'physical_rows':rles['physical']['rows_sha256'],
                                        'physical_runs':rles['physical']['runs_sha256'],
                                        'component_rows':'c'*64,'component_runs':'d'*64},
                        'output_rows_sha256':sha(lr),'output_runs_sha256':sha(lu)}}
                land_config={'grid':{'width':4,'height':2,'step':90.0,'west':-180,'north':90},
                    'snapshot':{'sha256':policy_hash},'physical_rows':{'sha256':rles['physical']['rows_sha256']},
                    'physical_runs':{'sha256':rles['physical']['runs_sha256']}}
                lcp=ld/'config.json';lcp.write_text(json.dumps(land_config));report['config_sha256']=sha(lcp)
                rp=ld/'report.json';rp.write_text(json.dumps(report))
                direct={'rows_path':str(lr.relative_to(root)),'runs_path':str(lu.relative_to(root)),
                        'rows_sha256':sha(lr),'runs_sha256':sha(lu),
                        'report_path':str(rp.relative_to(root)),'report_sha256':sha(rp)}
                direct_config={**config,'rle_inputs':{'physical':rles['physical'],'land':direct}}
                direct_plan=plans.assemble(direct_config,config_path,root,policy,policy_path,base/'direct-plan.json')
                self.assertEqual(direct_plan['land_input_kind'],'direct-research')
                shifted={**land_config,'grid':{**land_config['grid'],'west':-179}}
                lcp.write_text(json.dumps(shifted));shift_report={**report,'config_sha256':sha(lcp)};rp.write_text(json.dumps(shift_report))
                shifted_input={**direct,'report_sha256':sha(rp)}
                with self.assertRaisesRegex(ValueError,'configuration grid or input mismatch'):
                    plans.assemble({**direct_config,'rle_inputs':{'physical':rles['physical'],'land':shifted_input}},config_path,root,policy,policy_path,base/'shifted')
                lcp.write_text(json.dumps(land_config));rp.write_text(json.dumps(report))
                dp=base/'direct-plan.json';dp.write_text(json.dumps(direct_plan))
                with patch.object(sys,'argv',['build_prefill','--allow-unverified-snapshot','--allow-historical-v6','--plan',str(dp),'--input-root',str(root),'--out',str(base/'direct-out')]),contextlib.redirect_stdout(io.StringIO()):
                    prefill.main()
                self.assertEqual(np.fromfile(base/'direct-out/prefill-runs.u32le',dtype='<u4').tolist(),[1,2,3,6,4,0,4,18])
                # A shared basin requires the exact draft tie rules and the same direct land grid.
                draft=json.loads(json.dumps(policy));draft['schema']='worldatlas-geography-decision-draft-evidence-v1'
                draft['decision_revision']['status']='draft';draft['entity_revision']['status']='draft'
                for record in draft['policies']:record['evidence']={'execution_status':'selected_for_research'}
                draft['category_bindings'] += [{'entity_id':102,'code':5,'physical_class':'water'},
                    {'entity_id':101,'code':22,'physical_class':'land'},{'entity_id':102,'code':21,'physical_class':'land'}]
                tie={'method':'within_minimum_distance_tolerance','tie_break':'first_entity_in_priority_order',
                     'priority_entity_ids':[101,102],'tolerance_metres':'0.00001'}
                draft['basins'][0].update({'assignment_method':'shared_nearest_assigned_shore',
                                           'participant_entity_ids':[101,102],'tie_rules':tie})
                draft_path=root/'draft.json';draft_path.write_text(json.dumps(draft));dh=sha(draft_path)
                draft_report=json.loads(json.dumps(report));draft_report['snapshot_sha256']=dh;draft_report['decision_revision_asserted_status']='draft'
                draft_config={**land_config,'snapshot':{'sha256':dh}};lcp.write_text(json.dumps(draft_config));draft_report['config_sha256']=sha(lcp)
                dr=ld/'draft-report.json';dr.write_text(json.dumps(draft_report))
                draft_land={**direct,'report_path':str(dr.relative_to(root)),'report_sha256':sha(dr)}
                dc=json.loads((root/'coast.json').read_text());dc['source']['policy_sha256']=dh
                dcp=root/'draft-coast.json';dcp.write_text(json.dumps(dc))
                db=json.loads((root/'basin.json').read_text());db['source'].update({'policy_sha256':dh,
                    'assignment_method':'shared_nearest_assigned_shore','decision_status':'draft','tie_rules':tie,
                    'land_rows_sha256':sha(lr),'land_runs_sha256':sha(lu)})
                db['physical_water_cells']=2;db['algorithm_sha256']='a'*64
                db['nearest_assignment_audit']={'shore_method':'spherical-grid-edge-v1 (research, not an approved decision)',
                    'certified_bound_cells':1,'exact_distance_cells':1,'shared_nearest_sha256':'b'*64,'spherical_shore_sha256':'c'*64}
                dbp=root/'draft-basin.json';dbp.write_text(json.dumps(db))
                draft_cfg={**config,'rle_inputs':{'physical':rles['physical'],'land':draft_land},
                    'coastal_band':{'manifest_path':dcp.name,'manifest_sha256':sha(dcp)},
                    'basins':[{'decision_id':'b1','manifest_path':dbp.name,'manifest_sha256':sha(dbp)}]}
                with self.assertRaisesRegex(ValueError,'research opt-in'):
                    plans.assemble(draft_cfg,config_path,root,draft,draft_path,base/'draft-plan',allow_draft=True)
                bad_policy=json.loads(json.dumps(draft));bad_policy['policies'][1]['evidence']['execution_status']='research_only_not_selected'
                with self.assertRaisesRegex(ValueError,'policy requires explicit research selection'):
                    plans.assemble(draft_cfg,config_path,root,bad_policy,draft_path,base/'bad-policy',allow_draft=True,allow_research_shore=True)
                draft_plan=plans.assemble(draft_cfg,config_path,root,draft,draft_path,base/'draft-plan',allow_draft=True,allow_research_shore=True)
                self.assertEqual(draft_plan['research_shore_method'],'spherical-grid-edge-v1')
                db['source']['tie_rules']={**tie,'tolerance_metres':'0.1'};dbp.write_text(json.dumps(db))
                draft_cfg['basins'][0]['manifest_sha256']=sha(dbp)
                with self.assertRaisesRegex(ValueError,'research method or land binding mismatch'):
                    plans.assemble(draft_cfg,config_path,root,draft,draft_path,base/'bad-tie',allow_draft=True,allow_research_shore=True)
                lcp.write_text(json.dumps(land_config))
                report['compiler_report']['input_sha256']['physical_runs']='0'*64;rp.write_text(json.dumps(report))
                bad={**direct,'report_sha256':sha(rp)}
                with self.assertRaisesRegex(ValueError,'direct land report does not bind'):
                    plans.assemble({**direct_config,'rle_inputs':{'physical':rles['physical'],'land':bad}},config_path,root,policy,policy_path,base/'bad-direct')
                # A report changed after planning is rejected before output creation.
                with patch.object(sys,'argv',['build_prefill','--allow-unverified-snapshot','--allow-historical-v6','--plan',str(dp),'--input-root',str(root),'--out',str(base/'changed-report')]),contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(ValueError,'report hash mismatch'):prefill.main()
                self.assertFalse((base/'changed-report').exists())
                # A pinned direct grid may not turn physical water into land.
                report['compiler_report']['input_sha256']['physical_runs']=rles['physical']['runs_sha256']
                lu.write_bytes(np.array([4,18,4,18],dtype='<u4').tobytes())
                report['compiler_report']['output_runs_sha256']=sha(lu);rp.write_text(json.dumps(report))
                invalid_land={**direct,'runs_sha256':sha(lu),'report_sha256':sha(rp)}
                bad_grid=plans.assemble({**direct_config,'rle_inputs':{'physical':rles['physical'],'land':invalid_land}},config_path,root,policy,policy_path,base/'bad-grid-plan.json')
                gp=base/'bad-grid-plan.json';gp.write_text(json.dumps(bad_grid))
                with patch.object(sys,'argv',['build_prefill','--allow-unverified-snapshot','--allow-historical-v6','--plan',str(gp),'--input-root',str(root),'--out',str(base/'bad-grid')]),contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(ValueError,'disagrees with physical water'):prefill.main()
                wrong=json.loads(json.dumps(result));wrong['water_layers'][1]['allowed_codes']=[5];wp=base/'wrong.json';wp.write_text(json.dumps(wrong))
                with patch.object(sys,'argv',['build_prefill','--allow-unverified-snapshot','--allow-historical-v6','--plan',str(wp),'--input-root',str(root),'--out',str(base/'bad-code')]),contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(ValueError,'not allowed by selected basin policy'):prefill.main()


if __name__=='__main__': unittest.main()
