import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from build_seavox_basin import contiguous_spans, validate_source, grid_bounds, selected_basin, validate_extraction


class BasinTest(unittest.TestCase):
    def test_selection_uses_stable_entity_bindings(self):
        data={'category_bindings':[{'entity_id':101,'code':6,'physical_class':'water'}],
              'basins':[{'id':'b1','source_id':'s1','source_version':'v1','source_feature_id':'123',
                         'geometry_sha256':'a'*64,'assignment_method':'single_continent_named_basin','participant_entity_ids':[101]}],
              'sources':[{'source_id':'s1','version':'v1','sha256':'b'*64}]}
        self.assertEqual(selected_basin(data,'b1')[2],6)
        with self.assertRaisesRegex(ValueError,'exactly one selected'): selected_basin(data,'missing')
        data['category_bindings'].append({'entity_id':101,'code':5,'physical_class':'water'})
        with self.assertRaisesRegex(ValueError,'unique water binding'): selected_basin(data,'b1')

    def test_span_extraction_and_geometry_bounds(self):
        self.assertEqual(contiguous_spans(np.array([False,True,True,False,True]),10),[(11,13),(14,15)])
        self.assertEqual(grid_bounds({'geometry':{'coordinates':[[[0,0],[45,45]]]}}),(65536,81920,16384,32768))

    def test_sparse_source_intersection_matches_dense(self):
        from build_seavox_basin import source_water_spans
        rng=np.random.default_rng(83612)
        for _ in range(500):
            width=257;physical=rng.choice([1,17],width).astype('u4')
            x0=int(rng.integers(0,width));x1=int(rng.integers(x0+1,width+1))
            mask=rng.integers(0,4,x1-x0,dtype='u1')
            stops=np.r_[np.flatnonzero(physical[1:]!=physical[:-1])+1,width].astype('u4')
            values=physical[stops-1]
            x=np.arange(x0,x1,dtype='u4')
            expected=contiguous_spans((mask!=0)&(values[np.searchsorted(stops,x,side='right')]==1),x0)
            self.assertEqual(source_water_spans(mask,x0,stops,values),expected)
        self.assertEqual(source_water_spans(np.zeros(10,dtype='u1'),0,np.array([10]),np.array([1])),[])

    def test_extraction_binds_archive_and_feature_to_decision(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); archive=root/'source.zip'; archive.write_bytes(b'archive')
            feature=root/'source.geojson'; feature.write_bytes(b'feature')
            sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            snapshot={'decision_revision':{'id':'d1','entity_revision':'e1'}}
            basin={'id':'b1','source_id':'s1','source_version':'v1','source_feature_id':'123','geometry_sha256':'a'*64}
            source={'sha256':sha(archive)}
            manifest={'schema':'worldatlas-seavox-archive-extraction-v1','decision_id':'b1','decision_snapshot_sha256':'d'*64,'decision_revision':'d1','entity_revision':'e1',
                      'source_id':'s1','source_version':'v1','source_feature_id':'123','archive_sha256':sha(archive),'geometry_sha256':'a'*64,
                      'feature_file':'source.geojson','feature_file_sha256':sha(feature)}
            mp=root/'manifest.json';mp.write_text(json.dumps(manifest)); pin=sha(mp)
            self.assertEqual(validate_extraction(mp,pin,archive,feature,snapshot,basin,source,'d'*64),manifest)
            archive.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'archive hash mismatch'): validate_extraction(mp,pin,archive,feature,snapshot,basin,source,'d'*64)
            archive.write_bytes(b'archive'); feature.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'feature file hash mismatch'): validate_extraction(mp,pin,archive,feature,snapshot,basin,source,'d'*64)
            with self.assertRaisesRegex(ValueError,'manifest hash mismatch'): validate_extraction(mp,'0'*64,archive,feature,snapshot,basin,source,'d'*64)

    def test_pinned_feature_identity_and_geometry(self):
        geom={'type':'Polygon','coordinates':[[[1,1],[2,1],[1,2],[1,1]]]}
        obj={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'mrgid_sr':'123'},'geometry':geom}]}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'source.json';path.write_text(json.dumps(obj));fsha=hashlib.sha256(path.read_bytes()).hexdigest()
            gsha=hashlib.sha256(json.dumps(geom,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
            self.assertEqual(validate_source(path,fsha,gsha,'123')['properties']['mrgid_sr'],'123')
            with self.assertRaisesRegex(ValueError,'source file hash'): validate_source(path,'0'*64,gsha,'123')
            with self.assertRaisesRegex(ValueError,'geometry hash'): validate_source(path,fsha,'0'*64,'123')
            with self.assertRaisesRegex(ValueError,'selected SeaVoX feature'): validate_source(path,fsha,gsha,'999')

    def test_original_uppercase_field_and_reject_extra_features(self):
        geom={'type':'Polygon','coordinates':[[[1,1],[2,1],[1,2],[1,1]]]}
        feature={'type':'Feature','properties':{'MRGID_SR':'123'},'geometry':geom}
        obj={'type':'FeatureCollection','features':[feature]}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'source.json'; path.write_text(json.dumps(obj))
            fsha=hashlib.sha256(path.read_bytes()).hexdigest()
            gsha=hashlib.sha256(json.dumps(geom,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
            self.assertEqual(validate_source(path,fsha,gsha,'123'),feature)
            obj['features'].append({'type':'Feature','properties':{'MRGID_SR':'999'},'geometry':geom})
            path.write_text(json.dumps(obj));fsha=hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'exactly one selected'):
                validate_source(path,fsha,gsha,'123')


if __name__ == '__main__': unittest.main()
