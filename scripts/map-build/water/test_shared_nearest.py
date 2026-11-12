import json
import unittest
import numpy as np
from map_build.water import shared_nearest as s


def rle(array):
    rows=[0]; runs=[]
    for row in array:
        for i,x in enumerate(row):
            if i==len(row)-1 or row[i+1]!=x: runs.extend((i+1,int(x)))
        rows.append(len(runs)//2)
    return np.array(rows,dtype='<u4'),np.array(runs,dtype='<u4')


def snapshot():
    return {'category_bindings':[
        {'entity_id':11,'physical_class':'land','code':17},{'entity_id':11,'physical_class':'water','code':1},
        {'entity_id':22,'physical_class':'land','code':18},{'entity_id':22,'physical_class':'water','code':2}]}


def basin(order=(22,11), tolerance='0.00001'):
    return {'assignment_method':'shared_nearest_assigned_shore','participant_entity_ids':[11,22],
            'tie_rules':{'method':'within_minimum_distance_tolerance','tie_break':'first_entity_in_priority_order',
                         'tolerance_metres':tolerance,'priority_entity_ids':list(order)}}


class SharedTest(unittest.TestCase):
    def test_priority_is_entity_order_not_category_order(self):
        pairs,t=s.selected_rules(snapshot(),basin())
        self.assertEqual(pairs,[(22,18,2),(11,17,1)])
        # Symmetrical two-cell shores with a center water cell.
        p=np.ones((6,12),dtype=np.uint8); p[2,4]=p[2,6]=17
        l=np.zeros_like(p); l[2,4]=17; l[2,6]=18
        edges=s.centers_for_crop(rle(p),rle(l),(0,12,0,6),12,6,30,[17,18])
        indexes=s.make_indexes(edges,pairs)
        result,cert,exact=s.classify(np.array([15.]),np.array([-15.]),(0,12,0,6),12,6,30,pairs,t,indexes)
        self.assertEqual(result.tolist(),[2]); self.assertEqual((cert,exact),(0,1))
        pairs,t=s.selected_rules(snapshot(),basin((11,22)))
        result,_,_=s.classify(np.array([15.]),np.array([-15.]),(0,12,0,6),12,6,30,pairs,t,s.make_indexes(edges,pairs))
        self.assertEqual(result.tolist(),[1])

    def test_nearest_and_wrap(self):
        p=np.ones((6,12),dtype=np.uint8); p[2,0]=p[2,4]=17
        l=np.zeros_like(p); l[2,0]=17; l[2,4]=18
        self.assertEqual(s.crop(*rle(p),2,-1,2,12).tolist(),[1,17,1])
        pairs,t=s.selected_rules(snapshot(),basin())
        edges=s.centers_for_crop(rle(p),rle(l),(0,12,0,6),12,6,30,[17,18])
        codes,cert,exact=s.classify(np.array([15.,15.]),np.array([165.,-45.]),(0,12,0,6),12,6,30,pairs,t,s.make_indexes(edges,pairs))
        self.assertEqual(codes.tolist(),[1,2]);self.assertEqual(cert+exact,2)

    def test_fails_closed_on_unknown_rules_or_missing_bindings(self):
        for bad in ({}, {'method':'other','tie_break':'first_entity_in_priority_order','priority_entity_ids':[11,22],'tolerance_metres':'0.00001'},
                    {'method':'within_minimum_distance_tolerance','tie_break':'first_entity_in_priority_order','priority_entity_ids':[11,11],'tolerance_metres':'0.00001'}):
            b=basin(); b['tie_rules']=bad
            with self.assertRaises(ValueError):s.selected_rules(snapshot(),b)
        b=basin();b['tie_rules']['additional_constraint']='unknown'
        with self.assertRaises(ValueError):s.selected_rules(snapshot(),b)
        data=snapshot();data['category_bindings'].pop()
        with self.assertRaises(ValueError):s.selected_rules(data,basin())
        for t in ['nan','-1','2',None,True]:
            with self.assertRaises(ValueError):s.selected_rules(snapshot(),basin(tolerance=t))

    def test_uncertified_crop_rejected(self):
        p=np.ones((6,12),dtype=np.uint8);p[2,4]=p[2,6]=17
        l=np.zeros_like(p);l[2,4]=17;l[2,6]=18
        pairs,t=s.selected_rules(snapshot(),basin())
        bounds=(3,8,1,5); edges=s.centers_for_crop(rle(p),rle(l),bounds,12,6,30,[17,18]);idx=s.make_indexes(edges,pairs)
        # Exactly on a crop boundary cannot prove omitted shore irrelevance.
        with self.assertRaisesRegex(ValueError,'increase halo'):
            s.classify(np.array([15.]),np.array([-90.]),bounds,12,6,30,pairs,t,idx)

    def test_missing_shore_and_bad_physical_fails(self):
        p=np.ones((6,12),dtype=np.uint8);p[2,4]=17;l=np.zeros_like(p);l[2,4]=17
        pairs,_=s.selected_rules(snapshot(),basin())
        edges=s.centers_for_crop(rle(p),rle(l),(0,12,0,6),12,6,30,[17,18])
        with self.assertRaisesRegex(ValueError,'no shoreline'):s.make_indexes(edges,pairs)
        l[2,4]=0
        with self.assertRaisesRegex(ValueError,'invalid'):s.centers_for_crop(rle(p),rle(l),(0,12,0,6),12,6,30,[17,18],all_land_codes=[17,18])
        # Never narrow untrusted uint32 values before physical/land validation.
        p=p.astype(np.uint32);l=l.astype(np.uint32);l[2,4]=273
        with self.assertRaisesRegex(ValueError,'invalid'):s.centers_for_crop(rle(p),rle(l),(0,12,0,6),12,6,30,[17,18],all_land_codes=[17,18])
        l[2,4]=17;p[2,5]=257
        with self.assertRaisesRegex(ValueError,'invalid'):s.centers_for_crop(rle(p),rle(l),(0,12,0,6),12,6,30,[17,18])


class FullBuilderTest(unittest.TestCase):
    def test_draft_source_to_shared_assignment(self):
        import tempfile, hashlib, gzip, sys
        from pathlib import Path
        import build_seavox_basin as m
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'in';out=Path(d)/'out';root.mkdir()
            geometry={'type':'Polygon','coordinates':[[[-60,0],[30,0],[30,30],[-60,30],[-60,0]]]}
            geo={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'MRGID_SR':'123'},'geometry':geometry}]}
            src=root/'geo.json';src.write_text(json.dumps(geo));h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            gh=hashlib.sha256(json.dumps(geometry,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
            b=basin();b.update(id='b',source_id='s',source_version='v',source_feature_id='123',geometry_sha256=gh)
            doc={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export',
                 'decision_revision':{'id':'d','status':'draft','entity_revision':'e'},
                 'entity_revision':{'id':'e','status':'draft'},**snapshot(),
                 'basins':[b],'sources':[{'source_id':'s','version':'v','sha256':h(src)}]}
            sp=root/'snapshot.json';sp.write_text(json.dumps(doc))
            p=np.ones((6,12),dtype=np.uint8);p[2,4]=p[2,6]=17
            l=np.zeros_like(p);l[2,4]=17;l[2,6]=18
            for name,arr in [('physical',p),('land',l)]:
                rows,runs=rle(arr);rows.tofile(root/f'{name}-rows');runs.tofile(root/f'{name}-runs')
            old=(m.W,m.H,m.STEP,sys.argv);m.W,m.H,m.STEP=12,6,30
            try:
                sys.argv=['build','--input-root',str(root),'--geometry',str(src),'--decision-id','b',
                    '--policy',str(sp),'--policy-sha256',h(sp),'--rows',str(root/'physical-rows'),
                    '--rows-sha256',h(root/'physical-rows'),'--runs',str(root/'physical-runs'),
                    '--runs-sha256',h(root/'physical-runs'),'--land-rows',str(root/'land-rows'),
                    '--land-rows-sha256',h(root/'land-rows'),'--land-runs',str(root/'land-runs'),
                    '--land-runs-sha256',h(root/'land-runs'),'--shore-pad-degrees','180',
                    '--out',str(out),'--allow-unverified-snapshot','--allow-draft-snapshot',
                    '--research-shore-method','wgs84-coastal-4neighbor-center-v2','--research-interval']
                m.main()
                interval_argv=list(sys.argv)
                baseline_out=Path(d)/'baseline-out'
                sys.argv=[str(baseline_out) if arg==str(out) else arg for arg in sys.argv if arg!='--research-interval']+['--pointwise-nearest']
                m.main()
                baseline_argv=list(sys.argv)
                rectangle_out=Path(d)/'rectangle-out'
                sys.argv=[str(rectangle_out) if arg==str(out) else arg for arg in interval_argv if arg!='--research-interval']
                m.main()
                rectangle_manifest=json.loads((rectangle_out/'manifest.json').read_text())
                self.assertEqual(rectangle_manifest['nearest_assignment_audit']['execution_method'],'wgs84-center-rectangle-v1')
                from build_prefill_plan import validate_shared_audit
                validate_shared_audit(rectangle_manifest)
                with gzip.open(out/'basin-assignment.jsonl.gz','rb') as reference, gzip.open(rectangle_out/'basin-assignment.jsonl.gz','rb') as rectangular:
                    self.assertEqual(reference.read(),rectangular.read())
                sys.argv=baseline_argv
                # A helper changed after processing must not produce a completed manifest.
                from unittest.mock import patch
                tamper_out=Path(d)/'tamper-out'; seen=[0]
                sys.argv=[str(tamper_out) if arg==str(baseline_out) else arg for arg in sys.argv if arg!='--pointwise-nearest']
                def changed_digest(path):
                    if Path(path).resolve()==Path(m.exclusive_outputs.__file__).resolve():
                        seen[0]+=1
                        if seen[0]>1:return '0'*64
                    return h(Path(path))
                with patch.object(m,'digest',side_effect=changed_digest):
                    with self.assertRaisesRegex(ValueError,'helper code changed'):
                        m.main()
                self.assertFalse((tamper_out/'manifest.json').exists())
            finally: m.W,m.H,m.STEP,sys.argv=old
            with gzip.open(out/'basin-assignment.jsonl.gz','rb') as generated, gzip.open(baseline_out/'basin-assignment.jsonl.gz','rb') as reference:
                self.assertEqual(generated.read(),reference.read())
            baseline=json.loads((baseline_out/'manifest.json').read_text())
            self.assertEqual(baseline['nearest_assignment_audit']['shore_method'],'wgs84-coastal-4neighbor-center-v2 (research, not an approved decision)')
            self.assertNotIn('execution_method',baseline['nearest_assignment_audit'])
            with gzip.open(out/'basin-assignment.jsonl.gz','rt') as f: record=json.loads(f.readline())
            self.assertEqual(record['row'],2);self.assertEqual([(q['start'],q['end'],q['code']) for q in record['spans']],[(5,6,2)])
            manifest=json.loads((out/'manifest.json').read_text())
            self.assertEqual(manifest['physical_water_cells'],1)
            self.assertEqual(manifest['source']['tie_rules'],b['tie_rules'])
            self.assertEqual(manifest['source']['land_runs_sha256'],h(root/'land-runs'))
            self.assertEqual(manifest['nearest_assignment_audit']['exact_distance_cells'],1)
            audit=manifest['nearest_assignment_audit']
            self.assertEqual(audit['shore_method'],'wgs84-coastal-center-interval-v1 (research, not an approved decision)')
            self.assertEqual(audit['execution_method'],'wgs84-center-row-interval-v1')
            self.assertEqual(audit['interval_nearest_sha256'],h(Path(m.interval_nearest.__file__)))
            self.assertEqual(audit['helper_code_sha256'],{name:h(Path(module.__file__)) for name,module in [('exclusive_outputs',m.exclusive_outputs),('decision_snapshot',m.decision_snapshot),('seavox_properties',m.seavox_properties)]})
            self.assertEqual(audit['software'],{'python':m.platform.python_version(),'numpy':m.np.__version__,'scipy':m.scipy.__version__,'pyproj':m.pyproj.__version__,'proj':m.pyproj.proj_version_str})
            self.assertEqual(audit['certified_bound_cells']+audit['exact_distance_cells'],manifest['physical_water_cells'])


class DirectBuilderRegression(unittest.TestCase):
    def test_one_row_direct_basin_raster_is_not_lost(self):
        import tempfile, hashlib, gzip, sys
        from pathlib import Path
        import build_seavox_basin as m
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'in';out=Path(d)/'out';root.mkdir()
            geom={'type':'Polygon','coordinates':[[[-60,0],[30,0],[30,30],[-60,30],[-60,0]]]}
            geo={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'MRGID_SR':'123'},'geometry':geom}]}
            source=root/'geo.json';source.write_text(json.dumps(geo));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            gh=hashlib.sha256(json.dumps(geom,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
            doc={'schema':'worldatlas-geography-decision-export-v1','source':'neon-export',
                 'decision_revision':{'id':'synthetic','status':'accepted','entity_revision':'synthetic'},
                 'entity_revision':{'id':'synthetic','status':'accepted'},
                 'category_bindings':[{'entity_id':11,'physical_class':'water','code':1}],
                 'basins':[{'id':'b','source_id':'s','source_version':'v','source_feature_id':'123','geometry_sha256':gh,
                            'assignment_method':'single_continent_named_basin','participant_entity_ids':[11]}],
                 'sources':[{'source_id':'s','version':'v','sha256':sha(source)}]}
            policy=root/'policy.json';policy.write_text(json.dumps(doc))
            rows,runs=rle(np.ones((6,12),dtype=np.uint8));rows.tofile(root/'rows');runs.tofile(root/'runs')
            old=(m.W,m.H,m.STEP,sys.argv);m.W,m.H,m.STEP=12,6,30
            try:
                sys.argv=['build','--input-root',str(root),'--geometry',str(source),'--decision-id','b',
                          '--policy',str(policy),'--policy-sha256',sha(policy),'--rows',str(root/'rows'),
                          '--rows-sha256',sha(root/'rows'),'--runs',str(root/'runs'),'--runs-sha256',sha(root/'runs'),
                          '--out',str(out),'--allow-unverified-snapshot']
                m.main()
            finally: m.W,m.H,m.STEP,sys.argv=old
            with gzip.open(out/'basin-assignment.jsonl.gz','rt') as f:record=json.loads(f.readline())
            self.assertEqual([(q['start'],q['end'],q['code']) for q in record['spans']],[(4,7,1)])
            self.assertEqual(json.loads((out/'manifest.json').read_text())['physical_water_cells'],3)


class GeometryValidityTest(unittest.TestCase):
    def test_self_intersecting_polygon_rejected(self):
        import tempfile
        from pathlib import Path
        from build_seavox_basin import validate_geometry_ogr
        geo={'type':'FeatureCollection','features':[{'type':'Feature','properties':{},
             'geometry':{'type':'Polygon','coordinates':[[[0,0],[1,1],[1,0],[0,1],[0,0]]]}}]}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.geojson';p.write_text(json.dumps(geo))
            with self.assertRaisesRegex(ValueError,'invalid'):validate_geometry_ogr(p)


class SnapshotTest(unittest.TestCase):
    def test_draft_requires_explicit_opt_in_and_matching_revision(self):
        import tempfile, hashlib
        from pathlib import Path
        from decision_snapshot import read_snapshot
        doc={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export',
             'decision_revision':{'id':'d','status':'draft','entity_revision':'e'},
             'entity_revision':{'id':'e','status':'draft'}}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'snap';p.write_text(json.dumps(doc)); h=lambda: hashlib.sha256(p.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):read_snapshot(p,h())
            self.assertEqual(read_snapshot(p,h(),allow_draft=True)['decision_revision']['status'],'draft')
            doc['entity_revision']['id']='other';p.write_text(json.dumps(doc))
            with self.assertRaises(ValueError):read_snapshot(p,h(),allow_draft=True)

if __name__=='__main__': unittest.main()
