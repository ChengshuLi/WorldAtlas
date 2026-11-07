import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
import compare_water_selection as compare

class SelectionComparison(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.path=self.root/'water.parquet'
  osm=[{'dataset':'OpenStreetMap','property':''}];other=[{'dataset':'Other','property':'geometry'}]
  rows=[{'subtype':'lake','class':'lake','sources':osm},{'subtype':'lake','class':'lake','sources':other},{'subtype':'lake','class':'sea','sources':osm},{'subtype':'ocean','class':'ocean','sources':osm},{'subtype':'physical','class':'bay','sources':osm},{'subtype':None,'class':'lake','sources':osm}]
  pq.write_table(pa.Table.from_pylist(rows),self.path);self.digest=compare.sha(self.path)
 def tearDown(self):self.tmp.cleanup()
 def test_counts_and_hashes(self):
  got=compare.scan((str(self.path),self.digest));self.assertEqual({k:got[k] for k in ('rows','old_selected','new_selected','added','removed','missing_subtype')},{'rows':6,'old_selected':1,'new_selected':3,'added':2,'removed':0,'missing_subtype':1})
  with self.assertRaisesRegex(ValueError,'hash mismatch'):compare.scan((str(self.path),'0'*64))
 def test_manifest_cli(self):
  manifest=self.root/'manifest.json';manifest.write_text(json.dumps({'file_count':1,'files':[{'path':'water.parquet','sha256':self.digest}]}));digest=compare.sha(manifest)
  out=subprocess.check_output([sys.executable,str(Path(compare.__file__)),str(manifest),digest]);data=json.loads(out);self.assertEqual(data['totals']['added'],2);self.assertEqual(data['shards'],1)
if __name__=='__main__':unittest.main()
