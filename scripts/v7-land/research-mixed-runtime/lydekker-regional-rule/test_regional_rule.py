import unittest
import hashlib
import json
from regional_rule import Line, resolve, verified_line, ASIA, OCEANIA, SOURCE_ID, SOURCE_VERSION, SOURCE_PDF_SHA256


def c(w=0,e=0,b=0,o=0,total=None):
    n=w+e+b+o
    return dict(total=n if total is None else total, in_scope=n, west=w, east=e, boundary=b, outside_latitude=o)

class TestRegionalRule(unittest.TestCase):
    def setUp(self):
        self.line=Line({'type':'LineString','coordinates':[[130,3],[129,0],[133,-8]]})
    def test_side_and_endpoints(self):
        self.assertEqual(self.line.side(128,0),'west')
        self.assertEqual(self.line.side(130,0),'east')
        self.assertEqual(self.line.side(129,0),'boundary')
        self.assertEqual(self.line.side(130,3),'boundary')
        self.assertIsNone(self.line.side(130,3.01))
        self.assertIsNone(self.line.side(130,-8.01))
    def test_whole_islands_and_selected_endpoint_exception(self):
        result=resolve({1:c(w=5),2:c(e=3),3:c(w=2,o=4),4:c(o=6),5:c(w=1,e=1),6:c(w=1,total=2)},
                       {3:[ASIA],4:[OCEANIA]})
        self.assertEqual(result['proposals'],{1:{'code':ASIA,'basis':'whole_component_line_side'},2:{'code':OCEANIA,'basis':'whole_component_line_side'},3:{'code':ASIA,'basis':'selected_affiliation'},4:{'code':OCEANIA,'basis':'selected_affiliation'}})
        self.assertEqual(result['review'],{5:'crosses_or_touches_line',6:'partly_outside_region'})
    def test_unsupported_endpoints_and_mainland(self):
        result=resolve({1:c(w=3,o=1),2:c(o=9),3:c(e=7),4:c(b=1)}, {}, {3})
        self.assertEqual(result['proposals'],{})
        self.assertEqual(result['review'],{1:'outside_line_latitude',2:'outside_line_latitude',3:'protected_mainland',4:'crosses_or_touches_line'})
    def test_verified_satellite_beats_side_and_conflicts_fail(self):
        self.assertEqual(resolve({1:c(w=5)},{1:[OCEANIA]})['proposals'][1]['code'],OCEANIA)
        with self.assertRaisesRegex(ValueError,'conflicting'): resolve({1:c(w=5)},{1:[ASIA,OCEANIA]})
        with self.assertRaisesRegex(ValueError,'mainland'): resolve({1:c(w=5)},{1:[ASIA]}, {1})
        with self.assertRaisesRegex(ValueError,'missing'): resolve({1:c(w=5)},{2:[ASIA]})
    def test_unclaimed_single_side_receives_proposal(self):
        result=resolve({1:c(w=73)}, {})
        self.assertEqual(result['proposals'][1]['code'], ASIA)
        with self.assertRaises(ValueError): verified_line({'line_id':'wrong','geometry':{}},{'line_id':'test','geometry_sha256':'0'*64})
    def test_actual_vertex_midpoint_numeric_contact(self):
        a=[133.66727159566176, -7.763257609117708]
        b=[133.66727159569845, -7.764257576531984]
        line=Line({'type':'LineString','coordinates':[a,b]})
        x=(a[0]+b[0])/2; y=(a[1]+b[1])/2
        self.assertEqual(line.side(x,y),'boundary')
        self.assertEqual(line.side(x-1e-8,y),'west')
        self.assertEqual(line.side(x+1e-8,y),'east')
    def test_canonical_line_authentication(self):
        geometry={'type':'LineString','coordinates':[[130,3],[129,0],[133,-8]]}
        digest=hashlib.sha256(json.dumps(geometry,sort_keys=True,separators=(',', ':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
        record={'line_id':'test-line','geometry_sha256':digest,'geometry':geometry, 'source_id':SOURCE_ID, 'source_version':SOURCE_VERSION, 'status':'research', 'provenance':{'source_pdf_sha256':SOURCE_PDF_SHA256}}
        pin={'line_id':'test-line','geometry_sha256':digest}
        self.assertEqual(verified_line(record,pin).side(128,0),'west')
        bad=dict(record,geometry={'type':'LineString','coordinates':[[130,3],[129,-1],[133,-8]]})
        with self.assertRaisesRegex(ValueError,'hash mismatch'): verified_line(bad,pin)
        with self.assertRaisesRegex(ValueError,'hash mismatch'): verified_line(dict(record,geometry_sha256='0'*64),pin)
        with self.assertRaisesRegex(ValueError,'provenance mismatch'): verified_line(dict(record,source_id='wrong'),pin)
    def test_pending_source_group_blocks_all_proposals(self):
        out=resolve({1:c(w=4),2:c(e=2)}, {1:[ASIA]}, pending_roots={1})
        self.assertNotIn(1,out['proposals'])
        self.assertEqual(out['review'][1],'source_group_pending_review')
        self.assertEqual(out['proposals'][2]['code'],OCEANIA)
    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(ValueError): Line({'type':'LineString','coordinates':[[0,1],[1,1]]})
        with self.assertRaises(ValueError): resolve({1:dict(total=2,in_scope=1,west=2,east=0,boundary=0,outside_latitude=0)}, {})

if __name__ == '__main__': unittest.main()
