from functools import partial
from unittest import mock
import tempfile
import unittest
from pathlib import Path
import struct
import numpy as np

import numeric_land_stream
import test_write_land_stream as fixture
from ural_delta import SCHEMA,split_scope


class _NumericMixin:
    def setUp(self):
        super().setUp()
        patcher=mock.patch.object(fixture,'write_land_stream',new=partial(numeric_land_stream.write_land_stream,batch_rows=self.batch_rows))
        patcher.start();self.addCleanup(patcher.stop)


class NumericWriterOneRow(_NumericMixin,fixture.WriterTest):batch_rows=1
class NumericWriterBatches(_NumericMixin,fixture.WriterTest):batch_rows=128


def streams(directory,components,physical,seed):
    paths=[]
    for number,rows in enumerate((components,physical,seed)):
        offsets=[0];flat=[]
        for row in rows:flat.extend(row);offsets.append(len(flat))
        rowpath=directory/f'{number}.rows';runpath=directory/f'{number}.runs'
        np.asarray(offsets,dtype='<u4').tofile(rowpath);np.asarray(flat,dtype='<u4').tofile(runpath);paths.extend((rowpath,runpath))
    return paths


def full(row):
    return [(x+1,int(value)) for x,value in enumerate(row) if x+1==len(row) or row[x+1]!=value]


class NumericWriterOracles(unittest.TestCase):
    def test_random_layouts_match_legacy_reports_and_dense_pixels(self):
        random=np.random.default_rng(863491)
        for width,height in ((2,3),(7,135),(31,9)):
            for trial in range(6):
                roots=random.choice([-1,0,5,19,0xffffffff],size=(height,width));roots.flat[:4]=[0,5,19,0xffffffff]
                physical=np.where(roots<0,1,17).astype('u4')
                seed=np.where(roots==0,random.integers(17,20,size=roots.shape),np.where(roots==5,22,0)).astype('u4')
                expected=np.where(roots<0,0,np.where(np.isin(roots,[0,5]),seed,np.where(roots==19,21,20)))
                components=[]
                for row in roots:
                    spans=[];start=0
                    while start<width:
                        end=start+1
                        while end<width and row[end]==row[start]:end+=1
                        if row[start]>=0:spans.append((start,end,int(row[start])))
                        start=end
                    components.append(spans)
                with self.subTest(width=width,height=height,trial=trial),tempfile.TemporaryDirectory() as temp:
                    directory=Path(temp);paths=streams(directory,components,list(map(full,physical)),list(map(full,seed)))
                    rootfile=directory/'roots';codefile=directory/'codes'
                    np.asarray([19,0xffffffff],dtype='<u4').tofile(rootfile);codefile.write_bytes(bytes([21,20]))
                    reference=fixture.write_land_stream(width,height,*paths,rootfile,codefile,[0,5],directory/'reference',disk_reserve_bytes=0)
                    for batch in (1,3,128):
                        out=directory/str(batch)
                        actual=numeric_land_stream.write_land_stream(width,height,*paths,rootfile,codefile,[0,5],out,disk_reserve_bytes=0,batch_rows=batch)
                        self.assertEqual(actual,reference)
                        for kind in ('rows','runs'):self.assertEqual((out/(kind+'.u32le')).read_bytes(),(directory/'reference'/(kind+'.u32le')).read_bytes())
                        offsets=np.fromfile(out/'rows.u32le',dtype='<u4');records=np.fromfile(out/'runs.u32le',dtype='<u4').reshape(-1,2)
                        dense=np.zeros((height,width),dtype=np.uint32)
                        for y in range(height):
                            start=0
                            for end,code in records[offsets[y]:offsets[y+1]]:dense[y,start:end]=code;start=int(end)
                            self.assertEqual(start,width)
                        np.testing.assert_array_equal(dense,expected)

    def test_wide_override_does_not_expand_water_pixels(self):
        width=0xffffffff;height=1;bounds=[-180,-90,180,90]
        line,europe,asia=split_scope([[0,-90],[0,90]],bounds,[-90,0],[90,0])
        rule={'schema':SCHEMA,'revision':'synthetic','boundary_id':'divider','boundary_sha256':'0'*64,
            'route_id':'closure','route_sha256':'1'*64,'scope_bounds':bounds,'europe_code':19,'asia_code':18,
            'grid':{'width':width,'height':height,'west':-180,'north':90,'step':360/width},
            'line_scope_vertices':line,'europe_ring':europe,'asia_ring':asia}
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);paths=streams(directory,[[(0,1,1),(width-1,width,2)]],
                [[(1,17),(width-1,1),(width,17)]],[[(1,19),(width-1,0),(width,18)]])
            rootfile=directory/'roots';codefile=directory/'codes';rootfile.write_bytes(b'');codefile.write_bytes(b'');out=directory/'out'
            arange=np.arange
            def ordinary_range(*args,**kwargs):
                if len(args)==1 and args[0]>10000:raise AssertionError('pixel-sized range')
                return arange(*args,**kwargs)
            with mock.patch('numpy.arange',side_effect=ordinary_range),mock.patch.object(numeric_land_stream,'classify_cell',wraps=numeric_land_stream.classify_cell) as classify,mock.patch('subprocess.Popen',side_effect=AssertionError('no process')),mock.patch('ctypes.CDLL',side_effect=AssertionError('no bridge')):
                report=numeric_land_stream.write_land_stream(width,height,*paths,rootfile,codefile,[1,2],out,disk_reserve_bytes=0,delta_rule=rule)
            self.assertEqual(classify.call_count,2);self.assertEqual(report['ural_delta']['counts']['land_centers'],2)
            self.assertEqual((out/'runs.u32le').read_bytes(),struct.pack('<IIIIII',1,19,width-1,0,width,18))
