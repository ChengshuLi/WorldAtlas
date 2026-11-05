"""Compare pinned witness outputs; caller must independently authenticate and run both.

This helper compares evidence and its internal bindings; it does not authenticate
code or files, establish execution, or verify geographic correctness.
"""
import hashlib
import json
import math
import re

MAX_BYTES = 16 << 20
HEX = re.compile(r'^[0-9a-f]{64}$')
PIN_NAMES = ('snapshot', 'physical_rows', 'physical_runs', 'component_rows',
             'component_runs', 'component_manifest', 'component_source')
CODE_NAMES = frozenset(('resolver', 'helper', 'named_identity', 'identity_watch'))
REQUEST_KEYS = frozenset(('schema', 'grid', 'source_files', 'code_sha256', *PIN_NAMES))
REPORT_KEYS = frozenset(('schema', 'status', 'publishable', 'decision_revision',
    'entity_revision', 'snapshot_sha256', 'component_manifest_sha256',
    'component_lineage_mode', 'grid', 'input_sha256', 'code_sha256', 'groups',
    'witnesses', 'relations_checked', 'limitations', 'request_sha256'))


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def _load(data):
    if not isinstance(data, bytes) or len(data) > MAX_BYTES:
        raise ValueError('JSON input must be bounded bytes')
    def invalid(_):
        raise ValueError('nonfinite JSON value')
    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError('nonfinite JSON value')
        return result
    return json.loads(data, object_pairs_hook=_pairs, parse_constant=invalid, parse_float=finite_float)


def _same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b


def _validate(request, report, request_bytes):
    if not isinstance(request, dict) or set(request) != REQUEST_KEYS or request['schema'] != 'mainland-witness-request-v1':
        raise ValueError('unsupported witness request schema')
    if not isinstance(report, dict) or set(report) != REPORT_KEYS or report['schema'] != 'mainland-witness-resolution-v1' or report['status'] != 'selected-research-identity-claims-not-mainland-proof' or report['publishable'] is not False:
        raise ValueError('unsupported witness report schema')
    code = request['code_sha256']
    if not isinstance(code, dict) or set(code) != CODE_NAMES or not all(isinstance(x, str) and HEX.fullmatch(x) for x in code.values()) or not _same(code, report['code_sha256']):
        raise ValueError('request/report code pin mismatch')
    if report['request_sha256'] != hashlib.sha256(request_bytes).hexdigest():
        raise ValueError('request/report hash mismatch')
    for key in PIN_NAMES:
        pin = request[key]
        if not isinstance(pin, dict) or set(pin) != {'path', 'sha256'} or not isinstance(pin['path'], str) or not pin['path'] or not isinstance(pin['sha256'], str) or not HEX.fullmatch(pin['sha256']):
            raise ValueError('invalid request input pin: ' + key)
    if not isinstance(request['source_files'], list) or not request['source_files']:
        raise ValueError('missing witness source pins')
    seen = set()
    for source in request['source_files']:
        if not isinstance(source, dict) or set(source) != {'source_id', 'version', 'path', 'sha256'} or not all(isinstance(source[k], str) and source[k] for k in source) or not HEX.fullmatch(source['sha256']):
            raise ValueError('invalid witness source pin')
        key = (source['source_id'], source['version'])
        if key in seen:
            raise ValueError('duplicate witness source')
        seen.add(key)
    inputs = {k: request[k]['sha256'] for k in ('physical_rows', 'physical_runs', 'component_rows', 'component_runs')}
    if not _same(report['grid'], request['grid']) or not _same(report['input_sha256'], inputs) or report['snapshot_sha256'] != request['snapshot']['sha256'] or report['component_manifest_sha256'] != request['component_manifest']['sha256']:
        raise ValueError('request/report input binding mismatch')


def compare_witness_resolutions(old_request_bytes, old_report_bytes, new_request_bytes, new_report_bytes):
    """Return content hashes if all non-provenance request/report fields match.

    All four arguments are exact UTF-8 JSON bytes. Paths must match too. Hashes
    are evidence identifiers, not authentication or proof of execution.
    Raises ValueError on invalid schema, binding, or any semantic difference.
    """
    old_request, old_report = _load(old_request_bytes), _load(old_report_bytes)
    new_request, new_report = _load(new_request_bytes), _load(new_report_bytes)
    _validate(old_request, old_report, old_request_bytes)
    _validate(new_request, new_report, new_request_bytes)
    if not _same({k:v for k,v in old_request.items() if k != 'code_sha256'}, {k:v for k,v in new_request.items() if k != 'code_sha256'}):
        raise ValueError('witness requests differ')
    excluded = {'code_sha256', 'request_sha256'}
    if not _same({k:v for k,v in old_report.items() if k not in excluded}, {k:v for k,v in new_report.items() if k not in excluded}):
        raise ValueError('witness resolutions differ')
    return {'schema': 'witness-semantic-comparison-v1', 'status': 'matched',
            'old_request_sha256': hashlib.sha256(old_request_bytes).hexdigest(),
            'old_report_sha256': hashlib.sha256(old_report_bytes).hexdigest(),
            'new_request_sha256': hashlib.sha256(new_request_bytes).hexdigest(),
            'new_report_sha256': hashlib.sha256(new_report_bytes).hexdigest()}
