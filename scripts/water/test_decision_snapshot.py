import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import build_prefill_plan
import build_prefill
import build_seavox_basin
from decision_snapshot import read_snapshot, participant_water_codes, find_source


class DecisionSnapshotTest(unittest.TestCase):
    def test_hash_and_revision_are_required(self):
        base={'schema':'worldatlas-geography-decision-export-v1','source':'neon-export',
              'decision_revision':{'id':'d1','status':'accepted','entity_revision':'e1'},
              'entity_revision':{'id':'e1','status':'accepted'},
              'category_bindings':[{'entity_id':101,'code':6,'physical_class':'water'}]}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'snapshot.json';p.write_text(json.dumps(base));h=hashlib.sha256(p.read_bytes()).hexdigest()
            data=read_snapshot(p,h)
            self.assertEqual(participant_water_codes(data,{'participant_entity_ids':[101]}),[6])
            with self.assertRaisesRegex(ValueError,'snapshot hash'): read_snapshot(p,'0'*64)
            bad={**base,'decision_revision':{'id':'d1','status':'draft','entity_revision':'e1'}}
            p.write_text(json.dumps(bad));h=hashlib.sha256(p.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'revisioned Neon'): read_snapshot(p,h)
            with self.assertRaisesRegex(ValueError,'unique water binding'):
                participant_water_codes(data,{'participant_entity_ids':[102]})

    def test_draft_requires_explicit_opt_in_and_matching_revisions(self):
        base={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export',
              'decision_revision':{'id':'d1','status':'draft','entity_revision':'e1'},
              'entity_revision':{'id':'e1','status':'draft'}}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'draft.json'
            def save(value):
                p.write_text(json.dumps(value)); return hashlib.sha256(p.read_bytes()).hexdigest()
            h=save(base)
            with self.assertRaisesRegex(ValueError,'revisioned Neon'): read_snapshot(p,h)
            self.assertEqual(read_snapshot(p,h,allow_draft=True),base)
            bad={**base,'entity_revision':{'id':'e1','status':'accepted'}};h=save(bad)
            with self.assertRaisesRegex(ValueError,'revisioned Neon'): read_snapshot(p,h,allow_draft=True)
            bad={**base,'schema':'worldatlas-geography-decision-export-v1',
                 'decision_revision':{'id':'d1','status':'accepted','entity_revision':'e1'}};h=save(bad)
            with self.assertRaisesRegex(ValueError,'revisioned Neon'): read_snapshot(p,h,allow_draft=True)

    def test_draft_plan_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); plan=root/'plan.json'
            plan.write_text(json.dumps({'schema':'worldatlas-full-grid-composition-plan-v1',
                                        'decision_revision_status':'draft'}))
            argv=['prefill','--allow-unverified-snapshot','--plan',str(plan),'--input-root',str(root),'--out',str(root/'out')]
            with patch.object(sys,'argv',argv):
                with self.assertRaisesRegex(ValueError,'draft plan requires'): build_prefill.main()
            self.assertFalse((root/'out').exists())

    def test_source_pin_must_be_a_sha256(self):
        basin={'source_id':'s','source_version':'v'}
        for digest in ('', 'x'*64, 'A'*64, 'a'*63, None):
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                find_source({'sources':[{'source_id':'s','version':'v','sha256':digest}]},basin)
        self.assertEqual(find_source({'sources':[{'source_id':'s','version':'v','sha256':'a'*64}]},basin)['sha256'],'a'*64)

    def test_cli_refuses_unverified_snapshot_by_default(self):
        argv=['plan','--input-root','/tmp','--inputs','/tmp/input','--policy','/tmp/policy','--policy-sha256','a'*64,'--out','/tmp/out']
        with patch.object(sys,'argv',argv):
            with self.assertRaisesRegex(ValueError,'authenticated Neon revision verification'): build_prefill_plan.main()
        argv=['prefill','--plan','/tmp/plan','--input-root','/tmp','--out','/tmp/out']
        with patch.object(sys,'argv',argv):
            with self.assertRaisesRegex(ValueError,'authenticated Neon revision verification'): build_prefill.main()
        argv=['basin','--input-root','/tmp','--geometry','/tmp/g','--decision-id','b1',
              '--archive','/tmp/a','--extraction-manifest','/tmp/m','--extraction-manifest-sha256','f'*64,
              '--policy','/tmp/p','--policy-sha256','c'*64,'--rows','/tmp/r','--rows-sha256','d'*64,
              '--runs','/tmp/u','--runs-sha256','e'*64,'--out','/tmp/o']
        with patch.object(sys,'argv',argv):
            with self.assertRaisesRegex(ValueError,'authenticated Neon revision verification'): build_seavox_basin.main()


if __name__=='__main__': unittest.main()
