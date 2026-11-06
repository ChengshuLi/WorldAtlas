import tempfile,unittest
from pathlib import Path
import compose_full_water_grid as c
class Tests(unittest.TestCase):
 def test_relative_absolute_and_escape(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'root';root.mkdir();(root/'in').write_text('x');outside=Path(d)/'outside';outside.write_text('y');(root/'link').symlink_to(outside)
   self.assertEqual(c.resolve_input('in',root,root),root/'in');self.assertEqual(c.resolve_input(str(root/'in'),root,root),root/'in')
   for bad in (str(outside),'../outside','link'):
    with self.assertRaisesRegex(ValueError,'escapes'):c.resolve_input(bad,root,root)
if __name__=='__main__':unittest.main()
