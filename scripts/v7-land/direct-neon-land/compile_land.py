#!/usr/bin/python3
"""Prototype direct physical-land + revisioned source decisions compiler.

NOT production authority: authentication/acceptance of the exported snapshot is
not established here. Requires --allow-unverified-snapshot for research only.
"""
import argparse
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path
import sys

import numpy as np
from osgeo import gdal, ogr, osr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import assign_land

gdal.UseExceptions()
ogr.UseExceptions()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def obj(value, required, optional=(), name='object'):
    require(isinstance(value, dict), f'{name} must be an object')
    require(set(required) <= set(value) <= set(required) | set(optional), f'invalid {name} fields')


def pin(spec):
    obj(spec, ('path', 'sha256'), name='file pin')
    require(isinstance(spec['path'], str) and isinstance(spec['sha256'], str) and
            len(spec['sha256']) == 64 and all(c in '0123456789abcdef' for c in spec['sha256']), 'invalid file pin')
    p = Path(spec['path'])
    require(p.is_file() and assign_land.sha(p) == spec['sha256'], f'input digest mismatch: {p}')
    return p


def text(v):
    return isinstance(v, str) and bool(v.strip())


def geometry_hash(g):
    return hashlib.sha256(json.dumps(g, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def check_rings(g):
    """Reject ambiguous dateline-crossing edges; accept split MultiPolygons."""
    require(isinstance(g, dict) and g.get('type') in ('Polygon', 'MultiPolygon'), 'invalid geometry type')
    polys = [g.get('coordinates')] if g['type'] == 'Polygon' else g.get('coordinates')
    require(isinstance(polys, list) and bool(polys), 'empty geometry')
    for poly in polys:
        require(isinstance(poly, list) and bool(poly), 'empty polygon')
        for ring in poly:
            require(isinstance(ring, list) and len(ring) >= 4, 'invalid ring')
            previous = None
            for point in ring:
                require(isinstance(point, list) and len(point) == 2 and
                        all(type(v) in (int, float) and math.isfinite(v) for v in point), 'invalid coordinate')
                lon, lat = point
                require(-180 <= lon <= 180 and -90 <= lat <= 90, 'coordinate out of range')
                require(previous is None or abs(lon - previous) <= 180, 'unsplit antimeridian edge')
                previous = lon
            require(ring[0] == ring[-1], 'ring is not closed')
    geom = ogr.CreateGeometryFromJson(json.dumps(g, allow_nan=False))
    require(geom is not None and not geom.IsEmpty() and geom.IsValid(), 'invalid polygon')
    return geom


def read_feature(feature, source, source_map, cache):
    sid = (feature.get('source_id'), feature.get('source_version'))
    require(sid in source_map and sid in source, 'feature source is not selected and mapped')
    mapping = source_map[sid]
    path = Path(mapping['file']['path'])
    require(source[sid]['sha256'] == mapping['file']['sha256'], 'source map does not match snapshot source hash')
    field = mapping['id_property']
    require(text(field), 'source ID property required')
    if path not in cache:
        dataset = ogr.Open(str(path), 0)
        require(dataset is not None, 'source GeoJSON cannot be opened')
        source_srs = dataset.GetLayer(0).GetSpatialRef()
        expected_srs = osr.SpatialReference(); expected_srs.ImportFromEPSG(4326)
        if source_srs is not None: source_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        expected_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        require(source_srs is not None and source_srs.IsSame(expected_srs), 'source GeoJSON must use WGS84 coordinates')
        doc = json.loads(path.read_bytes())
        require(doc.get('type') == 'FeatureCollection' and isinstance(doc.get('features'), list), 'GeoJSON FeatureCollection required')
        cache[path] = doc['features']
    # Source feature IDs are strings; a source's integer ID is normalized to decimal.
    hits = [f for f in cache[path] if f.get('type') == 'Feature' and
            isinstance(f.get('properties'), dict) and field in f['properties'] and
            str(f['properties'][field]) == str(feature['source_feature_id'])]
    require(len(hits) == 1, f"source feature ID must be unique: {feature['feature_id']}")
    g = hits[0].get('geometry')
    require(geometry_hash(g) == feature['geometry_sha256'], 'canonical geometry hash mismatch')
    geom = check_rings(g)
    return g, geom


def select_roots(layer, envelope, grid, rr, runs, strip):
    w, h, step, west, north = (grid[k] for k in ('width', 'height', 'step', 'west', 'north'))
    xmin, xmax, ymin, ymax = envelope
    x0 = max(0, math.floor((xmin - west) / step) - 1)
    x1 = min(w, math.ceil((xmax - west) / step) + 1)
    y0 = max(0, math.floor((north - ymax) / step) - 1)
    y1 = min(h, math.ceil((north - ymin) / step) + 1)
    require(x0 < x1 and y0 < y1, 'source polygon does not intersect grid')
    roots = set()
    for sy in range(y0, y1, strip):
        ey = min(y1, sy + strip)
        raster = gdal.GetDriverByName('MEM').Create('', x1-x0, ey-sy, 1, gdal.GDT_Byte)
        raster.SetGeoTransform((west+x0*step, step, 0, north-sy*step, 0, -step))
        raster.GetRasterBand(1).Fill(0)
        layer.ResetReading()
        gdal.RasterizeLayer(raster, [1], layer, burn_values=[1])
        mask = raster.ReadAsArray()
        for y in range(sy, ey):
            for a, b, root in runs[int(rr[y]):int(rr[y+1])]:
                lo, hi = max(int(a), x0), min(int(b), x1)
                if lo < hi and np.any(mask[y-sy, lo-x0:hi-x0]):
                    roots.add(int(root))
    return roots


def witness_root(witness, grid, rr, runs):
    obj(witness, ('lon', 'lat'), name='component witness')
    require(all(isinstance(witness[k], str) and text(witness[k]) for k in ('lon', 'lat')), 'witness coordinates must be decimal strings')
    try:
        lon, lat = Decimal(witness['lon']), Decimal(witness['lat'])
        step, west, north = (Decimal(str(grid[k])) for k in ('step', 'west', 'north'))
        require(lon.is_finite() and lat.is_finite(), 'nonfinite witness')
        x = int(((lon-west)/step).to_integral_value(rounding=ROUND_FLOOR))
        y = int(((north-lat)/step).to_integral_value(rounding=ROUND_FLOOR))
    except (InvalidOperation, OverflowError):
        raise ValueError('invalid witness coordinate') from None
    require(0 <= x < grid['width'] and 0 <= y < grid['height'], 'witness outside grid')
    row = runs[int(rr[y]):int(rr[y+1])]
    found = row[(row[:,0] <= x) & (x < row[:,1])]
    require(len(found) == 1, 'witness must resolve to exactly one physical component')
    return int(found[0,2])


def require_selected_for_research(records, label):
    require(all(isinstance(row,dict) and isinstance(row.get('evidence'),dict)
                and row['evidence'].get('execution_status') == 'selected_for_research'
                for row in records), f'{label} require explicit research selection; unselected or unknown candidates cannot be executed')


def resolve_witness_rules(witnesses, grid, cfg, rr, runs, component_source_hash, bindings, claims, partitions, summaries):
    require_selected_for_research(witnesses, 'witness rules')
    w,h,step,west,north = (grid[k] for k in ('width','height','step','west','north'))
    for rule in sorted(witnesses, key=lambda r:r.get('rule_id','')):
        rid=rule['rule_id']; selector=rule.get('selector'); evidence=rule.get('evidence')
        require(rule.get('method')=='component_witness_list_v1' and type(rule.get('entity_id')) is int, 'unsupported witness rule')
        obj(selector, ('witnesses','verification'), name='witness selector')
        verification=selector['verification']
        obj(verification, ('grid_width','grid_height','grid_step','grid_west','grid_north','physical_rows_sha256','physical_runs_sha256',
                           'component_rows_sha256','component_runs_sha256','component_algorithm_sha256'), name='witness verification')
        require(type(verification['grid_width']) is int and type(verification['grid_height']) is int and
                verification['grid_width']==w and verification['grid_height']==h, 'witness grid dimensions mismatch')
        try:
            for key,value in (('grid_step',step),('grid_west',west),('grid_north',north)):
                raw=verification[key]
                require(isinstance(raw,str) and text(raw) and Decimal(raw).is_finite() and Decimal(raw)==Decimal(str(value)), 'witness grid georeferencing mismatch')
        except InvalidOperation:
            raise ValueError('invalid witness grid georeferencing') from None
        for key in ('physical_rows','physical_runs','component_rows','component_runs'):
            require(verification[key+'_sha256']==cfg[key]['sha256'], f'witness {key} pin mismatch')
        require(verification['component_algorithm_sha256']==component_source_hash, 'witness component algorithm pin mismatch')
        require(isinstance(evidence,dict), 'witness rules require source citations and evidence hashes')
        source_evidence=evidence.get('source_files_evidence_only',[])
        document_evidence=evidence.get('source_documents_evidence_only',[])
        def digest(value): return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
        require(isinstance(source_evidence,list) and isinstance(document_evidence,list) and bool(source_evidence or document_evidence) and
                all(isinstance(x,dict) and text(x.get('citation')) and digest(x.get('file_sha256')) and digest(x.get('geometry_sha256'))
                    for x in source_evidence) and
                all(isinstance(x,dict) and text(x.get('citation')) and digest(x.get('file_sha256')) for x in document_evidence),
                'witness rules require source citations and evidence hashes')
        citations = [x['citation'] for x in source_evidence+document_evidence]
        values=selector['witnesses'];require(isinstance(values,list) and bool(values), 'witness list must be nonempty')
        roots=[witness_root(x,grid,rr,runs) for x in values]
        require(len(set(roots))==len(roots), 'duplicate witness component')
        match=[b for b in bindings if b.get('entity_id')==rule['entity_id'] and b.get('physical_class')=='land']
        require(len(match)==1, 'land entity requires one category binding')
        for root in roots:
            require(root not in claims and root not in partitions, f'conflicting component claim {root}')
            claims[root]={'rule_id':f'{rid}:component:{root}', 'source_evidence':citations,
                          'component_id':root,'kind':'whole_component','code':match[0]['code']}
        summaries.append({'witness_rule_id':rid,'selected_components':len(roots),'mask_bound':True})


def prepare(config_path, output, allow_unverified_snapshot=False):
    require(allow_unverified_snapshot, 'snapshot authentication is not implemented; research requires --allow-unverified-snapshot')
    cfg_bytes = Path(config_path).read_bytes()
    cfg = json.loads(cfg_bytes)
    obj(cfg, ('schema','snapshot','grid','physical_rows','physical_runs','component_rows','component_runs','source_files'), ('strip_rows',), 'config')
    require(cfg['schema'] == 'direct-neon-land-build-v1', 'unknown config schema')
    pins = [cfg[k] for k in ('snapshot','physical_rows','physical_runs','component_rows','component_runs')]
    source_map = {}
    for item in cfg['source_files']:
        obj(item, ('source_id','source_version','file','id_property'), name='source map entry')
        key = (item['source_id'], item['source_version'])
        require(all(text(k) for k in key) and key not in source_map, 'duplicate or invalid source map')
        source_map[key] = item
        pins.append(item['file'])
    for spec in pins: pin(spec)
    out = Path(output).resolve()
    input_paths = [Path(config_path).resolve()] + [Path(p['path']).resolve() for p in pins]
    require(all(out != p and not p.is_relative_to(out) and not out.is_relative_to(p.parent) for p in input_paths),
            'output must not contain an input or be nested in an input directory')
    snapshot = json.loads(Path(cfg['snapshot']['path']).read_bytes())
    rev = snapshot.get('decision_revision', {})
    erev = snapshot.get('entity_revision', {})
    schema = snapshot.get('schema')
    require(schema in ('worldatlas-geography-decision-export-v1', 'worldatlas-geography-decision-draft-evidence-v1') and snapshot.get('source') == 'neon-export' and
            text(rev.get('id')) and rev.get('status') in ('draft','accepted') and text(rev.get('entity_revision')) and
            erev.get('id') == rev.get('entity_revision') and erev.get('status') in ('draft','accepted'), 'invalid revision snapshot')
    if schema == 'worldatlas-geography-decision-draft-evidence-v1':
        require(rev['status'] == erev['status'] == 'draft', 'draft evidence snapshot must remain draft')
    else:
        require(rev['status'] == erev['status'] == 'accepted', 'accepted export requires accepted revisions')
    sources = {(s['source_id'],s['version']):s for s in snapshot.get('sources',[])}
    require(len(sources) == len(snapshot.get('sources',[])), 'duplicate snapshot source')
    features = {f['feature_id']:f for f in snapshot.get('features',[])}
    require(len(features) == len(snapshot.get('features',[])), 'duplicate feature ID')
    bindings = snapshot.get('category_bindings', [])
    entities = snapshot.get('entities', [])
    require(isinstance(entities, list) and len({e.get('id') for e in entities}) == len(entities), 'duplicate entity IDs')
    entity_ids = {e['id'] for e in entities}
    land_bindings = [b for b in bindings if b.get('physical_class') == 'land']
    require(all(b.get('entity_id') in entity_ids and type(b.get('code')) is int and b['code'] in range(17,23) for b in land_bindings) and
            len({b['code'] for b in land_bindings}) == len(land_bindings) and
            len({b['entity_id'] for b in land_bindings}) == len(land_bindings), 'invalid or duplicate land category bindings')
    grid = cfg['grid']; obj(grid, ('width','height','step','west','north'), name='grid')
    w,h,step,west,north = (grid[k] for k in ('width','height','step','west','north'))
    require(type(w) is int and type(h) is int and w > 0 and h > 0 and
            all(type(v) in (int,float) and math.isfinite(v) for v in (step,west,north)) and
            0 < step <= 360 and west >= -180 and west+w*step <= 180.0000001 and north <= 90 and north-h*step >= -90.0000001, 'invalid grid')
    strip = cfg.get('strip_rows', 128)
    require(type(strip) is int and 1 <= strip <= 1024, 'invalid strip size')
    rr = np.memmap(cfg['component_rows']['path'], dtype='<u4', mode='r')
    runs = np.memmap(cfg['component_runs']['path'], dtype='<u4', mode='r')
    require(len(rr)==h+1 and len(runs)%3==0 and rr[0]==0 and rr[-1]==len(runs)//3 and np.all(rr[1:]>=rr[:-1]), 'invalid component stream')
    runs = runs.reshape(-1,3)
    land = [a for a in snapshot.get('affiliations',[]) if a.get('scope') == 'land']
    if schema == 'worldatlas-geography-decision-draft-evidence-v1':
        require_selected_for_research(land, 'draft land affiliations')
    if schema == 'worldatlas-geography-decision-draft-evidence-v1':
        require('land_component_witness_rules' in snapshot, 'draft snapshot must include land witness rules')
    witnesses = snapshot.get('land_component_witness_rules', [])
    require(isinstance(witnesses, list), 'invalid land witness rules')
    require(not witnesses or schema == 'worldatlas-geography-decision-draft-evidence-v1', 'witness rules are draft research only')
    require_selected_for_research(witnesses, 'witness rules')
    require(bool(land) or bool(witnesses), 'snapshot has no land affiliations or witness rules')
    ids = [a.get('affiliation_id') for a in land] + [r.get('rule_id') for r in witnesses]
    require(all(text(x) for x in ids) and len(set(ids)) == len(ids), 'duplicate or invalid land decision ID')
    os.mkdir(out)
    # Recompute components from the pinned physical mask, and demand exact
    # byte equality. Footprint alone does not prove the claimed connectivity.
    component_source = Path(__file__).resolve().parent.parent/'build_components.cpp'
    component_source_hash = assign_land.sha(component_source)
    binary = out/'component-builder'
    build = subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(component_source),'-o',str(binary)], capture_output=True, text=True)
    require(build.returncode == 0, f'component builder compilation failed: {build.stderr[-3000:]}')
    regenerated_rows=out/'verified-component-rows.u32le'
    regenerated_runs=out/'verified-component-runs.u32le'
    process=subprocess.run([str(binary),str(w),str(h),cfg['physical_rows']['path'],cfg['physical_runs']['path'],str(regenerated_rows),str(regenerated_runs)], capture_output=True, text=True)
    require(process.returncode == 0, f'component regeneration failed: {process.stderr[-3000:]}')
    require(assign_land.sha(regenerated_rows) == cfg['component_rows']['sha256'] and
            assign_land.sha(regenerated_runs) == cfg['component_runs']['sha256'], 'component connectivity does not match physical mask')
    require(assign_land.sha(component_source) == component_source_hash, 'component builder changed during run')
    compiler_version = subprocess.run(['g++','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    geomdir = out/'geometry'; geomdir.mkdir()
    cache = {}; claims = {}; partitions = {}; summaries = []
    resolve_witness_rules(witnesses, grid, cfg, rr, runs, component_source_hash, bindings, claims, partitions, summaries)
    for aff in sorted(land, key=lambda a:a.get('affiliation_id','')):
        aid = aff.get('affiliation_id'); method = aff.get('method')
        require(text(aid) and aff.get('relationship') == 'affiliation' and text(aff.get('rationale')) and
                method in ('component_intersection_v1','component_partition_v1'), f'unsupported land affiliation: {aid}')
        feature = features.get(aff.get('feature_id'))
        require(feature is not None and text(feature.get('source_feature_id')) and text(feature.get('geometry_sha256')), 'missing pinned decision feature')
        require(type(aff.get('entity_id')) is int, 'land entity ID must be an integer')
        match = [b for b in bindings if b.get('entity_id') == aff.get('entity_id') and b.get('physical_class') == 'land']
        require(len(match)==1 and type(match[0].get('code')) is int and match[0]['code'] in range(17,23), 'land entity requires one category binding')
        code = match[0]['code']
        evidence = aff.get('evidence')
        require(isinstance(evidence,dict) and isinstance(evidence.get('selector'),dict), 'selector evidence required')
        selector = evidence['selector']
        if method == 'component_intersection_v1':
            obj(selector, ('additional_feature_ids','include_witnesses','exclude_witnesses'), name='intersection selector')
            additional = selector['additional_feature_ids']
            require(isinstance(additional,list) and all(text(x) for x in additional), 'additional feature IDs must be a list of strings')
        else:
            obj(selector, ('component_witness',), name='partition selector')
            additional = []
        feature_ids = [feature['feature_id'], *additional]
        require(len(set(feature_ids)) == len(feature_ids), 'duplicate feature in group selector')
        hits = set(); per_feature_hits = {}; gp = None
        for fid in feature_ids:
            member = features.get(fid)
            require(member is not None and text(member.get('source_feature_id')) and text(member.get('geometry_sha256')), 'missing pinned decision feature')
            g, geom = read_feature(member, sources, source_map, cache)
            # Deterministic extraction, retained for audit and partition rasterization.
            name=hashlib.sha256(json.dumps([aid,fid],separators=(',',':')).encode()).hexdigest()
            gp = geomdir/(name+'.geojson')
            gp.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':g}]}, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n')
            ds, layer = assign_land.polygon({'path':str(gp),'sha256':assign_land.sha(gp)})
            member_hits = select_roots(layer, geom.GetEnvelope(), grid, rr, runs, strip)
            require(bool(member_hits), f'feature hits no land: {aid}/{fid}')
            hits.update(member_hits); per_feature_hits[fid]=len(member_hits)
            ds = layer = None
        if method == 'component_intersection_v1':
            witnesses = selector['exclude_witnesses']
            includes = selector['include_witnesses']
            require(isinstance(witnesses,list) and isinstance(includes,list), 'inclusion and exclusion witnesses must be lists')
            excluded_list = [witness_root(x,grid,rr,runs) for x in witnesses]
            included_list = [witness_root(x,grid,rr,runs) for x in includes]
            excluded, included = set(excluded_list), set(included_list)
            require(len(excluded)==len(excluded_list) and excluded <= hits, 'duplicate or non-intersecting exclusion')
            require(len(included)==len(included_list) and not included & hits, 'duplicate or already-intersecting inclusion')
            selected = (hits-excluded)|included
            require(bool(selected), f'empty component assignment: {aid}')
            for root in selected:
                require(root not in claims and root not in partitions, f'conflicting component claim {root}')
                claims[root] = {'rule_id':f'{aid}:component:{root}','source_evidence':feature_ids, 'component_id':root,'kind':'whole_component','code':code}
            summaries.append({'affiliation_id':aid,'source_feature_hit_counts':per_feature_hits,'hit_components':len(hits),'excluded_components':len(excluded),'included_components':len(included),'selected_components':len(selected)})
        else:
            root = witness_root(selector['component_witness'],grid,rr,runs)
            require(root in hits, f'partition does not intersect witness component: {aid}')
            require(root not in claims, f'partition conflicts with component claim {root}')
            partitions.setdefault(root,[]).append({'part_id':aid,'code':code,'geometry':{'path':str(gp),'sha256':assign_land.sha(gp)}})
            summaries.append({'affiliation_id':aid,'partition_component':root})
    rules = list(claims.values())
    for root, parts in sorted(partitions.items()):
        rules.append({'rule_id':f'partition:component:{root}','source_evidence':[x['part_id'] for x in parts], 'component_id':root,'kind':'polygon_partition','parts':parts})
    rules.sort(key=lambda r:r['component_id'])
    compiler = {'schema':'land-decision-compiler-prototype-v1','decision_revision':rev['id'], 'revision_status':rev['status'],
                'provenance_note':'UNVERIFIED snapshot, research output only; see direct build report', 'grid':grid,
                **{k:cfg[k] for k in ('physical_rows','physical_runs','component_rows','component_runs')}, 'strip_rows':strip, 'rules':rules}
    cpath=out/'compiler-config.json'; cpath.write_text(json.dumps(compiler,sort_keys=True,separators=(',',':'))+'\n')
    report=assign_land.build(cpath,out/'land')
    # Check all originally pinned bytes after output has finished.
    for spec in pins: pin(spec)
    require(Path(config_path).read_bytes() == cfg_bytes, 'config changed during run')
    result={'schema':'direct-neon-land-build-report-v1','status':'unverified-research-not-published',
            'decision_revision':rev['id'],'decision_revision_asserted_status':rev['status'],'entity_revision':erev['id'],
            'snapshot_sha256':cfg['snapshot']['sha256'],'config_sha256':hashlib.sha256(cfg_bytes).hexdigest(),
            'program_sha256':assign_land.sha(__file__), 'component_verification':{'builder_source_sha256':component_source_hash,
            'builder_binary_sha256':assign_land.sha(binary),'compiler_version':compiler_version,'builder_output':process.stdout.strip(),
            'rows_sha256':assign_land.sha(regenerated_rows),'runs_sha256':assign_land.sha(regenerated_runs)},
            'compiler_report':report,'decision_summary':summaries,
            'limitation':'Snapshot authenticity, decision completeness and geographic review are not proved. No prior continent grid was read. Water code 1 is only a placeholder.'}
    (out/'config.json').write_bytes(cfg_bytes)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('config',type=Path); p.add_argument('output',type=Path)
    p.add_argument('--allow-unverified-snapshot',action='store_true')
    a=p.parse_args()
    try: print(json.dumps(prepare(a.config,a.output,a.allow_unverified_snapshot),indent=2))
    except Exception as e: print(f'error: {e}',file=sys.stderr); raise SystemExit(1)

if __name__=='__main__': main()
