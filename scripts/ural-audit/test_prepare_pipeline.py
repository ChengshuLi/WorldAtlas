import unittest
from prepare_pipeline import bind_divider
class TestBinding(unittest.TestCase):
 def setUp(self):
  self.s={'mainland_boundaries':[{'boundary_id':'ural_kara_coast_to_caspian','geometry_sha256':'5a6526344cacbc1a23be174f589cec9710a0f317360ec5c8737ba6956c3f7fe2','geometry':{'coordinates':[[0,0],[1,1],[2,2]]}}], 'routes':[{'route_id':'europe_caspian_closure_v1','geometry_sha256':'6ee86cf4108b8622e01a4dd0be0b4ae19e809b4e04d8cceb25547425258ac62a','geometry':{'coordinates':[[2,2],[3,3],[4,4],[5,5],[6,6]]}}]};self.d=[[1,1],[2,2],[3,3],[4,4],[5,5]]
 def test_accept_exact_suffix(self):bind_divider(self.s,self.d)
 def test_reject_changed_line(self):
  with self.assertRaises(ValueError):bind_divider(self.s,[[1,1],[2,2],[3,3],[4,8],[5,5]])
 def test_reject_changed_source_hash(self):
  self.s['routes'][0]['geometry_sha256']='bad'
  with self.assertRaises(ValueError):bind_divider(self.s,self.d)
if __name__=='__main__':unittest.main()

class TestCurrentAndShell(unittest.TestCase):
 def test_current_binding_and_mismatch(self):
  from prepare_pipeline import verify_current
  a={'schema':'neon-current-boundary-selection-attestation-v1','boundary_id':'ural_kara_coast_to_caspian','route_id':'europe_caspian_closure_v1','project_id':'wild-cherry-46472487','branch_id':'br-shy-mountain-arsff6zb','revision':'v2-land-mainland-boundary-draft-1','boundary_sha256':'5a6526344cacbc1a23be174f589cec9710a0f317360ec5c8737ba6956c3f7fe2','closure_sha256':'6ee86cf4108b8622e01a4dd0be0b4ae19e809b4e04d8cceb25547425258ac62a','retrieved_at_utc':'2026-11-05T10:41:00Z'};verify_current(a);a['closure_sha256']='bad'
  with self.assertRaises(ValueError):verify_current(a)
 def test_shell_path_spaces_and_metacharacters(self):
  import shlex
  from prepare_pipeline import shell_arg
  path='/tmp/a path;$(not-run)/file';self.assertEqual(shlex.split(shell_arg(path)),[path])
  with self.assertRaises(ValueError):shell_arg('/tmp/new\nline')
