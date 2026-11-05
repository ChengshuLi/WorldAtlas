"""Independent Panama source-to-seed trace check for a future direct core.

The caller authenticates the selected snapshot and validates the complete seed,
region and closure contracts. This replays the OSM archive and checks that the
seed trace consumed the selected line; it makes no historical lineage claim.
"""
import hashlib, json, math, re
from pathlib import Path
from osm_source_handoff import verified_geometry
from panama_seed_source import BOUNDARY, SOURCE

RELATION = 'supporting_geographic_evidence_not_complete_construction_lineage'
REGION = 'north_america_mainland_region_v1'

def _one(rows, predicate, message):
    if not isinstance(rows, list): raise ValueError(message)
    found = [x for x in rows if isinstance(x, dict) and predicate(x)]
    if len(found) != 1: raise ValueError(message)
    return found[0]

def _sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda: f.read(1 << 20), b''): h.update(data)
    return h.hexdigest()

def validate_panama_source(snapshot, snapshot_sha256, seed_report, archive_pin):
    """Reconstruct selected source and bind its exact seed region trace.

    Caller authenticates snapshot_sha256, all other selected records and the
    physical closure. archive_pin is the pin from the outer seed request.
    """
    if not isinstance(snapshot, dict) or not isinstance(seed_report, dict) or not isinstance(archive_pin, dict) or set(archive_pin) != {'path', 'sha256'}: raise ValueError('invalid Panama validation inputs')
    if not isinstance(snapshot_sha256, str) or not re.fullmatch('[0-9a-f]{64}', snapshot_sha256): raise ValueError('invalid snapshot hash')
    rev = snapshot.get('decision_revision', {}).get('id')
    if not isinstance(rev, str) or not rev or seed_report.get('decision_snapshot_sha256') != snapshot_sha256 or seed_report.get('decision_revision') != rev: raise ValueError('snapshot or revision mismatch')
    policy = snapshot.get('land_baseline_policy', {})
    if policy.get('decision_revision') != rev or policy.get('execution_status') != 'selected_for_research' or BOUNDARY not in policy.get('boundary_ids', []) or REGION not in policy.get('region_ids', []): raise ValueError('Panama boundary or region not selected')
    boundary = _one(snapshot.get('mainland_boundaries'), lambda b: b.get('boundary_id') == BOUNDARY, 'missing or ambiguous Panama boundary')
    if boundary.get('decision_revision') != rev or boundary.get('execution_status') != 'selected_for_research': raise ValueError('stale Panama boundary')
    source = _one(snapshot.get('sources'), lambda s: (s.get('source_id'), s.get('version')) == SOURCE, 'missing or ambiguous Panama source')
    lineage = _one(snapshot.get('source_lineage_assets'), lambda s: (s.get('source_id'), s.get('version')) == SOURCE, 'missing or ambiguous Panama source lineage')
    deps = snapshot.get('source_lineage_dependencies')
    if not isinstance(deps, list) or any((x.get('source_id'), x.get('version')) == SOURCE for x in deps if isinstance(x, dict)): raise ValueError('Panama raw source marked derived')
    if lineage.get('kind') != 'raw' or any(source.get(k) != lineage.get(k) for k in ('sha256', 'size_bytes', 'r2_bucket', 'r2_key')) or not source.get('r2_bucket') or not source.get('r2_key'): raise ValueError('Panama source catalog mismatch')
    lp = lineage.get('provenance', {})
    if not lineage.get('provider') or not lineage.get('source_uri') or lp.get('representation') != 'provider_original_bundle' or not lp.get('origin'): raise ValueError('Panama source provenance mismatch')
    ref = {'source_id': SOURCE[0], 'version': SOURCE[1]}; prov = boundary.get('provenance', {})
    if prov.get('source_refs', []).count(ref) != 1 or prov.get('source_relationships', []).count({**ref, 'relationship': RELATION}) != 1: raise ValueError('selected Panama source link mismatch')
    archive = Path(archive_pin['path']).resolve(strict=True); digest = source.get('sha256')
    if archive_pin.get('sha256') != digest or seed_report.get('input_sha256', {}).get('panama_osm_archive') != digest or type(source.get('size_bytes')) is not int or archive.stat().st_size != source['size_bytes']: raise ValueError('Panama archive pin mismatch')
    geometry = boundary.get('geometry', {}); coords = geometry.get('coordinates') if geometry.get('type') == 'LineString' else None
    if not isinstance(coords, list) or len(coords) < 2 or any(not isinstance(p, list) or len(p) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float, str)) for v in p) for p in coords): raise ValueError('invalid selected Panama geometry')
    try: binary = [[float(x), float(y)] for x, y in coords]
    except (ValueError, OverflowError): raise ValueError('invalid selected Panama geometry') from None
    if any(not math.isfinite(x) or not math.isfinite(y) or not -180 <= x <= 180 or not -90 <= y <= 90 for x, y in binary): raise ValueError('invalid selected Panama geometry')
    raw = json.dumps({'type':'LineString','coordinates':binary}, sort_keys=True, separators=(',', ':'), allow_nan=False).encode(); selected_hash = hashlib.sha256(raw).hexdigest()
    if selected_hash != boundary.get('geometry_sha256'): raise ValueError('selected Panama geometry hash mismatch')
    reconstructed = verified_geometry(archive, digest, selected_hash)
    trace = {'boundary_id':BOUNDARY,'source_id':SOURCE[0],'source_version':SOURCE[1],'archive_sha256':digest,'geometry_sha256':selected_hash,'vertices':len(reconstructed['coordinates']),'method':'osm-way-full-chain-v1'}
    if seed_report.get('panama_source_trace') != trace: raise ValueError('Panama seed source trace mismatch')
    region = _one(snapshot.get('seed_regions'), lambda r: r.get('region_id') == REGION, 'missing or ambiguous selected Americas region')
    if region.get('decision_revision') != rev or region.get('execution_status') != 'selected_for_research': raise ValueError('stale selected Americas region')
    expected = {'kind':'boundary','id':BOUNDARY,'start':0,'end':trace['vertices'],'reverse':False}
    segment = _one(region.get('segments'), lambda s: s.get('kind') == 'boundary' and s.get('id') == BOUNDARY, 'missing or ambiguous Panama region segment')
    if segment != expected: raise ValueError('selected region does not consume complete Panama boundary')
    rt = _one(seed_report.get('region_traces'), lambda r: r.get('region_id') == REGION, 'missing or ambiguous seed region trace')
    executed = _one(rt.get('input_trace'), lambda s: s.get('kind') == 'boundary' and s.get('id') == BOUNDARY, 'missing or ambiguous executed Panama segment')
    if any(executed.get(k) != v for k, v in expected.items()) or executed.get('geometry_sha256') != selected_hash: raise ValueError('executed Panama segment mismatch')
    if _sha(archive) != digest: raise ValueError('Panama archive changed during validation')
    return trace
