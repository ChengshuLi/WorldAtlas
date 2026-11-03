import json,tempfile,unittest
from pathlib import Path
import numpy as np
from osgeo import gdal,osr
import compose_physical as b

class ComposeTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.d=Path(self.t.name);self.inputs=self.d/'inputs';self.inputs.mkdir();self.cfg={'schema':'candidate-physical-composition-v1','selection_notes':'synthetic test','minimum_free_bytes':0,'grid':{'width':8,'height':4,'west':-180,'north':90,'step':45}}
        land=np.zeros((4,8),dtype=np.uint8);land[:2,:3]=1
        water=np.zeros((4,8),dtype=np.uint8);water[0,0]=1
        ref=np.zeros((4,8),dtype=np.uint8);ref[:2,:2]=1
        for name,values in [('land',land),('water',water),('reference_mask',ref)]:
            path=self.inputs/(name+'.tif');ds=gdal.GetDriverByName('GTiff').Create(str(path),8,4,1,gdal.GDT_Byte);ds.SetGeoTransform((-180,45,0,90,0,-45));s=osr.SpatialReference();s.ImportFromEPSG(4326);ds.SetSpatialRef(s);ds.GetRasterBand(1).WriteArray(values);ds=None
            self.cfg[name]={'path':str(path),'sha256':b.sha(path)}
        rows=[0];pairs=[]
        for row in ref:
            codes=np.where(row,17,1);ends=np.flatnonzero(np.r_[codes[1:] != codes[:-1],True]);pairs.extend((int(x+1),int(codes[x])) for x in ends);rows.append(len(pairs))
        rp=self.inputs/'rows.u32';up=self.inputs/'runs.u32';np.asarray(rows,dtype='<u4').tofile(rp);np.asarray(pairs,dtype='<u4').tofile(up)
        self.cfg['reference_streams']={'rows':{'path':str(rp),'sha256':b.sha(rp)},'runs':{'path':str(up),'sha256':b.sha(up)}}
        self.p=self.inputs/'config.json';self.p.write_text(json.dumps(self.cfg))
    def tearDown(self):self.t.cleanup()
    def test_compose_and_compare(self):
        out=self.d/'out';b.main(self.p,out);r=json.loads((out/'report.json').read_text())
        self.assertEqual((r['candidate_dry_cells'],r['historic_dry_cells'],r['candidate_extra_land_cells'],r['candidate_missing_land_cells']),(5,4,2,1))
        self.assertEqual(r['mismatch_spans'],3)
        with self.assertRaises(FileExistsError):b.main(self.p,out)
        with self.assertRaises(ValueError):b.main(self.p,self.inputs/'nested')
        with self.assertRaises(ValueError):b.main(self.p,self.d)
    def test_without_reference(self):
        self.cfg.pop('reference_mask'); self.cfg.pop('reference_streams')
        self.p.write_text(json.dumps(self.cfg)); out=self.d/'no-reference'
        b.main(self.p,out); r=json.loads((out/'report.json').read_text())
        self.assertEqual(r['candidate_dry_cells'],5)
        self.assertNotIn('historic_dry_cells',r)
        self.assertEqual(r['grid'],self.cfg['grid'])
        self.assertEqual(r['inputs']['land'],self.cfg['land'])
        rows=np.fromfile(out/'rows.u32le',dtype='<u4')
        runs=np.fromfile(out/'runs.u32le',dtype='<u4').reshape(-1,2)
        self.assertEqual(rows.tolist(),[0,3,5,6,7])
        self.assertEqual(runs.tolist(),[[1,1],[3,17],[8,1],[3,17],[8,1],[8,1],[8,1]])

    def test_rejects_partial_reference(self):
        self.cfg.pop('reference_streams'); self.p.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'provided together'):b.main(self.p,self.d/'partial')
        self.assertFalse((self.d/'partial').exists())

    def test_rejects_negative_in_every_mask(self):
        for name in ('land','water','reference_mask'):
            original=self.cfg[name];p=self.inputs/(name+'-negative.tif')
            ds=gdal.GetDriverByName('GTiff').Create(str(p),8,4,1,gdal.GDT_Int16);ds.SetGeoTransform((-180,45,0,90,0,-45))
            sr=osr.SpatialReference();sr.ImportFromEPSG(4326);ds.SetSpatialRef(sr);a=np.zeros((4,8),dtype=np.int16);a[0,0]=-1;ds.GetRasterBand(1).WriteArray(a);ds=None
            self.cfg[name]={'path':str(p),'sha256':b.sha(p)};self.p.write_text(json.dumps(self.cfg))
            with self.assertRaisesRegex(ValueError,'nonbinary'):b.main(self.p,self.d/('bad-'+name))
            self.cfg[name]=original
    def test_rejects_zero_length_first_run(self):
        p=Path(self.cfg['reference_streams']['runs']['path']);x=np.fromfile(p,dtype='<u4');x[0]=0;x.tofile(p)
        self.cfg['reference_streams']['runs']['sha256']=b.sha(p);self.p.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'invalid reference row'):b.main(self.p,self.d/'zero-run')
    def test_bad_grid_and_hash_fail_before_output(self):
        self.cfg['grid']['step']=0;self.p.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'invalid grid'):b.main(self.p,self.d/'bad-grid')
        self.assertFalse((self.d/'bad-grid').exists())
        self.cfg['grid']['step']=45;self.cfg['land']['sha256']='0'*64;self.p.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'input hash mismatch'):b.main(self.p,self.d/'bad-hash')
        self.assertFalse((self.d/'bad-hash').exists())

    def test_reject_reference_mismatch(self):
        p=Path(self.cfg['reference_mask']['path']);ds=gdal.Open(str(p),gdal.GA_Update);a=ds.ReadAsArray();a[3,3]=1;ds.GetRasterBand(1).WriteArray(a);ds=None
        self.cfg['reference_mask']['sha256']=b.sha(p);self.p.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'historic binary mask disagrees'):b.main(self.p,self.d/'bad')
        self.assertFalse((self.d/'bad'/'report.json').exists())
if __name__=='__main__':unittest.main()
