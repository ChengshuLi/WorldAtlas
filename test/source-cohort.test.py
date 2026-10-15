"""Focused source-probe contracts; GIS execution is a separately reported check."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source_cohort', ROOT / 'scripts/qualify-source-cohort.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def fixture():
    paths = ['catalogue.json', 'roster.json', 'lineage.json', 'part.json', 'selector.json',
             'latitudes.bin', 'countries.json', 'registry.json', 'decisions.json',
             'scripts/reconcile-topology.py', 'scripts/prepare.mjs', 'physical.py']
    pins = [dict(path=p, commit='a' * 40, bytes=1, sha256='b' * 64, git_blob_oid='c' * 40) for p in paths]
    target = dict(owner=22849, id='gb:IDN:ADM2:22746128B38340908247842', name='Karimun',
                  source_index=36402, parent_id='framework:province:riau-islands:4839c8831796',
                  reference_owner='Indonesia', source_id='gb:IDN:ADM2', administrative_level='ADM2',
                  reference_year='2020', source_role='regency, city', shape_group='IDN', shape_type='ADM2')
    return dict(version=1, issue=1920, worker_id='focused-test', scientific_input_commit='a' * 40,
                accepted_head='d' * 40, inputs=pins,
                roles=dict(catalogue=paths[0], roster=paths[1], lineage=paths[2], geography=[paths[3]],
                           selector=paths[4], latitudes=paths[5], countries=paths[6], country_registry=paths[7],
                           decisions=paths[8], method_code=paths[9:11]),
                families=[dict(id=k, family_index=v) for k, v in probe.FAMILY_INDICES.items()],
                targets=[target], country=dict(code='IDN', source_prefix='gb:IDN:', registry_hash_key='ne_10m_admin_0_countries'),
                selector_format='cohort-intervals-v1', expected_counts=dict(repair=2, physical=1), expected_segments=2,
                resources=dict(input_bytes=268435456, output_bytes=16777216, deadline_seconds=180),
                runtime=dict(python=sys.version, numpy='test', shapely='test', geos='test'), physical_reproducer=pins[-1])


def selector():
    return dict(scientific_input_commit='a' * 40, source_conflict_segments=[],
                repair_segments=[dict(category='repair', y=130000, start=207200, end=207202,
                                      owners=[22849], sids=[36402], physical='land')],
                physical_segments=[dict(category='physical', y=130000, start=207202, end=207203,
                                        owners=[22849], sids=[36402], physical='source-relative')])


class SourceConfig(unittest.TestCase):
    def test_exact_declared_config(self):
        self.assertEqual(len(probe.validate_config(fixture())), 12)

    def test_missing_and_duplicate_pin_rejected(self):
        for mutate in (lambda c: c['inputs'].pop(0), lambda c: c['inputs'].append(copy.deepcopy(c['inputs'][0]))):
            c = fixture(); mutate(c)
            with self.assertRaises(ValueError): probe.validate_config(c)

    def test_competitor_families_cannot_be_omitted_or_replaced(self):
        for mutate in (lambda c: c['families'].pop(), lambda c: c['families'][2].update(family_index=152),
                       lambda c: c['families'].reverse()):
            c = fixture(); mutate(c)
            with self.assertRaises(ValueError): probe.validate_config(c)

    def test_exact_identity_contract(self):
        for mutate in (lambda c: c['targets'].append(copy.deepcopy(c['targets'][0])),
                       lambda c: c['targets'][0].update(source_id='gb:MYS:ADM2'),
                       lambda c: c['targets'][0].update(reference_year='2019'),
                       lambda c: c['targets'][0].update(parent_id='')):
            c = fixture(); mutate(c)
            with self.assertRaises(ValueError): probe.validate_config(c)

    def test_paths_and_resource_budgets(self):
        for name in ('../outside', '/tmp/file', 'nested/../file', 'nested//file', 'nested\\file'):
            with self.assertRaises(ValueError): probe.safe_path(name)
        for field, value in [('input_bytes', probe.MAX_INPUT + 1), ('output_bytes', probe.MAX_OUTPUT + 1),
                             ('deadline_seconds', 181), ('deadline_seconds', True)]:
            c = fixture(); c['resources'][field] = value
            with self.assertRaises(ValueError): probe.validate_config(c)
        c = fixture(); c['resources']['input_bytes'] = 11
        with self.assertRaisesRegex(ValueError, 'complete input budget'): probe.validate_config(c)

    def test_decoded_inputs_charged(self):
        c = fixture(); p = c['inputs'][0]; p['path'] += '.gz'; c['roles']['catalogue'] = p['path']
        with self.assertRaisesRegex(ValueError, 'Decoded pin'): probe.validate_config(c)
        p.update(decoded_bytes=100, decoded_sha256='e' * 64); c['resources']['input_bytes'] = 111
        with self.assertRaisesRegex(ValueError, 'complete input budget'): probe.validate_config(c)


class Selectors(unittest.TestCase):
    def test_equivalent_retained_and_candidate_formats(self):
        s, c = selector(), fixture()
        rows, counts = probe.selector_segments(s, c)
        candidate = dict(as_of_commit='a' * 40, rows=[[r[k] for k in ('category', 'y', 'start', 'end', 'owners', 'sids', 'physical')] for r in rows])
        c['selector_format'] = 'candidate-rows-v1'
        self.assertEqual(probe.selector_segments(candidate, c), (rows, counts))

    def test_bad_selector_boundaries(self):
        changes = [lambda s: s.update(scientific_input_commit='b' * 40),
                   lambda s: s.update(source_conflict_segments=[{}]),
                   lambda s: s['repair_segments'][0].update(owners=[999]),
                   lambda s: s['repair_segments'][0].update(y=262166),
                   lambda s: s['repair_segments'][0].update(sids=[36402, 36402]),
                   lambda s: s['repair_segments'][0].update(category='physical'),
                   lambda s: s['physical_segments'][0].update(start=207201, end=207202),
                   lambda s: s['repair_segments'][0].update(end=207203)]
        for change in changes:
            s = selector(); change(s)
            with self.subTest(selector=s), self.assertRaises(ValueError): probe.selector_segments(s, fixture())

    def test_duplicate_raw_records_are_not_silently_overwritten(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate identity'): probe.exact_map([{'id': 'x'}, {'id': 'x'}], 'id')
        with self.assertRaisesRegex(ValueError, 'Empty required'): probe.exact_map([], 'id')


class EntryAdmission(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'config.json'
        self.config.write_text(json.dumps(fixture()))
        self.admission = self.root / 'admission.json'
        self.output = self.root / 'result'
        self.receipt = dict(observed_unix_seconds=time.time(), allowance=dict(rssBytes=2**40, phaseBytes=2**40),
                            runtime_inventory_bytes=0, execution_reserve_bytes=0,
                            program_sha256=probe.sha(Path(probe.__file__).read_bytes()), config_sha256=probe.sha(self.config.read_bytes()))

    def execute(self):
        self.admission.write_text(json.dumps(self.receipt))
        return probe.run(self.root, self.config, self.admission, self.output, 'coordination/engineering/test/source-001')

    def test_stale_future_and_drift_admission_create_nothing(self):
        for changes in [dict(observed_unix_seconds=time.time()-61), dict(observed_unix_seconds=time.time()+60),
                        dict(program_sha256='0' * 64), dict(config_sha256='0' * 64)]:
            old = dict(self.receipt); self.receipt.update(changes)
            with self.assertRaises(ValueError): self.execute()
            self.assertFalse(self.output.exists()); self.receipt = old

    def test_complete_phase_admission_includes_runtime_and_reserve(self):
        self.receipt.update(runtime_inventory_bytes=7, execution_reserve_bytes=7)
        self.receipt['allowance']['phaseBytes'] = 26
        with self.assertRaisesRegex(ValueError, 'complete phase'): self.execute()
        self.assertFalse(self.output.exists())

    def test_output_collision_and_dangling_symlink_preserve_sentinel(self):
        self.output.mkdir(); sentinel = self.output / 'keep'; sentinel.write_text('unchanged')
        with self.assertRaisesRegex(ValueError, 'fresh output'): self.execute()
        self.assertEqual(sentinel.read_text(), 'unchanged')
        sentinel.unlink(); self.output.rmdir(); self.output.symlink_to(self.root / 'missing')
        with self.assertRaisesRegex(ValueError, 'Symlink'): self.execute()
        self.assertTrue(self.output.is_symlink()); self.assertFalse((self.root / 'missing').exists())

    def test_symlink_config_rejected(self):
        target = self.config.with_name('real.json'); self.config.rename(target); self.config.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'Symlink'): self.execute()
        self.assertFalse(self.output.exists())

    def test_optimized_cli_rejects_before_science(self):
        self.admission.write_text(json.dumps(self.receipt))
        command = [sys.executable, '-O', '-B', probe.__file__, '--repo', str(self.root), '--config', str(self.config),
                   '--admission', str(self.admission), '--output', str(self.output), '--publication-prefix', 'coordination/engineering/test/source-001']
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Optimized Python', result.stderr)
        self.assertFalse(self.output.exists())


class ScientificFixture(unittest.TestCase):
    """Tiny real Git/GEOS fixture; no full world or GSHHG replay."""
    @classmethod
    def setUpClass(cls):
        try:
            import numpy
            import shapely
            cls.np, cls.shapely = numpy, shapely
            if not hasattr(shapely, 'geos_version_string'):
                raise ImportError('Shapely 2 required')
        except ImportError as error:
            if os.environ.get('WORLDATLAS_REQUIRE_SOURCE_SCIENCE') == '1':
                raise RuntimeError('Required source scientific controls need repository-pinned NumPy/Shapely') from error
            raise unittest.SkipTest('Pinned NumPy/Shapely runtime unavailable: ' + str(error))

    def scientific_run(self, mutation=None, config_mutation=None, runtime_mutation=None):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        def git(*args):
            return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL)
        git('init'); git('config', 'user.email', 'fixture@example.invalid'); git('config', 'user.name', 'Fixture')
        c = fixture(); c['targets'][0].update(owner=1, source_index=11, id='gb:IDN:ADM2:target', name='Target')
        target = c['targets'][0]
        def rectangle(a, b, holes=None):
            rings = [[[a,-.01],[b,-.01],[b,.01],[a,.01],[a,-.01]]]
            return {'type':'Polygon','coordinates':rings + (holes or [])}
        geometry = rectangle(0, .005)
        selected = dict(type='Feature',id=target['id'],geometry=geometry,
                        properties=dict(name=target['name'],reference_owner=target['reference_owner'],parent_id=target['parent_id'],
                        metadata=dict(source_id=target['source_id'],administrative_level=target['administrative_level'],
                                      original_id='target',reference_year='2020',source_role='regency, city')))
        families=[]; roster=[]; data={}
        for i, (family,index) in enumerate(probe.FAMILY_INDICES.items()):
            suffix = 'target' if family == 'gb:IDN:ADM2' else 'other'
            feature=dict(type='Feature',geometry=geometry if suffix=='target' else rectangle(10,11),
                         properties=dict(shapeID=suffix,shapeName='Target' if suffix=='target' else 'Other',shapeGroup=family.split(':')[1],shapeType=family.split(':')[2]))
            product=dict(type='FeatureCollection',crs=dict(properties=dict(name='urn:ogc:def:crs:OGC:1.3:CRS84')),features=[feature])
            filename='source-'+str(i)+'.json'; data[filename]=product
            roster.append(dict(source_id=family+':'+suffix,source_index=i+10,family_index=index,owners=[1] if suffix=='target' else []))
            families.append(dict(key=family,parts=[dict(path=filename)],feature_count=1,source_represented_year_claim='2020',recorded_license='fixture'))
        data.update({'catalogue.json':dict(products=families), 'roster.json':roster,
            'lineage.json':dict(locations=[dict(index=1,id=target['id'],name='Target',province_id=target['parent_id'],source_atoms=[target['id']])],reverse={target['id']:[1]}),
            'part.json':dict(features=[selected]),
            'selector.json':dict(as_of_commit=None,rows=[['repair',130000,131083,131085,[1],[11],'land'],['physical',130000,131085,131086,[1],[11],'source-relative']]),
            'countries.json':dict(features=[dict(geometry=rectangle(.0005,.001),properties=dict(ADM0_A3='IDN',ADMIN='Indonesia'))]),
            'registry.json':dict(hashes={}), 'decisions.json':dict(location_review=[dict(ids=[target['id']],status='open')])})
        c['selector_format']='candidate-rows-v1'
        # Selector's scientific commit cannot self-reference the commit containing
        # itself; pin that later selector in a second immutable commit instead.
        if mutation: mutation(data, c)
        def encoded(value):return (json.dumps(value,separators=(',',':'))+'\n').encode()
        for family in families:
            raw=encoded(data[family['parts'][0]['path']]); family.update(original_bytes=len(raw),original_sha256=probe.sha(raw))
            family['parts'][0].update(bytes=len(raw),sha256=probe.sha(raw),uncompressed_bytes=len(raw),uncompressed_sha256=probe.sha(raw))
        data['registry.json']['hashes']['ne_10m_admin_0_countries']=probe.sha(encoded(data['countries.json']))
        for filename,value in data.items(): (root/filename).write_bytes(encoded(value))
        (root/'latitudes.bin').write_bytes(self.np.zeros(probe.GRID,dtype='<f8').tobytes())
        (root/'scripts').mkdir()
        for name in ('scripts/reconcile-topology.py','scripts/prepare.mjs','physical.py'): (root/name).write_text('# Fixture method bytes\n')
        git('add','.'); git('commit','-qm','scientific inputs'); base=git('rev-parse','HEAD').decode().strip()
        data['selector.json']['as_of_commit']=base; (root/'selector.json').write_bytes(encoded(data['selector.json']))
        git('add','selector.json'); git('commit','-qm','exact selectors'); selector_commit=git('rev-parse','HEAD').decode().strip()
        c.update(scientific_input_commit=base,accepted_head=selector_commit)
        paths=[p['path'] for p in c['inputs']]+['source-'+str(i)+'.json' for i in range(9)]
        c['inputs']=[]
        for name in paths:
            commit=selector_commit if name=='selector.json' else base; raw=git('show',commit+':'+name)
            c['inputs'].append(dict(path=name,commit=commit,bytes=len(raw),sha256=probe.sha(raw),git_blob_oid=git('rev-parse',commit+':'+name).decode().strip()))
        c['physical_reproducer']=next(p for p in c['inputs'] if p['path']=='physical.py')
        c['runtime']=dict(python=sys.version,numpy=self.np.__version__,shapely=self.shapely.__version__,geos=self.shapely.geos_version_string)
        if config_mutation: config_mutation(c)
        config=root/'config.json'; config.write_bytes(encoded(c))
        runtime_files=[dict(path=p,bytes=Path(p).stat().st_size,sha256=probe.sha(Path(p).read_bytes())) for p in probe.runtime_paths()]
        if runtime_mutation: runtime_mutation(runtime_files)
        admission=root/'admission.json'; admission.write_bytes(encoded(dict(observed_unix_seconds=time.time(),allowance=dict(rssBytes=536870912,phaseBytes=536870912),
            runtime_files=runtime_files,runtime_inventory_bytes=sum(p['bytes'] for p in runtime_files),execution_reserve_bytes=MAX_TEST_RESERVE,program_sha256=probe.sha(Path(probe.__file__).read_bytes()),config_sha256=probe.sha(config.read_bytes()))))
        output=root/'result'
        self.last_output = output
        result=probe.run(root,config,admission,output,'coordination/engineering/test/source-001')
        return root,output,result

    def test_actual_entry_products_preserve_holds_and_receipt_hashes(self):
        root,out,result=self.scientific_run()
        self.assertTrue(result['complete'])
        qualification=json.loads((out/'source-qualification.json').read_bytes())
        self.assertEqual(qualification['candidate_cells'],3)
        self.assertEqual(qualification['source_prerequisite_repair_candidates'],2)
        self.assertEqual(qualification['physical_interpretation_held_cells'],1)
        self.assertEqual(qualification['outside_retained_IDN_reference_cells'],2)
        self.assertEqual(qualification['native_authority_qualified_cells'],0)
        self.assertEqual(qualification['repaired_credit'],0)
        self.assertEqual(len(qualification['complete_families']),9)
        receipt=json.loads((out/'execution-receipt.json').read_bytes())
        for pin in receipt['outputs']:
            self.assertTrue(pin['path'].startswith('coordination/engineering/test/source-001/'))
            raw=(out/Path(pin['path']).name).read_bytes()
            self.assertEqual((len(raw),probe.sha(raw)),(pin['bytes'],pin['sha256']))

    def test_reference_competitor_withheld_but_source_observations_survive(self):
        def mutate(data,c):
            data['countries.json']['features'].append(dict(geometry={'type':'Polygon','coordinates':[[[.002,-.01],[.0022,-.01],[.0022,.01],[.002,.01],[.002,-.01]]]},properties=dict(ADM0_A3='MYS',ADMIN='Malaysia')))
        root,out,result=self.scientific_run(mutate)
        q=json.loads((out/'source-qualification.json').read_bytes())
        self.assertEqual(q['competing_reference_country_cells'],1)
        self.assertEqual(q['source_prerequisite_repair_candidates'],1)
        self.assertEqual(q['competing_reference_countries'][0]['interval_witnesses'],[dict(x=131084,y=130000)])
        self.assertEqual(q['covering_source_members'][0]['candidate_cells'],3)

    def test_foreign_source_withheld_even_without_reference_hit(self):
        def mutate(data,c):
            data['source-2.json']['features'][0]['geometry']={'type':'Polygon','coordinates':[[[.002,-.01],[.0022,-.01],[.0022,.01],[.002,.01],[.002,-.01]]]}
            data['selector.json']['rows']=[['repair',130000,131083,131084,[1],[11],'land'],['repair',130000,131084,131085,[1],[11,12],'land'],['physical',130000,131085,131086,[1],[11],'source-relative']]
            c['expected_segments']=3
        root,out,result=self.scientific_run(mutate)
        q=json.loads((out/'source-qualification.json').read_bytes())
        self.assertEqual(q['competing_foreign_source_cells'],1)
        self.assertEqual(q['competing_reference_country_cells'],0)
        self.assertEqual(q['source_prerequisite_repair_candidates'],1)


    def test_full_node_source_entry_resume_and_tampered_product(self):
        root, _, _ = self.scientific_run()
        source = json.loads((root / 'config.json').read_bytes())
        runtime_files = json.loads((root / 'admission.json').read_bytes())['runtime_files']
        executable = str(Path(sys.executable).resolve())
        python_pin = next(pin for pin in runtime_files if str(Path(pin['path']).resolve()) == executable)
        python_pin['path'] = sys.executable
        config = dict(version=1, source=source, runtime_inventory=dict(python=python_pin, files=runtime_files),
                      processing_allowance=dict(phaseBytes=536870912, rssBytes=536870912))
        (root / 'cli-config.json').write_text(json.dumps(config))
        destination = '.cache/delivery-handoff/source-fixture-001'
        command = ['node', str(ROOT / 'scripts/prepare-delivery-handoff.mjs'),
                   'source', 'cli-config.json', destination]
        env = {k: v for k, v in os.environ.items() if k not in ('NODE_OPTIONS', 'NODE_PATH')}
        env['GIT_NO_LAZY_FETCH'] = '1'
        # Fresh automatic Node admission replaces the duplicated manual parent
        # cap. Explicit intentional caps and unavailable memory still refuse
        # before scientific scratch or outputs are created.
        limited = dict(config, preparation_allowance=dict(phaseBytes=1, rssBytes=536870912))
        (root / 'cli-config.json').write_text(json.dumps(limited))
        denied = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(denied.returncode, 0)
        self.assertFalse((root / '.cache/delivery-handoff').exists())
        (root / 'cli-config.json').write_text(json.dumps(config))
        exhausted = dict(env, WORLDATLAS_MEMORY_HEADROOM_BYTES=str(2**52))
        denied = subprocess.run(command, cwd=root, env=exhausted, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn('Insufficient current preparation memory', denied.stderr)
        self.assertFalse((root / '.cache/delivery-handoff').exists())
        first = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertFalse(json.loads(first.stdout)['resumed'])
        output = root / destination
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.iterdir()}
        resumed = subprocess.run(command + ['--resume'], cwd=root, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertTrue(json.loads(resumed.stdout)['resumed'])
        self.assertNotIn('observation', json.loads(resumed.stdout))
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.iterdir()})
        # The prior admission time and every immutable output remain literal,
        # rather than rerunning the producer and normalizing its new observation.
        damaged = output / 'source-qualification.json'
        damaged.write_bytes(damaged.read_bytes() + b'\n')
        tampered = damaged.read_bytes()
        denied = subprocess.run(command + ['--resume'], cwd=root, env=env, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn('Source resumed product changed', denied.stderr)
        self.assertEqual(damaged.read_bytes(), tampered)

    def test_actual_consumed_pin_and_runtime_omission_fail(self):
        for mutation in [lambda c:c['inputs'][0].update(sha256='0'*64),
                         lambda c:c['inputs'][0].update(git_blob_oid='0'*40),
                         lambda c:c['inputs'][0].update(commit=c['accepted_head'])]:
            with self.assertRaises((ValueError,subprocess.CalledProcessError)):
                self.scientific_run(config_mutation=mutation)
            self.assertFalse(self.last_output.exists())
        with self.assertRaisesRegex(ValueError,'runtime file omitted'):
            self.scientific_run(runtime_mutation=lambda files:files.pop())
        self.assertFalse(self.last_output.exists())

    def test_scientific_adverse_inputs_rejected(self):
        mutations=[lambda d,c:d['lineage.json']['locations'][0].update(province_id='wrong'),
                   lambda d,c:d['part.json']['features'][0]['properties']['metadata'].update(topology_reconciled=True),
                   lambda d,c:d['source-1.json']['crs']['properties'].update(name='EPSG:3857'),
                   lambda d,c:d['source-1.json']['features'][0]['properties'].update(shapeName='Wrong'),
                   lambda d,c:d['selector.json']['rows'][0].__setitem__(5,[999]),
                   lambda d,c:d['roster.json'].append(copy.deepcopy(d['roster.json'][1])),
                   lambda d,c:d['source-1.json']['features'][0]['geometry']['coordinates'].append([[.004,-.005],[.0045,-.005],[.0045,.005],[.004,.005],[.004,-.005]])]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises((AssertionError,ValueError)):
                self.scientific_run(mutation)
            self.assertFalse(self.last_output.exists())


MAX_TEST_RESERVE = 64 * 1024 * 1024


if __name__ == '__main__':
    unittest.main()
