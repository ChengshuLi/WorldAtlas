"""Read-only, two-pass physical-component scan for the regional rule.

Consumes pinned little-endian row offsets and (start, end, root) land runs.
First collect the in-window statistics; second validate every global row and
count the full population of every touched root. No map or cell patch output.
"""
from array import array
from bisect import bisect_left, bisect_right
import hashlib
import math
from pathlib import Path
import struct
import sys

from regional_rule import BOUNDARY_EPSILON_DEGREES, _require

TRIPLE = struct.Struct('<III')


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _pin(spec):
    _require(isinstance(spec, dict) and set(spec) == {'path', 'sha256'} and
             isinstance(spec['sha256'], str) and len(spec['sha256']) == 64, 'invalid input pin')
    path = Path(spec['path']).resolve(strict=True)
    _require(path.is_file() and sha256_file(path) == spec['sha256'], 'component input hash mismatch')
    return path


def _offsets(path, run_path, height):
    _require(path.stat().st_size == (height + 1)*4 and run_path.stat().st_size % TRIPLE.size == 0, 'invalid stream sizes')
    values = array('I')
    _require(values.itemsize == 4, 'unsupported integer representation')
    with path.open('rb') as f:
        values.frombytes(f.read())
    if sys.byteorder != 'little':
        values.byteswap()
    _require(values[0] == 0 and values[-1] * TRIPLE.size == run_path.stat().st_size and
             all(a <= b for a,b in zip(values, values[1:])), 'invalid row offsets')
    return values


def _runs(file, start, end, width):
    file.seek(start * TRIPLE.size)
    raw = file.read((end-start) * TRIPLE.size)
    _require(len(raw) == (end-start)*TRIPLE.size, 'truncated run row')
    previous = 0
    for lo, hi, root in struct.iter_unpack('<III', raw):
        _require(previous <= lo < hi <= width and root < 0xffffffff, 'invalid component run')
        previous = hi
        yield lo, hi, root


def scan(row_spec, run_spec, grid, bounds, line):
    """Return complete root counts for all components touching a window.

    grid is width/height/west/north/step with center sampling; bounds is
    [west, south, east, north], inclusive of centers. No anti-meridian window.
    Caller authenticates the component manifest, physical mask correspondence,
    source snapshot and line before invoking. Hashes are verified twice.
    """
    _require(isinstance(grid, dict) and set(grid) == {'width','height','west','north','step'}, 'invalid grid')
    w,h,west,north,step = (grid[x] for x in ('width','height','west','north','step'))
    _require(type(w) is int and type(h) is int and 1 < w <= 1000000 and 0 < h <= 1000000 and
             type(step) in (int,float) and math.isfinite(step) and step > 0 and
             type(west) in (int,float) and type(north) in (int,float) and
             math.isfinite(west) and math.isfinite(north) and west >= -180 and
             north <= 90 and west + w*step <= 180 + 1e-8 and north-h*step >= -90-1e-8, 'invalid grid bounds')
    _require(isinstance(bounds, (list,tuple)) and len(bounds)==4 and
             all(type(v) in (int,float) and math.isfinite(v) for v in bounds), 'invalid region')
    bw,bs,be,bn = bounds
    _require(-180 <= bw < be <= 180 and -90 <= bs < bn <= 90, 'invalid region bounds')
    rp,sp = _pin(row_spec),_pin(run_spec)
    offsets = _offsets(rp,sp,h)
    # Binary searches use the same center formula as classification, including
    # the tiny numerical line-contact interval. No per-cell raster is built.
    xs=range(w)
    lon=lambda x: west+(x+0.5)*step
    x0=bisect_left(xs,bw,key=lon); x1=bisect_right(xs,be,key=lon)
    records = {}
    with sp.open('rb') as f:
        for y in range(h):
            lat=north-(y+0.5)*step
            if not bs <= lat <= bn:
                continue
            cut=line.longitude(lat)
            if cut is not None:
                left=bisect_left(xs,cut-BOUNDARY_EPSILON_DEGREES,key=lon)
                right=bisect_right(xs,cut+BOUNDARY_EPSILON_DEGREES,key=lon)
            for lo,hi,root in _runs(f,offsets[y],offsets[y+1],w):
                lo=max(lo,x0); hi=min(hi,x1)
                if lo >= hi:
                    continue
                r=records.setdefault(root,dict(total=0,in_scope=0,west=0,east=0,boundary=0,outside_latitude=0))
                r['in_scope']+=hi-lo
                if cut is None:
                    r['outside_latitude']+=hi-lo
                else:
                    r['west']+=max(0,min(hi,left)-lo)
                    r['boundary']+=max(0,min(hi,right)-max(lo,left))
                    r['east']+=max(0,hi-max(lo,right))
    with sp.open('rb') as f:
        for y in range(h):
            for lo,hi,root in _runs(f,offsets[y],offsets[y+1],w):
                if root in records:
                    records[root]['total']+=hi-lo
    _require(all(r['total'] >= r['in_scope'] > 0 and
                 sum(r[k] for k in ('west','east','boundary','outside_latitude')) == r['in_scope']
                 for r in records.values()), 'inconsistent scan')
    _require(sha256_file(rp)==row_spec['sha256'] and sha256_file(sp)==run_spec['sha256'], 'component input changed')
    return records


def collect_runs(row_spec, run_spec, grid, expected_counts):
    """Read complete global runs for selected roots and recheck their counts."""
    w,h=grid['width'],grid['height']
    _require(type(w) is int and type(h) is int and w>1 and h>0 and
             isinstance(expected_counts,dict) and all(type(r) is int and type(n) is int and n>0
                                                       for r,n in expected_counts.items()), 'invalid root request')
    rp,sp=_pin(row_spec),_pin(run_spec)
    offsets=_offsets(rp,sp,h)
    result={root:[] for root in expected_counts}
    with sp.open('rb') as f:
        for y in range(h):
            for lo,hi,root in _runs(f,offsets[y],offsets[y+1],w):
                if root in result:
                    result[root].append((y,lo,hi))
    _require(all(sum(hi-lo for _,lo,hi in result[r])==n for r,n in expected_counts.items()), 'incomplete root runs')
    _require(sha256_file(rp)==row_spec['sha256'] and sha256_file(sp)==run_spec['sha256'], 'component input changed')
    return result


def component_at(row_spec, run_spec, grid, lon, lat):
    """Resolve a source witness to its current physical component, if any."""
    w,h,west,north,step=(grid[k] for k in ('width','height','west','north','step'))
    _require(all(type(v) in (int,float) and math.isfinite(v) for v in (lon,lat)), 'invalid witness')
    x=math.floor((lon-west)/step);y=math.floor((north-lat)/step)
    _require(0<=x<w and 0<=y<h, 'witness outside grid')
    rp,sp=_pin(row_spec),_pin(run_spec);offsets=_offsets(rp,sp,h)
    with sp.open('rb') as f:
        hits=[root for lo,hi,root in _runs(f,offsets[y],offsets[y+1],w) if lo<=x<hi]
    _require(len(hits)==1, 'witness does not resolve to exactly one physical component')
    _require(sha256_file(rp)==row_spec['sha256'] and sha256_file(sp)==run_spec['sha256'], 'component input changed')
    return hits[0]
