#!/usr/bin/env python3
"""Run the pinned raw-source WorldAtlas research pipeline through final composition."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCRIPTS = REPO / 'scripts'
STAGE2 = 'v7-recovery/land/stage2-geodesic-20261104'
REGIONAL = 'v7-land/research-mixed-runtime/stage3-mixed-leeward-full-20261105'
OCEAN = 'v7-recovery/ocean'
REPLAY = 'v7-replay'
SHORE = 'wgs84-coastal-4neighbor-center-v2'


def validate_runtime():
    missing = [name for name in ('numpy', 'scipy', 'pyproj', 'osgeo', 'pyarrow')
               if importlib.util.find_spec(name) is None]
    missing.extend(name for name in ('g++', 'ogr2ogr', 'gdal_rasterize') if shutil.which(name) is None)
    if missing:
        raise ValueError('runtime prerequisites missing from this interpreter/PATH: ' + ', '.join(missing))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def pin(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError(f'not a file: {path}')
    return {'path': str(path), 'sha256': sha(path)}


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    """Create a durable new document; never overwrite a prior result."""
    path = Path(path)
    with path.open('x') as f:
        json.dump(value, f, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return path


def rle_spec(directory, *, physical=False):
    """Pin streams/report and, for physical input, its verified mask identity."""
    directory = Path(directory)
    spec = {key + '_' + field: value for key, name in
            [('rows', 'rows.u32le'), ('runs', 'runs.u32le'), ('report', 'report.json')]
            for field, value in pin(directory / name).items()}
    if physical:
        report = read(directory / 'report.json')
        mask_hash = sha(directory / 'physical-dry.tif')
        if report.get('output_sha256', {}).get('physical-dry.tif') != mask_hash:
            raise ValueError('physical mask does not match its producer report')
        spec['physical_mask_sha256'] = mask_hash
    return spec


def elapsed_union(intervals):
    """Elapsed busy time, counting simultaneous work only once."""
    merged = []
    for start, end in sorted(intervals):
        if not (math.isfinite(start) and math.isfinite(end) and end >= start):
            raise ValueError('invalid processing interval')
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return sum(end - start for start, end in merged)


class Timing:
    """Append-only same-process monotonic intervals, durable after each event.

    An unmatched start never becomes an estimated completed duration. The runner
    deliberately has no resume switch: preserve a failed run and start a fresh
    one when a complete baseline is needed.
    """
    def __init__(self, path):
        self.path = Path(path)
        with self.path.open('x') as f:
            f.flush()
            os.fsync(f.fileno())
        fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        self.lock = threading.Lock()
        self.records = []
        self.open = set()
        self.completed_groups = set()

    def event(self, value):
        with self.lock:
            with self.path.open('a') as f:
                f.write(json.dumps(value, sort_keys=True, allow_nan=False) + '\n')
                f.flush()
                os.fsync(f.fileno())
            self.records.append(value)
            if value['event'] == 'start':
                self.open.add(value['id'])
            elif value['event'] in ('complete', 'failed'):
                self.open.discard(value['id'])

    @contextmanager
    def measure(self, group, name):
        started = time.monotonic()
        ident = f'{group}/{name}'
        self.event({'event': 'start', 'id': ident, 'group': group,
                    'monotonic_seconds': started,
                    'utc': datetime.now(timezone.utc).isoformat()})
        try:
            yield
        except BaseException:
            self.event({'event': 'failed', 'id': ident, 'group': group,
                        'monotonic_seconds': time.monotonic()})
            raise
        else:
            self.event({'event': 'complete', 'id': ident, 'group': group,
                        'start_monotonic_seconds': started,
                        'monotonic_seconds': time.monotonic()})

    def summary(self, physical_report):
        groups = {}
        for group in ('setup', 'mainland', 'water', 'verification'):
            completed = [r for r in self.records if r['event'] == 'complete' and r['group'] == group]
            failed = any(r['event'] == 'failed' and r['group'] == group for r in self.records)
            groups[group] = {'processing_elapsed_seconds': elapsed_union([
                (r['start_monotonic_seconds'], r['monotonic_seconds']) for r in completed]),
                'complete': group in self.completed_groups and not failed and not any(x.startswith(group + '/') for x in self.open),
                'semantics': 'union of completed local processing intervals; concurrent work counted once'}
        # Staging is serialized. Subtract measured child acquisition from the
        # parent stage wall interval, retaining startup/configuration overhead.
        p = physical_report or {}
        physical_intervals = [(r['start_monotonic_seconds'], r['monotonic_seconds'])
                              for r in self.records if r['event'] == 'complete' and r['group'] == 'physical']
        physical_wall = elapsed_union(physical_intervals)
        download = p.get('source_download_elapsed_seconds')
        complete = ('physical' in self.completed_groups and p.get('status') == 'candidate-only'
                    and bool(physical_intervals))
        timing_error = None
        if complete and (type(download) not in (int, float) or not math.isfinite(download)
                         or download < 0 or download > physical_wall):
            complete = False
            timing_error = 'missing or invalid physical acquisition timing'
        groups['physical'] = {
            'processing_elapsed_seconds': physical_wall - download if complete else None,
            'source_download_elapsed_seconds': download,
            'producer_processing_elapsed_seconds': p.get('processing_elapsed_seconds'),
            'complete': complete, 'timing_error': timing_error,
            'semantics': 'parent physical-stage wall interval, excluding measured serialized source downloads'}
        return groups


class Pipeline:
    def __init__(self, config, output, *, allow_provisional=False):
        setup_started = time.monotonic()
        setup_utc = datetime.now(timezone.utc).isoformat()
        self.config_path = Path(config).resolve(strict=True)
        self.config_pin = pin(self.config_path)
        self.cfg = read(self.config_path)
        if self.cfg.get('schema') != 'worldatlas-end-to-end-pipeline-v1':
            raise ValueError('unsupported end-to-end configuration')
        if self.cfg.get('research_only') is not True or not allow_provisional:
            raise ValueError('explicit --allow-provisional-research required; no accepted geography is claimed')
        self.root = Path(self.cfg['input_root']).resolve(strict=True)
        self.out = Path(output).resolve()
        if (not self.root.is_dir() or self.out.exists() or not self.out.parent.is_dir()
                or not self.out.is_relative_to(self.root)
                or self.config_path.is_relative_to(self.out)):
            raise ValueError('new output inside input_root, outside its input files, required')
        validate_runtime()
        self.source_pins = []
        self.allow_provisional = allow_provisional
        # Verify every external document before expensive computation starts.
        self.sources = self.resolve_pins(self.cfg.get('sources', {}))
        required = {'land_config', 'water_config', 'raw_manifest', 'land_snapshot',
                    'resolution_template', 'regional_template', 'water_snapshot',
                    'seavox_archive', 'coastal_plan', 'neon_selection', 'osm_receipt'}
        if not required <= self.sources.keys() or set(self.sources) - required - {'prior_physical_report', 'ocean_snapshot', 'reference_rows', 'reference_runs'}:
            raise ValueError('wrong source selection input set')
        if bool('reference_rows' in self.sources) != bool('reference_runs' in self.sources):
            raise ValueError('both reference stream pins are required')
        self.out.mkdir(mode=0o700)
        for name in ('configs', 'work', 'logs', 'scratch', 'basins', 'extractions'):
            (self.out / name).mkdir(mode=0o700)
        self.env = os.environ.copy()
        self.env.update({key: str(self.out / 'scratch') for key in
                         ('TMPDIR', 'TMP', 'TEMP', 'CPL_TMPDIR', 'SQLITE_TMPDIR')})
        self.timing = Timing(self.out / 'timing-events.jsonl')
        self.processes = set()
        self.process_lock = threading.RLock()
        self.cancelled = threading.Event()
        write(self.out / 'request.json', self.cfg)
        self.timing.event({'event': 'start', 'id': 'setup/source-validation', 'group': 'setup',
                           'monotonic_seconds': setup_started, 'utc': setup_utc})
        self.timing.event({'event': 'complete', 'id': 'setup/source-validation', 'group': 'setup',
                           'start_monotonic_seconds': setup_started, 'monotonic_seconds': time.monotonic()})
        self.timing.completed_groups.add('setup')

    def resolve_pins(self, value):
        if isinstance(value, dict) and set(value) == {'path', 'sha256'}:
            path = Path(value['path'])
            if not path.is_absolute():
                path = self.config_path.parent / path
            path = path.resolve(strict=True)
            if (not path.is_relative_to(self.root) or path.is_relative_to(self.out)
                    or sha(path) != value['sha256']):
                raise ValueError(f'source pin mismatch or outside input root: {path}')
            self.source_pins.append({'path': str(path), 'sha256': value['sha256']})
            return path
        if isinstance(value, dict):
            return {key: self.resolve_pins(item) for key, item in value.items()}
        raise ValueError('all source selections must be explicit path/SHA-256 pins')

    def document(self, name, value):
        return write(self.out / 'configs' / (name + '.json'), value)

    def command(self, group, name, script, *args, **options):
        """Only repository stage entrypoints chosen in this module may run."""
        script_path = (SCRIPTS / script).resolve(strict=True)
        if not script_path.is_relative_to(SCRIPTS):
            raise ValueError('stage entrypoint outside repository')
        command = [sys.executable, str(script_path), *map(str, args)]
        for key, value in options.items():
            if value is False or value is None:
                continue
            command.append('--' + key.replace('_', '-'))
            if value is not True:
                command.extend(map(str, value if isinstance(value, (list, tuple)) else [value]))
        code = pin(script_path)
        with self.timing.measure(group, name):
            with (self.out / 'logs' / (name + '.log')).open('xb') as log:
                with self.process_lock:
                    if self.cancelled.is_set():
                        raise InterruptedError('pipeline cancelled')
                    process = subprocess.Popen(command, env=self.env, stdout=log,
                                               stderr=subprocess.STDOUT, start_new_session=True)
                    self.processes.add(process)
                try:
                    status = process.wait()
                    if status:
                        raise RuntimeError(f'{name} failed ({status}); inspect {log.name}')
                    if pin(script_path) != code:
                        raise ValueError(f'stage entrypoint changed during execution: {script}')
                finally:
                    with self.process_lock:
                        self.processes.discard(process)

    def cancel(self):
        self.cancelled.set()
        with self.process_lock:
            for process in self.processes:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass

    def flags(self):
        return {'allow_unverified_snapshot': True, 'allow_draft_snapshot': True}

    def pinned_options(self, prefix, path):
        spec = pin(path)
        return {prefix: spec['path'], prefix + '_sha256': spec['sha256']}

    def streams(self, prefix, directory):
        options = {}
        for key, name in (('rows', 'rows.u32le'), ('runs', 'runs.u32le'), ('report', 'report.json')):
            options.update(self.pinned_options(prefix + '_' + key, directory / name))
        return options

    def physical(self):
        cfg = {'schema': 'raw-physical-pipeline-v1',
               'selection_notes': self.cfg['selection_notes'],
               **self.cfg.get('physical_controls', {}),
               **{key: pin(self.sources[source]) for key, source in
                  [('land_config', 'land_config'), ('water_config', 'water_config'),
                   ('source_manifest', 'raw_manifest')]}}
        self.command('physical', 'physical', 'v7-raw-mask/build_physical.py',
                     self.document('physical', cfg), self.out / 'physical')
        return self.out / 'physical' / 'physical'

    def mainland(self, physical):
        """Generate requests from fresh streams; do not edit a prior run's reports."""
        with self.timing.measure('mainland', 'prepare-components'):
            grid = read(physical / 'report.json')['grid']
            cfg = {'schema': 'fresh-physical-components-v1', 'grid': grid,
                   'inputs': {key: pin(path) for key, path in {
                       'physical_rows': physical / 'rows.u32le',
                       'physical_runs': physical / 'runs.u32le',
                       'physical_report': physical / 'report.json',
                       'component_source': SCRIPTS / 'v7-recovery/land/simple-v2-baseline/build_components.cpp'}.items()},
                   'controls': {'minimum_free_bytes': self.cfg['land_controls']['minimum_free_bytes']}}
            component_request = self.document('components', cfg)
        components = self.out / 'components'
        self.command('mainland', 'components',
                     'v7-recovery/land/fresh-components-20261104/watch_components.py',
                     component_request, self.out / 'work' / 'components', components)
        with self.timing.measure('mainland', 'prepare-stage2'):
            inputs = self.prepare_stage2(physical, components, grid)
            outer = self.document('stage2', {'schema': 'stage2-fresh-orchestration-v1',
                'grid': grid, 'inputs': inputs,
                'policy_id': self.cfg['land_policy']['id'],
                'policy_version': self.cfg['land_policy']['version'],
                'controls': self.cfg['land_controls'],
                'seed_controls': self.cfg.get('seed_controls', {'strip_rows': 64})})
        work = self.out / 'work' / 'stage2-provisional-only'
        stageout = self.out / 'stage2-provisional-only'
        self.command('mainland', 'stage2', STAGE2 + '/orchestrate_stage2.py',
                     outer, work, stageout, provisional_only=True)
        prepared = self.out / 'regional-inputs'
        land = self.out / 'land'
        self.command('mainland', 'prepare-regional', REGIONAL + '/prepare_fresh_handoff.py',
                     template=self.sources['regional_template'],
                     template_sha256=sha(self.sources['regional_template']),
                     outer=outer, work=work, stage2_output=stageout,
                     destination=prepared, regional_output=land)
        self.command('mainland', 'regional', REGIONAL + '/apply_selected_mixed.py',
                     prepared / 'config.json')
        return land

    def prepare_stage2(self, physical, components, grid):
        inputs = {key: pin(path) for key, path in {
            'decision_snapshot': self.sources['land_snapshot'],
            'physical_rows': physical / 'rows.u32le', 'physical_runs': physical / 'runs.u32le',
            'physical_report': physical / 'report.json',
            'component_rows': components / 'rows.u32le', 'component_runs': components / 'runs.u32le',
            'component_manifest': components / 'manifest.json',
            'component_builder_binary': components / 'component-builder',
            'component_source': SCRIPTS / 'v7-recovery/land/simple-v2-baseline/build_components.cpp',
            'closure_checker': SCRIPTS / 'v7-recovery/land/mainland-source-verification-20261104/validate_water_closure_v2.py',
            'terminal_checker': SCRIPTS / 'v7-recovery/land/mainland-source-verification-20261104/validate_terminal_closure.py',
            'seed_builder': SCRIPTS / 'v7-recovery/land/neon-mainland-regions-20261104/rasterizer/build_seed.py',
            'seed_kernel': SCRIPTS / 'v7-recovery/land/neon-mainland-regions-20261104/rasterizer/seed_kernel.cpp'}.items()}
        if 'prior_physical_report' in self.sources:
            inputs['prior_physical_report'] = pin(self.sources['prior_physical_report'])
        resolution = read(self.sources['resolution_template'])
        if resolution.get('schema') != 'mainland-witness-request-v1':
            raise ValueError('wrong mainland resolution template')
        for key in ('physical_rows', 'physical_runs', 'component_rows', 'component_runs',
                    'component_manifest', 'component_source'):
            resolution[key] = inputs[key]
        resolution['snapshot'] = inputs['decision_snapshot']
        resolution['grid'] = grid
        resolution['code_sha256'] = {key: sha(SCRIPTS / STAGE2 / rel) for key, rel in {
            'resolver': 'v7-land/mainland-witness-prototype/resolve_mainland.py',
            'helper': 'v7-land/point-component-prototype/resolve.py',
            'named_identity': 'v7-land/named-identity-prototype/named_identity.py'}.items()}
        inputs['resolution_request'] = pin(self.document('resolution', resolution))
        # The supported source contract accepts an explicitly pinned producer;
        # no copied producer script or patched report is generated.
        closure = {'schema': 'physical-water-closure-contract-v2',
            'grid': {'crs': 'EPSG:4326', 'width': grid['width'], 'height': grid['height'],
                     'west': grid['west'], 'north': grid['north'],
                     'step_numerator': 360, 'step_denominator': grid['width']},
            'physical': {'rows_sha256': inputs['physical_rows']['sha256'],
                         'runs_sha256': inputs['physical_runs']['sha256'],
                         'report_sha256': inputs['physical_report']['sha256'],
                         'water_code': 1, 'land_code': 17,
                         'producer_code_path': str(SCRIPTS / 'v7-raw-mask/compose_physical.py'),
                         'encoding_evidence_sha256': sha(SCRIPTS / 'v7-raw-mask/compose_physical.py')},
            'resources': {'max_cell_visits': 2000000}}
        inputs['closure_contract'] = pin(self.document('closure', closure))
        lineage = {'schema': 'stage1-raw-physical-lineage-request-v1', 'code_root': str(SCRIPTS / 'v7-raw-mask'), 'inputs': {
            'pipeline_report': pin(self.out / 'physical' / 'report.json'),
            'neon_selection': pin(self.sources['neon_selection']),
            'osm_receipt': pin(self.sources['osm_receipt'])}}
        inputs['physical_lineage_request'] = pin(self.document('physical-lineage', lineage))
        return inputs

    def basin(self, decision, physical, land, snapshot):
        ident = decision['id']
        if not isinstance(ident, str) or not ident or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in ident):
            raise ValueError('unsafe basin decision ID')
        extraction = self.out / 'extractions' / ident
        self.command('water', 'extract-' + ident, REPLAY + '/extract_seavox_feature.py',
                     archive=self.sources['seavox_archive'], input_root=self.root,
                     policy=snapshot, policy_sha256=sha(snapshot), decision_id=ident,
                     out=extraction, **self.flags())
        out = self.out / 'basins' / ident
        options = {**self.pinned_options('rows', physical / 'rows.u32le'),
                   **self.pinned_options('runs', physical / 'runs.u32le'),
                   **self.pinned_options('land_rows', land / 'rows.u32le'),
                   **self.pinned_options('land_runs', land / 'runs.u32le')}
        self.command('water', 'basin-' + ident, REPLAY + '/build_seavox_basin.py',
                     input_root=self.root, geometry=extraction / 'source.geojson',
                     archive=self.sources['seavox_archive'],
                     extraction_manifest=extraction / 'manifest.json',
                     extraction_manifest_sha256=sha(extraction / 'manifest.json'),
                     policy=snapshot, policy_sha256=sha(snapshot), decision_id=ident,
                     shore_pad_degrees=self.cfg.get('shore_pad_degrees', 8),
                     research_shore_method=SHORE, out=out, **options, **self.flags())
        self.command('water', 'verify-basin-' + ident, REPLAY + '/verify_basin_coverage.py',
                     **self.pinned_options('manifest', out / 'manifest.json'),
                     physical_rows=physical / 'rows.u32le', physical_runs=physical / 'runs.u32le',
                     **self.pinned_options('policy', snapshot), allow_draft_snapshot=True)
        return {'decision_id': ident, 'manifest_path': str(out / 'manifest.json'),
                'manifest_sha256': sha(out / 'manifest.json')}

    def coast(self, physical, land, snapshot):
        out = self.out / 'coast'
        self.command('water', 'coast', REPLAY + '/batch_coastal_tiles.py',
                     **self.pinned_options('snapshot', snapshot),
                     **self.streams('physical', physical), **self.streams('land', land),
                     input_root=self.root, **self.pinned_options('plan', self.sources['coastal_plan']),
                     out=out, allow_unverified_snapshot=True, allow_draft=True,
                     allow_selected_research_policy=True)
        with self.timing.measure('water', 'prepare-coast-assembly'):
            batch = read(out / 'batch-complete.json')
            tile_list = self.document('coast-tiles', {'tiles': [
                {'manifest_path': str(out / f"tile-{item['tile']:04d}" / 'manifest.json'),
                 'manifest_sha256': item['manifest_sha256']} for item in batch['tiles']]})
        assembled = self.out / 'coast-manifest.json'
        self.command('water', 'assemble-coast', REPLAY + '/assemble_coastal_tiles.py',
                     **self.pinned_options('snapshot', snapshot), input_root=self.root,
                     tile_list=tile_list, out=assembled, allow_unverified_snapshot=True,
                     allow_draft=True, allow_selected_research_policy=True)
        return {'manifest_path': str(assembled), 'manifest_sha256': sha(assembled)}

    def water(self, physical, land):
        snapshot = self.sources['water_snapshot']
        with self.timing.measure('water', 'prepare-water-selection'):
            decisions = read(snapshot)['basins']
            workers = self.cfg.get('basin_workers', 1)
            if type(workers) is not int or workers < 1:
                raise ValueError('basin_workers must be a positive integer')
        with ThreadPoolExecutor(max_workers=1) as coast_pool, ThreadPoolExecutor(max_workers=workers) as pool:
            coastal = coast_pool.submit(self.coast, physical, land, snapshot)
            jobs = [pool.submit(self.basin, d, physical, land, snapshot) for d in decisions]
            try:
                basins = [job.result() for job in jobs]
                coast = coastal.result()
            except BaseException:
                self.cancel()
                for job in [coastal, *jobs]:
                    job.cancel()
                raise
        with self.timing.measure('water', 'prepare-prefill'):
            cfg = {'rle_inputs': {'physical': rle_spec(physical, physical=True), 'land': rle_spec(land)},
                   'coastal_band': coast, 'basins': basins}
            prefill_inputs = self.document('prefill-inputs', cfg)
        plan = self.out / 'prefill-plan.json'
        self.command('water', 'prefill-plan', REPLAY + '/build_prefill_plan.py',
                     input_root=self.root, inputs=prefill_inputs,
                     **self.pinned_options('policy', snapshot), out=plan,
                     allow_research_shore=True, **self.flags())
        prefill = self.out / 'prefill'
        self.command('water', 'prefill', REPLAY + '/build_prefill.py',
                     plan=plan, input_root=self.root, out=prefill,
                     allow_research_shore=True, **self.flags())
        ocean = self.run_ocean(physical, prefill, plan, snapshot, 'ocean')
        closed = self.out / 'closed'
        self.command('water', 'closed', REPLAY + '/build_closed_water.py',
                     **self.pinned_options('snapshot', snapshot),
                     **self.streams('physical', physical), **self.streams('land', land),
                     **self.pinned_options('prefill_rows', prefill / 'prefill-rows.u32le'),
                     **self.pinned_options('prefill_runs', prefill / 'prefill-runs.u32le'),
                     **self.pinned_options('prefill_audit', prefill / 'prefill-audit.json'),
                     **self.pinned_options('prefill_plan', plan),
                     **self.pinned_options('partition_manifest', ocean / 'partition/manifest.json'),
                     **self.pinned_options('component_rows', ocean / 'partition/unseeded_rows.u64le'),
                     **self.pinned_options('component_spans', ocean / 'partition/unseeded_component_spans.u32le'),
                     **self.pinned_options('barrier_edges', ocean / 'barrier_edges.u32le'),
                     input_root=self.root, out=closed, pad_degrees=self.cfg.get('closed_pad_degrees', 8),
                     allow_unverified_snapshot=True, allow_draft=True, allow_selected_research_policy=True)
        with self.timing.measure('water', 'prepare-final-spec'):
            spec = {key: pin(path) for key, path in {
                'plan': plan, 'audit': prefill / 'prefill-audit.json',
                'rows': prefill / 'prefill-rows.u32le', 'runs': prefill / 'prefill-runs.u32le',
                'ocean': ocean / 'ocean-layer-manifest.json', 'summary': ocean / 'run-summary.json',
                'closed': closed / 'manifest.json', 'partition': ocean / 'partition/manifest.json'}.items()}
            specpath = self.document('final-spec', spec)
        final_plan = self.out / 'final-plan.json'
        self.command('water', 'prepare-final', REPLAY + '/prepare_final_plan.py',
                     spec=specpath, spec_sha256=sha(specpath), out=final_plan)
        final = self.out / ('baseline-final' if 'ocean_snapshot' in self.sources else 'final')
        self.command('water', 'compose-final', REPLAY + '/compose_direct.py',
                     plan=final_plan, input_root=self.root, out=final,
                     allow_research_shore=True, **self.flags())
        if 'ocean_snapshot' in self.sources:
            final = self.split_ocean(physical, prefill, plan, snapshot, ocean, closed, final_plan, final)
        return final

    def run_ocean(self, physical, prefill, plan, snapshot, name, baseline_snapshot=None):
        candidate = self.out / (name + '-candidate.json')
        self.command('water', name + '-candidate', OCEAN + '/make_candidate_build.py',
                     **self.pinned_options('snapshot', snapshot), physical_dir=physical,
                     physical_report_sha256=sha(physical / 'report.json'), out=candidate,
                     allow_draft_snapshot=True)
        options = dict(physical_rows=physical / 'rows.u32le', physical_runs=physical / 'runs.u32le',
                       prefill_dir=prefill, prefill_plan=plan,
                       **self.pinned_options('candidate_build', candidate),
                       out=self.out / name, **self.flags())
        if baseline_snapshot is None:
            self.command('water', name, OCEAN + '/ocean_fill_runner.py',
                         **self.pinned_options('snapshot', snapshot), **options)
        else:
            options.pop('allow_unverified_snapshot')
            self.command('water', name, OCEAN + '/split_lineage_ocean.py',
                         **self.pinned_options('ocean_snapshot', snapshot),
                         **self.pinned_options('prefill_snapshot', baseline_snapshot),
                         allow_unverified_snapshots=True, **options)
        return self.out / name

    def split_ocean(self, physical, prefill, plan, snapshot, old, closed, baseline_plan, baseline):
        new_snapshot = self.sources['ocean_snapshot']
        new = self.run_ocean(physical, prefill, plan, new_snapshot, 'updated-ocean', snapshot)
        with self.timing.measure('water', 'prepare-split-final'):
            paths = {'baseline_report': baseline / 'report.json', 'baseline_rows': baseline / 'rows.u32le',
                'baseline_runs': baseline / 'runs.u32le', 'baseline_plan': baseline_plan,
                'closed_manifest': closed / 'manifest.json', 'prefill_snapshot': snapshot,
                'ocean_snapshot': new_snapshot, 'prefill_plan': plan,
                'prefill_audit': prefill / 'prefill-audit.json',
                'ocean_candidate_build': self.out / 'updated-ocean-candidate.json'}
            for prefix, directory in [('old', old), ('new', new)]:
                paths.update({prefix + '_' + key: directory / rel for key, rel in {
                    'partition': 'partition/manifest.json', 'layer_manifest': 'ocean-layer-manifest.json',
                    'summary': 'run-summary.json', 'ocean_rows': 'partition/ocean_rows.u64le',
                    'ocean_spans': 'partition/ocean_assignment_spans.u32le',
                    'unseeded_rows': 'partition/unseeded_rows.u64le',
                    'unseeded_spans': 'partition/unseeded_component_spans.u32le',
                    'barrier': 'barrier_edges.u32le'}.items()})
            config = self.document('split-final', {'schema': 'worldatlas-split-ocean-final-config-v1',
                                                   'inputs': {key: pin(path) for key, path in paths.items()}})
        final = self.out / 'final'
        self.command('water', 'compose-split-final', OCEAN + '/split_lineage_compose.py',
                     config=config, out=final, allow_unverified=True)
        return final

    def compare(self, final, physical):
        if not ({'reference_rows', 'reference_runs'} & self.sources.keys()):
            return None
        if not {'reference_rows', 'reference_runs'} <= self.sources.keys():
            raise ValueError('both reference streams are required')
        rows, runs = self.sources['reference_rows'], self.sources['reference_runs']
        if rows.name != 'rows.u32le' or runs.name != 'runs.u32le' or rows.parent != runs.parent:
            raise ValueError('reference must use rows.u32le and runs.u32le in one directory')
        grid = read(physical / 'report.json')['grid']
        report = self.out / 'comparison.json'
        self.command('verification', 'compare', REPLAY + '/compare_grids.py',
                     candidate=final, reference=rows.parent, width=grid['width'], height=grid['height'],
                     reference_rows_sha256=sha(rows), reference_runs_sha256=sha(runs), out=report)
        self.timing.completed_groups.add('verification')
        return pin(report)

    def run(self):
        physical = None
        try:
            with self.timing.measure('physical', 'stage-total'):
                physical = self.physical()
            self.timing.completed_groups.add('physical')
            with self.timing.measure('mainland', 'stage-total'):
                land = self.mainland(physical)
            self.timing.completed_groups.add('mainland')
            with self.timing.measure('water', 'stage-total'):
                final = self.water(physical, land)
            self.timing.completed_groups.add('water')
            with self.timing.measure('verification', 'stage-total'):
                comparison = self.compare(final, physical)
                if pin(self.config_path) != self.config_pin or any(pin(p['path']) != p for p in self.source_pins):
                    raise ValueError('source configuration changed during pipeline')
                final_pins = {key: pin(final / name) for key, name in
                              [('rows', 'rows.u32le'), ('runs', 'runs.u32le'), ('report', 'report.json')]}
            self.timing.completed_groups.add('verification')
            stages = self.timing.summary(read(self.out / 'physical/report.json'))
            if not all(stage['complete'] for stage in stages.values()):
                raise ValueError('complete stage timing is required for a successful pipeline report')
            result = {'schema': 'worldatlas-end-to-end-report-v1',
                'status': 'complete-provisional-research-not-published', 'publishable': False,
                'request': self.config_pin, 'runner': pin(__file__), 'comparison': comparison,
                'stages': stages,
                'final': final_pins}
            write(self.out / 'report.json', result)
            return result
        except BaseException:
            self.cancel()
            report = self.out / 'physical/report.json'
            write(self.out / 'failure.json', {'schema': 'worldatlas-end-to-end-failure-v1',
                'status': 'incomplete', 'publishable': False,
                'stages': self.timing.summary(read(report) if report.exists() else None),
                'limitations': 'Failed/interrupted attempts are not complete timing baselines. Preserve output; use a fresh run.'})
            raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('config', type=Path)
    p.add_argument('output', type=Path, help='new run directory inside input_root')
    p.add_argument('--allow-provisional-research', action='store_true')
    a = p.parse_args()
    pipeline = Pipeline(a.config, a.output, allow_provisional=a.allow_provisional_research)
    def stop(signum, frame):
        pipeline.cancel()
        raise KeyboardInterrupt(f'interrupted by signal {signum}')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(json.dumps(pipeline.run(), indent=2))


if __name__ == '__main__':
    main()
