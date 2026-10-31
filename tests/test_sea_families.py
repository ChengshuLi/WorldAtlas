import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sea_families import child_rules,OPEN_WATERS
class SeaFamiliesTest(unittest.TestCase):
 def test_reported_parent_gaps(self):
  r=child_rules()
  for name in ['Bahía de Campeche','Foxe Basin','Ungava Bay','Frobisher Bay','Kotzebue Sound','Cook Inlet']:
   self.assertEqual(r[name]['group'],4)
  self.assertEqual(r['Gulf of Honduras']['family'],'Caribbean Sea')
  self.assertEqual(r['Norton Sound']['family'],'Bering Sea')
 def test_open_seas_not_promoted(self):
  self.assertFalse(set(child_rules())&OPEN_WATERS)
 def test_global_families(self):
  r=child_rules()
  for name in ['Bo Hai','Gulf of Tonkin','Gulf of Suez','Gulf of Martaban','Bass Strait']:
   self.assertIn(name,r)
if __name__=='__main__':unittest.main()
