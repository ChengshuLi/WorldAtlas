import unittest
from satellite_geodesic import apply_satellites, run_lower_bound


def summary(n): return {'total':n,'in_scope':n,'west':n,'east':0,'boundary':0,'outside_latitude':0}
def fake_pair(y,a,b,yy,c,d,width,**kw): return (abs(a-c)*1000.0,{})
class TestSatelliteGeodesic(unittest.TestCase):
    def test_known_other_continent_competitor_conflicts(self):
        from satellite_geodesic import apply_satellites
        components={1:{'total':1,'in_scope':1},2:{'total':2,'in_scope':2}}
        runs={1:[(1,183,184)],2:[(1,184,186)]}
        result={'proposals':{1:{'code':18,'basis':'whole_component_line_side'}},
                'review':{},'competitor_targets':{2:9}}
        out=apply_satellites(result,components,runs,{},lambda *a,**k:(1000,None),
                             width=360,north=2,max_satellite_cells=1,max_gap_m=120000,candidate_roots={1})
        self.assertNotIn(1,out['proposals'])
        self.assertEqual(out['review'][1],'conflicting_nearest_land_targets')
        result['competitor_targets']={}
        out=apply_satellites(result,components,runs,{},lambda *a,**k:(1000,None),
                             width=360,north=2,max_satellite_cells=1,max_gap_m=120000,candidate_roots={1})
        self.assertEqual(out['proposals'][1]['code'],18)

    def test_source_group_target_and_provenance_precede_proximity(self):
        components={1:summary(1),2:summary(3)}
        runs={1:[(90,3,4)],2:[(90,0,3)]}
        result={'proposals':{1:{'code':18,'basis':'inferred_source_extent_group_convention'},2:{'code':22,'basis':'selected_affiliation'}},'review':{},'regional_group_proposals':{1:['source']}}
        anchor={2:{'code':22,'source_id':'islands','source_feature_id':'parent','source_version':'v1','source_sha256':'a'*64,'main_island_evidence':'source'}}
        out=apply_satellites(result,components,runs,anchor,fake_pair,width=360000,north=.09,max_satellite_cells=1,max_gap_m=5000,candidate_roots={1},allow_unanchored_nearest=True)
        self.assertNotIn(1,out['proposals'])
        self.assertEqual(out['review'][1],'conflicting_group_and_anchor')
        evidence=out['group_anchor_conflicts'][1]['competitors'][0]
        self.assertEqual((evidence['root_current_generation_only'],evidence['code']),(2,22))
        self.assertEqual(evidence['anchor']['source_id'],'islands')
        self.assertEqual(out['regional_group_proposals'][1],['source'])
        self.assertNotIn(1,out['satellites'])
        anchor[2]['code']=18;result['proposals'][2]['code']=18
        out=apply_satellites(result,components,runs,anchor,fake_pair,width=360000,north=.09,max_satellite_cells=1,max_gap_m=5000,candidate_roots={1},allow_unanchored_nearest=True)
        self.assertEqual(out['proposals'][1],result['proposals'][1])

    def test_inferred_satellite_cannot_be_an_anchor(self):
        components={1:summary(1),2:summary(3)};runs={1:[(90,3,4)],2:[(90,0,3)]}
        result={'proposals':{2:{'code':18,'basis':'source_anchored_nearest_main_island'}},'review':{}}
        anchor={2:{'code':18,'source_id':'islands','source_feature_id':'parent','source_version':'v1','source_sha256':'a'*64,'main_island_evidence':'source'}}
        with self.assertRaisesRegex(ValueError,'not an inferred satellite'):
            apply_satellites(result,components,runs,anchor,fake_pair,width=360000,north=.09,max_satellite_cells=1,max_gap_m=5000,candidate_roots={1})

    def test_prior_satellite_and_unanchored_evidence_survives_later_pass(self):
        components={1:summary(1),2:summary(3)}; runs={1:[(90,3,4)],2:[(90,0,3)]}
        result={'proposals':{2:{'code':18,'basis':'selected_affiliation'}},'review':{1:'conflicting_group_and_anchor'},'satellites':{'1':{'source_id':'earlier'}},'nearest_unanchored':{'1':{'roots_current_generation_only':[9]}}}
        anchor={2:{'code':18,'source_id':'islands','source_feature_id':'parent','source_version':'v1','source_sha256':'a'*64,'main_island_evidence':'source'}}
        out=apply_satellites(result,components,runs,anchor,fake_pair,width=360000,north=.09,max_satellite_cells=1,max_gap_m=5000,candidate_roots={1})
        self.assertEqual(out['satellites'][1]['source_id'],'earlier')
        self.assertEqual(out['nearest_unanchored'][1]['roots_current_generation_only'],[9])
        self.assertEqual(out['review'][1],'conflicting_group_and_anchor')

    def test_conflicts_from_earlier_passes_fail_closed(self):
        components={1:summary(1),2:summary(3),3:summary(1),4:summary(1)}
        runs={1:[(90,3,4)],2:[(90,0,3)],3:[(91,3,4)],4:[(92,3,4)]}
        result={'proposals':{2:{'code':18,'basis':'selected_affiliation'}},'review':{1:'conflicting_regional_group_conventions',3:'conflicting_group_and_anchor',4:'future_unrecognized_hold'}}
        anchor={2:{'code':18,'source_id':'islands','source_feature_id':'parent','source_version':'v1','source_sha256':'a'*64,'main_island_evidence':'source'}}
        out=apply_satellites(result,components,runs,anchor,fake_pair,width=360000,north=.09,max_satellite_cells=1,max_gap_m=5000,candidate_roots={1,3,4},allow_unanchored_nearest=True)
        for root in (1,3,4):
            self.assertNotIn(root,out['proposals']);self.assertEqual(out['review'][root],result['review'][root])

    def test_optional_direct_anchor_ignores_unknown_nearer_without_chaining(self):
        components={1:summary(1),2:summary(5),3:summary(2),4:summary(1)}
        runs={1:[(90,5,6)],2:[(90,0,5)],3:[(90,6,8)],4:[(90,9,10)]}
        result={'proposals':{2:{'code':18,'basis':'selected_affiliation'}},'review':{1:'outside_line_latitude',4:'source_group_pending_review'}}
        anchors={2:{'code':18,'source_id':'islands','source_feature_id':'parent','source_version':'v1','source_sha256':'a'*64,'main_island_evidence':'source'}}
        kw=dict(width=360000,north=.09,max_satellite_cells=2,max_gap_m=10000,candidate_roots={1,4},allow_unanchored_nearest=True)
        out=apply_satellites(result,components,runs,anchors,fake_pair,**kw)
        self.assertEqual(out['proposals'][1]['code'],18)
        self.assertEqual(out['satellites'][1]['parent_root_current_generation_only'],2)
        self.assertTrue(out['satellites'][1]['nearer_unanchored_land'])
        self.assertNotIn(4,out['proposals'])
        result['competitor_targets']={3:22}
        out=apply_satellites(result,components,runs,anchors,fake_pair,**kw)
        self.assertNotIn(1,out['proposals']);self.assertEqual(out['review'][1],'conflicting_nearest_land_targets')

    def test_satellite_inherits_source_anchor_and_selected_wins(self):
        components={1:summary(1),2:summary(3),3:summary(1)}
        runs={1:[(90,3,4)],2:[(90,0,3)],3:[(91,3,4)]}
        result={'proposals':{1:{'code':18,'basis':'whole_component_line_side'},2:{'code':22,'basis':'selected_affiliation'},3:{'code':18,'basis':'selected_affiliation'}},'review':{}}
        anchors={2:{'code':22,'source_id':'named-islands','source_feature_id':'parent','source_version':'v1','source_sha256':'a'*64,'main_island_evidence':'reviewed source'}}
        out=apply_satellites(result,components,runs,anchors,fake_pair,width=360000,north=.09,max_satellite_cells=1,max_gap_m=5000,candidate_roots={1,2,3})
        self.assertEqual(out['proposals'][1]['code'],22)
        self.assertEqual(out['proposals'][1]['basis'],'source_anchored_nearest_main_island')
        self.assertEqual(out['proposals'][3]['code'],18)
        self.assertEqual(out['satellites'][1]['parent_root_current_generation_only'],2)
        self.assertEqual(result['proposals'][1]['code'],18)
    def test_unknown_nearest_competitor_preserves_line(self):
        components={1:summary(1),2:summary(3),3:summary(3)}
        runs={1:[(90,5,6)],2:[(90,2,5)],3:[(90,6,9)]}
        result={'proposals':{1:{'code':18,'basis':'whole_component_line_side'},2:{'code':22,'basis':'selected_affiliation'}},'review':{}}
        anchors={2:{'code':22,'source_id':'islands','source_feature_id':'parent','source_version':'v1','source_sha256':'a'*64,'main_island_evidence':'reviewed source'}}
        out=apply_satellites(result,components,runs,anchors,fake_pair,width=360000,north=.09,max_satellite_cells=1,max_gap_m=5000,candidate_roots={1,2,3})
        self.assertEqual(out['proposals'][1]['code'],18);self.assertIn(1,out['nearest_unanchored'])
    def test_small_larger_unanchored_competitor_blocks(self):
        components={1:summary(1),2:summary(5),3:summary(2)}
        runs={1:[(90,5,6)],2:[(90,0,5)],3:[(90,6,8)]}
        result={'proposals':{1:{'code':18,'basis':'whole_component_line_side'},2:{'code':22,'basis':'selected_affiliation'}},'review':{}}
        anchors={2:{'code':22,'source_id':'islands','source_feature_id':'parent','source_version':'v1','source_sha256':'a'*64,'main_island_evidence':'reviewed source'}}
        out=apply_satellites(result,components,runs,anchors,fake_pair,width=360000,north=.09,max_satellite_cells=20,max_gap_m=10000,candidate_roots={1,2,3})
        self.assertEqual(out['proposals'][1]['code'],18);self.assertIn(1,out['nearest_unanchored'])
    def test_nearest_known_opposite_unanchored_is_reviewed(self):
        components={1:summary(1),2:summary(5),3:summary(2)}
        runs={1:[(90,5,6)],2:[(90,0,5)],3:[(90,6,8)]}
        result={'proposals':{1:{'code':18,'basis':'whole_component_line_side'},2:{'code':22,'basis':'selected_affiliation'},3:{'code':22,'basis':'whole_component_line_side'}},'review':{}}
        anchors={2:{'code':22,'source_id':'islands','source_feature_id':'parent','source_version':'v1','source_sha256':'a'*64,'main_island_evidence':'reviewed source'}}
        out=apply_satellites(result,components,runs,anchors,fake_pair,width=360000,north=.09,max_satellite_cells=20,max_gap_m=10000,candidate_roots={1,2,3})
        self.assertNotIn(1,out['proposals'])
        self.assertEqual(out['review'][1],'conflicting_nearest_land_targets')
    def test_nearest_unanchored_same_side_keeps_broad_line_result(self):
        components={1:summary(1),2:summary(5),3:summary(2)}
        runs={1:[(90,5,6)],2:[(90,0,5)],3:[(90,6,8)]}
        result={'proposals':{1:{'code':18,'basis':'whole_component_line_side'},2:{'code':22,'basis':'selected_affiliation'},3:{'code':18,'basis':'whole_component_line_side'}},'review':{},'replayed_claims':{'source':'preserved'}}
        anchors={2:{'code':22,'source_id':'islands','source_feature_id':'parent','source_version':'v1','source_sha256':'a'*64,'main_island_evidence':'reviewed source'}}
        out=apply_satellites(result,components,runs,anchors,fake_pair,width=360000,north=.09,max_satellite_cells=20,max_gap_m=10000,candidate_roots={1,2,3})
        self.assertEqual(out['proposals'][1]['basis'],'whole_component_line_side')
        self.assertEqual(out['replayed_claims'],result['replayed_claims'])
    def test_protected_and_line_contact_are_preserved(self):
        components={1:summary(1),2:summary(5),3:summary(1),4:summary(1),5:summary(1),6:summary(1)}
        runs={1:[(90,5,6)],2:[(90,0,5)],3:[(90,6,7)],4:[(90,7,8)],5:[(90,8,9)],6:[(90,9,10)]}
        result={'proposals':{2:{'code':22,'basis':'selected_affiliation'}},'review':{1:'protected_mainland',3:'existing_other_continent',4:'crosses_or_touches_line',5:'outside_line_latitude',6:'source_group_pending_review'}}
        anchors={2:{'code':22,'source_id':'islands','source_feature_id':'parent','source_version':'v1','source_sha256':'a'*64,'main_island_evidence':'reviewed source'}}
        out=apply_satellites(result,components,runs,anchors,fake_pair,width=360000,north=.09,max_satellite_cells=1,max_gap_m=10000,candidate_roots={1,2,3,4,5,6})
        for root in (1,3,4,6): self.assertNotIn(root,out['proposals']);self.assertEqual(out['review'][root],result['review'][root])
        self.assertEqual(out['proposals'][5]['code'],22);self.assertNotIn(5,out['review'])
    def test_incomplete_run_rejected(self):
        with self.assertRaisesRegex(ValueError,'incomplete'):
            apply_satellites({'proposals':{},'review':{}},{1:summary(2)},{1:[(90,1,2)]},{},fake_pair,width=360000,north=.09,max_satellite_cells=1,max_gap_m=1,candidate_roots={1})
    def test_wrapped_lower_bound_is_conservative(self):
        from pyproj import Geod
        g=Geod(ellps='WGS84')
        for y,a,b,yy,c,d in [(90,359,360,90,0,1),(80,10,13,81,13,15),(100,355,360,102,0,3)]:
            bound=run_lower_bound(y,a,b,yy,c,d,360,90)
            actual=min(g.inv(-180+x+.5,90-y-.5,-180+z+.5,90-yy-.5)[2]
                       for x in range(a,b) for z in range(c,d))
            self.assertLessEqual(bound,actual+1e-6)
    def test_lower_bound_against_random_wgs84_pairs(self):
        import random
        from pyproj import Geod
        rng=random.Random(20261105);geod=Geod(ellps='WGS84')
        for _ in range(500):
            y=rng.randrange(180); yy=rng.randrange(180)
            a=rng.randrange(357); c=rng.randrange(357)
            b=a+rng.randrange(1,4); d=c+rng.randrange(1,4)
            lower=run_lower_bound(y,a,b,yy,c,d,360,90)
            exact=min(geod.inv(-180+x+.5,90-y-.5,-180+z+.5,90-yy-.5)[2]
                      for x in range(a,b) for z in range(c,d))
            self.assertLessEqual(lower,exact+1e-6)
    def test_real_wgs84_run_pair(self):
        import importlib.util,os,sys
        from pathlib import Path
        path=os.environ.get('RUN_PAIR_PATH')
        if not path:
            path=str(Path(__file__).resolve().parent.parent/'stage2-geodesic-20261104'/'run_pair.py')
        if not Path(path).is_file(): self.skipTest('existing WGS84 run_pair unavailable')
        sys.path.insert(0,str(Path(path).parent))
        try:
            spec=importlib.util.spec_from_file_location('actual_run_pair',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            components={1:summary(1),2:summary(3)};runs={1:[(90,5,6)],2:[(90,2,5)]}
            result={'proposals':{1:{'code':18,'basis':'whole_component_line_side'},2:{'code':22,'basis':'selected_affiliation'}},'review':{}}
            anchors={2:{'code':22,'source_id':'islands','source_feature_id':'parent','source_version':'v1','source_sha256':'a'*64,'main_island_evidence':'reviewed source'}}
            out=apply_satellites(result,components,runs,anchors,module.run_pair,width=360,north=90,max_satellite_cells=1,max_gap_m=120000,candidate_roots={1,2})
            self.assertEqual(out['proposals'][1]['code'],22)
            self.assertTrue(110000 < out['satellites'][1]['distance_m'] < 112000)
        finally: sys.path.pop(0)

if __name__=='__main__':unittest.main()
