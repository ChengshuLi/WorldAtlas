"""Check report language without altering the conflict and provenance machinery."""
import ast
from pathlib import Path
import unittest

class RegionalReportWarningTests(unittest.TestCase):
 def test_report_omits_unsupported_missing_inventory_warning(self):
  tree=ast.parse((Path(__file__).parent/'apply_selected_mixed.py').read_text())
  all_nodes=list(ast.walk(tree));aug=[n for n in all_nodes if isinstance(n,ast.AugAssign) and isinstance(n.target,ast.Subscript) and isinstance(n.target.value,ast.Name) and n.target.value.id=='output' and isinstance(n.target.slice,ast.Constant) and n.target.slice.value=='limitations' and isinstance(n.value,ast.List)]
  warnings=[s.value for n in aug for s in n.value.elts if isinstance(s,ast.Constant) and isinstance(s.value,str)]
  self.assertTrue(any('Provisional locally derived baseline' in s for s in warnings))
  self.assertFalse(any('inventory is incomplete' in s.lower() for s in warnings))
  assignments=[n.value for n in all_nodes if isinstance(n,ast.Assign) and any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=='output' and isinstance(t.slice,ast.Constant) and t.slice.value=='regional_island_rule' for t in n.targets)]
  self.assertEqual(len(assignments),1); obj=assignments[0]; self.assertIsInstance(obj,ast.Dict)
  fields={k.value:v for k,v in zip(obj.keys,obj.values) if isinstance(k,ast.Constant)}
  limitation=ast.literal_eval(fields['limitation']);self.assertNotIn('incomplete inventories',limitation);self.assertIn('Withheld roots retain baseline',limitation)
  self.assertIn('result',fields);self.assertIn('provenance',fields)
  provenance=[n.value for n in all_nodes if isinstance(n,ast.Assign) and any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=='output' and isinstance(t.slice,ast.Constant) and t.slice.value=='diagnostic_provenance' for t in n.targets)]
  self.assertEqual(len(provenance),1); pfields={k.value:v for k,v in zip(provenance[0].keys,provenance[0].values) if isinstance(k,ast.Constant)}
  self.assertFalse(ast.literal_eval(pfields['pending_inventory_complete']));self.assertTrue(ast.literal_eval(pfields['profiling_standin']))
  self.assertIn('not independently verified',ast.literal_eval(pfields['pending_inventory_scope']));self.assertIn('conflicts remain held',ast.literal_eval(pfields['pending_inventory_scope']))

if __name__=='__main__':unittest.main()
