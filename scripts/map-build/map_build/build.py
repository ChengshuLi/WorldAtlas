#!/usr/bin/env python3
"""Run the pinned raw-source WorldAtlas pipeline through final composition."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import gzip
import hashlib
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import shutil
import sys
import threading
import time
import uuid
import zipfile

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from map_build.execution.runtime import (Timing, Checkpoints, RunLock, code_identity, inventory,
                             json_bytes, verify_pins, verify_anchor, write, elapsed_union)
from map_build.inputs.selection import canonical_bytes, read_saved, read_selection
from map_build.inputs.releases import read_release_streams

from map_build.execution.control import stage as stage_context, emit
def validate_runtime():
    missing = [name for name in ('numpy', 'scipy', 'pyproj', 'osgeo', 'pyarrow')
               if importlib.util.find_spec(name) is None]
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
            'gdal': gdal.VersionInfo('RELEASE_NAME'), 'pyarrow': pyarrow.__version__}


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


def catalog_references(value):
    if isinstance(value, list):
        for item in value:
            yield from catalog_references(item)
    elif isinstance(value, dict):
        if 'r2_source' in value:
            yield value
        for key, item in value.items():
            if key != 'r2_source':
                yield from catalog_references(item)


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


def physical_reference(run, sources):
    """Reuse completed physical outputs only for identical raw-source requests.

    The producer's reports stay intact. This receipt records which existing
    outputs the new run must verify; it does not create a replacement checkpoint.
    """
    run = Path(run).resolve(strict=True)
    root = run / 'physical'
    identity = read(root / 'pipeline-identity.json')
    report = read(root / 'report.json')
    if report.get('status') != 'candidate-only':
        raise ValueError('physical source run is incomplete')
    for key, selected in [('land_config', 'land_config'), ('water_config', 'water_config'),
                          ('source_manifest', 'raw_manifest')]:
        previous = Path(identity[key]['path'])
        if sha(previous) != identity[key]['sha256']:
            raise ValueError('physical source configuration changed: ' + key)
        data = lambda value: {k:v for k,v in value.items() if k != 'selection_notes'}
        if data(read(previous)) != data(read(sources[selected])):
            raise ValueError('physical input differs from the source run: ' + key)
    output = root / 'physical'
    produced = read(output / 'report.json')
    if produced.get('grid') != read(sources['land_config']).get('grid'):
        raise ValueError('physical grid differs from the selected grid')
    pins = [pin(root / 'report.json'),
            {'path': str(root / 'pipeline-identity.json'), 'sha256': report['pipeline_identity_sha256']},
            {'path': str(output / 'report.json'), 'sha256': report['stage_reports']['physical']['sha256']}]
    pins.extend({'path': str(output / name), 'sha256': produced['output_sha256'][name]}
                for name in ('physical-dry.tif', 'rows.u32le', 'runs.u32le'))
    return {'schema': 'worldatlas-physical-reuse-v1', 'status': 'reused',
            'source_run': str(run), 'pins': pins}


class Pipeline:
    def __init__(self, config, output=None, *, resume=False, work_dir=None,
                 land_revision=None, compare_release=None, physical_from=None, selection=None):
        setup_started = time.monotonic()
        setup_utc = datetime.now(timezone.utc).isoformat()
        self.config_path = Path(config).resolve(strict=True)
        self.config_pin = pin(self.config_path)
        self.cfg = read(self.config_path)
        if self.cfg.get('schema') != 'worldatlas-end-to-end-pipeline-v1':
            raise ValueError('unsupported end-to-end configuration')
        if work_dir is None and 'input_root' not in self.cfg:
            raise ValueError('choose a local input/run directory with --work-dir')
        root = Path(work_dir) if work_dir is not None else Path(self.cfg['input_root'])
        if not root.is_absolute():
            root = (Path.cwd() if work_dir is not None else self.config_path.parent) / root
        self.root = root.resolve()
        if work_dir is not None:
            self.root.mkdir(parents=True, exist_ok=True)
        self.out = Path(output).resolve() if output is not None else self.root / 'run'
        if (not self.root.is_dir() or (self.out.exists() != resume) or not self.out.parent.is_dir()
                or not self.out.is_relative_to(self.root)
                or self.config_path.is_relative_to(self.out)):
            raise ValueError('new output inside input_root, outside its input files, required')
        if resume and not (self.out / 'run-identity.json').is_file():
            raise ValueError('run has no supported checkpoint identity; preserve it and start a fresh run')
        validate_runtime()
        self.runtime = runtime_identity()
        self.resume = resume
        self.source_pins = []
        self.input_cache = {}
        self.acquisition_intervals = []
        self.selection = None
        selected_path = self.out / 'input-selection.json'
        revisions = copy.deepcopy(self.cfg.get('decision_revisions'))
        if land_revision is not None and revisions is not None:
            revisions['mainland'] = land_revision
        if resume and selected_path.is_file():
            self.selection = read_saved(selected_path, revisions)
            if selection is not None and canonical_bytes(read_saved(selection)) != canonical_bytes(self.selection):
                raise ValueError('resume uses a different saved geographic selection')
        elif selection is not None:
            self.selection = read_saved(selection, revisions)
        elif revisions:
            import psycopg
            connection = os.environ.get('NEON_DATABASE_URL')
            if not connection:
                raise ValueError('set NEON_DATABASE_URL to freeze the working geographic selection')
            with psycopg.connect(connection, connect_timeout=15) as database:
                self.selection = read_selection(database, revisions)
        if self.selection is not None:
            if set(self.selection['domains']) != {'mainland', 'regional', 'water', 'ocean'}:
                raise ValueError('a map build needs mainland, regional, water and ocean selections')
            selected_revision = self.selection['revisions']['mainland']
            if land_revision is not None and land_revision != selected_revision:
                raise ValueError('mainland argument differs from the saved selection')
        required = {'land_config', 'water_config', 'raw_manifest'}
        selections = self.cfg.get('sources', {})
        if not isinstance(selections, dict) or not required <= selections.keys() or set(selections)-required-{'reference_rows','reference_runs'}:
            raise ValueError('select land_config, water_config and raw_manifest')
        resolved = self.resolve_raw_catalog(selections)
        self.sources = {name: self.resolve_source(name, spec) for name, spec in resolved.items()}
        if compare_release is not None:
            if {'reference_rows', 'reference_runs'} & self.sources.keys():
                raise ValueError('choose a published comparison release or local reference streams')
            self.sources.update(self.release_reference(compare_release))
        if bool('reference_rows' in self.sources) != bool('reference_runs' in self.sources):
            raise ValueError('both reference stream pins are required')
        self.collect_source_files()
        if resume and physical_from is None:
            physical_from = read(self.out / 'run-identity.json').get('physical_reuse', {}).get('source_run')
        self.physical_reuse = physical_reference(physical_from, self.sources) if physical_from else None
        if self.physical_reuse is not None:
            self.source_pins.extend(p for p in self.physical_reuse['pins'] if p not in self.source_pins)
        self.code = code_identity(SCRIPTS)
        self.identity = {'schema': 'worldatlas-end-to-end-run-identity-v1',
            'request': self.config_pin, 'source_pins': self.source_pins,
            'code': self.code, 'scripts_root': str(SCRIPTS), 'output': str(self.out),
            'runtime': self.runtime,
            'runtime_paths': {key: os.environ.get(key) for key in ('PYTHONPATH', 'PROJ_DATA', 'PROJ_LIB', 'PROJ_NETWORK')}}
        if self.selection is not None:
            self.identity['input_selection_sha256'] = hashlib.sha256(canonical_bytes(self.selection)).hexdigest()
        if compare_release is not None:
            self.identity['compare_release'] = compare_release
        if self.physical_reuse is not None:
            self.identity['physical_reuse'] = self.physical_reuse
        if not resume:
            self.out.mkdir(mode=0o700)
            if self.selection is not None:
                write(selected_path, self.selection)
        self.run_lock = RunLock(self.out / 'run.lock')
        try:
            identity_path = self.out / 'run-identity.json'
            if resume:
                previous = read(identity_path)
                provenance = {'code', 'runtime', 'runtime_paths', 'scripts_root'}
                selection = lambda value: {k: v for k, v in value.items() if k not in provenance}
                if selection(previous) != selection(self.identity):
                    raise ValueError('resume request, input selection or output identity changed')
            else:
                write(identity_path, self.identity)
            for name in ('configs', 'logs', 'attempts'):
                (self.out / name).mkdir(mode=0o700, exist_ok=resume)
            self.attempt = uuid.uuid4().hex
            self.attempt_dir = self.out / 'attempts' / self.attempt
            self.attempt_dir.mkdir()
            write(self.attempt_dir / 'producer.json', {'code': self.code, 'runtime': self.runtime,
                                                       'scripts_root': str(SCRIPTS)})
            self.checkpoints = Checkpoints(self.out / 'checkpoints', self.attempt)
            self.checkpoints.verify_all()
            for marker in (self.out / 'attempts').glob('*/setup-timing.json'):
                verify_anchor(read(marker), self.out / 'timing-events.jsonl')
        except BaseException:
            self.run_lock.close()
            raise

        try:
            self.timing = Timing(self.out / 'timing-events.jsonl', resume=resume, attempt=self.attempt, heartbeat_seconds=1.0)
            self.cancelled = threading.Event()
            if not resume:
                write(self.out / 'request.json', self.cfg)
            elif (self.out / 'request.json').read_bytes() != json_bytes(self.cfg):
                raise ValueError('saved request changed')
            self.checkpoints.preserve('failure', [self.out / 'failure.json'])
            cursor = setup_started
            for start, end in [*self.acquisition_intervals, (time.monotonic(), None)]:
                token = uuid.uuid4().hex
                self.timing.event({'event': 'start', 'token': token, 'id': 'setup/source-validation', 'group': 'setup',
                                   'monotonic_seconds': cursor, 'utc': setup_utc})
                self.timing.event({'event': 'complete', 'token': token, 'id': 'setup/source-validation', 'group': 'setup',
                                   'start_monotonic_seconds': cursor, 'monotonic_seconds': start})
                cursor = end
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

    def resolve_raw_catalog(self, selections):
        """Expand exact raw source versions before any raw objects are acquired."""
        resolved = copy.deepcopy(selections)
        references = [(spec, 'size' if name == 'raw_manifest' else 'size_bytes')
                      for name, value in resolved.items() for spec in catalog_references(value)]
        if not references:
            return selections

        requested = set()
        for spec, _ in references:
            identity = spec['r2_source']
            if (not isinstance(identity, dict) or set(identity) != {'source_id', 'version'}
                    or any(not isinstance(v, str) or not v.strip() for v in identity.values())
                    or {'r2_bucket', 'r2_key', 'source_id', 'version', 'sha256', 'size_bytes', 'size'} & spec.keys()):
                raise ValueError('invalid raw catalog reference')
            requested.add((identity['source_id'], identity['version']))

        rows = sorted(self.neon_raw_catalog(sorted(requested)))
        catalog = {(row[0], row[1]): row for row in rows}
        if catalog.keys() != requested:
            raise ValueError('Neon raw catalog is missing selected source versions')
        for spec, size_field in references:
            identity = spec.pop('r2_source')
            source_id, version, bucket, key, digest, size = catalog[identity['source_id'], identity['version']]
            spec.update(source_id=source_id, version=version, r2_bucket=bucket, r2_key=key, sha256=digest)
            spec[size_field] = size
        return resolved

    def neon_raw_catalog(self, requested):
        if self.selection is not None:
            wanted = set(requested)
            return [tuple(source[key] for key in ('source_id', 'version', 'r2_bucket', 'r2_key', 'sha256', 'size_bytes'))
                    for source in self.selection['raw_sources'] if (source['source_id'], source['version']) in wanted]
        import psycopg

        connection = os.environ.get('NEON_DATABASE_URL')
        if not connection:
            raise ValueError('set NEON_DATABASE_URL for read-only access to the raw source catalog')
        source_ids, versions = zip(*requested, strict=True)
        with psycopg.connect(connection) as database:
            database.execute('SET TRANSACTION READ ONLY')
            return database.execute(
                "SELECT a.source_id, a.version, a.r2_bucket, a.r2_key, a.sha256, a.size_bytes "
                "FROM atlas.source_assets AS a "
                "JOIN unnest(%s::text[], %s::text[]) AS selected(source_id, version) USING (source_id, version) "
                "WHERE a.kind = 'raw'", (list(source_ids), list(versions))).fetchall()

    def cloud_file(self, spec):
        """Resolve one pinned R2 file or ZIP member locally."""
        expected = spec.get('sha256')
        size = spec.get('size_bytes')
        if (not isinstance(expected, str) or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected)
                or type(size) is not int or size < 0):
            raise ValueError('cloud inputs require explicit SHA-256 and byte size')
        if 'archive' in spec:
            archive = self.cloud_file(spec['archive'])
            member = spec['member']
            if not isinstance(member, str):
                raise ValueError('unsafe ZIP member')
            rel = Path(member)
            if (not member or rel.is_absolute() or '\\' in member
                    or any(part in ('', '.', '..') for part in member.split('/'))):
                raise ValueError('unsafe ZIP member')
            path = self.root / 'inputs' / spec['archive']['sha256'] / rel
            identity = ('member', str(archive), member, expected, size)
        else:
            bucket, key = spec.get('r2_bucket'), spec.get('r2_key')
            if (not isinstance(bucket, str) or not bucket or not isinstance(key, str) or not key
                    or key.endswith('/') or '\\' in key or any(p in ('', '.', '..') for p in key.split('/'))):
                raise ValueError('invalid pinned R2 location')
            path = self.root / 'inputs' / expected / Path(key).name
            identity = ('r2', bucket, key, expected, size)
        if identity in self.input_cache:
            return self.input_cache[identity]
        path = path.resolve()
        if not path.is_relative_to(self.root) or path.is_relative_to(self.out):
            raise ValueError('cloud input overlaps output or escapes work directory')
        if path.exists():
            if not path.is_file() or path.stat().st_size != size or sha(path) != expected:
                raise ValueError('cached cloud input size/SHA-256 mismatch: ' + str(path))
        else:
            started = time.monotonic()
            path.parent.mkdir(parents=True, exist_ok=True)
            partial = path.with_name(path.name + '.' + uuid.uuid4().hex + '.partial')
            try:
                if 'archive' in spec:
                    with zipfile.ZipFile(archive) as packed:
                        members = [item for item in packed.infolist() if item.filename == member]
                        if (len(members) != 1 or members[0].is_dir() or
                                ((members[0].external_attr >> 16) & 0o170000) == 0o120000):
                            raise ValueError('ZIP member must be one regular file')
                        with packed.open(members[0]) as src, partial.open('xb') as dst:
                            shutil.copyfileobj(src, dst, 1 << 20)
                else:
                    from map_build.physical import build as physical
                    staging = self.cfg.get('physical_controls', {}).get('source_staging', {})
                    physical.download_r2(staging.get('endpoint_url'),
                        {'r2_bucket': bucket, 'r2_key': key, 'size': size}, partial)
                if partial.stat().st_size != size or sha(partial) != expected:
                    raise ValueError('cloud input size/SHA-256 mismatch: ' + str(path))
                try:
                    os.link(partial, path)
                except FileExistsError:
                    if not path.is_file() or path.stat().st_size != size or sha(path) != expected:
                        raise ValueError('concurrent cloud input changed') from None
                partial.unlink()
            finally:
                self.acquisition_intervals.append((started, time.monotonic()))
        result = pin(path)
        if result not in self.source_pins:
            self.source_pins.append(result)
        self.input_cache[identity] = path
        return path


    def source_document(self, value, *, raw_manifest=False, field=None):
        """Resolve physical vector files; leave water shards for on-demand staging."""
        if isinstance(value, list):
            return [self.source_document(item, raw_manifest=raw_manifest, field=field) for item in value]
        if not isinstance(value, dict):
            return value
        if set(value) == {'json'} and isinstance(value['json'], (dict,list)):
            path = self.json_source(value['json'])
            return str(path) if field == 'dataset' else pin(path)
        if not raw_manifest and field in ('dataset','files') and any(key in value for key in ('r2_bucket','archive')):
            path = self.cloud_file(value)
            return str(path) if field == 'dataset' else dict(pin(path), size_bytes=value['size_bytes'])
        return {key: self.source_document(item, raw_manifest=raw_manifest, field=key) for key,item in value.items()}

    def json_source(self, value, *, raw_manifest=False):
        document = self.source_document(value, raw_manifest=raw_manifest)
        return self.save_source_document(document)

    def save_source_document(self, document):
        data = json_bytes(document)
        path = (self.root / 'inputs' / (hashlib.sha256(data).hexdigest() + '.json')).resolve()
        if not path.is_relative_to(self.root) or path.is_relative_to(self.out):
            raise ValueError('generated input overlaps output')
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError('generated input changed')
        else:
            with path.open('xb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        result = pin(path)
        if result not in self.source_pins:
            self.source_pins.append(result)
        return path

    def release_reference(self, version):
        streams = read_release_streams(version)
        digest = hashlib.sha256(json_bytes(streams)).hexdigest()
        directory = (self.root / 'inputs' / ('release-' + digest)).resolve()
        if not directory.is_relative_to(self.root) or directory.is_relative_to(self.out):
            raise ValueError('release reference overlaps output or escapes the work directory')
        directory.mkdir(parents=True, exist_ok=True)
        reference = {}
        for stream, bucket, key, size, stored_hash, decoded_hash in streams:
            path = directory / (stream + '.u32le')
            compressed = self.cloud_file({'r2_bucket': bucket, 'r2_key': key, 'size_bytes': size,
                                          'sha256': stored_hash})
            if not path.exists():
                started = time.monotonic()
                partial = path.with_name(path.name + '.' + uuid.uuid4().hex + '.partial')
                try:
                    with gzip.open(compressed, 'rb') as src, partial.open('xb') as dst:
                        shutil.copyfileobj(src, dst, 1 << 20)
                    if sha(partial) != decoded_hash:
                        raise ValueError('decoded reference stream hash mismatch')
                    try:
                        os.link(partial, path)
                    except FileExistsError:
                        pass
                finally:
                    partial.unlink(missing_ok=True)
                    self.acquisition_intervals.append((started, time.monotonic()))
            reference['reference_' + stream] = self.resolve_pins({'path': str(path), 'sha256': decoded_hash})
        return reference

    def resolve_source(self, name, spec):
        if isinstance(spec, dict) and set(spec) == {'json'} and isinstance(spec['json'], (dict,list)):
            return self.json_source(spec['json'], raw_manifest=name == 'raw_manifest')
        if isinstance(spec, dict) and any(key in spec for key in ('r2_bucket','archive')):
            return self.cloud_file(spec)
        return self.resolve_pins(spec)

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
        """Verify the selected local coastline files once during setup."""
        for layer in read(self.sources['land_config']).get('land', []):
            for spec in layer['files']:
                expected = pin(spec['path'])
                if expected['sha256'] != spec['sha256'] or not Path(expected['path']).is_relative_to(self.root):
                    raise ValueError('selected source file differs or is outside the work directory')
                if expected not in self.source_pins:
                    self.source_pins.append(expected)

    def document(self, name, value):
        path = self.out / 'configs' / (name + '.json')
        if path.exists():
            if path.read_bytes() != json_bytes(value):
                raise ValueError('generated request changed on resume: ' + name)
            return path
        return write(path, value)


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


    def physical(self):
        if self.physical_reuse is not None:
            verify_pins(self.physical_reuse['pins'])
            return Path(self.physical_reuse['source_run']) / 'physical' / 'physical'
        cfg = {'schema': 'raw-physical-pipeline-v1',
               'selection_notes': self.cfg['selection_notes'],
               **self.cfg.get('physical_controls', {}),
               **{key: pin(self.sources[source]) for key, source in
                  [('land_config', 'land_config'), ('water_config', 'water_config'),
                   ('source_manifest', 'raw_manifest')]}}
        from map_build.physical.build import run
        request = self.document('physical', cfg)
        marker = self.out/'physical/pipeline-identity.json'
        previous = self.physical_attempts()
        measurement = None
        try:
            with stage_context(self.cancelled), self.timing.measure('physical', 'physical-invocation', kind='command') as measurement:
                self.checkpoints.run_function('physical', 'physical', run,
                    (request, self.out/'physical'), kwargs={'resume': marker.is_file()},
                    timing=self.timing, inputs=[pin(request)], outputs=[self.out/'physical'], resume_marker=marker)
        finally:
            if measurement and 'end_monotonic_seconds' in measurement:
                self.record_physical_invocation(measurement, previous)
        return self.out / 'physical' / 'physical'

    def mainland(self, physical):
        if self.selection is None:
            raise ValueError('a complete saved or working geographic selection is required')
        return self.build_selected_land(physical)

    def build_selected_land(self, physical):
        """Run ordinary component, seed, search and regional functions directly."""
        from map_build.core.grid import Grid
        from map_build.land.components import ComponentGrid
        from map_build.land.connected import build_components
        from map_build.land.seeds import build_seeds
        from map_build.land.seed_index import build_seed_index
        from map_build.land.assignments import assign_components, read_assignments
        from map_build.land.regional import build_regional

        grid = Grid(**read(physical/'report.json')['grid'])
        selected = self.selection['domains']['mainland']
        common = [pin(self.out/'input-selection.json'), pin(physical/'report.json')]
        common += [pin(physical/name) for name in ('rows.u32le','runs.u32le')]
        component_directory = self.out/'components'
        self.checkpoints.run_function('components', 'mainland', build_components,
            (grid, physical, component_directory), timing=self.timing, inputs=common,
            outputs=[component_directory])
        component_inputs = common + [pin(component_directory/name) for name in ('rows.u32le','runs.u32le')]
        seeds = self.out/'seeds'
        index = self.out/'seed-index'
        assignments = self.out/'component-assignments'
        with ComponentGrid(physical, component_directory, grid) as components:
            seed_report = self.checkpoints.run_function('mainland-seeds', 'mainland', build_seeds,
                (selected, components, seeds), kwargs=self.cfg.get('seed_controls', {}),
                timing=self.timing, inputs=component_inputs, outputs=[seeds])
            seed_inputs = component_inputs + [pin(seeds/name) for name in ('rows.u32le','runs.u32le','report.json')]
            self.checkpoints.run_function('seed-index', 'mainland', build_seed_index,
                (grid, seeds, index), timing=self.timing, inputs=seed_inputs, outputs=[index])
            assignment_inputs = seed_inputs + [pin(index/'report.json')]
            controls = self.cfg['land_controls']
            assigned = self.checkpoints.run_function('land-distances', 'mainland', assign_components,
                (components, seed_report, index, selected['category_bindings'], assignments),
                kwargs=dict(tie_metres=float(selected['land_baseline_policy']['tie_tolerance_metres']),
                            guard_metres=controls['numerical_guard_metres'],
                            chunk_columns=controls['chunk_columns']), timing=self.timing,
                inputs=assignment_inputs, outputs=[assignments])
        protected = {g['component_id'] for g in seed_report['groups'].values() if g['role'] == 'mainland'}
        inputs = seed_inputs + [pin(assignments/name) for name in ('roots.u32le','entities.i64le','report.json')]
        result = self.checkpoints.run_function('regional-land', 'mainland', build_regional,
            (self.selection, grid, physical, component_directory, seeds, self.out/'regional'),
            kwargs=dict(protected=protected, component_defaults=read_assignments(assigned)),
            timing=self.timing, inputs=inputs, outputs=[self.out/'regional'])
        return Path(result['land'])


    def water(self, physical, land):
        from map_build.core.grid import Grid
        from map_build.water.build import build_water
        grid = Grid(**read(physical/'report.json')['grid'])
        inputs = [pin(self.out/'input-selection.json'), pin(physical/'report.json')]
        inputs += [pin(root/name) for root in (physical,land) for name in ('rows.u32le','runs.u32le')]
        result = self.checkpoints.run_function('water','water',build_water,
            (self.selection,grid,physical,land,self.out/'water'),timing=self.timing,
            inputs=inputs,outputs=[self.out/'water'])
        return Path(result['final'])

    def compare(self, final, physical):
        if not ({'reference_rows', 'reference_runs'} & self.sources.keys()):
            return None
        if not {'reference_rows', 'reference_runs'} <= self.sources.keys():
            raise ValueError('both reference streams are required')
        rows, runs = self.sources['reference_rows'], self.sources['reference_runs']
        if rows.name != 'rows.u32le' or runs.name != 'runs.u32le' or rows.parent != runs.parent:
            raise ValueError('reference must use rows.u32le and runs.u32le in one directory')
        from map_build.core.grid import Grid
        from map_build.core.comparison import compare
        grid = Grid(**read(physical/'report.json')['grid'])
        inputs = [pin(root/name) for root in (final,rows.parent) for name in ('rows.u32le','runs.u32le')]
        result = self.checkpoints.run_function('compare','verification',compare,
            (final,rows.parent,grid,self.out/'comparison',{'rows.u32le':sha(rows),'runs.u32le':sha(runs)}),
            timing=self.timing,inputs=inputs,outputs=[self.out/'comparison'])
        report = self.out/'comparison.json'
        if not report.exists():
            write(report,result)
        return pin(report)

    def run(self):
        physical = None
        try:
            if (self.out / 'report.json').exists():
                report = read(self.out / 'report.json')
                verify_pins(report['final'].values())
                verify_anchor(report['timing_anchor'], self.timing.path)
                return report
            if self.selection is None:
                raise ValueError('a complete saved or working geographic selection is required')
            with self.timing.measure('physical', 'stage-total'):
                physical = self.physical()
            physical_report = self.physical_reuse or read(self.out / 'physical/report.json')
            self.timing.mark_complete('physical', physical_report=physical_report)
            with self.timing.measure('mainland', 'stage-total'):
                land = self.mainland(physical)
            self.timing.mark_complete('mainland')
            with self.timing.measure('water', 'stage-total'):
                final = self.water(physical, land)
            self.timing.mark_complete('water')
            with self.timing.measure('verification', 'stage-total'):
                comparison = self.compare(final, physical)
                if pin(self.config_path) != self.config_pin or any(pin(p['path']) != p for p in self.source_pins):
                    raise ValueError('source configuration changed during pipeline')
                final_pins = {key: pin(final / name) for key, name in
                              [('rows', 'rows.u32le'), ('runs', 'runs.u32le'), ('report', 'report.json')]}
            self.timing.mark_complete('verification')
            stages = self.timing.summary(physical_report)
            if not all(stage['outputs_complete'] for stage in stages.values()):
                raise ValueError('all stage outputs must be complete')
            result = {'schema': 'worldatlas-end-to-end-report-v1',
                'status': 'complete',
                'request': self.config_pin, 'runner': pin(__file__), 'comparison': comparison,
                'original_run_identity': pin(self.out / 'run-identity.json'),
                'stages': stages, 'timing_complete': all(stage['timing_complete'] for stage in stages.values()),
                'timing_anchor': self.timing.anchor(),
                'final': final_pins}
            if self.physical_reuse is not None:
                result['physical_reuse'] = self.physical_reuse
            write(self.out / 'report.json', result)
            return result
        except BaseException:
            self.cancel()
            report = self.out / 'physical/report.json'
            try:
                physical_report = self.physical_reuse or (read(report) if report.exists() else None)
            except (ValueError, OSError):
                physical_report = None
            write(self.out / 'failure.json', {'schema': 'worldatlas-end-to-end-failure-v1',
                'status': 'incomplete',
                'stages': self.timing.summary(physical_report),
                'limitations': 'Resume validates source and output pins. Code changes are recorded as provenance. Missing interrupted endpoints remain timing-incomplete; no downtime is added.'})
            raise
        finally:
            self.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('config', type=Path)
    p.add_argument('output', type=Path, nargs='?', help='new run directory inside input_root; defaults to WORK_DIR/run')
    p.add_argument('--work-dir', type=Path, help='local input/run directory, overriding input_root; created if absent')
    p.add_argument('--resume', action='store_true', help='validate and continue the same checkpoint-enabled run')
    p.add_argument('--selection', type=Path, help='replay a saved complete geographic selection')
    p.add_argument('--land-revision',
                   help='build a candidate from the selected working mainland revision in Neon')
    p.add_argument('--compare-release', help='compare with a published map version in Neon')
    p.add_argument('--physical-from', type=Path,
                   help='reuse verified physical outputs from a previous run with identical physical inputs')
    a = p.parse_args()
    pipeline = Pipeline(a.config, a.output, resume=a.resume, work_dir=a.work_dir,
                        land_revision=a.land_revision, compare_release=a.compare_release,
                        physical_from=a.physical_from, selection=a.selection)

    def stop(signum, frame):
        pipeline.cancel()
        raise KeyboardInterrupt(f'interrupted by signal {signum}')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(json.dumps(pipeline.run(), indent=2))


if __name__ == '__main__':
    main()
