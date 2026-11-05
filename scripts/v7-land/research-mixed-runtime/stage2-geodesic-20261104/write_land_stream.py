"""Stream a validated, full-width research land RLE; no grid-sized arrays.

Inputs: row offsets are H+1 little-endian u32 record counts; component runs
are (start, end, root) u32, physical and mainland runs are (end, code) u32.
Physical codes are 1 water / 17 land. Mainland codes are 0 or 17..22.
Assignments are sorted unique roots u32 and one u8 code per root. Output
files are created in a new directory. A report exists only after success.
"""
import hashlib
import json
import mmap
import os
from pathlib import Path
import shutil
import struct

U32 = struct.Struct('<I')
PAIR = struct.Struct('<II')
TRIPLE = struct.Struct('<III')
MAX_U32 = (1 << 32) - 1


def _available_kib():
    with open('/proc/meminfo', encoding='ascii') as f:
        for line in f:
            if line.startswith('MemAvailable:'):
                return int(line.split()[1])
    raise RuntimeError('MemAvailable unavailable')


def _guard(directory, disk_reserve_bytes, min_mem_available_kib, extra=0):
    if shutil.disk_usage(directory).free < disk_reserve_bytes + extra:
        raise RuntimeError('disk reserve guard')
    if min_mem_available_kib and _available_kib() < min_mem_available_kib:
        raise RuntimeError('memory guard')


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
        end = U32.unpack(_read_exact(self.rows, 4))[0]
        if end < self.pos or end > self.count:
            raise ValueError('invalid row offset')
        n = end - self.pos
        self.pos = end
        for _ in range(n):
            yield self.record.unpack(_read_exact(self.runs, self.record.size))

    def finish(self):
        if self.pos != self.count or self.runs.read(1) or self.rows.read(1):
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
                      disk_reserve_bytes=1 << 30, min_mem_available_kib=1 << 20):
    """Write rows.u32le, runs.u32le and an atomic report.json; return report.

    Run streams are consumed one row at a time, with at most one record per
    input held during the boundary sweep. Roots/codes are memory-mapped, as is
    the on-disk assignment-seen bitmap. A failed build leaves partial files.
    """
    if type(width) is not int or not 0 < width <= MAX_U32 or type(height) is not int or not 0 < height <= MAX_U32:
        raise ValueError('invalid grid dimensions')
    if type(disk_reserve_bytes) is not int or disk_reserve_bytes < 0 or type(min_mem_available_kib) is not int or min_mem_available_kib < 0:
        raise ValueError('invalid resource guard')
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
    _guard(out.parent, disk_reserve_bytes, min_mem_available_kib, estimate)
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
        for i in range(n):
            root = root_at(i)
            if root <= previous or root in seed_ids or cm[i] not in range(17, 23):
                raise ValueError('invalid, duplicate, unsorted or mainland assignment')
            previous = root
        seen_f = open(out / 'assignment-seen.partial', 'w+b'); files.append(seen_f)
        seen_bytes = (n + 7) // 8
        seen_f.truncate(seen_bytes)
        seen = mmap.mmap(seen_f.fileno(), seen_bytes) if seen_bytes else None
        if seen is not None: maps.append(seen)
        def find(root):
            lo, hi = 0, n
            while lo < hi:
                m = (lo + hi) // 2
                if root_at(m) < root: lo = m + 1
                else: hi = m
            if lo == n or root_at(lo) != root:
                raise ValueError('component has no assignment: ' + str(root))
            return lo
        rows_out = open(out / 'rows.u32le', 'wb'); files.append(rows_out)
        runs_out = open(out / 'runs.u32le', 'wb'); files.append(runs_out)
        rh, dh = hashlib.sha256(), hashlib.sha256()
        def wr(f, h, data):
            f.write(data); h.update(data)
        wr(rows_out, rh, U32.pack(0))
        total = 0; seen_count = 0; seeds_seen = set(); land_cells = 0
        for y in range(height):
            _guard(out, disk_reserve_bytes, min_mem_available_kib)
            its = [iter(_components(sources[0].next(), width)),
                   iter(_full(sources[1].next(), width, {1, 17}, 'physical')),
                   iter(_full(sources[2].next(), width, {0, 17, 18, 19, 20, 21, 22}, 'mainland'))]
            current = [next(it) for it in its]
            x = 0; pending = None; pending_end = 0
            while x < width:
                end = min(v[1] for v in current)
                root, physical, seed = (v[2] for v in current)
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
                    i = find(root); code = cm[i]
                    byte, bit = divmod(i, 8)
                    if not seen[byte] & (1 << bit):
                        seen[byte] |= 1 << bit; seen_count += 1
                if code: land_cells += end - x
                if pending is not None and code != pending:
                    wr(runs_out, dh, PAIR.pack(pending_end, pending)); total += 1
                pending = code; pending_end = end; x = end
                for i in range(3):
                    if current[i][1] == x:
                        current[i] = next(its[i], None)
            if any(v is not None for v in current): raise ValueError('row extends past width')
            wr(runs_out, dh, PAIR.pack(pending_end, pending)); total += 1
            if total > MAX_U32: raise ValueError('output run count exceeds u32')
            wr(rows_out, rh, U32.pack(total))
        for source in sources: source.finish()
        if seeds_seen != seed_ids: raise ValueError('missing designated mainland roots')
        if seen_count != n: raise ValueError('unused assignment roots')
        _guard(out, disk_reserve_bytes, min_mem_available_kib)
        for f in (rows_out, runs_out): f.flush(); os.fsync(f.fileno())
        report = {'schema': 'streamed-land-rle-research-v1', 'status': 'complete',
                  'width': width, 'height': height, 'runs': total,
                  'land_cells': land_cells, 'assigned_roots': seen_count,
                  'mainland_roots': sorted(seed_ids), 'rows_sha256': rh.hexdigest(),
                  'runs_sha256': dh.hexdigest()}
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
