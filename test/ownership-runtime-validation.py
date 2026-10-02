"""Exact transport checks detect altered evidence even with refreshed asset hashes."""
import contextlib,gzip,hashlib,importlib.util,io,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]

def module(name,file):
 s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
runtime=module('runtime','prepare-ownership-runtime.py');validator=module('validator','validate-ownership-runtime.py')

class TransportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.source=self.root/'source';self.output=self.root/'runtime';self.source.mkdir()
  evidence=[[0,.6,.6,[[0,.6]],[0],0],[None,0,0,[],[],0]]
  self.part('evidence.json.gz',evidence);self.part('ownership.json.gz',[['A',[[-2,3,0,0,0]]],['B',[[-2,1,None,1,1],[1,3,1,0,0]]]])
  self.index={'version':2,'valid_from':-2,'valid_to':3,'parts':[{'path':'ownership.json.gz','sha256':validator.sha(self.source/'ownership.json.gz')}],'evidence_parts':[{'path':'evidence.json.gz','sha256':validator.sha(self.source/'evidence.json.gz')}],'evidence_records':2,'locations':2,'intervals':3,'footprints_sha256':'fixture','owner_ids':['A','B'],'labels':['A'],'source_ids':['S'],'statuses_order':['derived','no-majority']}
  (self.source/'index.json').write_text(json.dumps(self.index,separators=(',',':')))
  with contextlib.redirect_stdout(io.StringIO()):runtime.prepare(self.source,self.output)
 def tearDown(self):self.tmp.cleanup()
 def part(self,name,rows):(self.source/name).write_bytes(gzip.compress(json.dumps(rows,separators=(',',':')).encode(),mtime=0))
 def validate(self):
  with contextlib.redirect_stdout(io.StringIO()):return validator.validate(self.source,self.output)
 def alter(self,change):
  index=json.loads((self.output/'index.json').read_text());entry=index['buckets'][0];path=self.output/entry['path'];data=validator.read(path);change(data)
  path.write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0));entry['sha256']=validator.sha(path);(self.output/'index.json').write_text(json.dumps(index,separators=(',',':')))
 def test_full_interval_preserved_across_century_boundary(self):
  result=self.validate();self.assertTrue(result['all_exact_interval_and_evidence_tuples_match']);self.assertEqual(result['source_intervals'],3);self.assertEqual(result['transport_intervals'],4)
 def test_changed_evidence_with_updated_hash_detected(self):
  self.alter(lambda data:data['evidence'][0].__setitem__(1,.7))
  with self.assertRaisesRegex(ValueError,'exact interval/evidence'):self.validate()
 def test_shortened_cross_boundary_interval_detected(self):
  self.alter(lambda data:data['parts'][0][0][1][0].__setitem__(1,1))
  with self.assertRaisesRegex(ValueError,'exact interval/evidence'):self.validate()
 def test_missing_interval_detected(self):
  self.alter(lambda data:data['parts'][0][0][1].pop())
  with self.assertRaisesRegex(ValueError,'exact interval/evidence'):self.validate()
 def test_changed_dictionary_detected(self):
  path=self.output/'index.json';index=json.loads(path.read_text());index['shared']['owner_ids']=['B','A'];path.write_text(json.dumps(index))
  with self.assertRaisesRegex(ValueError,'dictionary'):self.validate()

if __name__=='__main__':unittest.main()
