#!/usr/bin/env python3
"""Fail-closed, exact all-touched water check for one selected LineString.

Coordinates are interpreted exactly as decimal GeoJSON degrees; the grid is EPSG:4326.
A closed grid cell is touched even at a corner or along an edge. No GDAL is used.
"""
import argparse, bisect, hashlib, json, os, re, struct, sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

# Input and geometry validation bounds.
MAX_ALLOWED_VISITS = 2000000
MAX_DIMENSION = 1048576
MAX_RUNS_PER_ROW = 131072
MAX_CONTRACT_BYTES = 65536
WIDTH = HEIGHT = STEP = WEST = NORTH = ROWS = RUNS = WATER = LAND = None
MAX_VISITS = MAX_ALLOWED_VISITS
MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_VERTICES = 100000


def load_contract(path, expected_sha256):
    global WIDTH, HEIGHT, STEP, WEST, NORTH, ROWS, RUNS, WATER, LAND, MAX_VISITS
    with open(path, 'rb') as f: raw = f.read(MAX_CONTRACT_BYTES+1)
    if len(raw) > MAX_CONTRACT_BYTES: raise ValueError('contract exceeds size limit')
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256: raise ValueError('contract hash mismatch')
    c = json.loads(raw, object_pairs_hook=no_duplicate_keys, parse_float=bounded_decimal,
                   parse_constant=lambda x: (_ for _ in ()).throw(ValueError('non-finite number')))
    if set(c) != {'schema','grid','physical','resources'} or c['schema'] != 'physical-water-closure-contract-v2': raise ValueError('unsupported contract')
    g, p, r = c['grid'], c['physical'], c['resources']
    if set(g) != {'crs','width','height','west','north','step_numerator','step_denominator'} or g['crs'] != 'EPSG:4326': raise ValueError('unsupported grid contract')
    if set(p) != {'rows_sha256','runs_sha256','water_code','land_code','report_sha256','encoding_evidence_sha256','producer_code_path'} or set(r) != {'max_cell_visits'}: raise ValueError('unsupported physical or resource contract')
    def integer(v, lower, upper, label):
        if type(v) is not int or not lower <= v <= upper: raise ValueError('invalid ' + label)
        return v
    WIDTH=integer(g['width'],1,MAX_DIMENSION,'width'); HEIGHT=integer(g['height'],1,MAX_DIMENSION,'height')
    numerator=integer(g['step_numerator'],1,360*(1<<30),'step numerator'); denominator=integer(g['step_denominator'],1,1<<30,'step denominator')
    STEP=Fraction(numerator,denominator)
    if not isinstance(g['west'],(int,Decimal)) or isinstance(g['west'],bool) or not isinstance(g['north'],(int,Decimal)) or isinstance(g['north'],bool): raise ValueError('invalid grid origin')
    WEST,NORTH=Fraction(g['west']),Fraction(g['north'])
    if not -180 <= WEST < 180 or not -90 < NORTH <= 90 or WEST+WIDTH*STEP > 180 or NORTH-HEIGHT*STEP < -90: raise ValueError('grid exceeds EPSG:4326 bounds')
    ROWS,RUNS=p['rows_sha256'],p['runs_sha256']
    if any(not isinstance(v,str) or not re.fullmatch('[0-9a-f]{64}',v) for v in (ROWS,RUNS,p['report_sha256'],p['encoding_evidence_sha256'])): raise ValueError('invalid physical checksum')
    WATER=integer(p['water_code'],0,(1<<32)-1,'water code'); LAND=integer(p['land_code'],0,(1<<32)-1,'land code')
    if WATER == LAND: raise ValueError('water and land codes must differ')
    path=p['producer_code_path']
    if not isinstance(path,str) or not path or Path(path).is_absolute() or '..' in Path(path).parts: raise ValueError('invalid producer evidence path')
    MAX_VISITS=integer(r['max_cell_visits'],1,MAX_ALLOWED_VISITS,'cell visit limit')
    return actual, c


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def interval_cells(a, b):
    lo, hi = sorted((a, b))
    # Include the cell immediately before an integral lower boundary.
    first = lo.numerator // lo.denominator - (lo.denominator == 1)
    last = hi.numerator // hi.denominator
    return range(first, last + 1)


def touched_segment(x0, y0, x1, y1):
    """Yield closed grid squares intersecting a segment, using rational arithmetic."""
    for y in interval_cells(y0, y1):
        dy = y1 - y0
        if dy == 0:
            xa, xb = x0, x1
        else:
            t0 = max(Fraction(0), min((Fraction(y) - y0) / dy, (Fraction(y + 1) - y0) / dy))
            t1 = min(Fraction(1), max((Fraction(y) - y0) / dy, (Fraction(y + 1) - y0) / dy))
            if t0 > t1:
                continue
            xa, xb = x0 + (x1 - x0) * t0, x0 + (x1 - x0) * t1
        for x in interval_cells(xa, xb):
            yield x, y


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def bounded_decimal(token):
    # Bound integer size before Fraction conversion, including tiny exponents.
    if len(token) > 80: raise ValueError('numeric token too long')
    value = Decimal(token)
    if not value.is_finite() or len(value.as_tuple().digits) > 30 or abs(value.as_tuple().exponent) > 24:
        raise ValueError('unsupported coordinate precision or exponent')
    return value


def geom_and_points(raw):
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError('geometry input exceeds size limit')
    ordinary = json.loads(raw, object_pairs_hook=no_duplicate_keys, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('non-finite number')))
    exact = json.loads(raw, object_pairs_hook=no_duplicate_keys, parse_float=bounded_decimal, parse_int=int, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('non-finite number')))
    def geometry(obj):
        if not isinstance(obj, dict): raise ValueError('expected GeoJSON object')
        if 'crs' in obj: raise ValueError('unsupported explicit CRS')
        if obj.get('type') == 'Feature': obj = obj.get('geometry')
        if not isinstance(obj, dict) or obj.get('type') != 'LineString': raise ValueError('expected exactly one LineString or Feature')
        if set(obj) != {'type','coordinates'}: raise ValueError('unsupported geometry members')
        return obj
    g, e = geometry(ordinary), geometry(exact)
    digest = hashlib.sha256(json.dumps(g, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    pts = e['coordinates']
    if not isinstance(pts, list) or not 2 <= len(pts) <= MAX_VERTICES: raise ValueError('invalid vertex count')
    grid = []
    for p in pts:
        if not isinstance(p, list) or len(p) != 2 or any(isinstance(v, bool) or not isinstance(v,(int, Decimal)) for v in p): raise ValueError('coordinates must be finite 2D numbers')
        if any(isinstance(v, Decimal) and Decimal(str(float(v))) != v for v in p): raise ValueError('coordinate loses precision in canonical JSON hash')
        lon, lat = map(Fraction, p)
        if not WEST < lon < WEST + WIDTH * STEP or not NORTH - HEIGHT * STEP < lat < NORTH: raise ValueError('unsupported world/grid edge')
        grid.append(((lon - WEST) / STEP, (NORTH - lat) / STEP, lon))
    for a, b in zip(grid, grid[1:]):
        if abs(a[2] - b[2]) >= 180: raise ValueError('unsupported dateline or ambiguous 180-degree segment')
        if a[:2] == b[:2]: raise ValueError('zero-length segment')
    return digest, grid


def verify_producer_code(contract_path, contract):
    base=Path(contract_path).resolve().parent
    path=(base/contract['physical']['producer_code_path']).resolve()
    if not path.is_relative_to(base): raise ValueError('producer evidence escapes contract directory')
    if path.stat().st_size > 4*1024*1024: raise ValueError('producer evidence exceeds size limit')
    if sha(path) != contract['physical']['encoding_evidence_sha256']: raise ValueError('producer evidence hash mismatch')
    return path


def verify_physical_report(directory, contract):
    path=Path(directory)/'report.json'
    if sha(path) != contract['physical']['report_sha256']: raise ValueError('physical report hash mismatch')
    with open(path,'rb') as f: raw=f.read(MAX_CONTRACT_BYTES+1)
    if len(raw) > MAX_CONTRACT_BYTES: raise ValueError('physical report too large')
    report=json.loads(raw, object_pairs_hook=no_duplicate_keys, parse_float=bounded_decimal,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('non-finite number')))
    g=report['grid']; out=report['output_sha256']
    if (g['width'] != WIDTH or g['height'] != HEIGHT or Fraction(g['west']) != WEST or
        Fraction(g['north']) != NORTH or Fraction(g['step']) != STEP): raise ValueError('physical report grid mismatch')
    if out['rows.u32le'] != ROWS or out['runs.u32le'] != RUNS: raise ValueError('physical report output hash mismatch')
    return path


class Mask:
    def __init__(self, directory):
        self.dir = Path(directory)
        self.rowpath, self.runpath = self.dir/'rows.u32le', self.dir/'runs.u32le'
        if self.rowpath.stat().st_size != 4 * (HEIGHT+1): raise ValueError('invalid row index length')
        if sha(self.rowpath) != ROWS or sha(self.runpath) != RUNS: raise ValueError('physical raster hash mismatch')
        with self.rowpath.open('rb') as f: raw = f.read(4 * (HEIGHT+1) + 1)
        if len(raw) != 4 * (HEIGHT+1): raise ValueError('invalid row index length')
        self.rows = struct.unpack('<' + str(HEIGHT+1) + 'I', raw)
        self.run = self.runpath.open('rb')
        if self.rows[0] != 0 or self.rows[-1] * 8 != self.runpath.stat().st_size: raise ValueError('invalid run index endpoints')
        self.cache = {}
    def code(self, x, y):
        if not 0 <= x < WIDTH or not 0 <= y < HEIGHT: raise ValueError('segment touches grid edge')
        if y not in self.cache:
            lo, hi = self.rows[y:y+2]
            if lo >= hi or hi > self.rows[-1] or hi-lo > min(WIDTH, MAX_RUNS_PER_ROW): raise ValueError('invalid row offsets')
            self.run.seek(lo*8); raw = self.run.read((hi-lo)*8)
            if len(raw) != (hi-lo)*8: raise ValueError('truncated row')
            pairs = list(struct.iter_unpack('<II', raw)); ends = [a for a,_ in pairs]; vals = [b for _,b in pairs]
            if ends[0] <= 0 or ends[-1] != WIDTH or any(a >= b for a,b in zip(ends,ends[1:])) or any(v not in (WATER,LAND) for v in vals): raise ValueError('invalid physical run values')
            self.cache[y] = ends, vals
        ends, vals = self.cache[y]
        return vals[bisect.bisect_right(ends,x)]
    def verify_again(self):
        if sha(self.rowpath) != ROWS or sha(self.runpath) != RUNS: raise ValueError('physical raster changed during check')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract',required=True,help='Exact reviewed physical and grid JSON contract')
    p.add_argument('--contract-sha256',required=True,help='Expected SHA-256 of exact contract bytes')
    p.add_argument('--geometry',required=True,help='Selected GeoJSON LineString or Feature')
    p.add_argument('--geometry-sha256',required=True,help='Expected canonical sorted compact GeoJSON geometry hash')
    p.add_argument('--physical-dir',default='physical-direct-output-20261103')
    p.add_argument('--output',required=True,help='New output JSON path; no overwrite')
    a=p.parse_args(); contract_sha, contract = load_contract(a.contract,a.contract_sha256)
    with open(a.geometry, 'rb') as f: raw=f.read(MAX_INPUT_BYTES+1)
    if len(raw) > MAX_INPUT_BYTES: raise ValueError('geometry input exceeds size limit')
    input_hash=hashlib.sha256(raw).hexdigest()
    geometry_hash, points=geom_and_points(raw)
    if geometry_hash != a.geometry_sha256: raise ValueError('selected geometry hash mismatch')
    checker_sha=sha(Path(__file__).resolve()); evidence_path=verify_producer_code(a.contract,contract); report_path=verify_physical_report(a.physical_dir,contract); mask=Mask(a.physical_dir); count=0
    for a0,b0 in zip(points,points[1:]):
        for x,y in touched_segment(a0[0],a0[1],b0[0],b0[1]):
            count+=1
            if count > MAX_VISITS: raise ValueError('cell visit limit exceeded')
            code=mask.code(x,y)
            if code != WATER: raise ValueError(f'closure touches non-water cell x={x}, y={y}, code={code}')
    mask.verify_again()
    if sha(Path(__file__).resolve()) != checker_sha or sha(Path(a.geometry)) != input_hash or sha(Path(a.contract)) != contract_sha or sha(report_path) != contract['physical']['report_sha256'] or sha(evidence_path) != contract['physical']['encoding_evidence_sha256']: raise ValueError('checker or geometry changed during validation')
    proof={'schema':'physical-water-closure-proof-v1','status':'valid', 'physical_rows_sha256':ROWS,'physical_runs_sha256':RUNS,'checker_sha256':checker_sha,'contract_sha256':contract_sha,'physical_report_sha256':contract['physical']['report_sha256'],'encoding_evidence_sha256':contract['physical']['encoding_evidence_sha256'],'geometry_sha256':geometry_hash,'input_file_sha256':input_hash,'grid':{k:(str(v) if isinstance(v,Decimal) else v) for k,v in contract['grid'].items()},'physical_code_contract':{'water':WATER,'land':LAND},'method':'exact-rational closed-cell all-touched; no GDAL; boundary and corner contacts included; no endpoint exceptions', 'geometry_hash_method':'SHA-256 of Python sorted-key compact UTF-8 JSON geometry, ensure_ascii=False, allow_nan=False', 'python_version':sys.version.split()[0],'vertices':len(points),'cell_visits':count,'max_cell_visits':MAX_VISITS,'warnings':['Grid, code semantics and resource settings derive from the externally reviewed hash-pinned contract.','Water-only raster proof does not establish selected-route authority, coastline closure, historical equivalence, topology, or continental labels.']}
    with open(a.output,'x') as f: json.dump(proof,f,indent=2); f.write('\n')
    print(json.dumps(proof,indent=2))

if __name__ == '__main__':
    try: main()
    except Exception as e:
        print(f'REJECTED: {type(e).__name__}: {e}', file=sys.stderr); sys.exit(1)
