import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np
import compile_land as c

HERE=Path(__file__).resolve().parent

def data(path, values):
    np.asarray(values,dtype='<u4').tofile(path)
    return pin(path)

def sha_file(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def pin(path):
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def polygon(fid, x0, x1):
    return {'type':'Feature','properties':{'id':fid},'geometry':{'type':'Polygon','coordinates':[[[x0,0],[x1,0],[x1,2],[x0,2],[x0,0]]]}}

class DirectLand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compile_tmp=tempfile.TemporaryDirectory()
        cls.component_binary=Path(cls.compile_tmp.name)/'components'
        subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(HERE.parent/'build_components.cpp'),'-o',str(cls.component_binary)],check=True)
    @classmethod
    def tearDownClass(cls): cls.compile_tmp.cleanup()
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); self.base=Path(self.t.name);self.d=self.base/'inputs';self.d.mkdir();self.out=self.base/'out'
        # Grid x=[0..5], two components: x=0,1 and x=3,4, both continuous for two rows.
        pr=data(self.d/'pr',[0,4,8]); pv=data(self.d/'pv',[2,17,3,1,5,17,6,1]*2)
        subprocess.run([str(self.component_binary),'6','2',pr['path'],pv['path'],str(self.d/'cr'),str(self.d/'cv')],check=True,capture_output=True)
        self.features=[polygon('left',-3,-2),polygon('middle',-2,-1),polygon('whole',0,2)]
        self.source=self.d/'source.geojson'; self.write_source()
        self.snap={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export',
          'decision_revision':{'id':'test-rev','status':'draft','entity_revision':'entity-rev'},
          'entity_revision':{'id':'entity-rev','status':'draft'},
          'sources':[{'source_id':'source','version':'v1','sha256':pin(self.source)['sha256']}],
          'features':[{'feature_id':f['properties']['id'],'source_id':'source','source_version':'v1','source_feature_id':f['properties']['id'],'geometry_sha256':c.geometry_hash(f['geometry'])} for f in self.features],
          'entities':[{'id':101},{'id':102},{'id':103}],
          'category_bindings':[{'entity_id':101,'physical_class':'land','code':17},{'entity_id':102,'physical_class':'land','code':18},{'entity_id':103,'physical_class':'land','code':19}],
          'land_component_witness_rules':[],
          'affiliations':[self.aff('a','left',101,'component_partition_v1',{'component_witness':{'lon':'-2.5','lat':'1.5'}}),
                          self.aff('b','middle',102,'component_partition_v1',{'component_witness':{'lon':'-2.5','lat':'1.5'}}),
                          self.aff('c','whole',103,'component_intersection_v1',{'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[]})]}
        self.snapfile=self.d/'snapshot.json'; self.write_snapshot()
        self.cfg={'schema':'direct-neon-land-build-v1','snapshot':pin(self.snapfile), 'grid':{'width':6,'height':2,'step':1,'west':-3,'north':2},
                  'physical_rows':pr,'physical_runs':pv,'component_rows':pin(self.d/'cr'),'component_runs':pin(self.d/'cv'),
                  'source_files':[{'source_id':'source','source_version':'v1','file':pin(self.source),'id_property':'id'}], 'strip_rows':1}
    def tearDown(self): self.t.cleanup()
    def aff(self,aid,feature,entity,method,selector):
        return {'affiliation_id':aid,'feature_id':feature,'entity_id':entity,'relationship':'affiliation','scope':'land',
                'method':method,'rationale':'synthetic only','evidence':{'execution_status':'selected_for_research','selector':selector}}
    def write_source(self): self.source.write_text(json.dumps({'type':'FeatureCollection','features':self.features}))
    def write_snapshot(self): self.snapfile.write_text(json.dumps(self.snap))
    def refresh_snapshot(self): self.write_snapshot(); self.cfg['snapshot']=pin(self.snapfile)
    def refresh_source(self):
        self.write_source(); self.cfg['source_files'][0]['file']=pin(self.source)
        self.snap['sources'][0]['sha256']=pin(self.source)['sha256'];self.refresh_snapshot()
    def run_build(self, flag=True):
        path=self.d/'config.json';path.write_text(json.dumps(self.cfg));return c.prepare(path,self.out,flag)
    def test_partition_and_whole_without_old_grid(self):
        r=self.run_build();self.assertEqual(r['status'],'unverified-research-not-published');self.assertEqual(r['decision_revision_asserted_status'],'draft')
        self.assertEqual(r['compiler_report']['land_cells'],8)
        self.assertEqual(np.fromfile(self.out/'land/runs.u32le',dtype='<u4').tolist(),[1,17,2,18,3,1,5,19,6,1]*2)
        self.assertEqual(r['compiler_report']['input_sha256']['physical_rows'],self.cfg['physical_rows']['sha256'])
        self.assertEqual(r['compiler_report']['output_runs_sha256'],pin(self.out/'land/runs.u32le')['sha256'])
    def test_draft_requires_explicit_witness_rule_list(self):
        del self.snap['land_component_witness_rules'];self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'must include land witness rules'):self.run_build()
        self.assertFalse(self.out.exists())
    def test_unselected_draft_affiliation_fails_closed(self):
        for marker in ('research_only_not_selected','unknown',None):
            if marker is None:self.snap['affiliations'][0]['evidence'].pop('execution_status',None)
            else:self.snap['affiliations'][0]['evidence']['execution_status']=marker
            self.refresh_snapshot()
            with self.assertRaisesRegex(ValueError,'affiliations require explicit research selection'):self.run_build()
            self.assertFalse(self.out.exists())
    def test_no_implicit_snapshot_authentication(self):
        with self.assertRaisesRegex(ValueError,'authentication'): self.run_build(False)
        self.assertFalse((self.out/'report.json').exists())
    def test_missing_component_fails(self):
        self.snap['affiliations'].pop();self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'unassigned component'): self.run_build()
        self.assertFalse((self.out/'report.json').exists())
    def test_explicit_include_can_extend_source_group(self):
        self.snap['affiliations']=self.snap['affiliations'][-1:]
        self.snap['affiliations'][0]['evidence']['selector']['include_witnesses']=[{'lon':'-2.5','lat':'1.5'}]
        self.refresh_snapshot();r=self.run_build()
        self.assertEqual(r['decision_summary'][0]['included_components'],1)
        self.assertEqual(np.fromfile(self.out/'land/runs.u32le',dtype='<u4').tolist(),[2,19,3,1,5,19,6,1]*2)
    def test_duplicate_inclusion_fails(self):
        self.snap['affiliations'][-1]['evidence']['selector']['include_witnesses']=[{'lon':'-2.5','lat':'1.5'}]*2
        self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'duplicate or already-intersecting inclusion'): self.run_build()
    def test_redundant_inclusion_fails(self):
        self.snap['affiliations'][-1]['evidence']['selector']['include_witnesses']=[{'lon':'0.5','lat':'1.5'}]
        self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'duplicate or already-intersecting inclusion'): self.run_build()
    def test_group_unions_multiple_pinned_features(self):
        self.snap['affiliations']=self.snap['affiliations'][-1:]
        self.snap['affiliations'][0]['evidence']['selector']['additional_feature_ids']=['left','middle']
        self.refresh_snapshot();r=self.run_build()
        self.assertEqual(r['decision_summary'][0]['source_feature_hit_counts'],{'whole':1,'left':1,'middle':1})
        self.assertEqual(np.fromfile(self.out/'land/runs.u32le',dtype='<u4').tolist(),[2,19,3,1,5,19,6,1]*2)
    def test_duplicate_group_feature_fails(self):
        self.snap['affiliations'][-1]['evidence']['selector']['additional_feature_ids']=['whole'];self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'duplicate feature in group selector'): self.run_build()
    def test_missing_group_feature_fails(self):
        self.snap['affiliations'][-1]['evidence']['selector']['additional_feature_ids']=['missing'];self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'missing pinned decision feature'): self.run_build()
    def test_partition_gap_fails(self):
        self.snap['affiliations'].pop(1);self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'gap or overlap'): self.run_build()
        self.assertFalse((self.out/'report.json').exists())
    def test_partition_overlap_fails(self):
        self.snap['affiliations'][1]['feature_id']='left';self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'gap or overlap'): self.run_build()
    def test_conflict_with_whole_fails(self):
        self.snap['affiliations'].append(self.aff('d','left',101,'component_intersection_v1',{'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[]}));self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'conflicting component'): self.run_build()
    def test_nonintersecting_exclusion_fails(self):
        self.snap['affiliations'][-1]['evidence']['selector']['exclude_witnesses']=[{'lon':'-2.5','lat':'1.5'}];self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'non-intersecting exclusion'): self.run_build()
    def test_invalid_feature_hash_fails(self):
        self.snap['features'][0]['geometry_sha256']='0'*64;self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'geometry hash mismatch'): self.run_build()
    def test_source_file_mismatch_fails(self):
        self.cfg['source_files'][0]['file']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'digest mismatch'): self.run_build()
    def test_invalid_or_ambiguous_entity_fails(self):
        self.snap['category_bindings'].append({'entity_id':101,'physical_class':'land','code':21});self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'invalid or duplicate land category bindings'): self.run_build()
    def test_unknown_entity_fails(self):
        self.snap['entities'].pop(0);self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'invalid or duplicate land category bindings'): self.run_build()
    def test_duplicate_land_code_fails(self):
        self.snap['category_bindings'][1]['code']=17;self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'invalid or duplicate land category bindings'): self.run_build()
    def test_unsupported_method_fails(self):
        self.snap['affiliations'][0]['method']='override';self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'unsupported land affiliation'): self.run_build()
    def test_witness_must_be_land(self):
        self.snap['affiliations'][0]['evidence']['selector']['component_witness']={'lon':'-0.5','lat':'1.5'};self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'exactly one physical component'): self.run_build()
    def test_wrong_source_crs_fails(self):
        doc={'type':'FeatureCollection','crs':{'type':'name','properties':{'name':'EPSG:3857'}},'features':self.features}
        self.source.write_text(json.dumps(doc)); self.cfg['source_files'][0]['file']=pin(self.source)
        self.snap['sources'][0]['sha256']=pin(self.source)['sha256'];self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'WGS84'): self.run_build()
    def test_entity_id_must_not_be_boolean(self):
        self.snap['affiliations'][0]['entity_id']=True;self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'integer'): self.run_build()
    def test_unsplit_antimeridian_rejected(self):
        self.features[0]['geometry']['coordinates']=[[[179,0],[-179,0],[-179,1],[179,1],[179,0]]]
        self.snap['features'][0]['geometry_sha256']=c.geometry_hash(self.features[0]['geometry']);self.refresh_source()
        with self.assertRaisesRegex(ValueError,'unsplit antimeridian'): self.run_build()
    def test_existing_output_not_overwritten(self):
        (self.out).mkdir();(self.out/'untouched').write_text('keep')
        with self.assertRaises(FileExistsError): self.run_build()
        self.assertEqual((self.out/'untouched').read_text(),'keep')
    def test_output_cannot_contain_inputs(self):
        p=self.d/'config.json';p.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'contain an input'): c.prepare(p,self.d,True)
    def test_accepted_export_rejects_draft(self):
        self.snap['schema']='worldatlas-geography-decision-export-v1';self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'accepted export requires accepted'): self.run_build()
    def test_draft_export_keeps_draft_status(self):
        self.snap['schema']='worldatlas-geography-decision-draft-evidence-v1';self.refresh_snapshot()
        r=self.run_build();self.assertEqual(r['decision_revision_asserted_status'],'draft')
    def test_draft_export_cannot_claim_acceptance(self):
        self.snap['schema']='worldatlas-geography-decision-draft-evidence-v1';self.snap['decision_revision']['status']='accepted';self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'must remain draft'): self.run_build()
    def test_component_connectivity_verified_from_physical(self):
        runs=np.fromfile(self.d/'cv',dtype='<u4');runs[2]=123456;runs.tofile(self.d/'cv')
        self.cfg['component_runs']=pin(self.d/'cv')
        with self.assertRaisesRegex(ValueError,'connectivity does not match'): self.run_build()
        self.assertFalse((self.out/'report.json').exists())
    def test_output_must_not_be_nested_in_input_directory(self):
        p=self.d/'config.json';p.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'nested in an input directory'): c.prepare(p,self.d/'new-output',True)
        self.assertFalse((self.d/'new-output').exists())
    def setup_witness_rule(self):
        self.snap['affiliations'].pop()
        verification={'grid_width':6,'grid_height':2,'grid_step':'1','grid_west':'-3','grid_north':'2',
          **{key+'_sha256':self.cfg[key]['sha256'] for key in ('physical_rows','physical_runs','component_rows','component_runs')},
          'component_algorithm_sha256':sha_file(HERE.parent/'build_components.cpp')}
        rule={'rule_id':'w','entity_id':103,'method':'component_witness_list_v1',
              'selector':{'witnesses':[{'lon':'0.5','lat':'1.5'}],'verification':verification},
              'evidence':{'execution_status':'selected_for_research','source_files_evidence_only':[{'citation':'synthetic-source','file_sha256':'a'*64,'geometry_sha256':'b'*64}]}}
        self.snap['land_component_witness_rules']=[rule]
        return rule
    def test_mask_bound_witness_rule(self):
        self.setup_witness_rule();self.refresh_snapshot();r=self.run_build()
        self.assertEqual(np.fromfile(self.out/'land/runs.u32le',dtype='<u4').tolist(),[1,17,2,18,3,1,5,19,6,1]*2)
        self.assertTrue(r['decision_summary'][0]['mask_bound'])
    def test_partial_witness_rules_fail_global_completeness(self):
        self.setup_witness_rule();self.snap['affiliations']=[];self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'unassigned component'):self.run_build()
        self.assertFalse((self.out/'report.json').exists())
    def test_unselected_or_unmarked_witness_rules_fail_closed(self):
        rule=self.setup_witness_rule()
        for marker in ('research_only_not_selected', 'unknown', None):
            if marker is None: rule['evidence'].pop('execution_status',None)
            else: rule['evidence']['execution_status']=marker
            self.refresh_snapshot()
            with self.assertRaisesRegex(ValueError,'explicit research selection'):self.run_build()
            self.assertFalse(self.out.exists())
    def test_witness_resolver_rejects_unselected_direct_call(self):
        rule=self.setup_witness_rule();rule['evidence']['execution_status']='research_only_not_selected'
        with self.assertRaisesRegex(ValueError,'explicit research selection'):
            c.resolve_witness_rules([rule],{},self.cfg,None,None,'',[],{}, {},[])
    def test_witness_rules_reject_accepted_snapshot(self):
        self.setup_witness_rule()
        self.snap['schema']='worldatlas-geography-decision-export-v1'
        self.snap['decision_revision']['status']='accepted';self.snap['entity_revision']['status']='accepted'
        self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'witness rules are draft research only'):self.run_build()
        self.assertFalse(self.out.exists())
    def test_witness_rule_rejects_changed_physical_pin(self):
        rule=self.setup_witness_rule();rule['selector']['verification']['physical_runs_sha256']='0'*64;self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'physical_runs pin mismatch'):self.run_build()
    def test_witness_rule_rejects_shifted_georeference(self):
        rule=self.setup_witness_rule();rule['selector']['verification']['grid_west']='-4';self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'georeferencing mismatch'):self.run_build()
    def test_witness_rule_rejects_duplicate_component(self):
        rule=self.setup_witness_rule();rule['selector']['witnesses'].append({'lon':'1.5','lat':'1.5'});self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'duplicate witness component'):self.run_build()
    def test_witness_rule_rejects_no_evidence(self):
        rule=self.setup_witness_rule();rule['evidence']={'execution_status':'selected_for_research'};self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'source citations and evidence hashes'):self.run_build()
    def test_witness_rule_accepts_document_evidence(self):
        rule=self.setup_witness_rule();rule['evidence']={'execution_status':'selected_for_research','source_documents_evidence_only':[{'citation':'named island decision','file_sha256':'c'*64}]};self.refresh_snapshot()
        self.assertTrue(self.run_build()['decision_summary'][0]['mask_bound'])
    def test_witness_rule_rejects_bad_document_hash(self):
        rule=self.setup_witness_rule();rule['evidence']={'execution_status':'selected_for_research','source_documents_evidence_only':[{'citation':'named island decision','file_sha256':'bad'}]};self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'source citations and evidence hashes'):self.run_build()
    def test_witness_rule_rejects_mixed_bad_evidence(self):
        rule=self.setup_witness_rule();rule['evidence']['source_documents_evidence_only']=[{'citation':'bad','file_sha256':'broken'}];self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'source citations and evidence hashes'):self.run_build()
    def test_witness_rule_rejects_conflict(self):
        rule=self.setup_witness_rule();rule['selector']['witnesses']=[{'lon':'-2.5','lat':'1.5'}];self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'partition conflicts with component claim'):self.run_build()
    def test_decimal_witness_required(self):
        self.snap['affiliations'][0]['evidence']['selector']['component_witness']['lon']=-2.5;self.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'decimal strings'): self.run_build()

if __name__=='__main__':unittest.main()
