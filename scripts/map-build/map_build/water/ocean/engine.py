#!/usr/bin/env python3
"""Fill residual water from source-backed barriers and registry-bound ocean seeds."""
from __future__ import annotations
import hashlib, json, math, re, struct, time
from bisect import bisect_right
from pathlib import Path
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from map_build.water.ocean.partition_core import rasterize_barriers, floodfill_run_graph
from map_build.water.ocean.rle_inputs import RunRasterU32LE, make_prefill_adapters
from map_build.execution.outputs import create_directory_exclusive, create_text_exclusive, write_json_exclusive
from map_build.execution import outputs

HEX = re.compile(r'^[0-9a-f]{64}$')
RULE = 'fresh-ocean-seed-floodfill-v1'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()

def unique_by(rows,key):
    if not isinstance(rows,list):raise ValueError(f'{key}: expected list')
    result={}
    for row in rows:
        ident=row.get(key)
        if not isinstance(ident,str) or not ident or ident in result:raise ValueError(f'duplicate or invalid {key}')
        result[ident]=row
    return result

def num(x):
    if isinstance(x,bool) or not isinstance(x,(str,int,float)):raise ValueError('invalid coordinate')
    n=float(x)
    if not math.isfinite(n):raise ValueError('invalid coordinate')
    return n

def coast_edge_latitude(physical, longitude, reference_latitude):
    """Find the nearest south-facing coast edge straddling the meridian."""
    step = Fraction(360, physical.width)
    west_cell = math.floor((longitude + 180) / step - Fraction(1, 2))
    if not 0 <= west_cell < physical.width - 1:
        raise ValueError('coast endpoint requires two cells bracketing its meridian')

    def codes(y):
        row = physical.row(y)
        return tuple(row[bisect_right(row, x, key=lambda run: run[0])][1]
                     for x in (west_cell, west_cell + 1))

    north_codes = codes(0)
    nearest = None
    for y in range(1, physical.height):
        south_codes = codes(y)
        if north_codes == (17, 17) and south_codes == (1, 1):
            latitude = 90 - y * step
            distance = abs(latitude - reference_latitude)
            if nearest is None or distance < nearest[0]:
                nearest = distance, latitude
        north_codes = south_codes
    if nearest is None:
        raise ValueError('no south-facing coast edge at the selected meridian')
    return nearest[1]


def endpoint_coordinate(endpoint, axis):
    raw = endpoint.get(axis)
    derivation = endpoint.get('derivation', {})
    if not isinstance(derivation, dict):
        raise ValueError('invalid endpoint derivation')
    if derivation.get('method') not in ('source_dms_exact_rational',
                                      'source_decimal_exact_rational', 'preserved_grid_edge',
                                      'grid_south_edge'):
        return num(raw)
    pair = derivation.get(axis + '_fraction')
    if (not isinstance(pair, list) or len(pair) != 2 or any(type(x) is not int for x in pair)
            or pair[1] <= 0 or any(abs(x).bit_length() > 128 for x in pair)):
        raise ValueError('invalid exact endpoint fraction')
    try:
        decimal = Decimal(str(raw))
        if not decimal.is_finite(): raise ValueError('invalid endpoint decimal')
        exact = Fraction(pair[0], pair[1])
        if abs(Fraction(decimal) - exact) > Fraction(1, 2 * 10**15):
            raise ValueError('endpoint fraction disagrees with rounded database coordinate')
        return float(exact)
    except (InvalidOperation, TypeError, ZeroDivisionError) as e:
        raise ValueError('invalid endpoint coordinate') from e



def spherical_rhumb_points(points, step_km):
    """Densify rhumb segments straight in spherical Mercator coordinates.

    This matches the interpolated construction lines in IHO S-130 Ed.1.0.0.
    The conservative step bound limits arc length on a sphere of radius 6378137m.
    The original longitude/latitude endpoints are retained exactly.
    """
    if not 0 < step_km <= 1:
        raise ValueError('rhumb max_step_km must be in (0,1]')
    def psi(phi):
        return math.asinh(math.tan(phi))
    dense = []
    for start, end in zip(points, points[1:]):
        if abs(end[0] - start[0]) > 180:
            raise ValueError('antimeridian-crossing rhumb unsupported')
        if abs(start[1]) >= 90 or abs(end[1]) >= 90:
            raise ValueError('rhumb endpoints at a pole unsupported')
        p0, p1 = psi(math.radians(start[1])), psi(math.radians(end[1]))
        dlambda = math.radians(end[0] - start[0])
        # Spherical Mercator's scale is at least one, so planar length is an upper bound.
        bound_m = 6378137.0 * math.hypot(p1-p0, dlambda)
        count = max(1, math.ceil(bound_m / (1000 * step_km)))
        dense.append(start)
        for i in range(1, count):
            t = i / count
            dense.append((start[0] + (end[0] - start[0]) * t,
                          math.degrees(math.atan(math.sinh(p0 + (p1-p0) * t)))))
    dense.append(points[-1])
    return dense


def load_config(snapshot,width,height,software_versions=None,*,physical=None):
    revision = snapshot.get('decision_revision', {})
    registry = snapshot.get('entity_revision', {})
    if not revision.get('id') or not revision.get('entity_revision') or registry.get('id') != revision['entity_revision']:
        raise ValueError('matching decision and entity revisions are required')
    policies = [p for p in snapshot.get('policies', []) if p.get('kind') == 'ocean_fill']
    if len(policies) != 1:
        raise ValueError('one ocean_fill policy is required')
    policy=policies[0].get('definition',{})
    if (policy.get('connectivity')!=4 or type(policy.get('wrap_longitude')) is not bool
        or policy.get('barrier_tie_rule')!='left-of-oriented-route' or policy.get('unseeded_policy')!='report-only'):
        raise ValueError('unsupported ocean-fill policy')
    endpoints=unique_by(snapshot.get('endpoints'), 'endpoint_id')
    routes=unique_by(snapshot.get('routes'), 'route_id')
    seed_rows=unique_by(snapshot.get('ocean_seeds'),'seed_id')
    bindings=snapshot.get('category_bindings',[])
    route_ids=policy.get('route_ids');seed_ids=policy.get('seed_ids')
    if not isinstance(route_ids,list) or len(set(route_ids))!=len(route_ids) or not route_ids:
        raise ValueError('policy requires explicit unique routes')
    if not isinstance(seed_ids,list) or len(set(seed_ids))!=len(seed_ids) or not seed_ids:
        raise ValueError('policy requires unique nonempty seeds')
    step=360.0/width
    def coord(ident):
        if ident not in endpoints:raise ValueError(f'unknown endpoint {ident}')
        e=endpoints[ident];lon=endpoint_coordinate(e,'longitude')
        derivation = e.get('derivation', {})
        if derivation.get('method') == 'physical_coast_edge':
            if physical is None or (physical.width, physical.height) != (width, height):
                raise ValueError('coast endpoint requires the current physical grid')
            reference = Fraction(str(derivation['reference_latitude']))
            if not -90 <= reference <= 90:
                raise ValueError('invalid coast endpoint reference latitude')
            lat = float(coast_edge_latitude(physical, Fraction(str(e['longitude'])), reference))
        elif derivation.get('method') == 'grid_south_edge':
            reference = endpoint_coordinate(e,'latitude')
            lat = float(Fraction(90) - Fraction(height * 360, width))
            if not lat <= reference < lat + step:
                raise ValueError('south-grid endpoint must lie in the final grid row')
        else:
            lat = endpoint_coordinate(e,'latitude')
        if not -180<=lon<=180 or not (90-height*step)<=lat<=90:raise ValueError(f'endpoint outside grid: {ident}')
        return lon,lat
    paths=[]
    for rid in route_ids:
        if rid not in routes:raise ValueError(f'unknown route {rid}')
        r=routes[rid]; kind=r.get('route_type'); points=r.get('points',[])
        if kind not in ('lonlat_polyline','meridian','wgs84_geodesic','spherical_rhumb'):raise ValueError(f'unsupported boundary route type: {kind}')
        if len(points)<2 or [p.get('ordinal') for p in points]!=list(range(len(points))):raise ValueError('route points must be contiguous and ordered')
        ll=[coord(p.get('endpoint_id')) for p in points]
        if kind=='meridian' and any(abs(x-ll[0][0])>1e-12 for x,_ in ll):raise ValueError('meridian longitudes differ')
        if kind=='spherical_rhumb':
            ll=spherical_rhumb_points(ll,num(r.get('parameters',{}).get('max_step_km')))
        if kind=='wgs84_geodesic':
            # Geographic interpolation is prescribed by the decision, never inferred.
            params=r.get('parameters',{}); step_km=num(params.get('max_step_km'))
            if not 0 < step_km <= 1:raise ValueError('geodesic max_step_km must be in (0,1]')
            try:
                from pyproj import Geod
            except ImportError as e:raise ValueError('wgs84_geodesic requires pinned pyproj and PROJ') from e
            import pyproj
            versions=software_versions if software_versions is not None else snapshot.get('build',{}).get('software_versions',{})
            if versions.get('pyproj')!=pyproj.__version__ or versions.get('proj')!=pyproj.proj_version_str:
                raise ValueError('WGS84 route requires matching pinned pyproj and PROJ versions')
            geod=Geod(ellps='WGS84'); dense=[]
            for a,b in zip(ll,ll[1:]):
                if abs(b[0]-a[0])>180:raise ValueError('antimeridian-crossing geodesic unsupported')
                _,_,distance=geod.inv(a[0],a[1],b[0],b[1]); count=max(1,math.ceil(distance/(1000*step_km)))
                dense.append(a)
                if count>1:dense.extend(geod.npts(a[0],a[1],b[0],b[1],count-1))
            dense.append(ll[-1]);ll=dense
        path=[]
        for (lon0,lat0),(lon1,lat1) in zip(ll,ll[1:]):
            if abs(lon1-lon0)>180:raise ValueError('antimeridian-crossing route requires explicit supported handling')
            x0,y0=(lon0+180)/step,(90-lat0)/step;x1,y1=(lon1+180)/step,(90-lat1)/step
            # Short linear segments bound rasterization cost while preserving route shape.
            n=max(1,math.ceil(max(abs(x1-x0),abs(y1-y0))))
            if n>width+height:raise ValueError('route segment unexpectedly long')
            path.extend((x0+(x1-x0)*i/n,y0+(y1-y0)*i/n) for i in range(n))
        path.append(((ll[-1][0]+180)/step,(90-ll[-1][1])/step));paths.append(path)
    seeds={}; metadata={}
    for sid in seed_ids:
        if sid not in seed_rows:raise ValueError(f'unknown seed {sid}')
        s=seed_rows[sid];found=[x for x in bindings if x.get('entity_id')==s.get('entity_id') and x.get('physical_class')=='water']
        if len(found)!=1 or type(found[0].get('code')) is not int or not 0 < found[0]['code'] < 2**32:raise ValueError('seed must bind uniquely to a water code')
        code=found[0]['code'];lon,lat=coord(s['endpoint_id']);x=math.floor((lon+180)/step);y=math.floor((90-lat)/step)
        if not (0<=x<width and 0<=y<height) or code in seeds:raise ValueError('duplicate code or seed outside grid')
        seeds[code]=(x,y);metadata[code]={'seed_id':sid,'endpoint_id':s['endpoint_id'],'entity_id':s['entity_id'],'nominal_longitude_deg':lon,'nominal_latitude_deg':lat}
    return policy,paths,seeds,metadata

def export_layer(partition,out,width,height,metadata,inputs,tile_height=256):
    offsets=struct.unpack('<%dQ'%(height+1),(partition/'ocean_rows.u64le').read_bytes())
    tiles=[]
    with (partition/'ocean_assignment_spans.u32le').open('rb') as stream:
        for y0 in range(0,height,tile_height):
            y1=min(height,y0+tile_height);p=out/f'ocean-{y0:06d}-{y1:06d}.jsonl'
            with create_text_exclusive(p,encoding='utf8',newline='\n') as f:
                for y in range(y0,y1):
                    stream.seek(offsets[y]*12); spans=[]
                    for _ in range(offsets[y+1]-offsets[y]):
                        raw=stream.read(12)
                        if len(raw)!=12:raise ValueError('truncated ocean spans')
                        a,b,code=struct.unpack('<III',raw)
                        if not (0<=a<b<=width) or code not in metadata:raise ValueError('invalid ocean output span')
                        spans.append({'start':a,'end':b,'code':code,'rule_id':RULE,'member_id':metadata[code]['seed_id']})
                    f.write(json.dumps({'row':y,'spans':spans},separators=(',',':'))+'\n')
            tiles.append({'core_rows':[y0,y1],'core_cols':[0,width],'span_file':{'path':p.name,'sha256':sha(p)}})
    manifest={'schema':'worldatlas-full-water-assignment-tiles-v1','status':'completed_unverified_candidate_not_published',
      'grid':{'width':width,'height':height,'angular_step_deg':360.0/width,'row_convention':'north-to-south; cell centers; half-open [start,end) x spans'},
      'coverage':{'complete':True,'meaning':'seeded residual marine components only; unseeded components require separate review'},
      'source':inputs,'tiles':tiles}
    write_json_exclusive(out/'ocean-layer-manifest.json',manifest,indent=2)
    return manifest

def run(snapshot,snapshot_hash,physical_rows,physical_runs,prefill_rows,prefill_runs,out,width,height,inputs,tile_height=256,software_versions=None,pre_finalize=None,pre_summary=None,processing_started=None):
    if processing_started is None: processing_started=time.perf_counter()
    with RunRasterU32LE(physical_rows,physical_runs,width,height) as physical:
        policy,paths,seeds,metadata=load_config(snapshot,width,height,software_versions,physical=physical)
    if tile_height<=0:raise ValueError('tile height must be positive')
    create_directory_exclusive(out)
    cuts=rasterize_barriers(paths,width,height)
    if not policy['wrap_longitude']:cuts.wrap.update(range(height))
    cut_path=out/'barrier_edges.u32le';cuts.write_u32le(cut_path)
    here=Path(__file__).resolve().parent
    code_pins={name:sha(here/name) for name in ('engine.py','partition_core.py','rle_inputs.py')}
    code_pins['outputs.py'] = sha(Path(outputs.__file__))
    software={}
    routes=unique_by(snapshot.get('routes'),'route_id')
    if any(routes[rid]['route_type']=='wgs84_geodesic' for rid in policy['route_ids']):
        import pyproj
        software={'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str}
    pins={**inputs,'decision_snapshot_sha256':snapshot_hash,'decision_revision':snapshot['decision_revision']['id'],
          'entity_revision':snapshot['decision_revision']['entity_revision'],'source_cut_edges_sha256':sha(cut_path),
          'route_ids':policy['route_ids'],'seed_ids':policy['seed_ids'],
          'candidate_code_sha256':code_pins,'geodesic_software':software}
    with RunRasterU32LE(physical_rows,physical_runs,width,height) as physical, RunRasterU32LE(prefill_rows,prefill_runs,width,height) as prefill:
        land_codes = {b['code'] for b in snapshot['category_bindings'] if b['physical_class'] == 'land'}
        land_entities = {b['entity_id'] for b in snapshot['category_bindings'] if b['physical_class'] == 'land'}
        water_codes = {b['code'] for b in snapshot['category_bindings'] if b['physical_class'] == 'water' and b['entity_id'] in land_entities}
        eligible,classes=make_prefill_adapters(physical,prefill,width,height,land_codes,water_codes)
        part=floodfill_run_graph(eligible,width,height,cuts,seeds,out/'partition',manifest_inputs=pins,
             unassigned_policy='report-only',classification_rows=classes,seed_metadata=metadata,
             required_seed_codes=set(seeds),class_labels={b['code']:str(b['entity_id'])+' '+b['physical_class'] for b in snapshot['category_bindings']})
    if pre_finalize: pre_finalize()
    export_layer(out/'partition',out,width,height,metadata,pins,tile_height)
    if pre_summary: pre_summary()
    write_json_exclusive(out/'run-summary.json',{'status':'unverified-candidate-not-published','snapshot_sha256':snapshot_hash,
      'unseeded_cell_count':part['unseeded_cell_count'],'assigned_cells_total':part['assigned_cells_total'],
      'barrier_sha256':pins['source_cut_edges_sha256'],'layer_manifest_sha256':sha(out/'ocean-layer-manifest.json'),
      'processing_elapsed_seconds':time.perf_counter()-processing_started},indent=2)
