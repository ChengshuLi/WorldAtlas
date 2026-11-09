import hashlib,json,unittest
from pathlib import Path
import apply_selected_mixed as driver
from test_mixed_driver import DriverTests,js

class NegativeDriverPins(DriverTests):
 def set_negative_method(self):
  rp=Path(self.cfg['point_request']['path']);req=json.loads(rp.read_text());sp=Path(req['snapshot']['path']);snap=json.loads(sp.read_text());snap['affiliations'][1]['method']='component_containment_excluding_source_v1';req['snapshot']=js(sp,snap);self.cfg['point_request']=js(rp,req)
 def test_negative_method_requires_both_helper_pins(self):
  self.set_negative_method()
  with self.assertRaisesRegex(ValueError,'source-negative helper code pins required'):self.runv()
 def test_partial_helper_pins_fail_closed(self):
  self.cfg['code']['negative_component_filter']=hashlib.sha256((driver.HERE/'negative_component_filter.py').read_bytes()).hexdigest()
  with self.assertRaisesRegex(ValueError,'missing trusted code pins'):self.runv()
