import json,os,sqlite3,tempfile,unittest
from pathlib import Path
from unittest import mock
import match_old_list1 as m

class MatcherTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.src=self.root/'clusters';self.src.mkdir();db=sqlite3.connect(self.src/'clusters.sqlite')
  db.executescript('CREATE TABLE clusters(root INTEGER PRIMARY KEY,cluster_id TEXT,cells INTEGER);CREATE TABLE resolved(row INTEGER,start INTEGER,end INTEGER,reference INTEGER,candidate INTEGER,root INTEGER);CREATE INDEX resolved_row ON resolved(row);')
  db.executemany('INSERT INTO clusters VALUES (?,?,?)',[(1,'cluster-a',3),(2,'cluster-b',1)]);db.executemany('INSERT INTO resolved VALUES (?,?,?,?,?,?)',[(0,0,1,17,18,1),(0,6,8,17,18,1),(2,3,4,17,18,2)]);db.commit();db.close()
  self.report=self.src/'report.json';self.report.write_text(json.dumps({'schema':'list1-land-clusters-report-v1','status':'diagnostic-complete-not-an-override','database_sha256':m.digest(self.src/'clusters.sqlite'),'config_sha256':'1'*64,'code_sha256':'2'*64,'comparison_sha256':'3'*64,'clusters':2,'identity_inputs':{'grid':{'width':8,'height':4,'step':45,'west':-180,'north':90}}}))
  self.i=self.root/'index';self.i.mkdir();self.index=self.i/'old.json';self.data={'schema':'old-list1-evidence-discovery-index-v1','grid':{'width':8,'height':4,'step':45,'west':-180,'north':90},'items':[{'old_item_id':'wrap','name':'West/East','historical_changed_land_extent':{'x_start':6,'x_end':0,'y_start':0,'y_end':0}},{'old_item_id':'other','historical_changed_land_extent':{'x_start':4,'x_end':4,'y_start':3,'y_end':3}}]};self.save()
 def save(self):self.index.write_text(json.dumps(self.data))
 def run_match(self,name='out',report=None,index=None):return m.match(self.src,self.index,index or m.digest(self.index),self.root/name,report or m.digest(self.report),0)
 def test_wrap_and_multi_span_aggregation(self):
  r=self.run_match();lines=[json.loads(x) for x in (self.root/'out/matches.jsonl').read_text().splitlines()];self.assertEqual(r['clusters'],2);self.assertEqual(lines[0]['old_list1_candidates'][0]['overlap_with_historical_changed_extent_cells'],3);self.assertEqual(lines[1]['old_list1_candidates'],[]);self.assertNotIn('comparison_monitor_sha256',r)
 def test_bad_input_pins(self):
  with self.assertRaisesRegex(ValueError,'report hash mismatch'):self.run_match('bad-report',report='0'*64)
  with self.assertRaisesRegex(ValueError,'index hash mismatch'):self.run_match('bad-index',index='0'*64)
 def test_duplicate_and_missing_ids(self):
  self.data['items']=[{'old_item_id':'same'},{'old_item_id':'same'}];self.save()
  with self.assertRaisesRegex(ValueError,'duplicate old item ID'):self.run_match('dup')
  self.data['items']=[{'name':'missing'}];self.save()
  with self.assertRaisesRegex(ValueError,'items or IDs'):self.run_match('missing')
 def test_report_marker_uncertainty(self):
  unlink=os.unlink
  def fail(path,*a,**k):
   if Path(path).name=='report.pending':raise OSError('injected')
   return unlink(path,*a,**k)
  with mock.patch.object(m.os,'unlink',side_effect=fail):
   with self.assertRaisesRegex(OSError,'marker may exist.*uncertain'):self.run_match('uncertain')
  self.assertTrue((self.root/'uncertain/report.json').exists())
if __name__=='__main__':unittest.main()
