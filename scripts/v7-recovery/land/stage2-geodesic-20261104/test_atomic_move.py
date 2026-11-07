import tempfile,pathlib,unittest
from atomic_move import move_noreplace
class Move(unittest.TestCase):
 def test_new_destination(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);(p/'source').mkdir();(p/'source'/'data').write_text('x');move_noreplace(p/'source',p/'destination');self.assertEqual((p/'destination'/'data').read_text(),'x')
 def test_destination_appears_before_rename(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);(p/'source').mkdir();(p/'destination').mkdir()
   with self.assertRaises(FileExistsError):move_noreplace(p/'source',p/'destination')
   self.assertTrue((p/'source').is_dir());self.assertTrue((p/'destination').is_dir())
if __name__=='__main__':unittest.main()
