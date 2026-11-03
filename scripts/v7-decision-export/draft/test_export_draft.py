import copy
import json
import unittest
from pathlib import Path
from export_draft import export, parse_snapshot, canonical_bytes, SCHEMA

D='a'*64

def sample():
    src={'source_id':'source','version':'v1','sha256':D,'size_bytes':5,'r2_bucket':'b','r2_key':'key'}
    return {'schema':SCHEMA,'serialization':'worldatlas-canonical-json-v1','source':'neon-export',
      'decision_revision':{'id':'d','entity_revision':'e','status':'draft','reviewed_by':None,'reviewed_at':None},
      'entity_revision':{'id':'e','status':'draft','reviewed_by':None,'reviewed_at':None},
      'sources':[src], 'source_lineage_assets':[{**src,'kind':'raw'}], 'source_lineage_dependencies':[],
      'entities':[{'id':1}], 'category_bindings':[{'code':1,'entity_id':1}],
      'features':[{'feature_id':'f','source_id':'source','source_version':'v1','source_feature_id':'x','geometry_sha256':D}],
      'endpoints':[{'endpoint_id':'p','longitude':1.5,'latitude':0}], 'routes':[],
      'basins':[{'id':'b','feature_id':'f','source_id':'source','source_version':'v1','source_feature_id':'x','geometry_sha256':D,'participant_entity_ids':[1]}],
      'affiliations':[], 'ocean_seeds':[], 'policies':[]}

def read(doc): return parse_snapshot(json.dumps(doc))
class Cursor:
    def __init__(self,raw): self.raw=raw; self.calls=[]; self.closed=False
    def execute(self,sql,params=None): self.calls.append((sql,params))
    def fetchall(self): return [(self.raw,)]
    def close(self): self.closed=True
class Conn:
    autocommit=True
    def __init__(self,doc): self.cur=Cursor(json.dumps(doc))
    def cursor(self): return self.cur

class DraftExportTest(unittest.TestCase):
    def test_transaction_is_read_only_and_closes(self):
        conn=Conn(sample()); out=export(conn,'d'); self.assertEqual(json.loads(out)['decision_revision']['status'],'draft')
        self.assertEqual(conn.cur.calls[0][0],'BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        self.assertEqual(conn.cur.calls[1][1],{'revision':'d'}); self.assertEqual(conn.cur.calls[-1][0],'ROLLBACK'); self.assertTrue(conn.cur.closed)
    def test_draft_only_and_mismatch(self):
        for field in ('decision_revision','entity_revision'):
            d=sample(); d[field]['status']='accepted'
            with self.assertRaisesRegex(ValueError,'draft'): read(d)
        d=sample(); d['decision_revision']['entity_revision']='other'
        with self.assertRaisesRegex(ValueError,'draft'): read(d)
        d=sample(); d['schema']='worldatlas-geography-decision-export-v1'
        with self.assertRaisesRegex(ValueError,'schema'): read(d)
        c=Conn(sample())
        with self.assertRaisesRegex(ValueError,'wrong revision'): export(c,'other')
        self.assertEqual(c.cur.calls[-1][0],'ROLLBACK'); self.assertTrue(c.cur.closed)
    def test_references_and_cycles_fail(self):
        d=sample(); d['features'][0]['source_id']='missing'
        with self.assertRaisesRegex(ValueError,'feature'): read(d)
        d=sample(); d['basins'][0]['geometry_sha256']='b'*64
        with self.assertRaisesRegex(ValueError,'basin'): read(d)
        d=sample(); d['affiliations']=[{'affiliation_id':'a','feature_id':'missing','entity_id':1}]
        with self.assertRaisesRegex(ValueError,'affiliation'): read(d)
        d=sample(); parent={**d['source_lineage_assets'][0], 'source_id':'parent'}; d['source_lineage_assets'].append(parent)
        d['source_lineage_dependencies']=[{'source_id':'source','version':'v1','parent_source_id':'parent','parent_version':'v1'}, {'source_id':'parent','version':'v1','parent_source_id':'source','parent_version':'v1'}]
        with self.assertRaisesRegex(ValueError,'cycle'): read(d)
        d=sample(); d['sources'][0]['sha256']='bad'; d['source_lineage_assets'][0]['sha256']='bad'
        with self.assertRaisesRegex(ValueError,'digest'): read(d)
    def test_canonical_sort_and_exact_coordinates(self):
        d=sample(); d['endpoints'].append({'endpoint_id':'a','longitude':0,'latitude':-2.125})
        result=read(d); self.assertEqual(result['endpoints'][0]['latitude'],'-2.125'); self.assertEqual(result['endpoints'][1]['longitude'],'1.5')
        shuffled=copy.deepcopy(d); shuffled['endpoints'].reverse()
        self.assertEqual(canonical_bytes(read(d)), canonical_bytes(read(shuffled)))
    def test_database_sql_is_select_only_and_scoped(self):
        sql=(Path(__file__).parent/'query.sql').read_text()
        self.assertTrue(sql.startswith('WITH RECURSIVE')); self.assertIn('%(revision)s',sql)
        self.assertNotIn('INSERT ',sql.upper()); self.assertNotIn('UPDATE ',sql.upper()); self.assertNotIn('DELETE ',sql.upper())

if __name__=='__main__': unittest.main()
