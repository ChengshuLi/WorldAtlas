import copy
import hashlib
import json
import unittest
from decimal import Decimal

from export_snapshot import canonical_bytes, export, parse_json

D = 'a' * 64

class Cursor:
    def __init__(self, data): self.data=data; self.calls=[]; self.description=[]; self.rows=[]; self.closed=False
    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        if sql.startswith('BEGIN') or sql == 'ROLLBACK': return
        if sql.startswith('WITH RECURSIVE lineage'):
            index = 15 if 'FROM lineage l JOIN atlas.source_assets' in sql else 16
            data=self.data[index]; names=list(data[0]) if data else []
            self.description=[(k,) for k in names]; self.rows=[tuple(row[k] for k in names) for row in data]
            return
        keys=['FROM atlas.source_builds b','FROM atlas.source_build_inputs i JOIN','FROM atlas.source_build_inputs WHERE',
              'FROM atlas.geographic_entities WHERE','FROM atlas.review_category_bindings WHERE','FROM atlas.decision_features WHERE',
              'FROM atlas.decision_endpoints WHERE','FROM atlas.decision_routes WHERE','FROM atlas.decision_route_points WHERE',
              'FROM atlas.decision_basins b LEFT JOIN','FROM atlas.decision_basin_participants WHERE','FROM atlas.decision_affiliations WHERE',
              'FROM atlas.decision_ocean_seeds WHERE','FROM atlas.decision_policies WHERE','FROM atlas.decision_ocean_fill_policies WHERE']
        index=next(i for i,k in enumerate(keys) if k in sql)
        data=self.data[index]; names=list(data[0]) if data else []
        self.description=[(k,) for k in names]; self.rows=[tuple(row[k] for k in names) for row in data]
    def fetchall(self): return self.rows
    def close(self): self.closed=True

class Conn:
    def __init__(self, data): self.cur=Cursor(data); self.autocommit=True
    def cursor(self): return self.cur


def sample():
    build={'build_id':'build','status':'draft','entity_revision':'e1','decision_revision':'d1','decision_snapshot_sha256':None,
           'physical_grid_revision':'grid1','physical_grid_sha256':D,'code_revision':'commit','git_paths':'[]','software_versions':'{}',
           'decision_status':'accepted','decision_evidence':'{}','decision_reviewer':'reviewer','decision_reviewed_at':'2026-01-01T00:00:00.000000Z',
           'entity_status':'accepted','entity_reviewer':'reviewer','entity_reviewed_at':'2026-01-01T00:00:00.000000Z'}
    source={'source_id':'s1','version':'v1','sha256':D,'size_bytes':1,'r2_bucket':'bucket','r2_key':'key'}
    feature={'feature_id':'f1','source_id':'s1','source_version':'v1','source_feature_id':'sf1','geometry_sha256':D,'evidence':'{}'}
    basin={'id':'b1','feature_id':'f1','source_id':'s1','source_version':'v1','source_feature_id':'sf1','geometry_sha256':D,'assignment_method':'shared_nearest_assigned_shore','tie_rules':'{}','evidence':'{}'}
    prec={'id':'p1','kind':'layer_precedence','definition':json.dumps({'priorities':{'coastal-band':1,'named-b1':2},'allowed_overrides':[{'winner':'named-b1','loser':'coastal-band'}]}),'evidence':'{}'}
    coast={'id':'p2','kind':'coastline_assignment','definition':json.dumps({'source_id':'s1','source_version':'v1','method':'nearest','parameters':{}}),'evidence':'{}'}
    return [[build],[source],[{'source_id':'s1','version':'v1','stage':'stage','role':'role'}],[{'id':10,'name':'A','level':'location','parent_id':None,'physical_class':'water'},{'id':11,'name':'B','level':'location','parent_id':None,'physical_class':'water'}],
            [{'code':1,'entity_id':10,'physical_class':'water'},{'code':2,'entity_id':11,'physical_class':'water'}],
            [feature],[{'endpoint_id':'x','name':'X','longitude':'-0.000','latitude':'3.1400','derivation':'{}','evidence':'{}'}],[],[],[basin],
            [{'basin_id':'b1','entity_id':10},{'basin_id':'b1','entity_id':11}],[],[],[prec,coast],[],
            [{**source,'title':'Source','kind':'raw','provider':'Provider','source_uri':'https://example.test/source','license_name':'License','license_uri':'https://example.test/license','attribution':'Attribution','provenance':'{}'}],[]]

class ExportTest(unittest.TestCase):
    def candidate(self, data): return export(Conn(data),'build',prepare_candidate=True)
    def test_round_trip_transaction_and_tamper(self):
        data=sample(); payload=self.candidate(data); digest=hashlib.sha256(payload).hexdigest()
        self.assertEqual(payload,self.candidate(copy.deepcopy(data)))
        doc=json.loads(payload); self.assertEqual(doc['endpoints'][0]['longitude'],'0'); self.assertEqual(doc['endpoints'][0]['latitude'],'3.14')
        locked=copy.deepcopy(data); locked[0][0]['status']='locked'; locked[0][0]['decision_snapshot_sha256']=digest
        conn=Conn(locked); self.assertEqual(export(conn,'build',digest),payload)
        self.assertEqual(conn.cur.calls[0][0], 'BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY'); self.assertEqual(conn.cur.calls[-1][0], 'ROLLBACK'); self.assertTrue(conn.cur.closed)
        locked[5][0]['evidence']='{"changed":true}'
        with self.assertRaisesRegex(ValueError, 'snapshot digest mismatch'): export(Conn(locked),'build',digest)
    def test_unaccepted_wrong_pin_and_bad_policy_fail(self):
        d=sample(); d[0][0]['entity_status']='draft'
        with self.assertRaises(ValueError): self.candidate(d)
        d=sample(); digest=hashlib.sha256(self.candidate(d)).hexdigest(); d[0][0].update(status='locked',decision_snapshot_sha256='f'*64)
        with self.assertRaisesRegex(ValueError,'build pin'): export(Conn(d),'build',digest)
        d=sample(); d[13][0]['definition']=json.dumps({'priorities':{'coastal-band':2,'named-b1':1},'allowed_overrides':[{'winner':'named-b1','loser':'coastal-band'}]})
        with self.assertRaisesRegex(ValueError,'override'): self.candidate(d)
    def test_order_independence_and_failed_transaction_closes(self):
        data=sample(); expected=self.candidate(data); shuffled=copy.deepcopy(data)
        for rows in shuffled[1:]: rows.reverse()
        self.assertEqual(expected,self.candidate(shuffled))
        conn=Conn(sample()); conn.cur.data[5][0]['geometry_sha256']='broken'
        with self.assertRaises(ValueError): export(conn,'build',prepare_candidate=True)
        self.assertEqual(conn.cur.calls[-1][0], 'ROLLBACK'); self.assertTrue(conn.cur.closed)

    def test_ocean_policy_requires_known_routes_and_seed(self):
        data=sample()
        data[14].append({'id':'ocean','kind':'ocean_fill','definition':json.dumps({'connectivity':4,'wrap_longitude':True,
            'barrier_tie_rule':'left-of-oriented-route','route_ids':['missing'],'seed_ids':['missing'],
            'unseeded_policy':'report-only'}),'evidence':'{}'})
        with self.assertRaisesRegex(ValueError,'ocean fill references'): self.candidate(data)
        data[14][0]['definition']=json.dumps({'connectivity':4,'wrap_longitude':True,
            'barrier_tie_rule':'left-of-oriented-route','route_ids':['r1'],'seed_ids':['s1'],
            'unseeded_policy':'report-only'})
        data[6].append({'endpoint_id':'y','name':'Y','longitude':'20','latitude':'30','derivation':'{}','evidence':'{}'})
        data[7].append({'route_id':'r1','route_type':'lonlat_polyline','parameters':'{}','evidence':'{}'})
        data[8].extend([{'route_id':'r1','ordinal':0,'endpoint_id':'x'}, {'route_id':'r1','ordinal':1,'endpoint_id':'y'}])
        data[12].append({'seed_id':'s1','endpoint_id':'x','entity_id':10,'evidence':'{}'})
        doc=json.loads(self.candidate(data)); self.assertEqual(sum(p['kind']=='ocean_fill' for p in doc['policies']),1)
        data[0][0]['software_versions']='{"pyproj":"3.7.1","proj":"9.6.0"}'
        data[7][0].update(route_type='wgs84_geodesic', parameters='{"max_step_km":0.5}')
        doc=json.loads(self.candidate(data)); self.assertEqual(doc['routes'][0]['parameters']['max_step_km'],'0.5')
        data[7][0]['parameters']='{"max_step_km":2}'
        with self.assertRaisesRegex(ValueError,'geodesic step'): self.candidate(data)

    def test_basin_method_cardinality(self):
        data=sample(); data[9][0]['assignment_method']='single_continent_named_basin'
        data[10]=data[10][:1]
        self.assertEqual(len(json.loads(self.candidate(data))['basins'][0]['participant_entity_ids']),1)
        data[9][0]['assignment_method']='shared_nearest_assigned_shore'
        with self.assertRaisesRegex(ValueError,'invalid basin participants'): self.candidate(data)
        data[9][0]['assignment_method']='unknown'
        with self.assertRaisesRegex(ValueError,'unsupported basin method'): self.candidate(data)

    def test_lineage_pinned_and_validated(self):
        data=sample()
        data[15][0]['kind']='derived'
        with self.assertRaisesRegex(ValueError,'derived source missing lineage'): self.candidate(data)
        parent={**data[15][0], 'kind':'raw', 'source_id':'parent', 'sha256':'b'*64, 'r2_key':'parent-key'}
        data[15].append(parent)
        data[16].append({'source_id':'s1','version':'v1','parent_source_id':'parent','parent_version':'v1','relationship':'derived from'})
        payload=self.candidate(data)
        digest=hashlib.sha256(payload).hexdigest()
        locked=copy.deepcopy(data); locked[0][0].update(status='locked',decision_snapshot_sha256=digest)
        self.assertEqual(export(Conn(locked),'build',digest),payload)
        locked[15][1]['provenance']='{"tampered":true}'
        with self.assertRaisesRegex(ValueError,'snapshot digest mismatch'): export(Conn(locked),'build',digest)
        bad=copy.deepcopy(data); bad[16].append({'source_id':'parent','version':'v1','parent_source_id':'s1','parent_version':'v1','relationship':'cycle'})
        with self.assertRaisesRegex(ValueError,'lineage cycle'): self.candidate(bad)
        bad=copy.deepcopy(data); bad[16].clear(); bad[15][0]['kind']='raw'
        with self.assertRaisesRegex(ValueError,'unreachable source lineage'): self.candidate(bad)

    def test_exact_serialization(self):
        self.assertEqual(parse_json('{"x":1.2300,"y":1,"z":1e-8}'), {'x':'1.23','y':1,'z':'0.00000001'})
        self.assertEqual(canonical_bytes({'z':Decimal('1.00'),'a':'é'}),b'{"a":"\\u00e9","z":"1"}\n')
        with self.assertRaises(ValueError): canonical_bytes({'x':1.5})

if __name__=='__main__': unittest.main()
