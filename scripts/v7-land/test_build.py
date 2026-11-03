import hashlib, json, struct, subprocess, tempfile, unittest
from pathlib import Path
import numpy as np
from osgeo import ogr, osr
import assign_land
ROOT=Path(__file__).resolve().parent

def data(path,values): np.asarray(values,dtype='<u4').tofile(path); return {'path':str(path),'sha256':assign_land.sha(path)}
def geo(path,coords):
    path.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':{'type':'Polygon','coordinates':[coords]}}]}))
    return {'path':str(path),'sha256':assign_land.sha(path)}
class LandBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary_dir = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.binary_dir.name) / 'build_components'
        subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(ROOT/'build_components.cpp'),'-o',str(cls.binary)],check=True)
    @classmethod
    def tearDownClass(cls): cls.binary_dir.cleanup()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.d=Path(self.tmp.name)
        # width 4: land x=0,1,3 in two rows, wrapping unites x0 and x3.
        self.pr=data(self.d/'pr',[0,3,6]); self.pv=data(self.d/'pv',[2,17,3,1,4,17]*2)
        subprocess.run([str(self.binary),'4','2',self.pr['path'],self.pv['path'],str(self.d/'cr'),str(self.d/'cv')],check=True,capture_output=True)
        self.cr={'path':str(self.d/'cr'),'sha256':assign_land.sha(self.d/'cr')}; self.cv={'path':str(self.d/'cv'),'sha256':assign_land.sha(self.d/'cv')}
        roots=np.fromfile(self.d/'cv',dtype='<u4').reshape(-1,3); self.root=int(roots[0,2]); self.assertEqual(set(roots[:,2]),{self.root})
        self.cfg={'schema':'land-decision-compiler-prototype-v1','decision_revision':'synthetic','revision_status':'draft','provenance_note':'synthetic test only','grid':{'width':4,'height':2,'step':1,'west':-2,'north':2},'physical_rows':self.pr,'physical_runs':self.pv,'component_rows':self.cr,'component_runs':self.cv,'strip_rows':1,'rules':[{'rule_id':'r','source_evidence':['synthetic'],'component_id':self.root,'kind':'whole_component','code':19}]}
    def tearDown(self): self.tmp.cleanup()
    def runbuild(self):
        path=self.d/'config.json'; path.write_text(json.dumps(self.cfg)); return assign_land.build(path,str(self.d/'out'))
    def test_whole_component(self):
        report=self.runbuild(); self.assertEqual(report['land_cells'],6); self.assertEqual(report['components'],1)
        self.assertEqual(np.fromfile(self.d/'out/runs.u32le',dtype='<u4').tolist(),[2,19,3,1,4,19]*2)
    def test_missing_rule_fails(self):
        self.cfg['rules']=[]
        with self.assertRaises(ValueError): self.runbuild()
        self.assertFalse((self.d/'out/report.json').exists())
    def test_duplicate_rule_fails(self):
        self.cfg['rules'].append(dict(self.cfg['rules'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate'): self.runbuild()
    def test_bad_input_hash_fails(self):
        self.cfg['physical_runs']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'digest'): self.runbuild()
    def test_partition_and_gap_fail(self):
        left=geo(self.d/'left.geojson',[[-2,0],[0,0],[0,2],[-2,2],[-2,0]])
        right=geo(self.d/'right.geojson',[[1,0],[2,0],[2,2],[1,2],[1,0]])
        self.cfg['rules']=[{'rule_id':'r','source_evidence':['synthetic'],'component_id':self.root,'kind':'polygon_partition','parts':[{'part_id':'L','code':19,'geometry':left},{'part_id':'R','code':18,'geometry':right}]}]
        self.runbuild(); self.assertEqual(np.fromfile(self.d/'out/runs.u32le',dtype='<u4').tolist(),[2,19,3,1,4,18]*2)
        self.cfg['rules'][0]['parts'].pop(); self.d.joinpath('config2.json').write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'gap or overlap'): assign_land.build(self.d/'config2.json',str(self.d/'gap'))
    def test_partition_overlap_fails(self):
        left=geo(self.d/'left2.geojson',[[-2,0],[2,0],[2,2],[-2,2],[-2,0]])
        right=geo(self.d/'right2.geojson',[[0,0],[2,0],[2,2],[0,2],[0,0]])
        self.cfg['rules']=[{'rule_id':'r','source_evidence':['synthetic'],'component_id':self.root,'kind':'polygon_partition','parts':[{'part_id':'L','code':19,'geometry':left},{'part_id':'R','code':18,'geometry':right}]}]
        with self.assertRaisesRegex(ValueError,'gap or overlap'): self.runbuild()
        self.assertFalse((self.d/'out/report.json').exists())
    def test_component_builder_rejects_noncanonical_input(self):
        rows=data(self.d/'prbad',[0,2]); runs=data(self.d/'pvbad',[2,17,4,17])
        cmd=[str(self.binary),'4','1',rows['path'],runs['path'],str(self.d/'badoutrows'),str(self.d/'badoutruns')]
        result=subprocess.run(cmd,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0); self.assertIn('noncanonical',result.stderr)
    def test_unused_rule_fails(self):
        self.cfg['rules'].append({'rule_id':'extra','source_evidence':['synthetic'],'component_id':999,'kind':'whole_component','code':17})
        with self.assertRaisesRegex(ValueError,'absent component'): self.runbuild()
        self.assertFalse((self.d/'out/report.json').exists())
    def test_footprint_mismatch(self):
        # Sorted component inventory falsely covers water.
        self.cfg['component_rows']=data(self.d/'badrows',[0,1,2])
        self.cfg['component_runs']=data(self.d/'bad',[0,4,self.root,0,4,self.root])
        with self.assertRaisesRegex(ValueError,'footprint'): self.runbuild()

if __name__=='__main__': unittest.main()
