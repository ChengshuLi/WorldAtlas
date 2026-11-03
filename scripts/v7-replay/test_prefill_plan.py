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
                result=plans.assemble(config,config_path,root,policy,policy_path,plan_path);plan_path.write_text(json.dumps(result))
                output=base/'prefill';argv=['build_prefill','--allow-unverified-snapshot','--plan',str(plan_path),'--input-root',str(root),'--out',str(output)]
                with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()): prefill.main()
                self.assertEqual(np.fromfile(output/'prefill-runs.u32le',dtype='<u4').tolist(),[1,2,3,6,4,0,4,18])
                audit=json.loads((output/'prefill-audit.json').read_text())
                self.assertEqual((audit['decision_revision'],audit['entity_revision'],audit['decision_snapshot_sha256']),('d1','e1',policy_hash))
                for invalid in ([],[basin,basin],[{**basin,'decision_id':'bad'}]):
                    with self.assertRaisesRegex(ValueError,'exactly match'):
                        plans.assemble({**config,'basins':invalid},config_path,root,policy,policy_path,base/'bad')
                bad_coast_path=root/'bad-coast.json'; bad_coast=json.loads((root/'coast.json').read_text())
                bad_coast['source']['parameters']['distance']=13; bad_coast_path.write_text(json.dumps(bad_coast))
                with self.assertRaisesRegex(ValueError,'coastal manifest source or assignment decision mismatch'):
                    plans.assemble({**config,'coastal_band':{'manifest_path':bad_coast_path.name,'manifest_sha256':sha(bad_coast_path)}},config_path,root,policy,policy_path,base/'bad-coast-plan')
                for definition in ({'priorities':{'coastal-band':1},'allowed_overrides':[]},
                                   {'priorities':{'coastal-band':1,'named-b1':10},'allowed_overrides':[{'winner':'coastal-band','loser':'named-b1'}]},
                                   {'priorities':{'coastal-band':1,'named-b1':10},'allowed_overrides':[{'winner':'named-b1','loser':'coastal-band'}]*2}):
                    bad_policy={**policy,'policies':[{'kind':'layer_precedence','definition':definition},policy['policies'][1]]}
                    with self.assertRaises(ValueError): plans.assemble(config,config_path,root,bad_policy,policy_path,base/'bad-precedence')
                # A manifest built with a different geographic rule is not interchangeable.
                bad_method_path=root/'bad-method.json'; bad_method=json.loads((root/'basin.json').read_text())
                bad_method['source']['assignment_method']='shared_nearest_assigned_shore'
                bad_method_path.write_text(json.dumps(bad_method))
                bad_method_basin={**basin,'manifest_path':bad_method_path.name,'manifest_sha256':sha(bad_method_path)}
                with self.assertRaisesRegex(ValueError,'manifest source does not match'):
                    plans.assemble({**config,'basins':[bad_method_basin]},config_path,root,policy,policy_path,base/'method-plan')
                # A pinned but partial layer must not silently omit ungenerated cells.
                partial_path=root/'partial.json'; partial=json.loads((root/'basin.json').read_text())
                partial['coverage']={'complete':False}; partial_path.write_text(json.dumps(partial))
                partial_basin={**basin,'manifest_path':partial_path.name,'manifest_sha256':sha(partial_path)}
                with self.assertRaisesRegex(ValueError,'complete coverage'):
                    plans.assemble({**config,'basins':[partial_basin]},config_path,root,policy,policy_path,base/'partial-plan')
                wrong=json.loads(json.dumps(result));wrong['water_layers'][1]['allowed_codes']=[5];wp=base/'wrong.json';wp.write_text(json.dumps(wrong))
                with patch.object(sys,'argv',['build_prefill','--allow-unverified-snapshot','--plan',str(wp),'--input-root',str(root),'--out',str(base/'bad-code')]),contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(ValueError,'not allowed by selected basin policy'):prefill.main()


if __name__=='__main__': unittest.main()
