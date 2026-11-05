import json,subprocess,tempfile,unittest
from pathlib import Path
import numpy as np
import derive_mainland_seed as d
import hashlib
HERE=Path(__file__).parent

def pin(path):return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def write_rle(prefix,values):
    rows=[0];runs=[]
    for row in values:
        for x in range(len(row)):
            if x==len(row)-1 or row[x]!=row[x+1]:runs.append((x+1,int(row[x])))
        rows.append(len(runs))
    rp=prefix.with_name(prefix.name+'-rows');xp=prefix.with_name(prefix.name+'-runs')
    np.asarray(rows,dtype='<u4').tofile(rp);np.asarray(runs,dtype='<u4').tofile(xp)
    return rp,xp

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



class BoundaryParity(unittest.TestCase):
    def test_nonbinary_full_width_origin_matches_final_stream(self):
        import assign_land_stream as stream
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
                        for func,config,out in ((d.build,sc,base/'seed'),(stream.build,cp,base/'final')):
                            try:func(config,out);actual.append('ok')
                            except ValueError:actual.append('error')
                        self.assertEqual(actual[0],actual[1])
                        if actual[0]=='ok':
                            self.assertEqual((base/'seed'/'rows.u32le').read_bytes(),(base/'final'/'rows.u32le').read_bytes())
                            sv=np.fromfile(base/'seed'/'runs.u32le',dtype='<u4').reshape(-1,2);fv=np.fromfile(base/'final'/'runs.u32le',dtype='<u4').reshape(-1,2);fv[:,1][fv[:,1]==1]=0;np.testing.assert_array_equal(sv,fv)

if __name__=='__main__':unittest.main()
