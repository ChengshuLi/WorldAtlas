import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import watch_group
class NoHostFloor(unittest.TestCase):
 def test_zero_available_does_not_prevent_success(self):
  with tempfile.TemporaryDirectory() as t, patch.object(watch_group,'memory_available',return_value=0), patch.object(watch_group,'die_with_parent'):
   d=Path(t); out=watch_group.run([sys.executable,'-c','pass'],d/'log',d,1048576,150000,5)
   self.assertEqual(out['status'],'complete');self.assertIsNone(out['memory_floor_kib']);self.assertEqual(out['minimum_available_kib'],0)
 def test_disk_floor_still_enforced(self):
  with tempfile.TemporaryDirectory() as t, patch.object(watch_group,'die_with_parent'):
   d=Path(t)
   with self.assertRaisesRegex(ValueError,'disk floor'):watch_group.run([sys.executable,'-c','pass'],d/'log',d,10**20,150000,5)
