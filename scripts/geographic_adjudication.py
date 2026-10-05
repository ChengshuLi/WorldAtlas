"""Validate whole-shape water support after separate trusted review validation.

This module never obtains authority from an author's dossier. The caller must
obtain its envelope from the trusted GitHub review adapter and revalidate it at
final merge. Native physical-water polygons support geometry; they do not infer
administrative affiliation, certify a historical shoreline, or publish data.
"""
import base64
import gzip
import hashlib
import io
import json
import re

from shapely import union_all
from shapely.geometry import mapping, shape
from evidence.geometry import canonical_land
from evidence.immutable import canonical_json, safe_path

VERSION = 'worldatlas-geographic-water-adjudication-v1'
MAX_BYTES = 32 * 1024 * 1024
MAX_FINDINGS = 4096
TARGET = 'current-reference-geography'


def digest(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def checksum(value):
    need(isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value),
         'Invalid whole-file or geometry checksum')
    return value


def context(report):
    """Bind consumed bytes without self-referential candidate commit hashes."""
    return {key: report[key] for key in (
        'trusted_code_inventory_sha256', 'baseline_input_inventory',
        'candidate_input_inventory')}


def decoded_source(raw, name):
    need(len(raw) <= MAX_BYTES, 'Physical source exceeds whole-file byte budget')
    if name.endswith('.gz'):
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(MAX_BYTES + 1)
    need(len(raw) <= MAX_BYTES, 'Decoded physical source exceeds byte budget')
    return raw


def native_water(ref, read_file, cache=None):
    """Read an exact native source feature, never a proposed replacement shape."""
    need(isinstance(ref, dict) and set(ref) == {
        'source_id', 'path', 'sha256', 'decoded_sha256', 'native_identity',
        'native_geometry_sha256', 'native_role'}, 'Invalid physical source binding')
    need(isinstance(ref['source_id'], str) and 0 < len(ref['source_id']) <= 256,
         'Missing physical source identity')
    cache = cache if cache is not None else {'collections': {}, 'geometries': {}, 'raw_bytes': 0, 'decoded_bytes': 0}
    geometry_key = canonical_json(ref)
    if geometry_key in cache['geometries']:
        return cache['geometries'][geometry_key]
    name = safe_path(ref['path'])
    key = (name, checksum(ref['sha256']), checksum(ref['decoded_sha256']))
    if key not in cache['collections']:
        raw = read_file(name)
        cache['raw_bytes'] += len(raw)
        need(cache['raw_bytes'] <= 256 * 1024 * 1024, 'Aggregate retained physical sources exceed byte budget')
        need(hashlib.sha256(raw).hexdigest() == ref['sha256'], 'Reviewed physical source bytes changed')
        raw = decoded_source(raw, name)
        cache['decoded_bytes'] += len(raw)
        need(cache['decoded_bytes'] <= 512 * 1024 * 1024, 'Aggregate decoded physical sources exceed byte budget')
        need(hashlib.sha256(raw).hexdigest() == ref['decoded_sha256'], 'Decoded original physical source bytes changed')
        cache['collections'][key] = json.loads(raw)
    collection = cache['collections'][key]
    need(isinstance(collection, dict) and collection.get('type') == 'FeatureCollection'
         and isinstance(collection.get('features'), list)
         and 0 < len(collection['features']) <= 200000,
         'Require a bounded original physical-water FeatureCollection')
    identity, role = ref['native_identity'], ref['native_role']
    for row in (identity, role):
        need(isinstance(row, dict) and set(row) == {'property', 'value'}
             and isinstance(row['property'], str) and 0 < len(row['property']) <= 128
             and isinstance(row['value'], (str, int)) and not isinstance(row['value'], bool),
             'Native identity and role must bind exact original properties')
        if isinstance(row['value'], int):
            need(abs(row['value']) <= 9007199254740991, 'Native identity exceeds safe integer range')
    matches = [feature for feature in collection['features']
               if isinstance(feature, dict) and isinstance(feature.get('properties'), dict)
               and type(feature['properties'].get(identity['property'])) is type(identity['value'])
               and feature['properties'].get(identity['property']) == identity['value']]
    need(len(matches) == 1, 'Missing or duplicate reviewed native water feature')
    feature = matches[0]
    need(feature.get('type') == 'Feature' and
         type(feature['properties'].get(role['property'])) is type(role['value']) and
         feature['properties'].get(role['property']) == role['value'],
         'Original native physical role differs from reviewed source')
    need(digest(feature.get('geometry')) == checksum(ref['native_geometry_sha256']),
         'Original native water geometry differs from reviewed source')
    geometry = canonical_land(shape(feature['geometry']))
    need(not geometry.is_empty, 'Native water support is empty')
    cache['geometries'][geometry_key] = geometry
    return geometry


def inspect_dossier(report, dossier, read_file, source_cache=None):
    """Return supported raw finding hashes; no approval is inferred here."""
    need(isinstance(dossier, dict) and set(dossier) == {
        'version', 'method_id', 'target_context', 'context', 'findings',
        'source_refs', 'rationale'}, 'Unsupported or author-approved dossier fields')
    need(dossier['version'] == 1 and dossier['method_id'] == VERSION
         and dossier['target_context'] == TARGET, 'Unsupported water adjudication method or target')
    need(isinstance(dossier['rationale'], str) and dossier['rationale'].strip(),
         'Intentional correction needs a substantive source rationale')
    need(canonical_json(dossier['context']) == canonical_json(context(report)),
         'Consumed geography or trusted method bytes changed')
    need(report['status'] == 'regressions-found' and report.get('regressions', 0) > 0,
         'Water adjudication requires actual retained detector findings')
    differential = report['differential_report']
    need(not differential['geometry_errors'], 'Invalid geometry cannot be waived')
    actual = {digest(feature): feature for feature in differential['findings']['features']}
    entries, refs = dossier['findings'], dossier['source_refs']
    need(isinstance(entries, list) and 0 < len(entries) <= MAX_FINDINGS
         and isinstance(refs, list) and 0 < len(refs) <= 32,
         'Empty or oversized exact-finding/source inventory')
    need(len({canonical_json(ref) for ref in refs}) == len(refs), 'Duplicate physical source binding')
    water = union_all([native_water(ref, read_file, source_cache) for ref in refs])
    supported = []
    for entry in entries:
        need(isinstance(entry, dict) and set(entry) == {'sha256', 'feature'},
             'Each finding needs its complete original feature and checksum')
        identity = checksum(entry['sha256'])
        need(identity in actual and digest(entry['feature']) == identity,
             'Finding or neighboring before/after geometry differs from review')
        feature = actual[identity]
        need(feature['properties']['kind'] == 'lost-previous-coverage',
             'New overlap and other findings cannot receive a water exception')
        loss = canonical_land(shape(feature['geometry']))
        need(not loss.is_empty, 'Empty loss cannot receive water adjudication')
        if not water.covers(loss):
            # Preserve an exact diagnostic; no centroid, buffering or area cutoff.
            error = ValueError('Whole proposed loss is not supported by native water geometry')
            error.unsupported_geometry = mapping(loss.difference(water))
            raise error
        supported.append(identity)
    need(len(set(supported)) == len(supported), 'Duplicate exact-finding decision')
    return sorted(supported)


def adjudicate(report, envelope, read_file):
    """Check API-validated decisions again against actual combined Git data."""
    need(isinstance(envelope, dict) and envelope.get('status') == 'reviewed'
         and envelope.get('version') == 1 and envelope.get('method_id') == VERSION,
         'Missing trusted exact-head source/geometry review envelope')
    authority = checksum(envelope.get('authority_sha256'))
    packets = envelope.get('dossiers')
    need(isinstance(packets, list) and 0 < len(packets) <= 64,
         'Missing or oversized reviewed dossier inventory')
    approved, retained = [], []
    source_cache = {'collections': {}, 'geometries': {}, 'raw_bytes': 0, 'decoded_bytes': 0}
    dossier_bytes = 0
    for packet in packets:
        name = safe_path(packet['path'])
        raw = read_file(name)
        dossier_bytes += len(raw)
        need(dossier_bytes <= MAX_BYTES, 'Aggregate reviewed dossiers exceed byte budget')
        need(len(raw) <= MAX_BYTES and hashlib.sha256(raw).hexdigest() == checksum(packet['sha256']),
             'Reviewed dossier differs from actual combined Git bytes')
        # Base64 retains original JSON numeric representations across Node/Python.
        need(base64.b64decode(packet['bytes_base64'], validate=True) == raw,
             'API-validated dossier bytes differ from combined candidate')
        dossier = json.loads(raw)
        decision = packet['decision']
        need(decision.get('dossier_path') == name and decision.get('dossier_sha256') == packet['sha256']
             and decision.get('target_context') == TARGET,
             'Source decision is not bound to this exact dossier and target')
        for key, expected in [('target_water', 'supported'),
                              ('physical_provenance', 'accepted'),
                              ('temporal_suitability', 'accepted'),
                              ('resolution_suitability', 'accepted'),
                              ('target_uncertainty', 'resolved-for-this-target')]:
            need(decision.get(key) == expected, 'Unknown or rejected target-specific source suitability')
        need(isinstance(decision.get('source_limits'), list) and
             all(isinstance(limit, str) and limit.strip() for limit in decision['source_limits']),
             'Source limitations must remain explicit')
        need(decision.get('source_refs_sha256') == digest(dossier['source_refs']),
             'Reviewed source/native-feature bindings changed')
        supported = inspect_dossier(report, dossier, read_file, source_cache)
        need(decision.get('finding_sha256s') == supported,
             'Review did not accept every complete supported finding')
        approved.extend(supported)
        retained.append({'path': name, 'sha256': packet['sha256'],
                         'finding_sha256s': supported, 'source_refs': dossier['source_refs'],
                         'source_limits': decision['source_limits']})
    need(len(set(approved)) == len(approved) and len(approved) <= MAX_FINDINGS,
         'Duplicate or oversized combined approval inventory')
    actual = sorted(digest(feature) for feature in report['differential_report']['findings']['features'])
    need(sorted(approved) == actual, 'Unreviewed additional combined-candidate finding')
    return {'status': 'all-findings-supported-and-reviewed', 'authority_sha256': authority,
            'finding_sha256s': sorted(approved), 'dossiers': retained,
            'review': envelope['review'], 'unresolved_findings': 0,
            'limits': ['Scoped mechanical acceptance of retained source/review decisions; no global water, territorial, historical or publication certification.']}
