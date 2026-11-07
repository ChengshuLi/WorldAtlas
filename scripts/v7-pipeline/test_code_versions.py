"""Committed downstream upgrades preserve old identities and fail closed."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import code_versions as versions
import run_pipeline as pipeline
from execution_state import code_identity, pin, write


class CodeVersionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.scripts = self.repo / 'scripts'
        for name in ('v7-raw-mask/build_physical.py', 'v7-replay/validator.py',
                     'v7-pipeline/run_pipeline.py', 'v7-replay/streaming_closed_water.py',
                     'v7-replay/compare_grids.py', 'v7-replay/unknown.py',
                     'v7-recovery/ocean/split_lineage_compose.py',
                     *sorted(versions.BEFORE_SPLIT_FINAL)):
            self.source(name, 'original\n')
        self.old = self.commit()
        self.run = self.root / 'run'
        self.run.mkdir()
        (self.run / 'checkpoints').mkdir()
        (self.run / 'preserved').mkdir()
        (self.run / 'timing-events.jsonl').write_text('{}\n')
        self.identity = {'code': code_identity(self.scripts), 'scripts_root': str(self.scripts),
                         'runtime': {'version': 'same'}, 'request': {'sha256': 'a' * 64}}
        self.original = write(self.run / 'run-identity.json', self.identity)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.PIPE).decode().strip()

    def source(self, name, content):
        path = self.scripts / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def commit(self):
        self.git('add', 'scripts')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'fixture')
        return self.git('rev-parse', 'HEAD')

    def new_identity(self):
        result = copy.deepcopy(self.identity)
        result['code'] = code_identity(self.scripts)
        return result

    def upgrade(self, identity=None):
        return versions.upgrade(self.run, self.identity, identity or self.new_identity(),
                                pin(self.original), self.old, self.repo, 0)

    def completed(self, script, name='stage', outputs=None):
        stage = self.run / 'checkpoints' / name
        stage.mkdir()
        return write(stage / 'complete.json', {'invocation': {'code': pin(self.scripts / script),
                                                            'outputs': outputs or []}})

    def change_water(self):
        self.source('v7-replay/validator.py', 'corrected\n')
        return self.commit()

    def test_committed_identity_matches_checked_out_code(self):
        commit, code = versions.committed_code(self.repo, 'HEAD')
        self.assertEqual(commit, self.old)
        self.assertEqual(code, self.identity['code'])

    def test_water_upgrade_retains_original_identity_and_checkpoint_bytes(self):
        receipt = self.completed('v7-raw-mask/build_physical.py')
        old_pins = [pin(self.original), pin(receipt)]
        new_commit = self.change_water()
        proof, stale = self.upgrade()
        self.assertEqual(stale, [])
        self.assertEqual(old_pins, [pin(self.original), pin(receipt)])
        record = json.loads(Path(proof['path']).read_bytes())
        self.assertEqual(record['from_commit'], self.old)
        self.assertEqual(record['to_commit'], new_commit)
        current, parent, stale, count = versions.load(self.run, self.identity, self.repo)
        self.assertEqual(current, self.new_identity())
        self.assertEqual(parent, proof)
        self.assertEqual(count, 1)

    def test_completed_water_is_not_reused_after_water_code_change(self):
        self.completed('v7-replay/validator.py')
        self.change_water()
        with self.assertRaisesRegex(ValueError, 'completed water'):
            self.upgrade()

    def test_upstream_or_shared_change_is_rejected(self):
        for name in ('v7-raw-mask/build_physical.py', 'shared.py'):
            with self.subTest(name=name):
                self.source(name, 'changed\n')
                self.commit()
                with self.assertRaisesRegex(ValueError, 'upstream/shared'):
                    self.upgrade()

    def test_unknown_completed_producer_is_rejected(self):
        self.completed('v7-pipeline/run_pipeline.py')
        self.change_water()
        with self.assertRaisesRegex(ValueError, 'unsupported completed producer'):
            self.upgrade()

    def test_dirty_new_source_is_rejected(self):
        self.source('v7-replay/validator.py', 'uncommitted\n')
        with self.assertRaisesRegex(ValueError, 'clean committed'):
            self.upgrade()

    def test_wrong_old_commit_is_rejected(self):
        self.old = self.change_water()
        with self.assertRaisesRegex(ValueError, 'old-run'):
            self.upgrade()

    def test_unnormalized_journal_cannot_publish_a_transition(self):
        self.change_water()
        with (self.run / 'timing-events.jsonl').open('ab') as stream:
            stream.write(b'{"event":"torn')
        with self.assertRaisesRegex(ValueError, 'normalize torn timing'):
            self.upgrade()
        self.assertFalse((self.run / 'code-versions').exists())

    def test_noncode_identity_changes_are_rejected(self):
        self.change_water()
        identity = self.new_identity()
        identity['runtime']['version'] = 'different'
        with self.assertRaisesRegex(ValueError, 'runtime'):
            self.upgrade(identity)

    def test_partial_coastal_batch_is_recorded_as_stale_without_modification(self):
        batch = self.run / 'coast/batch-start.json'
        batch.parent.mkdir()
        batch.write_text('{"identity":"old"}\n')
        original = pin(batch)
        self.change_water()
        proof, stale = self.upgrade()
        self.assertEqual(stale, [original])
        self.assertEqual(pin(batch), original)
        self.assertEqual(versions.load(self.run, self.identity, self.repo)[2], stale)

    def test_changed_checkpoint_or_timing_is_rejected_on_later_resume(self):
        receipt = self.completed('v7-raw-mask/build_physical.py')
        self.change_water()
        self.upgrade()
        before = receipt.read_bytes()
        receipt.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            versions.load(self.run, self.identity, self.repo)
        receipt.write_bytes(before)
        (self.run / 'timing-events.jsonl').write_text('{bad}\n')
        with self.assertRaisesRegex(ValueError, 'prefix changed'):
            versions.load(self.run, self.identity, self.repo)

    def test_original_identity_mutation_and_missing_transition_are_rejected(self):
        self.change_water()
        proof, _ = self.upgrade()
        self.original.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'chain changed'):
            versions.load(self.run, self.identity, self.repo)
        Path(proof['path']).rename(Path(proof['path']).with_name('000002.json'))
        with self.assertRaisesRegex(ValueError, 'missing or unordered'):
            versions.load(self.run, self.identity, self.repo)

    def test_multiple_transitions_form_a_verified_chain(self):
        self.change_water()
        proof, _ = self.upgrade()
        previous = self.new_identity()
        second_old = self.git('rev-parse', 'HEAD')
        self.source('v7-replay/validator.py', 'second fix\n')
        self.commit()
        second, _ = versions.upgrade(self.run, previous, self.new_identity(), proof,
                                      second_old, self.repo, 1)
        identity, parent, _, count = versions.load(self.run, self.identity, self.repo)
        self.assertEqual(identity, self.new_identity())
        self.assertEqual(parent, second)
        self.assertEqual(count, 2)

    def test_closed_only_upgrade_preserves_earlier_water_across_second_transition(self):
        self.change_water()
        first, _ = self.upgrade()
        previous = self.new_identity()
        old_commit = self.git('rev-parse', 'HEAD')
        receipt = self.completed('v7-recovery/ocean/ocean_fill_runner.py')
        before = [pin(self.original), pin(receipt), pin(self.run / 'timing-events.jsonl')]
        self.source('v7-replay/streaming_closed_water.py', 'closed-only correction\n')
        self.source('v7-replay/test_closed_water_row_lifetime.py', 'test\n')
        self.commit()
        second, stale = versions.upgrade(self.run, previous, self.new_identity(), first,
                                         old_commit, self.repo, 1)
        self.assertEqual(stale, [])
        self.assertEqual(before, [pin(self.original), pin(receipt), pin(self.run / 'timing-events.jsonl')])
        identity, parent, _, count = versions.load(self.run, self.identity, self.repo)
        self.assertEqual((identity, parent, count), (self.new_identity(), second, 2))

    def test_closed_only_upgrade_rejects_completed_closed_or_unknown_water_producer(self):
        self.completed('v7-replay/build_closed_water.py')
        self.source('v7-replay/streaming_closed_water.py', 'corrected\n')
        self.commit()
        with self.assertRaisesRegex(ValueError, 'cannot reuse completed water'):
            self.upgrade()
        (self.run / 'checkpoints/stage/complete.json').unlink()
        self.source('v7-replay/unknown_producer.py', 'producer\n')
        self.completed('v7-replay/unknown_producer.py', 'unknown')
        self.commit()
        with self.assertRaisesRegex(ValueError, 'cannot reuse completed water'):
            self.upgrade()

    def test_closed_upgrade_with_shared_water_change_is_rejected(self):
        self.completed('v7-recovery/ocean/ocean_fill_runner.py')
        self.source('v7-replay/streaming_closed_water.py', 'corrected\n')
        self.source('v7-replay/validator.py', 'shared change\n')
        self.commit()
        with self.assertRaisesRegex(ValueError, 'cannot reuse completed water'):
            self.upgrade()

    def change_split_final(self):
        self.source('v7-recovery/ocean/split_lineage_compose.py', 'split final correction\n')
        self.source('v7-recovery/ocean/test_split_lineage_compose.py', 'test\n')
        return self.commit()

    def test_split_final_third_transition_preserves_all_prior_water_and_provenance(self):
        self.change_water()
        first, _ = self.upgrade()
        previous, old_commit = self.new_identity(), self.git('rev-parse', 'HEAD')
        self.source('v7-replay/streaming_closed_water.py', 'closed correction\n')
        self.commit()
        second, _ = versions.upgrade(self.run, previous, self.new_identity(), first,
                                     old_commit, self.repo, 1)
        previous, old_commit = self.new_identity(), self.git('rev-parse', 'HEAD')
        receipts = []
        for index, entry in enumerate(sorted(versions.BEFORE_SPLIT_FINAL)):
            outputs = [str(self.run / 'baseline-final')] if entry.endswith('/compose_direct.py') else []
            receipts.append(self.completed(entry, 'earlier-' + str(index), outputs))
        batch = self.run / 'coast/batch-start.json'
        batch.parent.mkdir();batch.write_text('{}\n')
        immutable = [self.original, *receipts, self.run / 'timing-events.jsonl',
                     Path(first['path']), Path(second['path']), batch]
        before = [pin(path) for path in immutable]
        self.change_split_final()
        third, stale = versions.upgrade(self.run, previous, self.new_identity(), second,
                                        old_commit, self.repo, 2)
        self.assertEqual(stale, [])
        self.assertEqual(before, [pin(path) for path in immutable])
        identity, parent, _, count = versions.load(self.run, self.identity, self.repo)
        self.assertEqual((identity, parent, count), (self.new_identity(), third, 3))

    def test_split_final_upgrade_rejects_final_later_or_unknown_water_producers(self):
        self.change_split_final()
        for entry in ('v7-recovery/ocean/split_lineage_compose.py',
                      'v7-replay/compare_grids.py', 'v7-replay/unknown.py',
                      'v7-replay/compose_direct.py'):
            with self.subTest(entry=entry):
                receipt = self.completed(entry, outputs=[str(self.run / 'final')])
                with self.assertRaisesRegex(ValueError, 'cannot reuse completed water'):
                    self.upgrade()
                receipt.unlink();receipt.parent.rmdir()

    def test_split_final_plus_shared_or_other_leaf_water_change_is_rejected(self):
        self.completed('v7-recovery/ocean/ocean_fill_runner.py')
        self.change_split_final()
        for entry in ('v7-recovery/ocean/split_lineage_ocean.py',
                      'v7-recovery/ocean/partition_core.py',
                      'v7-replay/streaming_closed_water.py'):
            with self.subTest(entry=entry):
                self.source(entry, 'shared or different leaf\n')
                self.commit()
                with self.assertRaisesRegex(ValueError, 'cannot reuse completed water'):
                    self.upgrade()

    def test_split_final_resume_preserves_failed_output_and_reuses_completed_water(self):
        leaf = ('from pathlib import Path\nimport sys\n'
                'p=Path(sys.argv[1]);p.mkdir();(p/"result").write_text("done")\n')
        stages = [('ocean', 'v7-recovery/ocean/ocean_fill_runner.py'),
                  ('closed', 'v7-replay/build_closed_water.py'),
                  ('baseline-final', 'v7-replay/compose_direct.py'),
                  ('updated-ocean', 'v7-recovery/ocean/split_lineage_ocean.py')]
        split_final = 'v7-recovery/ocean/split_lineage_compose.py'
        for _, entry in stages:
            self.source(entry, leaf)
        self.source(split_final, leaf.replace('"done"', '"partial"') + 'sys.exit(1)\n')
        old_commit = self.commit()
        sentinel = write(self.root / 'sentinel.json', {})
        required = ('land_config water_config raw_manifest land_snapshot resolution_template '
                    'regional_template water_snapshot seavox_archive coastal_plan neon_selection osm_receipt').split()
        config = write(self.root / 'request.json', {'schema': 'worldatlas-end-to-end-pipeline-v1',
            'research_only': True, 'input_root': str(self.root),
            'sources': {key: pin(sentinel) for key in required}})
        out = self.root / 'integration'
        with patch.object(pipeline, 'REPO', self.repo), patch.object(pipeline, 'SCRIPTS', self.scripts):
            first = pipeline.Pipeline(config, out, allow_provisional=True)
            self.addCleanup(first.close)
            for name, entry in stages:
                first.command('water', name, entry, out / name, _outputs=[out / name])
            with self.assertRaisesRegex(RuntimeError, 'failed'):
                first.command('water', 'compose-split-final', split_final, out / 'final',
                              _outputs=[out / 'final'])
            first.close()
            immutable = [out / 'run-identity.json',
                         *(out / 'checkpoints').glob('*/complete.json')]
            before = [pin(path) for path in immutable]
            timing_prefix = (out / 'timing-events.jsonl').read_bytes()
            self.source(split_final, leaf)
            self.commit()
            second = pipeline.Pipeline(config, out, allow_provisional=True, resume=True,
                                       resume_code_from=old_commit, confirm_no_writers=True)
            self.addCleanup(second.close)
            with patch.object(pipeline.subprocess, 'Popen', side_effect=AssertionError('old water restarted')):
                for name, entry in stages:
                    self.assertFalse(second.command('water', name, entry, out / name,
                                                    _outputs=[out / name]))
            second.command('water', 'compose-split-final', split_final, out / 'final',
                           _outputs=[out / 'final'])
            self.assertEqual(before, [pin(path) for path in immutable])
            self.assertTrue((out / 'timing-events.jsonl').read_bytes().startswith(timing_prefix))
            preserved = list((out / 'preserved').glob('compose-split-final-*/0-final/result'))
            self.assertEqual([p.read_text() for p in preserved], ['partial'])
            self.assertEqual((out / 'final/result').read_text(), 'done')
            self.assertTrue((out / 'logs/compose-split-final.log').is_file())
            receipt = json.loads((out / 'checkpoints/compose-split-final/complete.json').read_bytes())
            self.assertEqual(receipt['producer_code_version'], second.code_version)
            self.assertNotEqual(receipt['producer_code_version'], before[0])
            second.close()
            third = pipeline.Pipeline(config, out, allow_provisional=True, resume=True)
            self.addCleanup(third.close)
            self.assertFalse(third.command('water', 'compose-split-final', split_final,
                out / 'final', _outputs=[out / 'final']))

    def test_runner_upgrade_reuses_old_stage_and_binds_new_stage_to_new_version(self):
        leaf = 'from pathlib import Path\nimport sys\np=Path(sys.argv[1]);p.mkdir();(p/"result").write_text("done")\n'
        self.source('v7-raw-mask/build_physical.py', leaf)
        self.source('v7-replay/validator.py', leaf)
        old_commit = self.commit()
        sentinel = write(self.root / 'sentinel.json', {})
        required = ('land_config water_config raw_manifest land_snapshot resolution_template '
                    'regional_template water_snapshot seavox_archive coastal_plan neon_selection osm_receipt').split()
        config = write(self.root / 'request.json', {'schema': 'worldatlas-end-to-end-pipeline-v1',
            'research_only': True, 'input_root': str(self.root),
            'sources': {key: pin(sentinel) for key in required}})
        out = self.root / 'integration'
        with patch.object(pipeline, 'REPO', self.repo), patch.object(pipeline, 'SCRIPTS', self.scripts):
            first = pipeline.Pipeline(config, out, allow_provisional=True)
            self.addCleanup(first.close)
            first.command('physical', 'physical', 'v7-raw-mask/build_physical.py', out / 'physical',
                          _outputs=[out / 'physical'])
            original = pin(out / 'run-identity.json')
            receipt = pin(out / 'checkpoints/physical/complete.json')
            first.close()
            coast = out / 'coast'
            coast.mkdir()
            old_batch = write(coast / 'batch-start.json', {'old': 'partial batch'})
            old_batch_bytes = old_batch.read_bytes()
            self.source('v7-replay/validator.py', leaf + '# downstream fix\n')
            self.commit()
            with (out / 'timing-events.jsonl').open('ab') as stream:
                stream.write(b'{"event":"torn')
            with self.assertRaisesRegex(ValueError, 'identity changed'):
                pipeline.Pipeline(config, out, allow_provisional=True, resume=True)
            second = pipeline.Pipeline(config, out, allow_provisional=True, resume=True,
                                       resume_code_from=old_commit)
            self.addCleanup(second.close)
            with patch.object(pipeline.subprocess, 'Popen', side_effect=AssertionError('old producer restarted')):
                self.assertFalse(second.command('physical', 'physical', 'v7-raw-mask/build_physical.py',
                    out / 'physical', _outputs=[out / 'physical']))
            with patch.object(pipeline.subprocess, 'Popen', wraps=subprocess.Popen) as spawn:
                second.command('water', 'coast', 'v7-replay/validator.py', coast,
                               _outputs=[coast], _resume_marker=coast / 'batch-start.json', _resume_from=True)
            self.assertNotIn('--resume-from', spawn.call_args.args[0])
            preserved = list((out / 'preserved').glob('coast-*/*/batch-start.json'))
            self.assertEqual(len(preserved), 1)
            self.assertEqual(preserved[0].read_bytes(), old_batch_bytes)
            self.assertEqual(original, pin(out / 'run-identity.json'))
            self.assertEqual(receipt, pin(receipt['path']))
            water = json.loads((out / 'checkpoints/coast/complete.json').read_bytes())
            self.assertEqual(water['producer_code_version'], second.code_version)
            self.assertNotEqual(water['producer_code_version'], original)
            self.assertTrue(list(out.glob('timing-events.jsonl.torn-*')))
            second.close()
            third = pipeline.Pipeline(config, out, allow_provisional=True, resume=True)
            self.addCleanup(third.close)
            self.assertEqual(third.code_version, water['producer_code_version'])


if __name__ == '__main__':
    unittest.main()
