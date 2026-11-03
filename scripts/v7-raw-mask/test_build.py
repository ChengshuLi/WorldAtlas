#!/usr/bin/python3
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from osgeo import gdal
from build import build, compare_row


def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def polygon(x0,y0,x1,y1):
    return {'type':'Polygon','coordinates':[[[x0,y0],[x1,y0],[x1,y1],[x0,y1],[x0,y0]]]}

def geojson(path, features):
    path.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':p,'geometry':g} for p,g in features]}))

class BuilderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        land, water = self.d/'land.geojson', self.d/'water.geojson'
        geojson(land, [({'keep':1},polygon(-3,-2,3,2)), ({'keep':0},polygon(3,-2,4,2))])
        geojson(water, [({'kind':'lake'},polygon(-1,-1,1,1)), ({'kind':'label'},polygon(-3,1,-2,2))])
        def spec(p, where): return {'dataset':str(p), 'files':[{'path':str(p),'sha256':digest(p)}], 'where':where}
        self.cfg = {'schema':'raw-physical-mask-prototype-v1', 'grid':{'width':8,'height':4,'step':1,'west':-4,'north':2},
                    'land':[spec(land,'keep = 1')], 'water':[spec(water,"kind = 'lake'")], 'strip_rows':2,
                    'selection_notes':'Synthetic polygons only; no historical claim.'}
        self.cfgfile=self.d/'config.json'
    def run_build(self, out):
        self.cfgfile.write_text(json.dumps(self.cfg))
        build(self.cfgfile, out)
    def decoded(self, out):
        rows=np.fromfile(out/'rows.u32le','<u4'); runs=np.fromfile(out/'runs.u32le','<u4').reshape(-1,2)
        return [np.repeat(runs[rows[y]:rows[y+1],1], np.diff(np.r_[0,runs[rows[y]:rows[y+1],0]]).astype(int)).tolist() for y in range(4)]
    def test_filtered_land_water_and_exact_reference(self):
        one=self.d/'one'; self.run_build(one)
        self.assertEqual(self.decoded(one),[[1,17,17,17,17,17,17,1],[1,17,17,1,1,17,17,1],[1,17,17,1,1,17,17,1],[1,17,17,17,17,17,17,1]])
        self.cfg['reference']={x:{'path':str(one/(x+'.u32le')),'sha256':digest(one/(x+'.u32le'))} for x in ['rows','runs']}
        two=self.d/'two'; self.run_build(two)
        self.assertEqual(json.loads((two/'report.json').read_text())['comparison']['mismatched_cells'],0)
        self.cfg['water'][0]['where']="kind = 'label'"
        three=self.d/'three'; self.run_build(three)
        self.assertEqual(json.loads((three/'report.json').read_text())['comparison']['mismatched_cells'],5)
        with self.assertRaises(FileExistsError): self.run_build(one)
    def test_partition_and_strip_invariance(self):
        self.run_build(self.d/'one')
        second = self.d/'second.geojson'
        geojson(second, [({'keep':1}, polygon(3,-2,4,2))])
        self.cfg['land'].append({'dataset':str(second),'files':[{'path':str(second),'sha256':digest(second)}],'where':'keep = 1'})
        self.cfg['strip_rows']=1
        self.run_build(self.d/'two')
        self.cfg['strip_rows']=4
        self.run_build(self.d/'three')
        self.assertEqual(digest(self.d/'two'/'runs.u32le'),digest(self.d/'three'/'runs.u32le'))
        self.assertNotEqual(digest(self.d/'one'/'runs.u32le'),digest(self.d/'two'/'runs.u32le'))
    def test_hash_and_reference_validation(self):
        self.cfg['land'][0]['files'][0]['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'digest mismatch'): self.run_build(self.d/'bad')
        self.assertFalse((self.d/'bad').exists())
        with self.assertRaisesRegex(ValueError,'invalid reference row'):
            compare_row(np.array([1,17]),np.array([[1,1]],dtype=np.uint32),2)
    def test_invalid_geometry_rejected(self):
        bad=self.d/'bad.geojson'
        geojson(bad,[({}, {'type':'Polygon','coordinates':[[[0,0],[1,1],[1,0],[0,1],[0,0]]]})])
        self.cfg['land']=[{'dataset':str(bad),'files':[{'path':str(bad),'sha256':digest(bad)}],'where':None}]
        with self.assertRaisesRegex(ValueError,'invalid geometry'): self.run_build(self.d/'bad-out')
    def test_selection_must_be_explicit(self):
        del self.cfg['water'][0]['where']
        with self.assertRaisesRegex(ValueError,'predicate must be explicit'): self.run_build(self.d/'bad')

if __name__ == '__main__': unittest.main()
