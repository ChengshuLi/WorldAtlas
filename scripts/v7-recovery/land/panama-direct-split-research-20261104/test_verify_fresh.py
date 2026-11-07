import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import verify_fresh as v

class SweepReaderTests(unittest.TestCase):
 def test_rows_for_both_stream_formats(self):
  with tempfile.TemporaryDirectory() as td,patch.object(v,'H',3):
   p=Path(td);np.array([0,1,1,3],dtype='<u4').tofile(p/'rows')
   for cols in (2,3):
    expected=np.arange(3*cols,dtype='<u4').reshape(-1,cols);expected.tofile(p/'runs')
    r=v.Rows(p,'rows','runs',cols)
    self.assertEqual(r.row(0).tolist(),expected[:1].tolist());self.assertEqual(r.row(1).tolist(),[]);self.assertEqual(r.row(2).tolist(),expected[1:].tolist());r.close()
   (p/'runs').write_bytes(b'x')
   with self.assertRaisesRegex(ValueError,'bad stream size'):v.Rows(p,'rows','runs',3)
 def test_offsets_are_checked(self):
  with tempfile.TemporaryDirectory() as td,patch.object(v,'H',3):
   p=Path(td);np.array([0,2,1,3],dtype='<u4').tofile(p/'rows');(p/'runs').write_bytes(bytes(36))
   with self.assertRaisesRegex(ValueError,'bad offsets'):v.Rows(p,'rows','runs',3)
class WholeSweepTests(unittest.TestCase):
 def fixture(self,root,bad=False):
  dirs={x:root/x for x in ('direct','components','seed','stage2')}
  for x in dirs.values():x.mkdir()
  def write(where,rows,runs,data,offsets):
   np.array(offsets,dtype='<u4').tofile(dirs[where]/rows);np.array(data,dtype='<u4').tofile(dirs[where]/runs)
  write('direct','direct-rows.u32le','direct-spans.u32le',[[1,2,20],[2,4,21]]*3,[0,2,4,6])
  write('components','rows.u32le','runs.u32le',[[1,4,9]]*3,[0,1,2,3])
  baseline=[list(z) for _ in range(3) for z in ((1,0),(2,20),(4,21),(5,0))]
  write('seed','rows.u32le','runs.u32le',baseline,[0,4,8,12])
  if bad:baseline[1][1]=21
  write('stage2','rows.u32le','runs.u32le',baseline,[0,4,8,12])
  (dirs['direct']/'report.json').write_text(json.dumps({'schema':'panama-direct-source-split-prototype-v1','status':'unselected-research','component_id_current_generation_only':9,'inputs_sha256':{},'direct_rows_sha256':'file','direct_spans_sha256':'file','graph':{'selected_cells':9}}))
  (dirs['seed']/'report.json').write_text(json.dumps({'seed_rows_sha256':'file','seed_runs_sha256':'file'}))
  (dirs['stage2']/'report.json').write_text(json.dumps({'output_rows_sha256':'file','output_runs_sha256':'file'}))
  def fake_sha(p):
   if p==dirs['seed']/'report.json':return 'ade23ba357813c95cc7edde7cceb313a49fccabf4489b1f7f2944925d44645ce'
   if p==dirs['stage2']/'report.json':return '9086511ba0fb64a9331847cc8271129c125cec4e0e873ab04ad719023a503a20'
   return 'file'
  return dirs,fake_sha
 def test_full_coverage_and_mismatch(self):
  for bad in (False,True):
   with self.subTest(bad=bad),tempfile.TemporaryDirectory() as td:
    p=Path(td);dirs,sha=self.fixture(p,bad)
    with patch.multiple(v,H=3,W=5,D=dirs['direct'],C=dirs['components'],S=dirs['seed'],B=dirs['stage2'],sha=sha,__file__=str(p/'verify.py')):
     if bad:
      with self.assertRaisesRegex(ValueError,'mismatch'):v.main()
     else:v.main()
    result=json.loads((p/'fresh-verification.json').read_text())
    self.assertEqual(result['status'],'failed' if bad else 'passed')
    self.assertEqual(result['cells'],9)
    self.assertEqual(result['stage2_matching_cells'],8 if bad else 9)
if __name__=='__main__':unittest.main()
