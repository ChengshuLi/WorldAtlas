import importlib.util,unittest
from pathlib import Path
from fractions import Fraction as F
p=Path(__file__).with_name('validate_terminal_closure.py');s=importlib.util.spec_from_file_location('terminal',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def pt(x,y):return (F(x),F(y),F(0))
class TerminalClosure(unittest.TestCase):
 def call(self,points,lands):
  def code(x,y):return 17 if (x,y) in lands else 1
  return m.verify_path(points,points[0],points[-1],code,1,17,100)
 def test_land_start_water_finish(self):
  p=[pt(F(1,2),F(1,2)),pt(F(3,2),F(1,2)),pt(F(5,2),F(1,2))];r=self.call(p,{(0,0)});self.assertEqual(r['terminal_land_cells_touched'],[[0,0]])
 def test_water_start_land_finish(self):
  p=[pt(F(1,2),F(1,2)),pt(F(3,2),F(1,2)),pt(F(5,2),F(1,2))];r=self.call(p,{(2,0)});self.assertEqual(r['terminal_land_cells_touched'],[[2,0]])
 def test_reject_nonterminal_land(self):
  p=[pt(F(1,2),F(1,2)),pt(F(3,2),F(1,2)),pt(F(5,2),F(1,2))]
  with self.assertRaisesRegex(ValueError,'nonterminal land'):self.call(p,{(1,0)})
 def test_reject_land_land_edge(self):
  p=[pt(F(1,2),F(1,2)),pt(F(3,2),F(1,2))]
  with self.assertRaisesRegex(ValueError,'more than one land'):self.call(p,{(0,0),(1,0)})
 def test_reject_start_cell_reentry(self):
  p=[pt(F(1,2),F(1,2)),pt(F(3,2),F(1,2)),pt(F(1,2),F(1,2)),pt(F(1,2),F(3,2))]
  with self.assertRaisesRegex(ValueError,'nonterminal land'):self.call(p,{(0,0)})
 def test_reject_corner_touch(self):
  p=[pt(F(1,2),F(1,2)),pt(F(3,2),F(3,2))]
  with self.assertRaisesRegex(ValueError,'nonterminal land'):self.call(p,{(1,0)})
 def test_reject_boundary_terminal(self):
  p=[pt(1,F(1,2)),pt(F(3,2),F(1,2))]
  with self.assertRaisesRegex(ValueError,'boundary'):self.call(p,set())
 def test_reject_wrong_endpoint(self):
  p=[pt(F(1,2),F(1,2)),pt(F(3,2),F(1,2))]
  with self.assertRaisesRegex(ValueError,'oriented'):m.verify_path(p,pt(F(1,4),F(1,2)),p[-1],lambda x,y:1,1,17,100)
 def test_reject_visits(self):
  p=[pt(F(1,2),F(1,2)),pt(F(3,2),F(1,2))]
  with self.assertRaisesRegex(ValueError,'visit limit'):m.verify_path(p,p[0],p[-1],lambda x,y:1,1,17,1)
if __name__=='__main__':unittest.main()
