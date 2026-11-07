import copy, unittest
from build_prefill_plan import validate_shared_audit

class SharedAuditTests(unittest.TestCase):
    def manifest(self, wrapped=False, interval=False):
        method = ('wgs84-wrapped-center-interval-v1' if wrapped and interval else
                  'wgs84-wrapped-certified-with-streamed-full-fallback-v1' if wrapped else
                  'wgs84-coastal-center-interval-v1' if interval else
                  'wgs84-coastal-4neighbor-center-v2')
        audit = {'shore_method': method+' (research, not an approved decision)',
                 'certified_bound_cells':8, 'exact_distance_cells':2,
                 'shared_nearest_sha256':'b'*64, 'shore_geometry_sha256':'c'*64}
        if wrapped:
            audit.update(index_optimization='certified-wrapped-crop-with-streamed-full-shore-fallback',
                         shore_order='original-full-crop-row-column-order',
                         wrapped_narrow_cells=3 if interval else 8, wrapped_fallback_cells=2,
                         wrapped_bounds_sha256='d'*64, streamed_fallback_sha256='e'*64)
        if interval:
            audit.update(execution_method='wgs84-center-row-interval-v1',interval_certified_cells=5,
                         interval_nearest_sha256='f'*64,helper_code_sha256={'interval_nearest':'f'*64})
        return {'physical_water_cells':10,'algorithm_sha256':'a'*64,'nearest_assignment_audit':audit}

    def test_all_versioned_methods(self):
        for wrapped in (False,True):
            for interval in (False,True):
                with self.subTest(wrapped=wrapped,interval=interval):
                    m=self.manifest(wrapped,interval)
                    self.assertEqual(validate_shared_audit(m),m['nearest_assignment_audit']['shore_method'])

    def test_missing_pins_accounting_and_relabeling_rejected(self):
        cases=[]
        for wrapped in (False,True):
            for interval in (False,True):
                m=self.manifest(wrapped,interval);m['algorithm_sha256']=None;cases.append(m)
                m=self.manifest(wrapped,interval);m['nearest_assignment_audit']['exact_distance_cells']=3;cases.append(m)
        m=self.manifest(interval=True);m['nearest_assignment_audit']['helper_code_sha256']={};cases.append(m)
        m=self.manifest(interval=True);m['nearest_assignment_audit'].update(interval_leaf_cells=6,exact_interval_probe_count=2);cases.append(m)
        m=self.manifest(interval=True);m['nearest_assignment_audit'].update(interval_leaf_cells=5,exact_interval_probe_count=-1);cases.append(m)
        m=self.manifest(wrapped=True);m['nearest_assignment_audit']['wrapped_fallback_cells']=3;cases.append(m)
        m=self.manifest(interval=True);m['nearest_assignment_audit']['shore_method']=self.manifest()['nearest_assignment_audit']['shore_method'];cases.append(m)
        for m in cases:
            with self.subTest(manifest=m), self.assertRaises(ValueError):validate_shared_audit(m)

if __name__=='__main__':unittest.main()
