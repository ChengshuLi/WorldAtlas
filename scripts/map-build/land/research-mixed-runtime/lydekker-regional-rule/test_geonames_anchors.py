import hashlib
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from geonames_anchors import discover


def record(identifier,name,lon,lat,feature='ISL'):
    return '\t'.join([identifier,name,name,'',str(lat),str(lon),'T',feature,'ID']+['']*10)+'\n'
def pin(path): return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
class TestAnchorDiscovery(unittest.TestCase):
    def test_source_witnesses_resolve_unique_complete_roots(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);rows=d/'rows';runs=d/'runs';archive=d/'source.zip'
            rows.write_bytes(struct.pack('<IIIII',0,0,2,2,2));runs.write_bytes(struct.pack('<IIIIII',183,184,1,184,187,2))
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('ID.txt',record('100','Second Name',5.5,.5)+record('99','Main Island',4.5,.5)+record('101','Point In Water',9.5,.5))
            source={**pin(archive),'source_id':'geonames-country-id','source_version':'v1','country':'ID'}
            grid={'width':360,'height':4,'west':-180,'north':2,'step':1}
            components={1:{'total':1},2:{'total':3}}
            out=discover(source,pin(rows),pin(runs),grid,components,{2:{'code':22}},max_satellite_cells=1)
            self.assertEqual(out['anchors'][2]['source_feature_ids'],['99','100'])
            self.assertEqual(out['anchors'][2]['source_feature_id'],'99')
            self.assertEqual(out['statistics']['source_points_on_water'],1)
            self.assertEqual(out['statistics']['eligible_anchors'],1)
            self.assertEqual(out['anchors'][2]['source_sha256'],source['sha256'])
    def test_duplicate_source_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);rows=d/'rows';runs=d/'runs';archive=d/'source.zip'
            rows.write_bytes(struct.pack('<II',0,1));runs.write_bytes(struct.pack('<III',0,1,1))
            with zipfile.ZipFile(archive,'w') as z:z.writestr('ID.txt',record('99','Island',-179.5,.5)*2)
            source={**pin(archive),'source_id':'s','source_version':'v','country':'ID'}
            with self.assertRaisesRegex(ValueError,'island identity'):
                discover(source,pin(rows),pin(runs),{'width':360,'height':1,'west':-180,'north':1,'step':1},{1:{'total':1}},{1:{'code':18}},max_satellite_cells=1)
if __name__=='__main__':unittest.main()
