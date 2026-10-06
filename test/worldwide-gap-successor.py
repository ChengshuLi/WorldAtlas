import copy
import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from worldwide_gap_successor import (coordinate_bytes, record_delta, reconstruct,
                                     tile_equal, component_lineage, overlay_membership_view,
                                     contact_key, validate_selected, SELECTED)
from worldwide_gap_successor import numeric_metadata_bytes,overlay_links,overlay_neighbors
from shapely.geometry import box,mapping
from evidence.immutable import canonical_json


def feature(identity, x=0):
    return {'id':identity,'type':'Feature','geometry':{'type':'Polygon','coordinates':[[[x,0],[x+1,0],[x+1,1],[x,0]]]},
            'properties':{'area_m2':None}}


def component(identity, ids):
    return {'id':identity,'properties':{'fragment_bindings':[{'id':i} for i in ids],
                                       'unmeasured_fragment_ids':ids}}


class SuccessorControls(unittest.TestCase):
    def test_metadata_representation_preserves_exact_json_semantics(self):
        self.assertEqual(numeric_metadata_bytes({'overlap':1}),numeric_metadata_bytes({'overlap':1.0}))
        for a,b in [(9007199254740993,9007199254740992.0),(True,1),(None,'null'),(-0.0,0.0),([1,2],[2,1]),([[1]],[1])]:
            self.assertNotEqual(numeric_metadata_bytes(a),numeric_metadata_bytes(b))

    def test_equality_overlay_disagreement_remains_unknown(self):
        old=[component('old',['a'])];new=[component('new',['b'])]
        for kind,flag in [('identical-coordinates',True),('equal-point-set',True),('equal-point-set',False)]:
            pair={'old_fragment':'a','new_fragment':'b','status':'checked','kind':kind,
                  'intersection_planar_area':0,'equality_overlay_disagreement':flag}
            links,unknown=overlay_links([pair]);self.assertEqual(links,[]);self.assertEqual(unknown,[('a','b')])
            ledger=component_lineage(old,new,links,unknown)
            self.assertEqual(ledger['original'][0]['relation'],'unknown-overlay')
            self.assertEqual(ledger['current'][0]['relation'],'unknown-overlay')

    def test_exact_wrapped_dateline_neighbor_closure(self):
        west={'id':'west','geometry':mapping(box(-180,0,-179,1))}
        east={'id':'east','geometry':mapping(box(179,0,180,1))}
        self.assertEqual({r['id'] for r in overlay_neighbors([west,east],[box(179,0,180,1)])},{'west','east'})
        self.assertEqual({r['id'] for r in overlay_neighbors([west,east],[box(-180,0,-179,1)])},{'west','east'})

    def test_numeric_representation_is_not_raw_identity(self):
        a={'type':'Point','coordinates':[1,2]}; b={'type':'Point','coordinates':[1.0,2.0]}
        self.assertNotEqual(canonical_json(a),canonical_json(b))
        self.assertEqual(coordinate_bytes(a),coordinate_bytes(b))
        b['coordinates'][0]=1.0000000000000002
        self.assertNotEqual(coordinate_bytes(a),coordinate_bytes(b))

    def test_signed_zero_order_and_invalid_coordinate(self):
        self.assertNotEqual(coordinate_bytes([0.0,1]),coordinate_bytes([-0.0,1]))
        self.assertNotEqual(coordinate_bytes([1,2]),coordinate_bytes([2,1]))
        self.assertNotEqual(coordinate_bytes([[1,2]]),coordinate_bytes([1,2]))
        for value in [True,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):coordinate_bytes(value)

    def test_exact_release_required(self):
        for value in ['main',SELECTED[:8],SELECTED.upper()]:
            with self.assertRaises(ValueError):validate_selected(value)
        self.assertEqual(validate_selected(SELECTED),SELECTED)

    def test_changed_operand_order_and_unknowns_force_recompute(self):
        before={k:[] for k in ['land','locations','invalid_land','invalid_locations','invalid_water','shorelines']}
        before['locations']=['a','b']
        members={k:{} for k in before};members['locations']={'a':('geometryA','metadataA'),'b':('geometryB','metadataB')}
        self.assertTrue(tile_equal(before,before,members,members,[],[]))
        changed=copy.deepcopy(members);changed['locations']['a']=('changedGeometry','metadataA')
        self.assertFalse(tile_equal(before,before,members,changed,[],[]))
        order=copy.deepcopy(before);order['locations'].reverse()
        self.assertFalse(tile_equal(before,order,members,members,[],[]))
        self.assertFalse(tile_equal(before,before,members,members,[],[{'cause':'unknown'}]))
        missing=copy.deepcopy(members);del missing['locations']['a']
        with self.assertRaisesRegex(ValueError,'Declared tile member missing'):tile_equal(before,before,members,missing,[],[])

    def test_lossless_deletion_upsert_and_ordinal_churn(self):
        old=[feature('old:0'),feature('old:1',3),feature('stable',5)]
        new=[feature('new:0',3),feature('stable',5)]
        delta=record_delta(old,new)
        self.assertEqual(reconstruct(old,delta),sorted(new,key=lambda r:r['id']))
        self.assertEqual(delta['removed_ids'],['old:0','old:1'])
        self.assertEqual(delta['retained_count'],1)
        bad=copy.deepcopy(delta);bad['upsert_records'][0]['properties']['area_m2']=1
        with self.assertRaisesRegex(ValueError,'Current full record bytes'):reconstruct(old,bad)

    def test_omitted_unchanged_member_cannot_reconstruct(self):
        old=[feature('a'),feature('b',2)];delta=record_delta(old,old)
        with self.assertRaisesRegex(ValueError,'Original delta roster'):reconstruct(old[:1],delta)
        bad=copy.deepcopy(delta);bad['retained_ids_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Retained roster'):reconstruct(old,bad)
        bad=copy.deepcopy(delta);bad['removed_ids']=['missing']
        with self.assertRaisesRegex(ValueError,'Missing/duplicated'):reconstruct(old,bad)

    def test_residue_addition_loss_and_unknown_preservation(self):
        old=[{'id':'residue:a','geometry':{'type':'Point','coordinates':[0,0]},'unknown':'original'}]
        new=old+[{'id':'residue:b','geometry':{'type':'LineString','coordinates':[[0,0],[1,1]]}}]
        delta=record_delta(old,new);self.assertEqual(reconstruct(old,delta),new)
        bad=copy.deepcopy(delta);bad['upsert_records']=[]
        with self.assertRaisesRegex(ValueError,'Current full record bytes'):reconstruct(old,bad)
        self.assertEqual(reconstruct(old,record_delta(old,[])),[])

    def test_contacts_full_membership_and_metadata(self):
        old=[{'fragments':['a','b'],'dateline':True,'kind':'point-only-ambiguous','components':['x','y']}]
        new=[{**old[0],'components':['x','z']}]
        delta=record_delta(old,new,contact_key)
        self.assertEqual(reconstruct(old,delta,contact_key),new)
        tamper=copy.deepcopy(delta);tamper['upsert_records'][0]['components']=['x','y']
        with self.assertRaisesRegex(ValueError,'Current full record bytes'):reconstruct(old,tamper,contact_key)

    def test_component_split_merge_removed_new_and_unmeasured(self):
        old=[component('oldA',['a','b']),component('oldB',['c']),component('removed',['gone'])]
        new=[component('newA',['aa','cc']),component('newB',['bb']),component('new',['fresh'])]
        rows=component_lineage(old,new,[('a','aa'),('b','bb'),('c','cc')])
        self.assertEqual([r['relation'] for r in rows['original']],['split','linked','removed'])
        self.assertEqual([r['relation'] for r in rows['current']],['merged','linked','new'])
        self.assertEqual(rows['original'][0]['unmeasured_fragment_ids'],['a','b'])
        with self.assertRaisesRegex(ValueError,'Lineage member absent'):component_lineage(old,new,[('missing','aa')])
        uncertain=component_lineage(old,new,[],[('a','aa')])
        self.assertEqual(uncertain['original'][0]['relation'],'unknown-overlay')
        self.assertEqual(uncertain['current'][0]['relation'],'unknown-overlay')


if __name__=='__main__':unittest.main()
