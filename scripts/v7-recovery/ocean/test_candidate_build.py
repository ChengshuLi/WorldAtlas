import hashlib, json, tempfile, unittest
from pathlib import Path
import make_candidate_build as m

class CandidateBuildTest(unittest.TestCase):
 def test_draft_build_binds_physical_outputs(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);physical=root/'physical';physical.mkdir();snapshot=root/'draft.json'
   d={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export',
      'decision_revision':{'id':'d','status':'draft','entity_revision':'e'},'entity_revision':{'id':'e','status':'draft'}}
   snapshot.write_text(json.dumps(d));hashes={}
   for name in ('rows.u32le','runs.u32le','physical-dry.tif'):
    p=physical/name;p.write_bytes(name.encode());hashes[name]=m.sha(p)
   rp=physical/'report.json';rp.write_text(json.dumps({'status':'candidate-only','grid':{'width':4,'height':2},'output_sha256':hashes}))
   out=root/'build.json';doc=m.build(snapshot,m.sha(snapshot),physical,m.sha(rp),out)
   self.assertEqual(doc['physical_runs_sha256'],hashes['runs.u32le']);self.assertEqual(doc['decision_revision'],'d')
   with self.assertRaises(FileExistsError):m.build(snapshot,m.sha(snapshot),physical,m.sha(rp),out)
   (physical/'runs.u32le').write_bytes(b'tampered')
   with self.assertRaisesRegex(ValueError,'physical output hash'):m.build(snapshot,m.sha(snapshot),physical,m.sha(rp),root/'bad')
   self.assertFalse((root/'bad').exists())
