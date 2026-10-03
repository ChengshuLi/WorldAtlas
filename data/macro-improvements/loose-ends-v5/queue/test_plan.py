import importlib.util, pathlib, sys, unittest
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('queue_plan', pathlib.Path(__file__).with_name('plan.py'))
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
class QueueSafety(unittest.TestCase):
    def test_preserve_closed_even_without_claim_label(self):
        self.assertTrue(module.protected({'state': 'closed', 'labels': ['status:ready']}))
    def test_preserve_canonical_claim_without_label(self):
        self.assertTrue(module.protected({'state': 'open', 'labels': [], 'canonical_claim': {'active': True}}))
    def test_preserve_claim_label_when_snapshot_comments_incomplete(self):
        self.assertTrue(module.protected({'state': 'open', 'labels': [{'name': 'status:claimed'}]}))
    def test_released_claim_and_open_ready_scope_can_be_planned(self):
        self.assertFalse(module.protected({'state': 'open', 'labels': ['status:ready'], 'canonical_claim': {'active': False}}))
    def test_member_pin_is_order_independent_and_changes_with_subject(self):
        self.assertEqual(module.member(['b', 'a']), module.member(['a', 'b']))
        self.assertNotEqual(module.member(['a']), module.member(['a', 'b']))
if __name__ == '__main__': unittest.main()
