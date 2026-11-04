import json,sys,tempfile,unittest
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent))
import assign_land as base
import assign_land_stream as stream

def pin(path,values):np.asarray(values,dtype='<u4').tofile(path);return {'path':str(path),'sha256':base.sha(path)}
def geo(path,coords):
    path.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':{'type':'Polygon','coordinates':[coords]}}]}))
    return {'path':str(path),'sha256':base.sha(path)}

class Streaming(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.d=Path(self.t.name)
        self.cfg={'schema':'land-decision-compiler-prototype-v1','decision_revision':'synthetic','revision_status':'draft','provenance_note':'synthetic test','grid':{'width':4,'height':2,'step':1,'west':-2,'north':2},
                  'physical_rows':pin(self.d/'pr',[0,3,6]),'physical_runs':pin(self.d/'pv',[2,17,3,1,4,17]*2),
                  'component_rows':pin(self.d/'cr',[0,2,4]),'component_runs':pin(self.d/'cv',[0,2,0,3,4,0]*2),'strip_rows':1,
                  'rules':[{'rule_id':'r','source_evidence':['synthetic'],'component_id':0,'kind':'whole_component','code':19}]}
    def tearDown(self):self.t.cleanup()
    def config(self):p=self.d/'config';p.write_text(json.dumps(self.cfg));return p
    def compare(self):
        p=self.config();base.build(p,self.d/'baseline');stream.build(p,self.d/'stream')
        for name in ('rows.u32le','runs.u32le'):self.assertEqual((self.d/'baseline'/name).read_bytes(),(self.d/'stream'/name).read_bytes())
    def partition(self):
        left=geo(self.d/'left.geojson',[[-2,0],[0,0],[0,2],[-2,2],[-2,0]])
        right=geo(self.d/'right.geojson',[[1,0],[2,0],[2,2],[1,2],[1,0]])
        self.cfg['rules']=[{'rule_id':'r','source_evidence':['synthetic'],'component_id':0,'kind':'polygon_partition','parts':[{'part_id':'left','code':19,'geometry':left},{'part_id':'right','code':18,'geometry':right}]}]
    def test_whole_byte_parity(self):self.compare()
    def test_partition_byte_parity(self):self.partition();self.compare()
    def test_partition_gap_rejected(self):
        self.partition();self.cfg['rules'][0]['parts'].pop()
        with self.assertRaisesRegex(ValueError,'gap or overlap'):stream.build(self.config(),self.d/'out')
    def test_partition_overlap_rejected(self):
        self.partition();self.cfg['rules'][0]['parts'].append(dict(self.cfg['rules'][0]['parts'][0],part_id='duplicate'))
        with self.assertRaisesRegex(ValueError,'gap or overlap'):stream.build(self.config(),self.d/'out')
    def test_missing_root_rejected(self):
        self.cfg['rules'][0]['component_id']=5
        with self.assertRaisesRegex(ValueError,'unassigned'):stream.build(self.config(),self.d/'out')
    def test_footprint_mismatch_rejected(self):
        self.cfg['component_runs']=pin(self.d/'bad',[0,4,0,0,4,0]);self.cfg['component_rows']=pin(self.d/'badrows',[0,1,2])
        with self.assertRaisesRegex(ValueError,'footprint mismatch'):stream.build(self.config(),self.d/'out')
    def test_partition_nonbinary_steps_byte_parity(self):
        for step in (0.1,0.3,360/131072):
            with self.subTest(step=step), tempfile.TemporaryDirectory() as tmp:
                d=Path(tmp);w,h=100,4;west,north=-10,20
                left=geo(d/'left.geojson',[[west,north-h*step],[west+50*step,north-h*step],[west+50*step,north],[west,north],[west,north-h*step]])
                right=geo(d/'right.geojson',[[west+50*step,north-h*step],[west+w*step,north-h*step],[west+w*step,north],[west+50*step,north],[west+50*step,north-h*step]])
                config={'schema':'land-decision-compiler-prototype-v1','decision_revision':'synthetic','revision_status':'draft','provenance_note':'test','grid':{'width':w,'height':h,'step':step,'west':west,'north':north},'physical_rows':pin(d/'pr',[0,3,6,9,12]),'physical_runs':pin(d/'pv',[13,1,87,17,100,1]*4),'component_rows':pin(d/'cr',[0,1,2,3,4]),'component_runs':pin(d/'cv',[13,87,0]*4),'strip_rows':2,'rules':[{'rule_id':'p','component_id':0,'source_evidence':['synthetic'],'kind':'polygon_partition','parts':[{'part_id':'l','code':18,'geometry':left},{'part_id':'r','code':19,'geometry':right}]}]}
                path=d/'config';path.write_text(json.dumps(config));base.build(path,d/'a');stream.build(path,d/'b')
                for name in ('rows.u32le','runs.u32le'):self.assertEqual((d/'a'/name).read_bytes(),(d/'b'/name).read_bytes())
    def test_exact_center_boundary_tie_parity(self):
        for step in (0.1,0.3,360/131072,1.0):
            for boundary_col in (20,33,50,66,80):
                for offset in (0.0,0.5,1e-8):
                    with self.subTest(step=step,boundary_col=boundary_col,offset=offset), tempfile.TemporaryDirectory() as tmp:
                        d=Path(tmp);w,h=100,3;west,north=-10,20;edge=west+(boundary_col+offset)*step;bottom=north-h*step;east=west+w*step
                        left=geo(d/'l.geojson',[[west,bottom],[edge,bottom],[edge,north],[west,north],[west,bottom]])
                        right=geo(d/'r.geojson',[[edge,bottom],[east,bottom],[east,north],[edge,north],[edge,bottom]])
                        cfg={'schema':'land-decision-compiler-prototype-v1','decision_revision':'t','revision_status':'draft','provenance_note':'test','grid':{'width':w,'height':h,'step':step,'west':west,'north':north},'physical_rows':pin(d/'pr',[0,3,6,9]),'physical_runs':pin(d/'pv',[13,1,87,17,100,1]*3),'component_rows':pin(d/'cr',[0,1,2,3]),'component_runs':pin(d/'cv',[13,87,0]*3),'strip_rows':2,'rules':[{'rule_id':'p','component_id':0,'source_evidence':['synthetic'],'kind':'polygon_partition','parts':[{'part_id':'l','code':18,'geometry':left},{'part_id':'r','code':19,'geometry':right}]}]}
                        p=d/'config';p.write_text(json.dumps(cfg));out=[]
                        for module,name in ((base,'a'),(stream,'b')):
                            try:
                                module.build(p,d/name);out.append(('ok',(d/name/'rows.u32le').read_bytes(),(d/name/'runs.u32le').read_bytes()))
                            except ValueError:out.append(('error',))
                        self.assertEqual(out[0],out[1])
    def test_random_physical_rows_byte_parity(self):
        for seed in range(20):
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as tmp:
                d=Path(tmp);rng=np.random.default_rng(seed);w,h=32,10;physical=rng.integers(0,2,size=(h,w));pro=[0];cro=[0];pv=[];cv=[];rules=[];root=0
                for row in physical:
                    starts=np.r_[0,np.flatnonzero(row[1:]!=row[:-1])+1];ends=np.r_[starts[1:],w]
                    for a,b in zip(starts,ends):
                        code=17 if row[a] else 1;pv.extend([int(b),code])
                        if code==17:cv.extend([int(a),int(b),root]);rules.append({'rule_id':f'r{root}','component_id':root,'source_evidence':['synthetic'],'kind':'whole_component','code':17+root%6});root+=1
                    pro.append(len(pv)//2);cro.append(len(cv)//3)
                config={'schema':'land-decision-compiler-prototype-v1','decision_revision':'synthetic','revision_status':'draft','provenance_note':'test','grid':{'width':w,'height':h,'step':1,'west':-16,'north':10},'physical_rows':pin(d/'pr',pro),'physical_runs':pin(d/'pv',pv),'component_rows':pin(d/'cr',cro),'component_runs':pin(d/'cv',cv),'strip_rows':3,'rules':rules};path=d/'config';path.write_text(json.dumps(config));base.build(path,d/'a');stream.build(path,d/'b')
                for name in ('rows.u32le','runs.u32le'):self.assertEqual((d/'a'/name).read_bytes(),(d/'b'/name).read_bytes())
if __name__=='__main__':unittest.main()
