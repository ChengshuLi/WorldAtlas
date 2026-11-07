import json
import copy
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import benchmark_regional as benchmark


class BenchmarkRegionalTests(unittest.TestCase):
    def test_only_declared_equivalence_metadata_is_normalized(self):
        before_pin={'path':'/reviewed/module.py','sha256':'c'*64}
        after_pin={'path':'/current/module.py','sha256':'c'*64}
        before={'code_sha256':{'driver':'a'*64,'resolver':'b'*64},
                'point_resolution':{'resolver_sha256':'b'*64,'claims':[{'code':18}]},
                'regional_island_rule':{'provenance':{'code':{'polygon_intersection':before_pin}}}}
        after=copy.deepcopy(before)
        after['code_sha256'].update(driver='d'*64,resolver='e'*64)
        after['point_resolution']['resolver_sha256']='e'*64
        runtime={'path':'/current/runtime.py','sha256':'f'*64}
        after['point_resolution']['equivalent_runtime']={'schema':'selected-point-equivalent-runtime-v1','code':runtime,'geographic_policy_changed':False}
        after['polygon_equivalent_runtime']={'schema':'polygon-equivalent-runtime-v1','code':runtime,'geographic_policy_changed':False,'rasterization_changed':False}
        after['regional_island_rule']['provenance']['code']['polygon_intersection']=after_pin
        equivalence={'orchestration':{'driver':{'before':'a'*64,'after':'d'*64},'resolver':{'before':'b'*64,'after':'e'*64}},
                     'reviewed_code_rebindings':{'polygon_intersection':{'before':before_pin,'after':after_pin}},
                     'point_runtime':runtime,'polygon_runtime':runtime}
        self.assertEqual(benchmark.normalize_equivalence(before,after,equivalence),before)
        after['point_resolution']['claims'][0]['code']=22
        self.assertNotEqual(benchmark.normalize_equivalence(before,after,equivalence),before)
        after['polygon_equivalent_runtime']['rasterization_changed']=True
        with self.assertRaisesRegex(ValueError,'runtime provenance mismatch'):
            benchmark.normalize_equivalence(before,after,equivalence)

    def test_fresh_replay_preserves_reviewed_pins_and_checks_full_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / 'reference'
            reference.mkdir()
            for name in ('rows.u32le', 'runs.u32le', 'changes.jsonl'):
                (reference / name).write_bytes(name.encode())
            report = {'writer': {'affiliation_statistics': {'selected': 7}},
                      'regional_island_rule': {'result': {'proposals': {'1': {'code': 18}}}, 'proposal_trace': {'1': 'source'}}}
            (reference / 'report.json').write_text(json.dumps(report))
            script = root / 'apply_selected_mixed.py'
            script.write_text('# admitted producer\n')
            cfg = {'output': str(reference), 'regional': {'hook': {'reviewed': True},
                    'request': {'code': {'reviewed': 'unchanged'}, 'policy': {'reviewed': 'policy'}}}}
            request = root / 'request.json'
            request.write_text(json.dumps(cfg))
            report['input_lineage']={'request':benchmark.pin(request)}
            report['request_sha256']=benchmark.pin(request)['sha256']
            (reference/'report.json').write_text(json.dumps(report))
            admission = root / 'complete.json'
            admission.write_text(json.dumps({'invocation': {'command': ['python', str(script), str(request)]},
                                            'inputs': [benchmark.pin(script), benchmark.pin(request)]}))
            integration = root / benchmark.INTEGRATION
            integration.mkdir(parents=True)
            for name in ('driver_hook', *benchmark.RUNTIME_NAMES):
                (integration / (name + '.py')).write_text(name)
            seen = {}
            def replay(command, **kwargs):
                prepared = json.loads(Path(command[2]).read_bytes())
                seen.update(prepared)
                shutil.copytree(reference, prepared['output'])
                output=Path(prepared['output'])/'report.json'
                actual=json.loads(output.read_bytes());actual['input_lineage']['request']=benchmark.pin(command[2])
                actual['request_sha256']=benchmark.pin(command[2])['sha256'];output.write_text(json.dumps(actual))
            with patch.object(benchmark, 'environment', return_value={}), patch.object(benchmark.subprocess, 'run', side_effect=replay):
                result = benchmark.run(admission, root / 'benchmark', root)
            self.assertTrue(all(result['parity'][key] for key in result['parity'] if key != 'streams'))
            self.assertEqual(seen['regional']['request']['code'], cfg['regional']['request']['code'])
            self.assertEqual(seen['regional']['request']['policy'], cfg['regional']['request']['policy'])
            self.assertEqual(set(seen['regional']['request']['runtime']), set(benchmark.RUNTIME_NAMES))
            config_parent=(root/'benchmark/inputs/config.json').parent
            self.assertFalse(Path(seen['output']).is_relative_to(config_parent))
            with self.assertRaisesRegex(ValueError, 'fresh benchmark'):
                benchmark.run(admission, root / 'benchmark')
            script.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'admitted input changed'):
                benchmark.run(admission, root / 'never-created')
            self.assertFalse((root / 'never-created').exists())
            candidate = root / 'benchmark/candidate'
            with self.assertRaisesRegex(ValueError,'fresh request provenance mismatch'):
                benchmark.compare(reference,candidate,request_rebinding={'before':benchmark.pin(request),'after':{'path':'wrong','sha256':'0'*64}})
            changed = json.loads((candidate / 'report.json').read_bytes())
            changed['regional_island_rule']['result']['proposals']['1']['code'] = 22
            (candidate / 'report.json').write_text(json.dumps(changed))
            self.assertFalse(benchmark.compare(reference, candidate)['regional_decisions_equal'])


if __name__ == '__main__':
    unittest.main()
