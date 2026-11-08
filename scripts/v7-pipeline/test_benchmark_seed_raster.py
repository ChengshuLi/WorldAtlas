import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import benchmark_seed_raster as bench
from compare_land_sweeps import source_module


def write(path,value):path.write_text(json.dumps(value))


class SeedRasterBenchmarkTests(unittest.TestCase):
    def fixture(self,root):
        staged=root/'staged';staged.mkdir();regions=root/'regions';regions.mkdir();geometry=regions/'shape.geojson'
        write(geometry,{'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':{'type':'Polygon','coordinates':[[[0,1],[2,1],[2,-1],[0,-1],[0,1]]]}}]})
        proof=geometry.with_name(geometry.name+'.report.json');write(proof,{'status':'fixture'})
        grid={'width':4,'height':2,'west':0,'north':1,'step':0.5}
        rows=staged/'fresh-components-rows';runs=staged/'fresh-components-runs'
        np.asarray([0,1,2],dtype='<u4').tofile(rows);np.asarray([(0,4,1),(0,4,1)],dtype='<u4').tofile(runs)
        pin=lambda path:{'path':str(path),'sha256':bench.digest(path)}
        component={'component_rows':pin(rows),'component_runs':pin(runs)}
        config={'schema':'direct-region-seed-research-v1','grid':{**grid,'crs':'EPSG:4326'},**component,
            'regions':[{'id':'area','geometry':pin(geometry),'witnesses':[]}],
            'rules':[{'component_id':1,'region_id':'area','inside_code':17,'outside_code':18}],
            'evidence':[],'strip_rows':1,'workers':1,'reserve_bytes':0}
        cfg=staged/'reference.json';write(cfg,config)
        builder=source_module('_seed_benchmark_fixture',bench.RASTER/'build_seed.py',bench.digest(bench.RASTER/'build_seed.py'))
        expected=builder.build(cfg,root/'reference')
        metadata=staged/'additional-metadata';metadata.mkdir();archive=metadata/'fresh-stage2-rasterizer-report';write(archive,expected)
        seed={'grid':grid,'rasterizer_report_sha256':bench.digest(archive),'resource_controls':{'strip_rows':1},
            'seed_rules':[{'component_id_current_generation_only':1,'region_id':'area','inside_code':17,'outside_code':18}]}
        tiles=root/'tiles';tiles.mkdir();tile=tiles/'00000-00000.bin'
        np.asarray([(0,0,4,17),(1,0,4,17)],dtype='<u4').tofile(tile)
        manifest=tiles/'manifest.txt';manifest.write_text(f'0 0 2 1 {bench.digest(tile)}\n')
        write(staged/'fresh-stage2-seed-report',seed);write(staged/'fresh-stage2-core-config',{'grid':grid,'inputs':{**component,'tile_manifest':pin(manifest)}})
        assets={p.name:{'sha256':bench.digest(p),'size_bytes':p.stat().st_size} for p in staged.iterdir() if p.is_file()}
        write(staged/'plan.json',{'grid':grid,'assets':assets})
        write(regions/'report.json',{'status':'exact-pinned-polygons-recreated-with-fresh-closure-proofs','publishable':False,
            'staging_plan_sha256':bench.digest(staged/'plan.json'),'rasterizer_report_sha256':bench.digest(archive),
            'regions':[{'region_id':'area','geometry':pin(geometry),'witnesses':[],'report_sha256':bench.digest(proof)}]})
        return staged,regions

    def test_complete_in_process_pair_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);staged,regions=self.fixture(root);out=root/'pair'
            with patch('subprocess.Popen',side_effect=AssertionError('no process')),patch('ctypes.CDLL',side_effect=AssertionError('no bridge')):
                result=bench.run(staged,regions,out,2,verify_tiles=root/'tiles')
            self.assertEqual(result['status'],'complete-seed-streams-and-populations-exact')
            self.assertEqual(result['results'][0]['outputs_sha256'],result['results'][1]['outputs_sha256'])
            self.assertEqual(result['tile_verification']['tile_records'],2)
            with self.assertRaises(FileExistsError):bench.run(staged,regions,out,2)

    def test_source_geometry_and_fresh_proof_tampering_fail(self):
        for target in ('shape.geojson','shape.geojson.report.json'):
            with self.subTest(target=target),tempfile.TemporaryDirectory() as td:
                root=Path(td);staged,regions=self.fixture(root);(regions/target).write_text('{}')
                with self.assertRaisesRegex(ValueError,'differs'):bench.run(staged,regions,root/'pair',2)
                self.assertFalse((root/'pair').exists())


if __name__=='__main__':unittest.main()
