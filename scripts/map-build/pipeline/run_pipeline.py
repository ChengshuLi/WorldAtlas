#!/usr/bin/env python3
"""Run the pinned raw-source WorldAtlas pipeline through final composition."""
from __future__ import annotations

import argparse
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
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
import tempfile
import time
import traceback
import uuid
import zipfile

from execution_state import (Timing, Checkpoints, RunLock, code_identity, inventory,
                             json_bytes, verify_pins, verify_anchor, write, elapsed_union)
from draft_snapshot import draft_physical_selection, prepare_land_draft, read_land_draft, read_release_streams

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))
from stage_external import ExternalCommands, emit
STAGE2 = 'stages/land/stage2-geodesic-20261104'
REGIONAL = 'land/research-mixed-runtime/stage3-mixed-leeward-full-20261105'
OCEAN = 'stages/ocean'
REPLAY = 'water'
SHORE = 'wgs84-coastal-4neighbor-center-v2'


_IMPORT_LOCK = threading.Lock()
_ENV_LOCK = threading.Lock()
_active_scratch = None
_scratch_users = 0


def stage_module(path):
    # The standalone scripts use sibling imports. Keep their directories
    # available for deferred imports without changing sys.argv.
    with _IMPORT_LOCK:
        for directory in (path.parent, SCRIPTS, SCRIPTS / REPLAY, SCRIPTS / OCEAN):
            if str(directory) not in sys.path:
                sys.path.append(str(directory))
        module = importlib.import_module(path.stem)
        if Path(module.__file__).resolve() != path:
            raise ImportError(f'stage module {path.stem} resolved outside its source: {module.__file__}')
        return module


@contextmanager
def stage_scratch(directory):
    # Temporary-directory settings are process-wide. Parallel stages of one
    # run may share them, and the last stage restores the caller's settings.
    global _active_scratch, _scratch_users
    keys = ('TMPDIR', 'TMP', 'TEMP', 'CPL_TMPDIR', 'SQLITE_TMPDIR')
    with _ENV_LOCK:
        if _scratch_users and _active_scratch != directory:
            raise RuntimeError('another in-process build is using a different scratch directory')
        if not _scratch_users:
            _active_scratch = directory
            stage_scratch.previous = tempfile.tempdir, {key: os.environ.get(key) for key in keys}
            tempfile.tempdir = directory
            os.environ.update({key: directory for key in keys})
        _scratch_users += 1
    try:
        yield
    finally:
        with _ENV_LOCK:
            _scratch_users -= 1
            if not _scratch_users:
                tempfile.tempdir, previous = stage_scratch.previous
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
                _active_scratch = None


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


def source_json_bytes(value, serialization='pretty-ascii'):
    if serialization == 'physical-report-v1':
        # The physical producer's original field order is part of this pin.
        value = copy.deepcopy(value)
        value = {key: value[key] for key in ('status', 'configuration_sha256', 'grid', 'inputs',
                    'candidate_dry_cells', 'output_sha256', 'limitations')}
        value['grid'] = {key: value['grid'][key] for key in ('width', 'height', 'west', 'north', 'step')}
        value['inputs'] = {key: {field: value['inputs'][key][field] for field in ('path', 'sha256')}
                           for key in ('land', 'water')}
        value['output_sha256'] = {key: value['output_sha256'][key]
                                 for key in ('physical-dry.tif', 'rows.u32le', 'runs.u32le')}
        serialization = 'original-pretty-utf8'
    if serialization not in {'canonical-ascii', 'canonical-utf8', 'spaced-ascii',
                              'spaced-utf8', 'pretty-ascii', 'pretty-utf8',
                              'original-order-utf8', 'original-pretty-utf8'}:
        raise ValueError('unsupported source JSON serialization')
    pretty = 'pretty' in serialization
    return (json.dumps(value, sort_keys=not serialization.startswith('original-'),
        ensure_ascii=serialization.endswith('ascii'), indent=2 if pretty else None,
        separators=None if pretty or serialization.startswith('spaced-') else (',', ':'),
        allow_nan=False) + '\n').encode()


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
    def __init__(self, config, output=None, *, resume=False, work_dir=None,
                 draft_revision=None, compare_release=None):
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
        # Verify every external document before expensive computation starts.
        required = {'land_config', 'water_config', 'raw_manifest', 'land_snapshot',
                    'resolution_template', 'regional_template', 'water_snapshot',
                    'seavox_archive', 'coastal_plan', 'neon_selection', 'osm_receipt'}
        selections = self.cfg.get('sources', {})
        if (not isinstance(selections, dict) or not required <= selections.keys() or
                set(selections) - required - {'reference_rows', 'reference_runs'}):
            raise ValueError('wrong source selection input set')
        resolved = self.resolve_raw_catalog(selections)
        self.draft_land = None
        self.preview_land = None
        if draft_revision is not None:
            if resume:
                previous = read(self.out / 'run-identity.json').get('land_draft', {})
                if previous.get('revision') != draft_revision:
                    raise ValueError('resume requires the same mainland draft revision')
                self.draft_land = self.resolve_pins(previous['snapshot'])
            else:
                snapshot = read_land_draft(draft_revision)
                self.draft_land = self.save_source_document(snapshot, serialization='canonical-ascii')
            published = self.resolve_source('land_snapshot', resolved['land_snapshot'])
            draft = read(self.draft_land)
            prepared = prepare_land_draft(draft, read(published))
            self.preview_land = self.save_source_document(prepared, serialization='canonical-ascii')
        self.sources = {name: self.resolve_source(name, spec) for name, spec in resolved.items()}
        if self.preview_land is not None:
            physical_selection = draft_physical_selection(draft, read(self.sources['neon_selection']))
            self.sources['neon_selection'] = self.save_source_document(physical_selection)
        if compare_release is not None:
            if {'reference_rows', 'reference_runs'} & self.sources.keys():
                raise ValueError('choose a published comparison release or local reference streams')
            self.sources.update(self.release_reference(compare_release))
        if bool('reference_rows' in self.sources) != bool('reference_runs' in self.sources):
            raise ValueError('both reference stream pins are required')
        self.collect_source_files()
        self.code = code_identity(SCRIPTS)
        self.identity = {'schema': 'worldatlas-end-to-end-run-identity-v1',
            'request': self.config_pin, 'source_pins': self.source_pins,
            'code': self.code, 'scripts_root': str(SCRIPTS), 'output': str(self.out),
            'runtime': self.runtime,
            'runtime_paths': {key: os.environ.get(key) for key in ('PYTHONPATH', 'PROJ_DATA', 'PROJ_LIB', 'PROJ_NETWORK')}}
        if self.draft_land is not None:
            self.identity['land_draft'] = {'revision': draft_revision, 'snapshot': pin(self.draft_land)}
        if compare_release is not None:
            self.identity['compare_release'] = compare_release
        if not resume:
            self.out.mkdir(mode=0o700)
        self.run_lock = RunLock(self.out / 'run.lock')
        try:
            identity_path = self.out / 'run-identity.json'
            if resume:
                if read(identity_path) != self.identity:
                    raise ValueError('resume request, input, code, runtime or output identity changed')
            else:
                write(identity_path, self.identity)
            for name in ('configs', 'work', 'logs', 'scratch', 'basins', 'extractions', 'attempts'):
                (self.out / name).mkdir(mode=0o700, exist_ok=resume)
            self.attempt = uuid.uuid4().hex
            self.attempt_dir = self.out / 'attempts' / self.attempt
            self.attempt_dir.mkdir()
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
            self.external = ExternalCommands(self.run_lock, self.cancelled)
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
        if hashlib.sha256(json_bytes(rows)).hexdigest() != self.cfg.get('raw_catalog_sha256'):
            raise ValueError('Neon raw catalog metadata differs from the config pin')
        for spec, size_field in references:
            identity = spec.pop('r2_source')
            source_id, version, bucket, key, digest, size = catalog[identity['source_id'], identity['version']]
            spec.update(source_id=source_id, version=version, r2_bucket=bucket, r2_key=key, sha256=digest)
            spec[size_field] = size
        return resolved

    def neon_raw_catalog(self, requested):
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
        """Resolve one pinned R2 file, Neon document or ZIP member locally."""
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
        elif 'neon' in spec:
            source = spec['neon']
            if (not isinstance(source, dict) or set(source) not in ({'source_id', 'version'},
                    {'source_id', 'version', 'serialization'}) or
                    any(not isinstance(value, str) or not value for value in source.values())):
                raise ValueError('Neon input requires source_id and version')
            path = self.root / 'inputs' / expected / 'snapshot.json'
            identity = ('neon', source['source_id'], source['version'], expected, size, source.get('serialization'))
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
                elif 'neon' in spec:
                    partial.write_bytes(self.neon_source(source, expected, size))
                else:
                    physical = stage_module(SCRIPTS / 'physical/build_physical.py')
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

    def neon_source(self, source, expected, size):
        """Read a pinned research document from Neon."""
        try:
            import psycopg
        except ImportError:
            raise ValueError('Neon inputs require psycopg in the pipeline Python environment') from None
        connection = os.environ.get('NEON_DATABASE_URL')
        if not connection:
            raise ValueError('set NEON_DATABASE_URL for read-only access to the selected Neon database')
        try:
            with psycopg.connect(connection) as database:
                database.execute('SET TRANSACTION READ ONLY')
                row = database.execute(
                    'SELECT sha256,size_bytes,document::text '
                    'FROM atlas.structured_documents WHERE source_id=%s AND version=%s',
                    (source['source_id'], source['version'])).fetchone()
        except Exception:
            raise ValueError('Neon source read failed; check database access and selected source identity') from None
        if row is None or row[0] != expected or int(row[1]) != size or not isinstance(row[2], str):
            raise ValueError('Neon structured document identity/SHA-256/size mismatch')
        document = json.loads(row[2])
        if not isinstance(document, dict):
            raise ValueError('Neon structured document must be an object')
        # Keep PostgreSQL's stored text intact for records pinned in that form.
        # Parsing and reserializing it can change numeric spelling and byte order.
        # Every accepted representation must still match the selected size/hash.
        formats = dict.fromkeys([source.get('serialization', 'canonical-ascii'),
            'canonical-ascii', 'canonical-utf8', 'spaced-ascii', 'spaced-utf8',
            'pretty-ascii', 'pretty-utf8', 'original-order-utf8',
            'original-pretty-utf8', 'physical-report-v1', 'stored-json-text'])
        for serialization in formats:
            try:
                data = (row[2].encode() if serialization in ('stored-json-text', 'jsonb-text')
                        else source_json_bytes(document, serialization))
            except KeyError:
                continue
            if len(data) == size and hashlib.sha256(data).hexdigest() == expected:
                return data
        raise ValueError('Neon JSON cannot reconstruct the selected source byte hash')

    def source_document(self, value, *, raw_manifest=False, field=None, location=()):
        """Fill local file pins in inline ordinary stage configurations only."""
        if isinstance(value, list):
            return [self.source_document(item, raw_manifest=raw_manifest, field=field, location=location) for item in value]
        if not isinstance(value, dict):
            return value
        if set(value) in ({'json'}, {'json', 'serialization'}) and isinstance(value['json'], (dict, list)):
            path = self.json_source(value['json'], serialization=value.get('serialization', 'pretty-ascii'))
            return str(path) if field == 'dataset' else pin(path)
        if field == 'bering_proj_db' and set(value) == {'sha256'}:
            if value['sha256'] != self.runtime['proj_database']['sha256']:
                raise ValueError('selected PROJ database does not match active runtime database')
            return self.runtime['proj_database']
        file_fields = {'dataset', 'shapefile', 'files', 'source_files', 'polygon_source_files', 'evidence_source_files',
                       'corroboration_source_files', 'bering_source_files', 'point_request',
                       'line', 'policy', 'pending', 'snapshot', 'neon_water_structure'}
        regional_source = location[:3] == ('regional', 'request', 'sources') and len(location) in (3, 4)
        if regional_source:
            file_fields.add(field)
        if not raw_manifest and field in file_fields and any(key in value for key in ('r2_bucket', 'archive', 'neon')):
            path = self.cloud_file(value)
            if field in ('dataset', 'shapefile'):
                return str(path)
            metadata = {key: value[key] for key in ('source_id', 'version', 'size_bytes') if key in value}
            if field in ('evidence_source_files', 'corroboration_source_files'):
                metadata.update({key: value[key] for key in ('r2_bucket', 'r2_key') if key in value})
            result = {**(metadata if field.endswith('files') or regional_source else {}), **pin(path)}
            if field == 'polygon_source_files' and 'shapefile_path' in value:
                result['shapefile_path'] = str(self.cloud_file(value['shapefile_path']))
            if regional_source and 'shapefile' in value:
                result['shapefile'] = self.source_document(value['shapefile'], field='shapefile')
            return result
        return {key: self.source_document(item, raw_manifest=raw_manifest, field=key, location=location + (key,))
                for key, item in value.items()}

    def json_source(self, value, *, raw_manifest=False, serialization='pretty-ascii'):
        document = self.source_document(value, raw_manifest=raw_manifest)
        return self.save_source_document(document, serialization=serialization)

    def save_source_document(self, document, *, serialization='pretty-ascii'):
        data = source_json_bytes(document, serialization)
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
        if name == 'land_snapshot' and self.preview_land is not None:
            return self.preview_land
        if name == 'water_snapshot':
            if not isinstance(spec, dict) or set(spec) != {'selected_water'}:
                raise ValueError('water_snapshot must select named-water and ocean decisions')
            inputs = spec['selected_water']
            if not isinstance(inputs, dict) or set(inputs) != {'water', 'ocean'}:
                raise ValueError('selected water requires named-water and ocean decisions')
            return {key: self.resolve_source(key, value) for key, value in inputs.items()}
        if isinstance(spec, dict) and set(spec) in ({'json'}, {'json', 'serialization'}) and isinstance(spec['json'], (dict, list)):
            return self.json_source(spec['json'], raw_manifest=name == 'raw_manifest',
                                    serialization=spec.get('serialization', 'pretty-ascii'))
        if isinstance(spec, dict) and any(key in spec for key in ('r2_bucket', 'archive', 'neon')):
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

    def document(self, name, value):
        path = self.out / 'configs' / (name + '.json')
        if path.exists():
            if path.read_bytes() != json_bytes(value):
                raise ValueError('generated request changed on resume: ' + name)
            return path
        return write(path, value)

    def stage(self, group, name, script, *args, _outputs=None, _restart=(),
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
        outputs = [Path(os.path.abspath(path)) for path in outputs]
        if any(not path.is_relative_to(self.out) or path == self.out
               or not path.resolve().is_relative_to(self.out) or path.resolve() == self.out
               for path in outputs):
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
        prior_physical = self.physical_attempts() if name == 'physical' else None
        measurement = None
        try:
            with self.timing.measure(group, name, kind='command') as measurement:
                with log.open('x', encoding='utf-8') as stream:
                    write(attempt / 'admitted.json', {'invocation': invocation,
                        'name': name, 'inputs': inputs, 'log': str(log),
                        'timing_anchor': self.timing.anchor()})
                    try:
                        with stage_scratch(str(self.out / 'scratch')), self.external.stage(stream):
                            stage_module(script_path).main(effective[2:], emit=emit)
                    except SystemExit as exc:
                        if exc.code not in (0, None):
                            traceback.print_exc(file=stream)
                            raise RuntimeError(f'{name} failed ({exc.code}); inspect {log}') from exc
                    except BaseException:
                        traceback.print_exc(file=stream)
                        raise
                    if pin(script_path) != invocation['code']:
                        raise ValueError('stage entrypoint changed during execution: ' + script)
                self.checkpoints.complete(name, invocation, outputs, inputs, log, self.timing.anchor())
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
        self.external.cancel()

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
        self.stage('physical', 'physical', 'physical/build_physical.py',
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
                       'component_source': SCRIPTS / 'stages/land/fresh-components-20261104/components.py'}.items()},
                   'controls': {'minimum_free_bytes': self.cfg['land_controls']['minimum_free_bytes']}}
            component_request = self.document('components', cfg)
        components = self.out / 'components'
        self.stage('mainland', 'components',
                     'stages/land/fresh-components-20261104/build_components.py',
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
        self.stage('mainland', 'stage2', STAGE2 + '/orchestrate_stage2.py',
                     outer, work, stageout, provisional_only=True,
                     _outputs=[stageout, work], _restart=[work],
                     _resume_marker=work / 'derived/manifest.json')
        prepared = self.out / 'regional-inputs'
        land = self.out / 'land'
        self.stage('mainland', 'prepare-regional', REGIONAL + '/prepare_fresh_handoff.py',
                     template=self.sources['regional_template'],
                     template_sha256=sha(self.sources['regional_template']),
                     outer=outer, work=work, stage2_output=stageout,
                     destination=prepared, regional_output=land, _outputs=[prepared])
        self.stage('mainland', 'regional', REGIONAL + '/apply_selected_mixed.py',
                     prepared / 'config.json', _outputs=[land])
        return land

    def prepare_stage2(self, physical, components, grid):
        inputs = {key: pin(path) for key, path in {
            'decision_snapshot': self.sources['land_snapshot'],
            'physical_rows': physical / 'rows.u32le', 'physical_runs': physical / 'runs.u32le',
            'physical_report': physical / 'report.json',
            'component_rows': components / 'rows.u32le', 'component_runs': components / 'runs.u32le',
            'component_manifest': components / 'manifest.json',
            'component_builder': components / 'component-builder.py',
            'component_source': SCRIPTS / 'stages/land/fresh-components-20261104/components.py',
            'closure_checker': SCRIPTS / 'stages/land/mainland-source-verification-20261104/validate_water_closure_v2.py',
            'terminal_checker': SCRIPTS / 'stages/land/mainland-source-verification-20261104/validate_terminal_closure.py',
            'seed_builder': SCRIPTS / 'stages/land/neon-mainland-regions-20261104/rasterizer/build_seed.py',
            'seed_kernel': SCRIPTS / 'stages/land/neon-mainland-regions-20261104/rasterizer/seed_runtime.py'}.items()}
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
                         'producer_code_path': str(SCRIPTS / 'physical/compose_physical.py'),
                         'encoding_evidence_sha256': sha(SCRIPTS / 'physical/compose_physical.py')},
            'resources': {'max_cell_visits': 2000000}}
        inputs['closure_contract'] = pin(self.document('closure', closure))
        authored = inputs['decision_snapshot']
        snapshot = read(authored['path'])
        if snapshot.get('source') != 'neon-export':
            raise ValueError('current physical binding requires an editable Neon export')
        physical_pins = {key + '_sha256': inputs[key]['sha256']
                         for key in ('physical_rows', 'physical_runs', 'physical_report')}
        snapshot['land_baseline_policy'].update(physical_pins)
        selected = set(snapshot['land_baseline_policy']['route_ids'])
        for route in snapshot['routes']:
            if route['route_id'] not in selected:
                continue
            provenance = route['provenance']
            checker = ('terminal_checker' if route['closure_method'] == 'physical_terminal_closure_v1'
                       else 'closure_checker')
            route['provenance'] = {
                'source_refs': provenance['source_refs'],
                'lineage_status': provenance.get('lineage_status', 'incomplete'),
                **physical_pins,
                'encoding_evidence_sha256': closure['physical']['encoding_evidence_sha256'],
                'contract_sha256': inputs['closure_contract']['sha256'],
                'support_checker_sha256': inputs['closure_checker']['sha256'],
                'checker_sha256': inputs[checker]['sha256'],
            }
        snapshot['runtime_physical_binding'] = {'authored_snapshot_sha256': authored['sha256']}
        inputs['decision_snapshot'] = pin(self.document('land-snapshot-for-current-physical', snapshot))
        resolution = read(self.sources['resolution_template'])
        if resolution.get('schema') != 'mainland-witness-request-v1':
            raise ValueError('wrong mainland resolution template')
        for key in ('physical_rows', 'physical_runs', 'component_rows', 'component_runs',
                    'component_manifest', 'component_source'):
            resolution[key] = inputs[key]
        resolution['snapshot'] = inputs['decision_snapshot']
        resolution['grid'] = grid
        resolution['code_sha256'] = {key: sha(SCRIPTS / STAGE2 / rel) for key, rel in {
            'resolver': 'land/mainland-witness-prototype/resolve_mainland.py',
            'helper': 'land/point-component-prototype/resolve.py',
            'named_identity': 'land/named-identity-prototype/named_identity.py'}.items()}
        inputs['resolution_request'] = pin(self.document('resolution', resolution))
        lineage = {'schema': 'stage1-raw-physical-lineage-request-v1', 'code_root': str(SCRIPTS / 'physical'), 'inputs': {
            'pipeline_report': pin(physical.parent / 'report.json'),
            'neon_selection': pin(self.sources['neon_selection']),
            'osm_receipt': pin(self.sources['osm_receipt'])}}
        inputs['physical_lineage_request'] = pin(self.document('physical-lineage', lineage))
        return inputs

    def extract_basins(self, snapshot):
        extraction = self.out / 'extractions'
        self.stage('water', 'extract-basins', REPLAY + '/extract_seavox_features.py',
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
            self.stage('water', 'extract-' + ident, REPLAY + '/extract_seavox_feature.py',
                         archive=self.sources['seavox_archive'], input_root=self.root,
                         policy=snapshot, policy_sha256=sha(snapshot), decision_id=ident,
                         out=extraction, **self.flags())
        out = self.out / 'basins' / ident
        options = {**self.pinned_options('rows', physical / 'rows.u32le'),
                   **self.pinned_options('runs', physical / 'runs.u32le'),
                   **self.pinned_options('land_rows', land / 'rows.u32le'),
                   **self.pinned_options('land_runs', land / 'runs.u32le')}
        self.stage('water', 'basin-' + ident, REPLAY + '/build_seavox_basin.py',
                     input_root=self.root, geometry=extraction / 'source.geojson',
                     archive=self.sources['seavox_archive'],
                     extraction_manifest=extraction / 'manifest.json',
                     extraction_manifest_sha256=sha(extraction / 'manifest.json'),
                     policy=snapshot, policy_sha256=sha(snapshot), decision_id=ident,
                     shore_pad_degrees=self.cfg.get('shore_pad_degrees', 8),
                     research_shore_method=SHORE, out=out, **options, **self.flags())
        self.stage('water', 'verify-basin-' + ident, REPLAY + '/verify_basin_coverage.py',
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
        self.stage('water', 'coast', REPLAY + '/batch_coastal_tiles.py',
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
        self.stage('water', 'assemble-coast', REPLAY + '/assemble_coastal_tiles.py',
                     **self.pinned_options('snapshot', snapshot), input_root=self.root,
                     tile_list=tile_list, out=assembled, allow_unverified_snapshot=True,
                     allow_draft=True, allow_selected_research_policy=True)
        return {'manifest_path': str(assembled), 'manifest_sha256': sha(assembled)}

    def water(self, physical, land):
        sources = self.sources['water_snapshot']
        with self.timing.measure('water', 'prepare-water-selection'):
            stage2 = read(self.out / 'configs/stage2.json')['inputs']['decision_snapshot']
            verify_pins([stage2])
            binder = stage_module(SCRIPTS / REPLAY / 'local_water_overlay.py')
            selected = binder.bind_selected(stage2['path'], sources['water'], sources['ocean'])
            snapshot = self.document('water-snapshot', selected)
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
        self.stage('water', 'prefill-plan', REPLAY + '/build_prefill_plan.py',
                     input_root=self.root, inputs=prefill_inputs,
                     **self.pinned_options('policy', snapshot), out=plan,
                     allow_research_shore=True, **self.flags())
        prefill = self.out / 'prefill'
        self.stage('water', 'prefill', REPLAY + '/build_prefill.py',
                     plan=plan, input_root=self.root, out=prefill,
                     allow_research_shore=True, **self.flags())
        ocean = self.run_ocean(physical, prefill, plan, snapshot, 'ocean')
        closed = self.out / 'closed'
        self.stage('water', 'closed', REPLAY + '/build_closed_water.py',
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
        self.stage('water', 'prepare-final', REPLAY + '/prepare_final_plan.py',
                     spec=specpath, spec_sha256=sha(specpath), out=final_plan)
        final = self.out / 'final'
        self.stage('water', 'compose-final', REPLAY + '/compose_direct.py',
                     plan=final_plan, input_root=self.root, out=final,
                     allow_research_shore=True, **self.flags())
        return final

    def run_ocean(self, physical, prefill, plan, snapshot, name):
        candidate = self.out / (name + '-candidate.json')
        self.stage('water', name + '-candidate', OCEAN + '/make_candidate_build.py',
                     **self.pinned_options('snapshot', snapshot), physical_dir=physical,
                     physical_report_sha256=sha(physical / 'report.json'), out=candidate,
                     allow_draft_snapshot=True)
        options = dict(physical_rows=physical / 'rows.u32le', physical_runs=physical / 'runs.u32le',
                       prefill_dir=prefill, prefill_plan=plan,
                       **self.pinned_options('candidate_build', candidate),
                       out=self.out / name, **self.flags())
        self.stage('water', name, OCEAN + '/ocean_fill_runner.py',
                   **self.pinned_options('snapshot', snapshot), **options)
        return self.out / name

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
        self.stage('verification', 'compare', REPLAY + '/compare_grids.py',
                     candidate=final, reference=rows.parent, width=grid['width'], height=grid['height'],
                     reference_rows_sha256=sha(rows), reference_runs_sha256=sha(runs),
                     allow_different=self.preview_land is not None, out=report)
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
            self.timing.mark_complete('physical', physical_report=read(self.out / 'physical/report.json'))
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
                'status': 'complete',
                'request': self.config_pin, 'runner': pin(__file__), 'comparison': comparison,
                'original_run_identity': pin(self.out / 'run-identity.json'),
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
                'status': 'incomplete',
                'stages': self.timing.summary(physical_report),
                'limitations': 'Resume validates source/code/output pins. Missing interrupted endpoints remain timing-incomplete; no downtime is added.'})
            raise
        finally:
            self.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('config', type=Path)
    p.add_argument('output', type=Path, nargs='?', help='new run directory inside input_root; defaults to WORK_DIR/run')
    p.add_argument('--work-dir', type=Path, help='local input/run directory, overriding input_root; created if absent')
    p.add_argument('--resume', action='store_true', help='validate and continue the same checkpoint-enabled run')
    p.add_argument('--draft-land-revision', help='preview the selected editable mainland revision in Neon')
    p.add_argument('--compare-release', help='compare with a published map version in Neon')
    a = p.parse_args()
    compare_release = a.compare_release or ('v8.0' if a.draft_land_revision else None)
    pipeline = Pipeline(a.config, a.output, resume=a.resume, work_dir=a.work_dir,
                        draft_revision=a.draft_land_revision, compare_release=compare_release)

    def stop(signum, frame):
        pipeline.cancel()
        raise KeyboardInterrupt(f'interrupted by signal {signum}')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(json.dumps(pipeline.run(), indent=2))


if __name__ == '__main__':
    main()
