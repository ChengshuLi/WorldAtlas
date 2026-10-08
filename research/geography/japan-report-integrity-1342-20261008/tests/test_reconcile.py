import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import hashlib
import unittest
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[4]
MODULE=ROOT/'research/geography/japan-report-integrity-1342-20261008/methods/reconcile_source_fitness_table.py'
spec=importlib.util.spec_from_file_location('repair',MODULE); repair=importlib.util.module_from_spec(spec); spec.loader.exec_module(repair)
OLD=ROOT/'research/geography/japan-nine-gap-family-source-fitness-20261007'
scope=json.loads((OLD/'inputs/immutable-scope-and-inputs.json').read_text())
physical=json.loads((OLD/'inputs/existing-physical-row-scope.json').read_text())
overlay=json.loads((OLD/'results/source-overlays.json').read_text())
table=json.loads((OLD/'results/source-fitness-table.json').read_text())
subjects={x['id']:x for x in scope['full_current_contact_features']}
hierarchy=json.loads(__import__('subprocess').check_output(['git','-C',str(ROOT),'show','HEAD:data/hierarchy.json']))

class ReconciliationTests(unittest.TestCase):
    def validate(self,o=None,t=None,s=None):
        return repair.validate(copy.deepcopy(s or scope),copy.deepcopy(physical),copy.deepcopy(o or overlay),copy.deepcopy(t or table),copy.deepcopy(subjects),copy.deepcopy(hierarchy))
    def test_exact_retained_area_transfer(self):
        scope_copy=copy.deepcopy(scope); physical_copy=copy.deepcopy(physical); overlay_copy=copy.deepcopy(overlay); table_copy=copy.deepcopy(table)
        pairs=repair.validate(scope_copy,physical_copy,overlay_copy,table_copy,copy.deepcopy(subjects),copy.deepcopy(hierarchy))
        self.assertEqual(len(pairs),37); self.assertTrue(all(v>0 for _,v in pairs))
        expected=copy.deepcopy(table)
        values={(k[0],k[1],k[2],k[3]):v for k,v in pairs}
        for component in expected['component_rows']:
            for row in component['MLIT_exact_intersection_records']:
                row['intersection_area_jgd2011_degrees2']=values[(component['component_id'],row['record_ordinal'],row['N03_007'],row['intersection_geometry_sha256'])]
        self.assertEqual(table_copy,expected)
    def test_reject_target_roster_mutations(self):
        for mutate in ('omit','duplicate','foreign'):
            o=copy.deepcopy(overlay)
            if mutate=='omit': o['targets'].pop()
            elif mutate=='duplicate': o['targets'][-1]=copy.deepcopy(o['targets'][0])
            else: o['targets'][0]['id']='foreign-target'
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): self.validate(o=o)
    def test_contact_context_reports_metadata_vintage(self):
        context=repair.report_context(scope,subjects,hierarchy,overlay)
        self.assertEqual(len(context['contacts']),21)
        self.assertTrue(all(row['reference_year']=='2017' for row in context['contacts']))
        self.assertTrue(all(row['recorded_parent_level']=='province' for row in context['contacts']))
    def test_reject_source_record_mutations(self):
        for mutate in ('foreign_id','wrong_ordinal','wrong_number'):
            o=copy.deepcopy(overlay)
            row=next(r for r in o['pairwise_exact_overlays'] if r['source_product']=='mlit-n03-2017' and r['target_kind']=='component' and r['intersects'])
            if mutate=='foreign_id': row['source_id']='99999'
            elif mutate=='wrong_ordinal': row['source_record']['record_ordinal']+=1
            else: row['source_record']['record_number']+=1
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): self.validate(o=o)
    def test_reject_pair_mutations(self):
        for mutate in ('omit','duplicate','foreign','wrong_geometry'):
            o=copy.deepcopy(overlay)
            if mutate=='omit': o['pairwise_exact_overlays'].pop()
            elif mutate=='duplicate': o['pairwise_exact_overlays'][-1]=copy.deepcopy(o['pairwise_exact_overlays'][0])
            elif mutate=='foreign': o['pairwise_exact_overlays'][0]['target_id']='foreign-target'
            else: o['pairwise_exact_overlays'][0]['target_geometry_sha256']='0'*64
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): self.validate(o=o)
    def test_reject_area_unit_and_summary_mismatch(self):
        for mutate in ('null','zero','infinite','wrong_count','wrong_unit','false_target_summary','wrong_pair_product_count'):
            o=copy.deepcopy(overlay)
            row=next(r for r in o['pairwise_exact_overlays'] if r['source_product']=='mlit-n03-2017' and r['target_kind']=='component' and r['intersects'])
            if mutate=='null': row['intersection_area_jgd2011_degrees2']=None
            elif mutate=='zero': row['intersection_area_jgd2011_degrees2']=0
            elif mutate=='infinite': row['intersection_area_jgd2011_degrees2']=float('inf')
            elif mutate=='wrong_count': next(x for x in o['source_summaries'] if x['source_product']=='mlit-n03-2017')['source_shape_records']+=1
            elif mutate=='wrong_unit':
                row['intersection_area_jgd2011_m2']=row.pop('intersection_area_jgd2011_degrees2')
            elif mutate=='false_target_summary': o['source_summaries'][0]['per_target_exact_intersections'][0]['exact_intersection_count']+=1
            else: row['source_product']='geoboundaries-full'
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): self.validate(o=o)
    def test_reject_false_table_identity(self):
        t=copy.deepcopy(table); row=next(r for c in t['component_rows'] for r in c['MLIT_exact_intersection_records']); row['record_ordinal']+=10
        with self.assertRaises(ValueError): self.validate(t=t)
    def test_reject_missing_or_duplicate_family_members(self):
        s=copy.deepcopy(scope);s['families_full_records'][0]['complete_component_ids'].pop()
        with self.assertRaises(ValueError): self.validate(s=s)

class ActualCliFailureTests(unittest.TestCase):
    def test_complete_cli_late_failure_publishes_nothing(self):
        vintage='late-failure-control-pinned-helper-20261008'
        destination=ROOT/'research/geography/japan-report-integrity-1342-20261008/vintages'/vintage
        self.assertFalse(destination.exists())
        result=subprocess.run([sys.executable,str(MODULE),'--repo',str(ROOT),'--vintage',vintage,'--fail-after-compute'],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(result.stdout,b'')
        self.assertIn(b'intentional late failure before publication',result.stderr)
        self.assertFalse(destination.exists())
        receipts=ROOT/'research/geography/japan-report-integrity-1342-20261008/receipts'
        receipts.mkdir(exist_ok=True)
        (receipts/'late-failure-pinned-helper-stderr.txt').write_bytes(result.stderr)
        payload={'schema':'worldatlas-late-failure-control-v1','command':'reconcile_source_fitness_table.py --vintage '+vintage+' --fail-after-compute','exit_code':result.returncode,'stdout_bytes':len(result.stdout),'stderr_sha256':hashlib.sha256(result.stderr).hexdigest(),'publication_directory_exists':destination.exists(),'status':'expected failure before output admission/publication'}
        (receipts/'late-failure-pinned-helper.json').write_text(json.dumps(payload,indent=2)+'\n')

class DestinationAdmissionTests(unittest.TestCase):
    def test_existing_symlink_and_ancestor_symlink_rejected(self):
        import sys
        sys.path.insert(0,str(ROOT/'scripts/evidence')); import immutable
        with tempfile.TemporaryDirectory() as temp:
            repo=Path(temp); owned='research/geography/japan-report-integrity-1342-20261008'
            base=SimpleNamespace(repo=str(repo))
            parent=repo/owned/'vintages';parent.mkdir(parents=True)
            root=parent/'live';root.mkdir(); (root/'a.json').write_text('sentinel')
            with self.assertRaises(FileExistsError): immutable.admit_destination(base,owned+'/', 'live',['a.json'])
            (root/'a.json').unlink(); root.rmdir(); (parent/'broken').symlink_to(parent/'absent')
            with self.assertRaises(ValueError): immutable.admit_destination(base,owned+'/', 'broken',['a.json'])
            (parent/'broken').unlink(); parent.rmdir(); (repo/owned).rmdir(); (repo/'research/geography').mkdir(parents=True,exist_ok=True)
            (repo/'research/geography/japan-report-integrity-1342-20261008').symlink_to(repo/'escape')
            with self.assertRaises(ValueError): immutable.admit_destination(base,owned+'/', 'ancestor',['a.json'])
            with self.assertRaises(ValueError): immutable.admit_destination(base,'research/geography/../escape/','bad',['a.json'])

if __name__=='__main__': unittest.main()
