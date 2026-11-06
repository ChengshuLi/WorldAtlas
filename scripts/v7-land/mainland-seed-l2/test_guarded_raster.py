import unittest

class GuardedRasterTests(unittest.TestCase):
 def test_wrapper_has_no_address_space_limit(self):
  from pathlib import Path
  p=Path(__file__).with_name('guarded_raster_exec.py')
  self.assertNotIn('RLIMIT_AS',p.read_text())
if __name__=='__main__':unittest.main()
