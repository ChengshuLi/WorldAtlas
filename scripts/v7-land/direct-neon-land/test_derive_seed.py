import json,subprocess,tempfile,unittest
from pathlib import Path
import numpy as np
import nearest_mainland as n
import derive_mainland_seed as d
from test_nearest_mainland import write_rle,pin,HERE

def polygon(path,x0,x1):
    g={'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':{'type':'Polygon','coordinates':[[[x0,60],[x1,60],[x1,90],[x0,90],[x0,60]]]}}]}
    path.write_text(json.dumps(g));return pin(path)

class Seed(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.base=Path(self.t.name);self.inp=self.base/'in';self.inp.mkdir();w,h=12,6
        physical=np.ones((h,w),np.uint32); seed=np.zeros_like(physical)
        for x,code in [(0,17),(1,18),(3,19),(5,20),(7,21),(9,22)]:physical[0,x]=17;seed[0,x]=code
        physical[2,1]=17
        pr,px=write_rle(self.inp/'physical',physical);mr,mx=write_rle(self.inp/'expected',seed)
        subprocess.run(['g++','-std=c++17','-O2',str(HERE.parent/'build_components.cpp'),'-o',str(self.inp/'builder')],check=True)
        cr=self.inp/'cr';cx=self.inp/'cx';subprocess.run([str(self.inp/'builder'),str(w),str(h),str(pr),str(px),str(cr),str(cx)],check=True,capture_output=True)
        ro=np.fromfile(cr,dtype='<u4');r=np.fromfile(cx,dtype='<u4').reshape(-1,3);roots=[int(x[2]) for x in r[ro[0]:ro[1]]]
        self.pins={'physical_rows':pin(pr),'physical_runs':pin(px),'component_rows':pin(cr),'component_runs':pin(cx)}
        self.grid={'width':w,'height':h,'step':30,'west':-180,'north':90}
        rules=[{'component_id':roots[0],'rule_id':'cut','source_evidence':['explicit source'],'kind':'polygon_partition','parts':[{'part_id':'left','code':17,'geometry':polygon(self.inp/'l.geojson',-180,-150)},{'part_id':'right','code':18,'geometry':polygon(self.inp/'r.geojson',-150,-120)}]}]
        rules += [{'component_id':root,'rule_id':f'r{root}','source_evidence':['explicit source'],'kind':'whole_component','code':19+i} for i,root in enumerate(roots[1:])]
        self.compiler={'schema':'land-decision-compiler-prototype-v1','decision_revision':'d1','revision_status':'draft','provenance_note':'fixture','grid':self.grid,**self.pins,'strip_rows':2,'rules':rules}
        self.snapshot={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','decision_revision':{'id':'d1','status':'draft','entity_revision':'e1'},'entity_revision':{'id':'e1','status':'draft'},'land_mainland_policy':{'execution_status':'selected_for_research','grid':self.grid,'mainland_component_ids':roots,**{k+'_sha256':v['sha256'] for k,v in self.pins.items()}}}
        self.expected=(mr,mx);self.sp=self.inp/'snapshot.json';self.rp=self.inp/'resolved.json';self.cp=self.inp/'config.json';self.save()
    def save(self):
        self.sp.write_text(json.dumps(self.snapshot));self.rp.write_text(json.dumps(self.compiler));self.cp.write_text(json.dumps({'schema':'resolved-mainland-seed-v1','snapshot':pin(self.sp),'compiler_config':pin(self.rp),'strip_rows':2}))
    def tearDown(self):self.t.cleanup()
    def test_render_matches_expected(self):
        result=d.build(self.cp,self.base/'out')
        self.assertEqual((self.base/'out'/'rows.u32le').read_bytes(),self.expected[0].read_bytes());self.assertEqual((self.base/'out'/'runs.u32le').read_bytes(),self.expected[1].read_bytes())
        self.assertEqual(sorted(result['part_cell_counts'].values()),[1,1])
    def test_gap_fails(self):
        self.compiler['rules'][0]['parts'].pop();self.save()
        with self.assertRaisesRegex(ValueError,'gap or overlap'):d.build(self.cp,self.base/'out')
        self.assertFalse((self.base/'out'/'report.json').exists())
    def test_overlap_fails(self):
        self.compiler['rules'][0]['parts'].append(dict(self.compiler['rules'][0]['parts'][0],part_id='duplicate'));self.save()
        with self.assertRaisesRegex(ValueError,'gap or overlap'):d.build(self.cp,self.base/'out')
    def test_missing_rule_fails(self):
        self.compiler['rules'].pop();self.save()
        with self.assertRaisesRegex(ValueError,'lacks an explicit source rule'):d.build(self.cp,self.base/'out')
    def test_unselected_policy_fails(self):
        self.snapshot['land_mainland_policy']['execution_status']='candidate';self.save()
        with self.assertRaisesRegex(ValueError,'selected research mainland policy'):d.build(self.cp,self.base/'out')
    def test_accepted_snapshot_rejected(self):
        self.snapshot['schema']='worldatlas-geography-decision-export-v1';self.snapshot['decision_revision']['status']='accepted';self.snapshot['entity_revision']['status']='accepted';self.save()
        with self.assertRaisesRegex(ValueError,'requires draft snapshot'):d.build(self.cp,self.base/'out')
        self.assertFalse((self.base/'out').exists())
    def test_mismatched_components_fails(self):
        self.snapshot['land_mainland_policy']['component_runs_sha256']='0'*64;self.save()
        with self.assertRaisesRegex(ValueError,'policy/compiler input mismatch'):d.build(self.cp,self.base/'out')


class Joined(Seed):
    def adapter_request(self):
        import integrate_resolved_land as joined
        pol=self.snapshot['land_mainland_policy'];pol.update({'method':'nearest_mainland_v1','distance':'minimum_spherical_cell_center','tie':'fail','precedence':'mainland_then_reviewed_component_then_nearest','component_algorithm_sha256':n.sha(HERE.parent/'build_components.cpp'),'reviewed_component_claims':[],'source_cut_feature_ids':[],'chunk_columns':2,'tolerance_metres':1e-5,'mainland_rows_sha256':n.sha(self.expected[0]),'mainland_runs_sha256':n.sha(self.expected[1])})
        self.snapshot['entities']=[{'id':i+1} for i in range(6)];self.snapshot['category_bindings']=[{'entity_id':i+1,'physical_class':'land','code':17+i} for i in range(6)]
        cut={'type':'Feature','properties':{'id':'fixture-cut'},'geometry':{'type':'LineString','coordinates':[[-150,60],[-150,90]]}}
        cut_path=self.inp/'cut.geojson';cut_path.write_text(json.dumps({'type':'FeatureCollection','features':[cut]}))
        ghash=__import__('hashlib').sha256(json.dumps(cut['geometry'],sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
        self.snapshot['sources']=[{'source_id':'fixture-cut','version':'1','sha256':n.sha(cut_path)}];self.snapshot['features']=[{'feature_id':'fixture-cut','source_id':'fixture-cut','source_version':'1','source_feature_id':'fixture-cut','geometry_sha256':ghash}];pol['source_cut_feature_ids']=['fixture-cut'];self.save()
        report={'schema':'direct-land-explicit-resolution-v1','status':'research-partial-no-land-grid','snapshot_sha256':n.sha(self.sp),'compiler_config_sha256':n.sha(self.rp),'compiler_config_path':str(self.rp),'grid':self.grid,'decision_revision':'d1','decision_revision_asserted_status':'draft','program_sha256':n.sha(joined.DIRECT/'compile_land.py'),'shared_backend_sha256':n.sha(joined.DIRECT.parent/'assign_land.py'),'component_source_sha256':n.sha(HERE.parent/'build_components.cpp'),'explicit_root_count':len(self.compiler['rules']),'input_pins':{'snapshot':pin(self.sp),**self.pins},'gdal_version':d.gdal.VersionInfo('--version'),'numpy_version':np.__version__,'source_files':[{'source_id':'fixture-cut','source_version':'1','file':pin(cut_path),'id_property':'id'}],'component_generation_method':'independent-recompute','component_manifest_sha256':None}
        self.report_path=self.inp/'resolver-report.json';self.report_path.write_text(json.dumps(report))
        path=self.inp/'adapter.json';path.write_text(json.dumps({'schema':'resolved-land-nearest-adapter-v1','snapshot':pin(self.sp),'compiler_config':pin(self.rp),'resolution_report':pin(self.report_path),'workers':2,'strip_rows':2}));return joined,path
    def refresh_adapter_snapshot(self,path):
        report=json.loads(self.report_path.read_bytes());report['snapshot_sha256']=n.sha(self.sp);report['input_pins']['snapshot']=pin(self.sp);self.report_path.write_text(json.dumps(report))
        req=json.loads(path.read_bytes());req['snapshot']=pin(self.sp);req['resolution_report']=pin(self.report_path);path.write_text(json.dumps(req))
    def test_joined_pipeline(self):
        joined,path=self.adapter_request();r=joined.build(path,self.base/'joined',True)
        self.assertEqual(r['status'],'unverified-research-not-published')
        rows=np.fromfile(self.base/'joined'/'land'/'rows.u32le',dtype='<u4');runs=np.fromfile(self.base/'joined'/'land'/'runs.u32le',dtype='<u4').reshape(-1,2)
        result=np.empty((6,12),np.uint32)
        for y in range(6):
            prev=0
            for end,code in runs[rows[y]:rows[y+1]]:result[y,prev:int(end)]=code;prev=int(end)
        self.assertEqual(result[2,1],18);self.assertEqual(result[0,[0,1,3,5,7,9]].tolist(),[17,18,19,20,21,22]);self.assertEqual(result[1].tolist(),[1]*12)
    def test_actual_direct_resolver_to_nearest(self):
        import run_direct_nearest as driver
        import compile_land as compiler
        _,path=self.adapter_request()
        regions=[('left',-180,-150,1),('right',-150,-120,2),('r3',-90,-60,3),('r5',-30,0,4),('r7',30,60,5),('r9',90,120,6)]
        features=[];aff=[]
        for i,(fid,x0,x1,entity) in enumerate(regions):
            geom={'type':'Polygon','coordinates':[[[x0,60],[x1,60],[x1,90],[x0,90],[x0,60]]]}
            features.append({'type':'Feature','properties':{'id':fid},'geometry':geom})
            if i<2:
                method='component_partition_v1';selector={'component_witness':{'lon':'-165','lat':'75'}}
            else:
                method='component_intersection_v1';selector={'additional_feature_ids':[],'include_witnesses':[],'exclude_witnesses':[]}
            aff.append({'affiliation_id':'rule-'+fid,'feature_id':fid,'entity_id':entity,'relationship':'affiliation','scope':'land','method':method,'rationale':'synthetic fixture','evidence':{'execution_status':'selected_for_research','selector':selector}})
        features.append({'type':'Feature','properties':{'id':'cut-line'},'geometry':{'type':'LineString','coordinates':[[-150,60],[-150,90]]}})
        self.snapshot['land_mainland_policy']['source_cut_feature_ids']=['cut-line']
        source=self.inp/'features.geojson';source.write_text(json.dumps({'type':'FeatureCollection','features':features}))
        self.snapshot.update({'sources':[{'source_id':'synthetic','version':'1','sha256':n.sha(source)}],'features':[{'feature_id':f['properties']['id'],'source_id':'synthetic','source_version':'1','source_feature_id':f['properties']['id'],'geometry_sha256':compiler.geometry_hash(f['geometry'])} for f in features],'affiliations':aff,'land_component_witness_rules':[]})
        self.sp.write_text(json.dumps(self.snapshot))
        direct_config={'schema':'direct-neon-land-build-v1','snapshot':pin(self.sp),'grid':self.grid,**self.pins,'source_files':[{'source_id':'synthetic','source_version':'1','file':pin(source),'id_property':'id'}],'strip_rows':2}
        dpath=self.inp/'direct.json';dpath.write_text(json.dumps(direct_config))
        request=self.inp/'orchestration.json';request.write_text(json.dumps({'schema':'direct-nearest-orchestration-v1','direct_config':pin(dpath),'workers':2,'strip_rows':2}))
        result=driver.build(request,self.base/'integrated',True)
        self.assertEqual(result['status'],'unverified-research-not-published');self.assertTrue((self.base/'integrated'/'resolved'/'resolution-report.json').exists())
        audit=json.loads((self.base/'integrated'/'integrated'/'report.json').read_bytes());self.assertEqual([e['feature_id'] for e in audit['verified_cut_evidence']],['cut-line'])
        rows=np.fromfile(self.base/'integrated'/'integrated'/'land'/'rows.u32le',dtype='<u4');runs=np.fromfile(self.base/'integrated'/'integrated'/'land'/'runs.u32le',dtype='<u4').reshape(-1,2)
        x=1;self.assertEqual(int(runs[rows[2]:rows[3]][np.searchsorted(runs[rows[2]:rows[3],0],x,side='right'),1]),18)
        import run_single_generation_nearest as one_driver
        physical_report=self.inp/'physical-report.json';physical_report.write_text(json.dumps({'status':'candidate-only','grid':self.grid,'output_sha256':{'rows.u32le':self.pins['physical_rows']['sha256'],'runs.u32le':self.pins['physical_runs']['sha256']}}))
        single_request={'schema':'single-generation-direct-land-v1','snapshot':pin(self.sp),'grid':self.grid,'physical_rows':self.pins['physical_rows'],'physical_runs':self.pins['physical_runs'],'physical_report':pin(physical_report),'source_files':direct_config['source_files'],'component_source_sha256':n.sha(HERE.parent/'build_components.cpp'),'strip_rows':2}
        sr=self.inp/'single-request.json';sr.write_text(json.dumps(single_request));outer=self.inp/'one-driver.json';outer.write_text(json.dumps({'schema':'single-generation-nearest-v1','single_generation_request':pin(sr),'workers':2,'strip_rows':2}))
        one=one_driver.build(outer,self.base/'one-integrated',True)
        self.assertEqual(one['component_generations'],1);self.assertEqual(one['output_rows_sha256'],result['output_rows_sha256']);self.assertEqual(one['output_runs_sha256'],result['output_runs_sha256'])
        self.assertFalse((self.base/'one-integrated'/'single'/'assignment'/'land').exists())
        self.assertFalse((self.base/'one-integrated'/'integrated'/'nearest'/'component-builder').exists());claims=json.loads((self.base/'one-integrated'/'integrated'/'nearest'/'claims.json').read_bytes());self.assertEqual(claims['component_generation_method'],'single-generation-manifest')
    def test_one_generation_rejects_unselected_before_output(self):
        import run_single_generation_nearest as one
        self.snapshot['land_mainland_policy']['execution_status']='research_only_not_selected';self.save()
        request=self.inp/'early.json';request.write_text(json.dumps({'snapshot':pin(self.sp),'physical_report':{'path':'not-read','sha256':'0'*64}}))
        outer=self.inp/'early-wrapper.json';outer.write_text(json.dumps({'schema':'single-generation-nearest-v1','single_generation_request':pin(request),'workers':1,'strip_rows':2}))
        with self.assertRaisesRegex(ValueError,'before component generation'):one.build(outer,self.base/'out',True)
        self.assertFalse((self.base/'out').exists())
    def test_seed_pin_mismatch_fails(self):
        joined,path=self.adapter_request();self.snapshot['land_mainland_policy']['mainland_runs_sha256']='0'*64;self.save()
        self.refresh_adapter_snapshot(path)
        with self.assertRaisesRegex(ValueError,'seed differs from policy pins'):joined.build(path,self.base/'joined',True)
        self.assertFalse((self.base/'joined'/'report.json').exists())
    def test_runtime_version_mismatch_fails(self):
        joined,path=self.adapter_request();report=json.loads(self.report_path.read_bytes());report['gdal_version']='different';self.report_path.write_text(json.dumps(report));req=json.loads(path.read_bytes());req['resolution_report']=pin(self.report_path);path.write_text(json.dumps(req))
        with self.assertRaisesRegex(ValueError,'runtime versions differ'):joined.build(path,self.base/'joined',True)
    def test_partition_requires_source_cut_evidence(self):
        joined,path=self.adapter_request();self.snapshot['land_mainland_policy']['source_cut_feature_ids']=[];self.save();self.refresh_adapter_snapshot(path)
        with self.assertRaisesRegex(ValueError,'partition requires pinned cut evidence'):joined.build(path,self.base/'joined',True)
    def test_unmatched_reviewed_claim_fails(self):
        joined,path=self.adapter_request();self.snapshot['land_mainland_policy']['reviewed_component_claims']=[{'rule_id':'invented','component_id':999,'entity_id':1}];self.save()
        self.refresh_adapter_snapshot(path)
        with self.assertRaisesRegex(ValueError,'resolved reviewed components differ'):joined.build(path,self.base/'joined',True)

class BoundaryParity(unittest.TestCase):
    def test_nonbinary_full_width_origin_matches_final_stream(self):
        import integrate_resolved_land as joined
        for step in (0.1,0.3,360/131072):
            for boundary_col in (20,33,50,66,80):
                for offset in (0.0,0.5,1e-8):
                    with self.subTest(step=step,boundary_col=boundary_col,offset=offset),tempfile.TemporaryDirectory() as tmp:
                        base=Path(tmp);inp=base/'input';inp.mkdir();w,h=100,3;west,north=-10,20;edge=west+(boundary_col+offset)*step;bottom=north-h*step;east=west+w*step
                        physical=np.ones((h,w),np.uint32);physical[:,13:87]=17
                        for x in (90,92,94,96):physical[0,x]=17
                        pr,px=write_rle(inp/'physical',physical)
                        cr=inp/'cr';cx=inp/'cx';crow=[0];runs=[]
                        for y in range(h):
                            runs.append((13,87,0))
                            if y==0:runs.extend((x,x+1,i+1) for i,x in enumerate((90,92,94,96)))
                            crow.append(len(runs))
                        np.asarray(crow,dtype='<u4').tofile(cr);np.asarray(runs,dtype='<u4').tofile(cx)
                        def geo(name,x0,x1):
                            p=inp/name;coords=[[[x0,bottom],[x1,bottom],[x1,north],[x0,north],[x0,bottom]]];p.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':{'type':'Polygon','coordinates':coords}}]}));return pin(p)
                        left=geo('left.geojson',west,edge);right=geo('right.geojson',edge,east)
                        rules=[{'component_id':0,'rule_id':'split','source_evidence':['fixture'],'kind':'polygon_partition','parts':[{'part_id':'left','code':17,'geometry':left},{'part_id':'right','code':18,'geometry':right}]}]+[{'component_id':i+1,'rule_id':f'r{i}','source_evidence':['fixture'],'kind':'whole_component','code':19+i} for i in range(4)]
                        grid={'width':w,'height':h,'step':step,'west':west,'north':north};pins={'physical_rows':pin(pr),'physical_runs':pin(px),'component_rows':pin(cr),'component_runs':pin(cx)}
                        cfg={'schema':'land-decision-compiler-prototype-v1','decision_revision':'t','revision_status':'draft','provenance_note':'fixture','grid':grid,**pins,'strip_rows':2,'rules':rules};cp=inp/'compiler.json';cp.write_text(json.dumps(cfg))
                        snap={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','decision_revision':{'id':'t','status':'draft','entity_revision':'e'},'entity_revision':{'id':'e','status':'draft'},'land_mainland_policy':{'execution_status':'selected_for_research','grid':grid,'mainland_component_ids':[0,1,2,3,4],**{k+'_sha256':v['sha256'] for k,v in pins.items()}}};sp=inp/'snapshot.json';sp.write_text(json.dumps(snap))
                        sc=inp/'seed.json';sc.write_text(json.dumps({'schema':'resolved-mainland-seed-v1','snapshot':pin(sp),'compiler_config':pin(cp),'strip_rows':2}));actual=[]
                        for func,config,out in ((d.build,sc,base/'seed'),(joined.stream.build,cp,base/'final')):
                            try:func(config,out);actual.append('ok')
                            except ValueError:actual.append('error')
                        self.assertEqual(actual[0],actual[1])
                        if actual[0]=='ok':
                            self.assertEqual((base/'seed'/'rows.u32le').read_bytes(),(base/'final'/'rows.u32le').read_bytes())
                            sv=np.fromfile(base/'seed'/'runs.u32le',dtype='<u4').reshape(-1,2);fv=np.fromfile(base/'final'/'runs.u32le',dtype='<u4').reshape(-1,2);fv[:,1][fv[:,1]==1]=0;np.testing.assert_array_equal(sv,fv)

if __name__=='__main__':unittest.main()
