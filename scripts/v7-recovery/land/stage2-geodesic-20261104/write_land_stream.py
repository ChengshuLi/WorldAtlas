"""Stream a validated, full-width research land RLE; no grid-sized arrays.

Inputs: row offsets are H+1 little-endian u32 record counts; component runs
are (start, end, root) u32, physical and mainland runs are (end, code) u32.
Physical codes are 1 water / 17 land. Mainland codes are 0 or 17..22.
Assignments are sorted unique roots u32 and one u8 code per root. Output
files are created in a new directory. A report exists only after success.
"""
import hashlib
import json
import math
import mmap
import os
from operator import length_hint
from pathlib import Path
import shutil
import struct
from ural_delta import SCHEMA as URAL_DELTA_SCHEMA, classify_cell

U32 = struct.Struct('<I')
PAIR = struct.Struct('<II')
TRIPLE = struct.Struct('<III')
MAX_U32 = (1 << 32) - 1


def _guard(directory, disk_reserve_bytes, extra=0):
    if shutil.disk_usage(directory).free < disk_reserve_bytes + extra:
        raise RuntimeError('disk reserve guard')


def _read_exact(f, n):
    b = f.read(n)
    if len(b) != n:
        raise ValueError('truncated file: ' + str(f.name))
    return b


class _Rows:
    def __init__(self, row_path, run_path, height, record):
        self.rows = open(row_path, 'rb')
        try:
            self.runs = open(run_path, 'rb')
            try:
                self.record = record
                self.pending = None
                if os.fstat(self.rows.fileno()).st_size != 4 * (height + 1):
                    raise ValueError('invalid row offset length')
                size = os.fstat(self.runs.fileno()).st_size
                if size % record.size:
                    raise ValueError('invalid run file length')
                self.count = size // record.size
                self.pos = U32.unpack(_read_exact(self.rows, 4))[0]
                if self.pos != 0:
                    raise ValueError('offsets must start at zero')
            except BaseException:
                self.runs.close()
                raise
        except BaseException:
            self.rows.close()
            raise

    def next(self):
        if self.pending is not None and length_hint(self.pending, -1) != 0:
            raise ValueError('previous row records not fully consumed')
        end = U32.unpack(_read_exact(self.rows, 4))[0]
        if end < self.pos or end > self.count:
            raise ValueError('invalid row offset')
        n = end - self.pos
        self.pos = end
        # One ordinary row buffer replaces a Python read/unpack per record.
        # Keep this a generator so offsets still advance only on consumption.
        self.pending = self.record.iter_unpack(_read_exact(self.runs, n * self.record.size))
        yield from self.pending

    def finish(self):
        if ((self.pending is not None and length_hint(self.pending, -1) != 0) or
                self.pos != self.count or self.runs.read(1) or self.rows.read(1)):
            raise ValueError('run count mismatch')

    def close(self):
        self.rows.close()
        self.runs.close()


def _full(records, width, valid, label):
    start = 0
    for end, code in records:
        if not start < end <= width or code not in valid:
            raise ValueError('invalid ' + label + ' row')
        yield start, end, code
        start = end
    if start != width:
        raise ValueError('incomplete ' + label + ' row')


def _components(records, width):
    start = 0
    for a, b, root in records:
        if not start <= a < b <= width:
            raise ValueError('overlapping or invalid component runs')
        if a > start:
            yield start, a, None
        yield a, b, root
        start = b
    if start < width:
        yield start, width, None


def write_land_stream(width, height, component_rows, component_runs,
                      physical_rows, physical_runs, mainland_rows, mainland_runs,
                      roots, codes, mainland_roots, output_dir, *,
                      disk_reserve_bytes=1 << 30, delta_rule=None):
    """Write rows.u32le, runs.u32le and an atomic report.json; return report.

    Run streams are decoded one row at a time. Every assignment root is indexed
    once in an input-sized dictionary; codes and the assignment-seen bitmap
    remain memory-mapped. A failed build leaves partial files.
    """
    if type(width) is not int or not 0 < width <= MAX_U32 or type(height) is not int or not 0 < height <= MAX_U32:
        raise ValueError('invalid grid dimensions')
    if type(disk_reserve_bytes) is not int or disk_reserve_bytes < 0:
        raise ValueError('invalid resource guard')
    delta_range = None
    delta_totals = None
    if delta_rule is not None:
        grid = delta_rule.get('grid') if isinstance(delta_rule, dict) else None
        if (delta_rule.get('schema') != URAL_DELTA_SCHEMA or not isinstance(grid, dict) or
                set(grid) != {'width', 'height', 'west', 'north', 'step'} or
                grid != {'width': width, 'height': height, 'west': -180, 'north': 90,
                         'step': 360 / width}):
            raise ValueError('invalid Ural delta rule or grid binding')
        w, s, e, n = delta_rule.get('scope_bounds', (None, None, None, None))
        if not all(type(v) in (int, float) for v in (w, s, e, n)) or not w < e or not s < n:
            raise ValueError('invalid Ural delta scope')
        step = grid['step']
        # Include centers exactly on a scope edge so classify_cell fails closed
        # rather than silently excluding an ambiguous boundary cell.
        x0 = max(0, math.ceil((w - grid['west']) / step - 0.5 - 1e-12))
        x1 = min(width, math.floor((e - grid['west']) / step - 0.5 + 1e-12) + 1)
        y0 = max(0, math.ceil((grid['north'] - n) / step - 0.5 - 1e-12))
        y1 = min(height, math.floor((grid['north'] - s) / step - 0.5 + 1e-12) + 1)
        if x0 >= x1 or y0 >= y1:
            raise ValueError('Ural delta scope has no grid centers')
        delta_range = (x0, x1, y0, y1)
        delta_totals = {'land_centers': 0, 'other_land_labels': 0,
                        'europe_to_asia': 0, 'asia_to_europe': 0}
    mr = tuple(mainland_roots)
    if not mr or any(type(x) is not int or not 0 <= x <= MAX_U32 for x in mr) or len(set(mr)) != len(mr):
        raise ValueError('non-empty unique valid mainland roots required')
    seed_ids = set(mr)
    out = Path(output_dir)
    # Reserve a conservative upper bound on output records and the bitmap.
    cs = os.stat(component_runs).st_size
    ps = os.stat(physical_runs).st_size
    ss = os.stat(mainland_runs).st_size
    rs = os.stat(roots).st_size
    ks = os.stat(codes).st_size
    if cs % 12 or ps % 8 or ss % 8 or rs % 4 or ks != rs // 4:
        raise ValueError('invalid input file lengths')
    n = rs // 4
    estimate = (2 * (cs // 12) + (ps // 8) + (ss // 8) + height) * 8 + 4 * (height + 1) + (n + 7) // 8 + 4096
    _guard(out.parent, disk_reserve_bytes, estimate)
    out.mkdir(exist_ok=False)
    sources = []
    maps = []
    files = []
    try:
        for rp, dp, rec in ((component_rows, component_runs, TRIPLE), (physical_rows, physical_runs, PAIR), (mainland_rows, mainland_runs, PAIR)):
            obj = _Rows(rp, dp, height, rec)
            sources.append(obj)
        rf = open(roots, 'rb'); files.append(rf)
        cf = open(codes, 'rb'); files.append(cf)
        rm = mmap.mmap(rf.fileno(), 0, access=mmap.ACCESS_READ) if n else None
        cm = mmap.mmap(cf.fileno(), 0, access=mmap.ACCESS_READ) if n else None
        maps.extend(x for x in (rm, cm) if x is not None)
        def root_at(i): return U32.unpack_from(rm, 4 * i)[0]
        previous = -1
        positions = {}
        for i in range(n):
            root = root_at(i)
            if root <= previous or root in seed_ids or cm[i] not in range(17, 23):
                raise ValueError('invalid, duplicate, unsorted or mainland assignment')
            previous = root
            positions[root] = i
        seen_f = open(out / 'assignment-seen.partial', 'w+b'); files.append(seen_f)
        seen_bytes = (n + 7) // 8
        seen_f.truncate(seen_bytes)
        seen = mmap.mmap(seen_f.fileno(), seen_bytes) if seen_bytes else None
        if seen is not None: maps.append(seen)
        rows_out = open(out / 'rows.u32le', 'wb'); files.append(rows_out)
        runs_out = open(out / 'runs.u32le', 'wb'); files.append(runs_out)
        rh, dh = hashlib.sha256(), hashlib.sha256()
        def wr(f, h, data):
            f.write(data); h.update(data)
        wr(rows_out, rh, U32.pack(0))
        total = 0; seen_count = 0; seeds_seen = set(); land_cells = 0
        for y in range(height):
            _guard(out, disk_reserve_bytes)
            its = [iter(_components(sources[0].next(), width)),
                   iter(_full(sources[1].next(), width, {1, 17}, 'physical')),
                   iter(_full(sources[2].next(), width, {0, 17, 18, 19, 20, 21, 22}, 'mainland'))]
            current = [next(it) for it in its]
            x = 0; pending = None; pending_end = 0
            encoded_row = bytearray()
            delta_row_active = delta_range is not None and delta_range[2] <= y < delta_range[3]
            lat = delta_rule['grid']['north'] - (y + 0.5) * delta_rule['grid']['step'] if delta_row_active else None
            while x < width:
                end = min(current[0][1], current[1][1], current[2][1])
                # Only split the small Ural scope into cell-sized spans.
                # All other rows and columns retain the original run stream.
                if delta_row_active:
                    dx0, dx1 = delta_range[0], delta_range[1]
                    if x < dx0 < end:
                        end = dx0
                    elif dx0 <= x < dx1:
                        end = min(end, x + 1)
                root, physical, seed = current[0][2], current[1][2], current[2][2]
                if (root is not None) != (physical == 17):
                    raise ValueError('physical/component coverage mismatch at row ' + str(y))
                if root is None:
                    if seed != 0: raise ValueError('mainland seed on water')
                    code = 0
                elif root in seed_ids:
                    if seed == 0: raise ValueError('mainland seed gap')
                    seeds_seen.add(root); code = seed
                else:
                    if seed != 0: raise ValueError('mainland seed overlaps non-mainland component')
                    i = positions.get(root)
                    if i is None:
                        raise ValueError('component has no assignment: ' + str(root))
                    code = cm[i]
                    byte, bit = divmod(i, 8)
                    if not seen[byte] & (1 << bit):
                        seen[byte] |= 1 << bit; seen_count += 1
                if delta_row_active and delta_range[0] <= x < delta_range[1] and physical == 17:
                    if code not in (delta_rule['europe_code'], delta_rule['asia_code']):
                        delta_totals['other_land_labels'] += 1
                        raise ValueError('non-Europe/Asia land label in Ural delta scope')
                    lon = delta_rule['grid']['west'] + (x + 0.5) * delta_rule['grid']['step']
                    side_code = classify_cell(delta_rule, lon, lat)
                    if side_code is None:
                        raise ValueError('land center fell outside active Ural delta scope')
                    delta_totals['land_centers'] += 1
                    if code == delta_rule['europe_code'] and side_code == delta_rule['asia_code']:
                        delta_totals['europe_to_asia'] += 1
                    elif code == delta_rule['asia_code'] and side_code == delta_rule['europe_code']:
                        delta_totals['asia_to_europe'] += 1
                    code = side_code
                if code: land_cells += end - x
                if pending is not None and code != pending:
                    encoded_row.extend(PAIR.pack(pending_end, pending)); total += 1
                pending = code; pending_end = end; x = end
                for i in range(3):
                    if current[i][1] == x:
                        current[i] = next(its[i], None)
            if any(v is not None for v in current): raise ValueError('row extends past width')
            encoded_row.extend(PAIR.pack(pending_end, pending)); total += 1
            if total > MAX_U32: raise ValueError('output run count exceeds u32')
            wr(runs_out, dh, encoded_row)
            wr(rows_out, rh, U32.pack(total))
        for source in sources: source.finish()
        if seeds_seen != seed_ids: raise ValueError('missing designated mainland roots')
        if seen_count != n: raise ValueError('unused assignment roots')
        _guard(out, disk_reserve_bytes)
        for f in (rows_out, runs_out): f.flush(); os.fsync(f.fileno())
        report = {'schema': 'streamed-land-rle-research-v1', 'status': 'complete',
                  'width': width, 'height': height, 'runs': total,
                  'land_cells': land_cells, 'assigned_roots': seen_count,
                  'mainland_roots': sorted(seed_ids), 'rows_sha256': rh.hexdigest(),
                  'runs_sha256': dh.hexdigest()}
        if delta_rule is not None:
            report['ural_delta'] = {
                'schema': URAL_DELTA_SCHEMA,
                'revision': delta_rule['revision'],
                'boundary_id': delta_rule['boundary_id'],
                'boundary_sha256': delta_rule['boundary_sha256'],
                'route_id': delta_rule['route_id'],
                'route_sha256': delta_rule['route_sha256'],
                'scope_bounds': delta_rule['scope_bounds'],
                'europe_code': delta_rule['europe_code'],
                'asia_code': delta_rule['asia_code'],
                'counts': delta_totals,
                'status': 'applied-to-land-cell-centers',
            }
        if seen is not None: seen.flush(); seen.close(); maps.remove(seen)
        seen_f.close(); files.remove(seen_f)
        tmp = out / 'report.json.partial'
        with open(tmp, 'x', encoding='utf-8') as f:
            json.dump(report, f, sort_keys=True, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, out / 'report.json')
        try: os.unlink(out / 'assignment-seen.partial')
        except OSError: pass
        return report
    finally:
        for m in reversed(maps): m.close()
        for f in reversed(files): f.close()
        for source in sources: source.close()
