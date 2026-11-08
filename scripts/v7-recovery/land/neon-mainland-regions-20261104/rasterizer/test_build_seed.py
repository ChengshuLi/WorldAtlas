import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from osgeo import gdal, ogr

import build_seed


def pin(path):
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def decode(directory, width, height):
    offsets=np.fromfile(directory/'rows.u32le',dtype='<u4')
    runs=np.fromfile(directory/'runs.u32le',dtype='<u4').reshape(-1,2)
    dense=np.zeros((height,width),dtype=np.uint8)
    for y in range(height):
        start=0
        for end,code in runs[offsets[y]:offsets[y+1]]:
            dense[y,start:end]=code;start=int(end)
        if start!=width:raise AssertionError('incomplete row')
    return dense


class SeedBuildTests(unittest.TestCase):
    def fixture(self,root,step,strip,workers):
        source=root/'source';source.mkdir()
        width,height=13,9
        grid={'width':width,'height':height,'west':-7.3,'north':4.1,'step':step,'crs':'EPSG:4326'}
        regions=[]
        for i,(a,b,c,d) in enumerate(((1.5,7.5,1.5,7.5),(5,11,0,9))):
            # Include vertices on pixel centers and a nonbinary global affine.
            ring=[[grid['west']+x*step,grid['north']-y*step] for x,y in ((a,c),(b,c),(b,d),(a,d),(a,c))]
            path=source/f'{i}.geojson'
            path.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':{'type':'Polygon','coordinates':[ring]}}]}))
            regions.append({'id':str(i),'geometry':pin(path),'witnesses':[]})
        records=[];offsets=[0];roots=np.zeros((height,width),dtype=np.uint32)
        for y in range(height):
            # Vary boundaries and include empty physical rows, unknown roots,
            # zero and maximum uint32 identities, and a whole-component rule.
            if y!=3:
                for a,b,r in ((0,3,0),(4,8,0xffffffff),(8,11,42),(12,13,77)):
                    if (r==0 and y>=5) or (r==0xffffffff and y<5):continue
                    records.append((a,b,r));roots[y,a:b]=r
            offsets.append(len(records))
        rowpath=source/'rows';runpath=source/'runs'
        np.asarray(offsets,dtype='<u4').tofile(rowpath)
        np.asarray(records,dtype='<u4').tofile(runpath)
        rules=[{'component_id':0,'region_id':'0','inside_code':17,'outside_code':18},
               {'component_id':0xffffffff,'region_id':'1','inside_code':19,'outside_code':20},
               {'component_id':42,'region_id':None,'inside_code':21,'outside_code':21}]
        config={'schema':'direct-region-seed-research-v1','grid':grid,'component_rows':pin(rowpath),'component_runs':pin(runpath),'regions':regions,'rules':rules,'evidence':[],'strip_rows':strip,'workers':workers,'reserve_bytes':0}
        path=source/'config.json';path.write_text(json.dumps(config))
        expected=np.zeros((height,width),dtype=np.uint8);pop={str(r['component_id']):[0,0] for r in rules}
        for y in range(0,height,strip):
            h=min(strip,height-y);ds=gdal.GetDriverByName('MEM').Create('',width,h,1,gdal.GDT_Byte)
            ds.SetGeoTransform((grid['west'],step,0,grid['north']-y*step,0,-step))
            for i,region in enumerate(regions):
                source_ds=ogr.Open(region['geometry']['path']);gdal.RasterizeLayer(ds,[1],source_ds.GetLayer(0),burn_values=[1<<i],options=['MERGE_ALG=ADD'])
            mask=ds.ReadAsArray()
            for row in range(y,y+h):
                for a,b,r in records[offsets[row]:offsets[row+1]]:
                    for rule in rules:
                        if rule['component_id']!=r:continue
                        for x in range(a,b):
                            inside=rule['region_id'] is None or bool(mask[row-y,x] & (1<<int(rule['region_id'])))
                            expected[row,x]=rule['inside_code'] if inside else rule['outside_code'];pop[str(r)][0 if inside else 1]+=1
        return path,expected,pop

    def test_parallel_and_serial_match_independent_dense_oracle(self):
        for step in (0.25,0.17):
            for strip in (1,4,9):
                outputs=[]
                for workers in (1,3):
                    with self.subTest(step=step,strip=strip,workers=workers),tempfile.TemporaryDirectory() as td:
                        root=Path(td);config,expected,pop=self.fixture(root,step,strip,workers);out=root/'output'
                        with mock.patch('subprocess.Popen',side_effect=AssertionError('no process')),mock.patch('ctypes.CDLL',side_effect=AssertionError('no bridge')):
                            report=build_seed.build(config,out)
                        np.testing.assert_array_equal(decode(out,13,9),expected)
                        self.assertEqual(report['rule_population'],{r:{'inside_cells':v[0],'outside_cells':v[1]} for r,v in pop.items()})
                        self.assertEqual(report['category_cell_counts'],{str(c):int(np.count_nonzero(expected==c)) for c in range(17,23)})
                        self.assertNotIn('compiled_kernel',report['program_sha256'])
                        if strip==1:self.assertLess(report['execution']['polygon_burns'],report['execution']['possible_polygon_burns'])
                        outputs.append(((out/'rows.u32le').read_bytes(),(out/'runs.u32le').read_bytes()))
                self.assertEqual(*outputs)

    def test_missing_root_and_invalid_offsets_never_complete(self):
        for kind in ('root','offsets'):
            with tempfile.TemporaryDirectory() as td:
                root=Path(td);config,_,_=self.fixture(root,0.25,4,1);c=json.loads(config.read_text())
                if kind=='root':c['rules'][0]['component_id']=999
                else:
                    p=Path(c['component_rows']['path']);v=np.fromfile(p,dtype='<u4');v[2]=0;v.tofile(p);c['component_rows']=pin(p)
                config.write_text(json.dumps(c));out=root/'output'
                with self.assertRaises(ValueError):build_seed.build(config,out)
                self.assertFalse((out/'report.json').exists())

    def test_occupied_dangling_output_is_not_followed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);config,_,_=self.fixture(root,0.25,4,1);out=root/'output';target=root/'missing';out.symlink_to(target)
            with self.assertRaisesRegex(ValueError,'output exists'):build_seed.build(config,out)
            self.assertFalse(target.exists())


if __name__=='__main__':unittest.main()
