"""Regression coverage for the seed watchdog's explicit no-floor record."""
import ast
from pathlib import Path
import unittest

path=Path(__file__).with_name('orchestrate_stage2.py')
tree=ast.parse(path.read_text())
helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='seed_monitor_floor_matches')
expr=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='need' and len(n.value.args)==2 and getattr(n.value.args[1],'value',getattr(n.value.args[1],'s',None))=='seed monitor incomplete')
def need(value,message):
 if not value:raise ValueError(message)
ns={'need':need};exec(compile(ast.Module(body=[helper],type_ignores=[]),str(path),'exec'),ns)
condition=compile(ast.Expression(expr),str(path),'eval')
class SeedMonitorFloorTest(unittest.TestCase):
 def setUp(self):
  self.sc={'memory_floor_kib':100,'disk_reserve_bytes':200,'max_group_rss_kib':300}
  self.h={'seed_watchdog_code':{'sha256':'w'},'seed_guardian_code':{'sha256':'g'}}
  self.mon={'schema':'sampled-process-group-watchdog-v1','status':'complete','watchdog_sha256':'w','guardian_sha256':'g','memory_floor_kib':None,'disk_floor_bytes':200,'group_rss_limit_kib':300,'samples':2,'minimum_available_kib':120,'peak_group_rss_kib':50,'sample_interval_seconds':0.05}
 def check(self):eval(condition,dict(ns,mon=self.mon,sc=self.sc,h=self.h))
 def test_null_accepted(self):self.check()
 def test_matching_floor_accepted(self):self.mon['memory_floor_kib']=100;self.check()
 def test_missing_floor_rejected(self):del self.mon['memory_floor_kib'];self.assertRaises(ValueError,self.check)
 def test_mismatched_floor_rejected(self):self.mon['memory_floor_kib']=99;self.assertRaises(ValueError,self.check)
 def test_bad_watchdog_rejected(self):self.mon['watchdog_sha256']='x';self.assertRaises(ValueError,self.check)
 def test_no_samples_rejected(self):self.mon['samples']=0;self.assertRaises(ValueError,self.check)
 def test_over_limit_rejected(self):self.mon['peak_group_rss_kib']=301;self.assertRaises(ValueError,self.check)
 def test_below_requested_minimum_rejected(self):self.mon['minimum_available_kib']=99;self.assertRaises(ValueError,self.check)
 def test_infinite_available_rejected(self):self.mon['minimum_available_kib']=float('inf');self.assertRaises(ValueError,self.check)
 def test_infinite_disk_rejected(self):self.mon['disk_floor_bytes']=float('inf');self.assertRaises(ValueError,self.check)
 def test_boolean_peak_rejected(self):self.mon['peak_group_rss_kib']=True;self.assertRaises(ValueError,self.check)
if __name__=='__main__':unittest.main()
