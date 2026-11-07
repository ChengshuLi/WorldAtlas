#!/usr/bin/env python3
"""Run the pinned raw-source WorldAtlas research pipeline through final composition."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
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
import uuid

from execution_state import (Timing, Checkpoints, RunLock, code_identity, inventory,
                             json_bytes, process_identity, verify_pins, verify_anchor, write, elapsed_union)
import code_versions

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
    # All selected coordinate operations use the pinned local database. Never
    # fetch a grid implicitly, including when pyproj was imported by a caller.
    os.environ['PROJ_NETWORK'] = 'OFF'
    import pyproj
    pyproj.network.set_network_enabled(False)
    if pyproj.network.is_network_enabled():
        raise ValueError('PROJ network must be disabled')


def runtime_identity():
    import numpy
    import scipy
    import pyproj
    import pyarrow
    from osgeo import gdal
    return {'executable': sys.executable, 'version': sys.version,
            'binary_sha256': sha(Path(sys.executable).resolve()),
            'numpy': numpy.__version__, 'scipy': scipy.__version__,
            'pyproj': pyproj.__version__, 'proj': pyproj.proj_version_str,
            'proj_database': pin(Path(pyproj.datadir.get_data_dir()) / 'proj.db'),
            'proj_network_enabled': pyproj.network.is_network_enabled(),
            'gdal': gdal.VersionInfo('RELEASE_NAME'), 'pyarrow': pyarrow.__version__,
            'tools': {name: pin(shutil.which(name)) for name in ('g++', 'ogr2ogr', 'gdal_rasterize')}}


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


class Pipeline:
    def __init__(self, config, output, *, allow_provisional=False, resume=False, confirm_no_writers=False,
                 resume_code_from=None):
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
        if (not self.root.is_dir() or (self.out.exists() != resume) or not self.out.parent.is_dir()
                or not self.out.is_relative_to(self.root)
                or self.config_path.is_relative_to(self.out)):
            raise ValueError('new output inside input_root, outside its input files, required')
        if resume and not (self.out / 'run-identity.json').is_file():
            raise ValueError('run has no supported checkpoint identity; preserve it and start a fresh run')
        validate_runtime()
        self.runtime = runtime_identity()
        self.resume = resume
        if resume_code_from and not resume:
            raise ValueError('--resume-code-from requires --resume')
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
        self.collect_source_files()
        self.code = code_identity(SCRIPTS)
        self.identity = {'schema': 'worldatlas-end-to-end-run-identity-v1',
            'request': self.config_pin, 'source_pins': self.source_pins,
            'code': self.code, 'scripts_root': str(SCRIPTS), 'output': str(self.out),
            'runtime': self.runtime,
            'runtime_paths': {key: os.environ.get(key) for key in ('PYTHONPATH', 'PROJ_DATA', 'PROJ_LIB', 'PROJ_NETWORK')}}
        if not resume:
            self.out.mkdir(mode=0o700)
        self.run_lock = RunLock(self.out / 'run.lock')
        try:
            self.stale_coast_batches = []
            if resume:
                previous, self.code_version, self.stale_coast_batches, version_count = code_versions.load(
                    self.out, read(self.out / 'run-identity.json'), REPO)
                if previous != self.identity and not resume_code_from:
                    raise ValueError('resume request, input, code, runtime or output identity changed')
            else:
                write(self.out / 'run-identity.json', self.identity)
                self.code_version = pin(self.out / 'run-identity.json')
            for name in ('configs', 'work', 'logs', 'scratch', 'basins', 'extractions', 'attempts'):
                (self.out / name).mkdir(mode=0o700, exist_ok=resume)
            self.attempt = uuid.uuid4().hex
            self.attempt_dir = self.out / 'attempts' / self.attempt
            self.attempt_dir.mkdir()
            self.checkpoints = Checkpoints(self.out / 'checkpoints', self.attempt)
            uncertain = self.checkpoints.check_live(confirm_no_writers=confirm_no_writers)
            if uncertain:
                write(self.attempt_dir / 'operator-writer-confirmation.json', {
                    'schema': 'worldatlas-operator-quiescence-confirmation-v1',
                    'unproven_old_attempts': uncertain,
                    'metadata_pins': [pin(path) for admission in uncertain
                        for path in (Path(admission), Path(admission).with_name('started.json')) if path.is_file()],
                    'limitation': 'Operator assertion that all old writers stopped; not inferred from invisible PIDs.'})
            self.checkpoints.verify_all()
            for marker in (self.out / 'attempts').glob('*/setup-timing.json'):
                verify_anchor(read(marker), self.out / 'timing-events.jsonl')
        except BaseException:
            self.run_lock.close()
            raise

        try:
            self.env = os.environ.copy()
            self.env['PROJ_NETWORK'] = 'OFF'
            local_modules = [str(SCRIPTS), str(SCRIPTS / REPLAY), str(SCRIPTS / OCEAN)]
            self.env['PYTHONPATH'] = os.pathsep.join(local_modules +
                ([self.env['PYTHONPATH']] if self.env.get('PYTHONPATH') else []))
            self.env.update({key: str(self.out / 'scratch') for key in
                             ('TMPDIR', 'TMP', 'TEMP', 'CPL_TMPDIR', 'SQLITE_TMPDIR')})
            self.timing = Timing(self.out / 'timing-events.jsonl', resume=resume, attempt=self.attempt, heartbeat_seconds=1.0)
            self.processes = set()
            self.process_lock = threading.RLock()
            self.cancelled = threading.Event()
            if not resume:
                write(self.out / 'request.json', self.cfg)
            elif (self.out / 'request.json').read_bytes() != json_bytes(self.cfg):
                raise ValueError('saved request changed')
            # Timing first preserves/repairs any torn final journal record.
            # Seal the normalized prefix, never bytes that recovery will remove.
            if resume_code_from:
                self.code_version, stale = code_versions.upgrade(self.out, previous, self.identity,
                    self.code_version, resume_code_from, REPO, version_count)
                self.stale_coast_batches.extend(stale)
            self.checkpoints.code_version = self.code_version
            self.checkpoints.preserve('failure', [self.out / 'failure.json'])
            token = uuid.uuid4().hex
            self.timing.event({'event': 'start', 'token': token, 'id': 'setup/source-validation', 'group': 'setup',
                               'monotonic_seconds': setup_started, 'utc': setup_utc})
            self.timing.event({'event': 'complete', 'token': token, 'id': 'setup/source-validation', 'group': 'setup',
                               'start_monotonic_seconds': setup_started, 'monotonic_seconds': time.monotonic()})
            if resume:
                for previous in (self.out / 'attempts').iterdir():
                    if previous != self.attempt_dir and not (previous / 'setup-timing.json').exists():
                        self.timing.event({'event': 'unmeasured-initialization', 'attempt': previous.name,
                                           'id': 'setup/interrupted-initialization', 'group': 'setup'})
            self.timing.mark_complete('setup')
            write(self.attempt_dir / 'setup-timing.json', self.timing.anchor())
        except BaseException:
            if hasattr(self, 'timing'):
                self.timing.close()
            self.run_lock.close()
            raise

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

    def collect_source_files(self):
        """Verify the selected static files that producer templates refer to.

        Historical physical/component/code paths in regional templates are not
        input sources and are deliberately not adopted as reusable outputs.
        """
        def add(spec, *, proj_database=False):
            if not isinstance(spec, dict) or not {'path', 'sha256'} <= spec.keys():
                raise ValueError('invalid selected source pin')
            expected = {'path': str(Path(spec['path']).resolve()), 'sha256': spec['sha256']}
            verify_pins([expected])
            if proj_database:
                if expected != self.runtime['proj_database']:
                    raise ValueError('selected PROJ database does not match active runtime database')
            elif not Path(expected['path']).is_relative_to(self.root):
                raise ValueError('selected source file outside input root')
            if expected not in self.source_pins:
                self.source_pins.append(expected)
        for layer in read(self.sources['land_config']).get('land', []):
            for spec in layer['files']:
                add(spec)
        for spec in read(self.sources['resolution_template']).get('source_files', []):
            add(spec)
        template = read(self.sources['regional_template'])
        for key in ('polygon_source_files', 'evidence_source_files', 'corroboration_source_files',
                    'bering_source_files'):
            values = template.get(key, [])
            if isinstance(values, dict):
                values = [values]
            for spec in values:
                add(spec)
        if template.get('bering_proj_db'):
            add(template['bering_proj_db'], proj_database=True)
        if template.get('point_request'):
            add(template['point_request'])
            for spec in read(template['point_request']['path']).get('source_files', []):
                add(spec)
        snapshot = read(self.sources['water_snapshot'])
        provenance = snapshot.get('local_overlay_provenance', {})
        for prefix in ('base_land_snapshot', 'water_neon_snapshot', 'overlay'):
            if prefix + '_path' in provenance:
                add({'path': provenance[prefix + '_path'], 'sha256': provenance[prefix + '_sha256']})

    def document(self, name, value):
        path = self.out / 'configs' / (name + '.json')
        if path.exists():
            if path.read_bytes() != json_bytes(value):
                raise ValueError('generated request changed on resume: ' + name)
            return path
        return write(path, value)

    def command(self, group, name, script, *args, _outputs=None, _restart=(),
                _resume_marker=None, _resume_from=False, **options):
        """Run or validate a completed canonical stage. No arbitrary command list."""
        if self.cancelled.is_set():
            raise InterruptedError('pipeline cancelled')
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
        outputs = list(_outputs or ([options['out']] if options.get('out') else []))
        outputs = [Path(path).resolve() for path in outputs]
        if any(not path.is_relative_to(self.out) or path == self.out for path in outputs):
            raise ValueError('stage output outside run or replaces run root')
        invocation = {'command': command, 'code': pin(script_path),
                      'outputs': list(map(str, outputs))}
        with self.timing.measure(group, name + '-checkpoint-validation'):
            if self.checkpoints.completed(name, invocation, outputs):
                return False
        effective = list(command)
        resumable = _resume_marker is not None and Path(_resume_marker).is_file()
        if resumable and not _resume_from:
            effective.append('--resume')
            # Orchestrated Stage2 accepts its durable work but needs fresh final output.
            if script == STAGE2 + '/orchestrate_stage2.py':
                self.checkpoints.preserve(name, outputs[:1])
        elif _resume_from:
            self.checkpoints.preserve(name, outputs)
            marker = Path(_resume_marker).name
            sources = sorted(path for parent in self.checkpoints.preserved.glob(name + '-*')
                             for path in parent.iterdir() if (path / marker).is_file())
            for source in sources:
                if sha(source / marker) not in {p['sha256'] for p in self.stale_coast_batches}:
                    effective.extend(['--resume-from', str(source)])
        else:
            self.checkpoints.preserve(name, [*outputs, *_restart])
        inputs = []
        for token in command[1:]:
            path = Path(token)
            if (path.is_absolute() and path.is_file()
                    and not any(path == output or path.is_relative_to(output) for output in outputs)):
                candidate = pin(path)
                if candidate not in inputs:
                    inputs.append(candidate)
        attempt = self.checkpoints.begin(name)
        log = self.out / 'logs' / (name + '.log')
        if log.exists():
            log = self.out / 'logs' / (name + '-' + self.attempt + '.log')
        process = None
        prior_physical = self.physical_attempts() if name == 'physical' else None
        measurement = None
        try:
            with self.timing.measure(group, name, kind='command') as measurement:
                try:
                    with log.open('xb') as stream:
                        with self.process_lock:
                            if self.cancelled.is_set():
                                raise InterruptedError('pipeline cancelled')
                            write(attempt / 'admitted.json', {'invocation': invocation,
                                'name': name, 'inputs': inputs, 'log': str(log),
                                'producer_code_version': self.code_version,
                                'timing_anchor': self.timing.anchor()})
                            process = subprocess.Popen(effective, env=self.env, stdout=stream,
                                stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(self.run_lock.fd,))
                            self.processes.add(process)
                        identity = process_identity(process.pid)
                        if identity is None:
                            identity = {'pid': process.pid, 'identity_unavailable_after_spawn': True}
                        write(attempt / 'started.json', {'process': identity, 'invocation': invocation,
                            'name': name, 'pipeline_attempt': self.attempt, 'inputs': inputs, 'log': str(log),
                            'producer_code_version': self.code_version,
                            'timing_anchor': self.timing.anchor()})
                        status = process.wait()
                        write(attempt / 'finished.json', {'returncode': status})
                        if status:
                            raise RuntimeError(f'{name} failed ({status}); inspect {log}')
                        if pin(script_path) != invocation['code']:
                            raise ValueError('stage entrypoint changed during execution: ' + script)
                    self.checkpoints.complete(name, invocation, outputs, inputs, log, self.timing.anchor())
                finally:
                    if process is not None:
                        if process.poll() is None:
                            try:
                                os.killpg(process.pid, signal.SIGTERM)
                            except ProcessLookupError:
                                pass
                            try:
                                process.wait(timeout=30)
                            except subprocess.TimeoutExpired:
                                os.killpg(process.pid, signal.SIGKILL)
                                process.wait()
                        with self.process_lock:
                            self.processes.discard(process)
        finally:
            if name == 'physical' and measurement and 'end_monotonic_seconds' in measurement:
                self.record_physical_invocation(measurement, prior_physical)
        return True

    def physical_attempts(self):
        path = self.out / 'physical/processing-events.jsonl'
        if not path.exists():
            return []
        # Only newline-terminated, complete durable records can supply timing.
        lines = path.read_bytes().splitlines(keepends=True)
        records = []
        for line in lines:
            if not line.endswith(b'\n'):
                break
            try:
                records.append(json.loads(line))
            except ValueError:
                break
        return records

    def record_physical_invocation(self, measurement, previous):
        before = {record.get('attempt') for record in previous if record.get('event') == 'attempt_start'}
        after = self.physical_attempts()
        started = {record.get('attempt') for record in after if record.get('event') == 'attempt_start'} - before
        ends = [record for record in after if record.get('event') == 'attempt_end' and record.get('attempt') in started]
        elapsed = measurement['end_monotonic_seconds'] - measurement['monotonic_seconds']
        if not started:
            # A completed producer verification (or rejected preflight) did not
            # start another producer attempt. Its entire invocation is validation.
            self.timing.event({'event': 'physical-command-overhead', 'id': 'physical', 'seconds': elapsed})
        elif len(started) == len(ends) == 1:
            processing = ends[0].get('processing_elapsed_seconds')
            downloads = ends[0].get('source_download_elapsed_seconds')
            if not all(type(value) in (int, float) and math.isfinite(value) and value >= 0
                       for value in (processing, downloads)) or processing + downloads > elapsed:
                raise ValueError('invalid physical invocation timing')
            self.timing.event({'event': 'physical-command-overhead', 'id': 'physical',
                               'seconds': elapsed - processing - downloads})
            self.timing.event({'event': 'physical-invocation-processing', 'id': 'physical',
                               'seconds': processing})
        # A killed producer with no durable attempt end supplies no exact tail.
        # Its own report will retain timing_complete=false after shard resume.

    def close(self):
        self.timing.close()
        self.run_lock.close()

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
                     self.document('physical', cfg), self.out / 'physical',
                     _outputs=[self.out / 'physical'],
                     _resume_marker=self.out / 'physical/pipeline-identity.json')
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
                     'v7-recovery/land/fresh-components-20261104/build_components.py',
                     component_request, self.out / 'work' / 'components', components,
                     _outputs=[components], _restart=[self.out / 'work/components'])
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
                     outer, work, stageout, provisional_only=True,
                     _outputs=[stageout, work], _restart=[work],
                     _resume_marker=work / 'derived/manifest.json')
        prepared = self.out / 'regional-inputs'
        land = self.out / 'land'
        self.command('mainland', 'prepare-regional', REGIONAL + '/prepare_fresh_handoff.py',
                     template=self.sources['regional_template'],
                     template_sha256=sha(self.sources['regional_template']),
                     outer=outer, work=work, stage2_output=stageout,
                     destination=prepared, regional_output=land, _outputs=[prepared])
        self.command('mainland', 'regional', REGIONAL + '/apply_selected_mixed.py',
                     prepared / 'config.json', _outputs=[land])
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
            'pipeline_report': pin(physical.parent / 'report.json'),
            'neon_selection': pin(self.sources['neon_selection']),
            'osm_receipt': pin(self.sources['osm_receipt'])}}
        inputs['physical_lineage_request'] = pin(self.document('physical-lineage', lineage))
        return inputs

    def extract_basins(self, snapshot):
        extraction = self.out / 'extractions'
        self.command('water', 'extract-basins', REPLAY + '/extract_seavox_features.py',
                     archive=self.sources['seavox_archive'], input_root=self.root,
                     **self.pinned_options('policy', snapshot), out=extraction,
                     work_root=self.out / 'scratch', **self.flags())
        return extraction

    def basin(self, decision, physical, land, snapshot, extraction_root=None):
        ident = decision['id']
        if not isinstance(ident, str) or not ident or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in ident):
            raise ValueError('unsafe basin decision ID')
        extraction = (extraction_root or self.out / 'extractions') / ident
        # Keep the independently callable single-basin path for targeted work.
        # Full runs extract and checkpoint the entire pinned selection once.
        if extraction_root is None:
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
        workers = self.cfg.get('coastal_workers')
        if workers is not None and (type(workers) is not int or workers < 1):
            raise ValueError('coastal_workers must be a positive integer')
        self.command('water', 'coast', REPLAY + '/batch_coastal_tiles.py',
                     **self.pinned_options('snapshot', snapshot),
                     **self.streams('physical', physical), **self.streams('land', land),
                     input_root=self.root, **self.pinned_options('plan', self.sources['coastal_plan']),
                     out=out, workers=workers, allow_unverified_snapshot=True, allow_draft=True,
                     allow_selected_research_policy=True,
                     _resume_marker=out / 'batch-start.json', _resume_from=True)
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
        extraction = self.extract_basins(snapshot) if decisions else None
        with ThreadPoolExecutor(max_workers=1) as coast_pool, ThreadPoolExecutor(max_workers=workers) as pool:
            coastal = coast_pool.submit(self.coast, physical, land, snapshot)
            jobs = [pool.submit(self.basin, d, physical, land, snapshot, extraction) for d in decisions]
            try:
                for completed in as_completed([coastal, *jobs]):
                    completed.result()
                basins = [job.result() for job in jobs]
                coast = coastal.result()
            except BaseException:
                for job in [coastal, *jobs]:
                    job.cancel()
                self.cancel()
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
        self.timing.mark_complete('verification')
        return pin(report)

    def run(self):
        physical = None
        try:
            if (self.out / 'report.json').exists():
                report = read(self.out / 'report.json')
                verify_pins(report['final'].values())
                verify_anchor(report['timing_anchor'], self.timing.path)
                return report
            with self.timing.measure('physical', 'stage-total'):
                physical = self.physical()
            self.timing.mark_complete('physical')
            with self.timing.measure('mainland', 'stage-total'):
                land = self.mainland(physical)
            self.timing.mark_complete('mainland')
            with self.timing.measure('water', 'stage-total'):
                final = self.water(physical, land)
            self.timing.mark_complete('water')
            with self.timing.measure('verification', 'stage-total'):
                comparison = self.compare(final, physical)
                if (pin(self.config_path) != self.config_pin or any(pin(p['path']) != p for p in self.source_pins)
                        or code_identity(SCRIPTS) != self.code):
                    raise ValueError('source configuration changed during pipeline')
                final_pins = {key: pin(final / name) for key, name in
                              [('rows', 'rows.u32le'), ('runs', 'runs.u32le'), ('report', 'report.json')]}
            self.timing.mark_complete('verification')
            stages = self.timing.summary(read(self.out / 'physical/report.json'))
            if not all(stage['outputs_complete'] for stage in stages.values()):
                raise ValueError('all stage outputs must be complete')
            result = {'schema': 'worldatlas-end-to-end-report-v1',
                'status': 'complete-provisional-research-not-published', 'publishable': False,
                'request': self.config_pin, 'runner': pin(__file__), 'comparison': comparison,
                'original_run_identity': pin(self.out / 'run-identity.json'),
                'current_code_version': self.code_version,
                'stages': stages, 'timing_complete': all(stage['timing_complete'] for stage in stages.values()),
                'timing_anchor': self.timing.anchor(),
                'final': final_pins}
            write(self.out / 'report.json', result)
            return result
        except BaseException:
            self.cancel()
            report = self.out / 'physical/report.json'
            try:
                physical_report = read(report) if report.exists() else None
            except (ValueError, OSError):
                physical_report = None
            write(self.out / 'failure.json', {'schema': 'worldatlas-end-to-end-failure-v1',
                'status': 'incomplete', 'publishable': False,
                'stages': self.timing.summary(physical_report),
                'limitations': 'Resume validates source/code/output pins. Missing interrupted endpoints remain timing-incomplete; no downtime is added.'})
            raise
        finally:
            self.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('config', type=Path)
    p.add_argument('output', type=Path, help='new run directory inside input_root')
    p.add_argument('--allow-provisional-research', action='store_true')
    p.add_argument('--resume', action='store_true', help='validate and continue the same checkpoint-enabled run')
    p.add_argument('--resume-code-from', metavar='COMMIT',
                   help='explicit committed-code transition, preserving unchanged upstream producer provenance')
    p.add_argument('--confirm-no-live-writers', action='store_true',
                   help='operator confirms all old writers stopped when an interrupted stage has no normal exit record')
    a = p.parse_args()
    pipeline = Pipeline(a.config, a.output, allow_provisional=a.allow_provisional_research, resume=a.resume,
                        confirm_no_writers=a.confirm_no_live_writers, resume_code_from=a.resume_code_from)
    def stop(signum, frame):
        pipeline.cancel()
        raise KeyboardInterrupt(f'interrupted by signal {signum}')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(json.dumps(pipeline.run(), indent=2))


if __name__ == '__main__':
    main()
