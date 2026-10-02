"""A diagnostic refresh must not rewrite frozen hierarchy/source products."""
import importlib.util,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('framework',ROOT/'scripts/review-framework.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ReportOnly(unittest.TestCase):
 def test_report_uses_actual_children_without_mutating_geography_or_policies(self):
  with tempfile.TemporaryDirectory() as tmp:
   data=pathlib.Path(tmp)
   files={'hierarchy.json':[{'id':'p','name':'Parent','level':'province','parent_id':None,'metadata':{'source':'source','child_count':999,'framework_status':'source-backed'}}], 'world-index.json':{'parts':['world.json']},'world.json':{'features':[{'id':'l','properties':{'parent_id':'p','metadata':{'framework_overlap':.5}}}]},'hierarchy-report.json':{},'sources.json':{'immutable':True},'location-policy.json':{'immutable':True},'granularity-report.json':{'immutable':True}}
   for name,value in files.items():(data/name).write_text(json.dumps(value))
   before={name:(data/name).read_bytes() for name in files if name!='hierarchy-report.json'}
   module.main(data,True)
   self.assertEqual(before,{name:(data/name).read_bytes() for name in before})
   report=json.loads((data/'hierarchy-report.json').read_text())
   self.assertEqual(report['review_queue'][0]['children'],1)
   self.assertEqual(report['source_counts'],{'review-required':1})
   self.assertFalse(report['semantic_review_complete'])
if __name__=='__main__':unittest.main()
