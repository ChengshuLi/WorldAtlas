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


class GeometryValidityTest(unittest.TestCase):
    def test_self_intersecting_polygon_rejected(self):
        from map_build.core.geometry import rasterize
        from map_build.core.grid import Grid
        geometry = {'type': 'Polygon', 'coordinates': [
            [[0, 0], [10, 10], [10, 0], [0, 10], [0, 0]]]}
        with self.assertRaisesRegex(ValueError, 'invalid'):
            rasterize(geometry, Grid(360, 180, 1.))


if __name__ == '__main__':
    unittest.main()
