"""Bounded genuine-input controls; no producer or native authority invocation."""
import copy, hashlib, importlib.util, json, pathlib, sys, tempfile, unittest
P=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('png_prepare',P/'prepare-nine.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
REPO=pathlib.Path(sys.argv[1]);D,RAW,PINS=m.load(REPO);D['_physical_sha']=PINS['physical']['sha256'];sys.argv=sys.argv[:1]
class Preparation(unittest.TestCase):
    def check_bad(self, name, mutate):
        data=dict(D);data[name]=copy.deepcopy(D[name]);mutate(data[name])
        with self.assertRaises((ValueError,KeyError)):m.project(data)
    def test_genuine_exact_partition_and_literal_retention(self):
        products,r=m.project(D);self.assertEqual((r['original_cells'],r['previous_supported'],r['proposed_supported'],r['remaining_held']),(56552,56476,56485,67))
        before=m.unpack(D['previous/native-patch.json']['rows']);after=m.unpack(products['native-patch.json']['rows'])
        self.assertEqual(after.keys()-before.keys(),set(m.KEYS));self.assertEqual({k:after[k] for k in before},before)
        held=m.unpack(D['previous/held-original.json']['rows'],True);self.assertEqual(m.unpack(products['held-original.json']['rows'],True),{k:v for k,v in held.items() if k not in m.KEYS})
        old=D['previous/source-evidence.json'];new=products['source-evidence.json']
        self.assertEqual({k:v for k,v in old.items() if k!='targets'},{k:v for k,v in new.items() if k!='targets'})
        for a,b in zip(old['targets'],new['targets']):
            if a['pixelIndex']!=m.OWNER:self.assertEqual(a,b)
            else:
                self.assertEqual({k:v for k,v in a.items() if k!='coverage_rows'},{k:v for k,v in b.items() if k!='coverage_rows'})
                self.assertEqual(m.coverage(b).keys()-m.coverage(a).keys(),set(m.KEYS))
        self.assertFalse(r['authority_executed']);self.assertEqual(r['acceptance_credit'],0)
    def test_wrong_original_class(self):
        def change(rows):
            next(r for r in rows if r[0]==138071 and r[1]<=239881<r[2])[5]='inland-water'
        self.check_bad('frozen-queue/block-033.json.gz',change)
    def test_wrong_component(self):
        self.check_bad('previous/prior-source-fitness-holds.json',lambda d:next(c for c in d['components'] if c['component_id']==m.COMPONENT).__setitem__('component_id','wrong'))
    def test_omitted_key(self):
        self.check_bad('previous/prior-source-fitness-holds.json',lambda d:next(c for c in d['components'] if c['component_id']==m.COMPONENT)['original_keys'].pop())
    def test_duplicate_key(self):
        self.check_bad('previous/prior-source-fitness-holds.json',lambda d:next(c for c in d['components'] if c['component_id']==m.COMPONENT)['original_keys'].append(list(m.KEYS[0])))
    def test_wrong_owner(self):
        self.check_bad('proof/exact-native-centres-result.json',lambda d:d['rows'][0]['key_x_y_owner'].__setitem__(2,1))
    def test_wrong_coordinate_contract(self):
        self.check_bad('proof/exact-native-centres-result.json',lambda d:d.__setitem__('longitude_rule','rounded'))
    def test_missing_separation(self):
        self.check_bad('proof/exact-native-centres-result.json',lambda d:d['rows'][0]['extra_residue_separations'].pop())
    def test_changed_predicate(self):
        self.check_bad('proof/exact-native-centres-result.json',lambda d:d['rows'][0]['states'].__setitem__('mapped_land_support','outside'))
    def test_whole_component_clearance(self):
        self.check_bad('proof/exact-native-controls-result.json',lambda d:d.__setitem__('whole_multipart_refusal_retained',False))
    def test_territorial_hold_cannot_discharge(self):
        def change(d):d['held_rows'].append({'y':138071,'runs':[[239881,239882,35458]]})
        self.check_bad('native-diagnostic-001/native-diagnostic.json',change)
    def test_missing_native_support(self):
        def change(d):d['supported_rows']=[r for r in d['supported_rows'] if r['y']!=138071]
        self.check_bad('native-diagnostic-001/native-diagnostic.json',change)
    def test_changed_direct_target(self):
        self.check_bad('compaction-001/source-evidence.json',lambda d:next(t for t in d['targets'] if t['pixelIndex']==m.OWNER).__setitem__('id','wrong'))
    def test_changed_source_geometry(self):
        self.check_bad('compaction-001/source-evidence.json',lambda d:next(t for t in d['targets'] if t['pixelIndex']==m.OWNER).__setitem__('base_geometry',{}))
    def test_missing_physical_coverage(self):
        self.check_bad('compaction-001/source-evidence.json',lambda d:next(t for t in d['targets'] if t['pixelIndex']==m.OWNER).__setitem__('coverage_rows',[]))
    def test_physical_issue(self):
        self.check_bad('physical',lambda d:next(t for t in d['results'] if t['target']==m.TARGET)['issues'].append('unresolved'))
    def test_changed_contact(self):
        self.check_bad('original-roster',lambda d:next(r for r in d if r['source_id']==m.TARGET).__setitem__('source_id','wrong'))
    def test_manifest_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp);p.joinpath('input-pins.json').write_bytes(b'{}');old=m.HERE;m.HERE=p
            try:
                with self.assertRaisesRegex(ValueError,'manifest'):m.load('.')
            finally:m.HERE=old
    def test_review_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp);p.joinpath('input-pins.json').write_bytes((P/'input-pins.json').read_bytes());p.joinpath('independent-correction-review.json').write_bytes(b'{}');old=m.HERE;m.HERE=p
            try:
                with self.assertRaisesRegex(ValueError,'independent'):m.load('.')
            finally:m.HERE=old
    def test_real_reader_refuses_tampered_bodies(self):
        from unittest.mock import patch
        original=m.subprocess.check_output
        for role in ['previous/native-patch.json','previous/source-evidence.json','previous/prior-source-fitness-holds.json','physical','proof/exact-native-centres-result.json','original-roster']:
            oid=PINS[role]['git_blob_oid']
            def read(args, **kwargs):
                b=original(args, **kwargs)
                return b+b' ' if args[-3:]==['cat-file','blob',oid] else b
            with self.subTest(role=role), patch.object(m.subprocess,'check_output',read):
                with self.assertRaisesRegex(ValueError,'custody'):m.load(REPO)
if __name__=='__main__':unittest.main(verbosity=2)
