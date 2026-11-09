#!/usr/bin/env python3
"""Read and combine the pinned water-assignment layers used by the V8 build."""
from __future__ import annotations
import gzip, hashlib, heapq, json
from collections import defaultdict
from pathlib import Path
import numpy as np

W, H = 131072, 54614
STEP = 360.0 / W
GRID = {"width": W, "height": H, "longitude_origin_center": -180 + STEP/2,
        "latitude_origin_center": 90 - STEP/2, "angular_step_deg": STEP,
        "row_convention": "north-to-south; cell centers; half-open [start,end) x spans"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def resolve_input(value, base: Path, input_root: Path) -> Path:
    """Resolve a relative or absolute input only within the supplied root."""
    root = input_root.resolve()
    value = Path(value)
    candidate = value if value.is_absolute() else base / value
    candidate = candidate.resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f'input escapes recovery root: {candidate}')
    return candidate


def read_pinned_manifest(entry, plan_path: Path, input_root: Path):
    expected = entry.get('manifest_sha256')
    if not isinstance(expected, str) or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
        raise ValueError('manifest_sha256 must be a lowercase SHA-256 digest')
    path = resolve_input(entry['manifest_path'], plan_path.parent, input_root)
    if sha256(path) != expected:
        raise ValueError(f'manifest hash mismatch: {path}')
    return path, read_manifest(path, input_root)

def read_manifest(path: Path, input_root: Path):
    m = json.loads(path.read_text())
    if m.get('schema') != 'worldatlas-full-water-assignment-tiles-v1':
        raise ValueError(f"unsupported tile manifest schema in {path}: {m.get('schema')}")
    if str(m.get('status', '')).lower() in ('active', 'running', 'partial', 'failed'):
        raise ValueError(f"tile manifest is not a completed candidate: {path} status={m.get('status')}")
    g = m.get('grid', {})
    if int(g.get('width', -1)) != W or int(g.get('height', -1)) != H:
        raise ValueError(f"grid mismatch in {path}")
    for key, value in GRID.items():
        if key not in g: continue
        if key == 'row_convention':
            text = str(g[key]).lower()
            if 'north-to-south' not in text or 'half-open' not in text:
                raise ValueError(f"grid coordinate contract mismatch {key} in {path}: {g[key]!r}")
        elif g[key] != value:
            raise ValueError(f"grid coordinate contract mismatch {key} in {path}: {g[key]!r}")
    tiles = m.get('tiles')
    if not isinstance(tiles, list) or not tiles:
        raise ValueError(f"manifest has no tiles: {path}")
    for t in tiles:
        pinfo = t.get('span_file', t.get('file', t))
        if isinstance(pinfo, dict):
            rel = pinfo.get('path')
            digest = pinfo.get('sha256') or pinfo.get('span_sha256')
        elif isinstance(pinfo, str):
            rel = pinfo
            digest = t.get('span_sha256') or t.get('sha256')
        else:
            rel = None; digest = None
        if not rel or not digest:
            raise ValueError(f"tile missing path/hash in {path}: {t}")
        fp = resolve_input(rel, path.parent, input_root)
        if not fp.is_file() or sha256(fp) != digest:
            raise ValueError(f"tile missing or hash mismatch: {fp}")
        yb = t.get('core_rows', t.get('row_bounds', [t.get('row_start', t.get('y_start')),
                                                        t.get('row_end_exclusive', t.get('y_end_exclusive'))]))
        xb = t.get('core_cols', t.get('col_bounds', [t.get('x_start'), t.get('x_end_exclusive')]
                                                    if t.get('x_start') is not None else None))
        if not isinstance(yb, list) or len(yb) != 2 or not (0 <= int(yb[0]) < int(yb[1]) <= H):
            raise ValueError(f"bad core row bounds in {path}: {t}")
        if xb is not None and (not isinstance(xb, list) or len(xb) != 2 or not (0 <= int(xb[0]) < int(xb[1]) <= W)):
            raise ValueError(f"bad core col bounds in {path}: {t}")
        t['_path'] = fp
        t['_sha256'] = digest
        t['_rows'] = [int(yb[0]), int(yb[1])]
        t['_cols'] = None if xb is None else [int(xb[0]), int(xb[1])]
    m['_sparse_rows_allowed'] = m.get('coverage', {}).get('complete') is True
    return m


def open_text(path: Path):
    return gzip.open(path, 'rt', encoding='utf8') if path.suffix == '.gz' else path.open('rt', encoding='utf8')


def tile_spans(tile, y0, y1, role, sparse_rows_allowed=False):
    """Validate monotone tile rows and stream span tuples in selected row range."""
    arow, brow = tile['_rows']; expected_row = arow; last_row = arow - 1
    last_end = -1
    with open_text(tile['_path']) as f:
        for ln, line in enumerate(f, 1):
            if not line.strip():
                continue
            rec = json.loads(line)
            y = int(rec.get('row', -1))
            if sparse_rows_allowed:
                if y < last_row:
                    raise ValueError(f"out-of-order sparse tile row in {tile['_path']} line {ln}: previous {last_row}, got {y}")
            elif y < last_row or (y != last_row and y != expected_row):
                raise ValueError(f"missing/duplicate/out-of-order tile row in {tile['_path']} line {ln}: expected {expected_row}, got {y}")
            if not arow <= y < brow:
                raise ValueError(f"row {y} outside tile bounds in {tile['_path']} line {ln}")
            if y != last_row:
                last_row, last_end = y, -1
                expected_row = y + 1
            for s in rec.get('spans', []):
                x0 = int(s.get('start', s.get('x_start', -1)))
                x1 = int(s.get('end', s.get('x_end_exclusive', -1)))
                code = int(s.get('code', s.get('to_code', -1)))
                if not (0 <= x0 < x1 <= W) or x0 < last_end:
                    raise ValueError(f"bad/unsorted span in {tile['_path']} line {ln}: {s}")
                if tile['_cols'] is not None and not (tile['_cols'][0] <= x0 < x1 <= tile['_cols'][1]):
                    raise ValueError(f"span escapes tile columns in {tile['_path']} line {ln}: {s}")
                if y0 <= y < y1:
                    owner = s.get('member_id') or s.get('source_member_id')
                    rule = s.get('rule_id')
                    if not (1 <= code <= 10 and owner and rule):
                        raise ValueError(f"water assignment lacks a valid code/rule/member: {s}")
                    yield (y, x0, x1, code, rule, owner, None, None)
                last_end = x1
    if not sparse_rows_allowed and (expected_row != brow or last_row != brow - 1):
        raise ValueError(f"tile row record count mismatch in {tile['_path']}: ended at {expected_row}, expected {brow}")
    # Empty trailing rows have no spans; manifest row bounds provide coverage metadata.


def layer_rows(manifest, y0, y1, role):
    """K-way merge tile streams; return an iterator of (row, spans)."""
    streams = [tile_spans(t, y0, y1, role, manifest.get('_sparse_rows_allowed', False)) for t in manifest['_tiles']]
    merged = heapq.merge(*streams, key=lambda z: (z[0], z[1], z[2]))
    cur_y = None; items = []
    for item in merged:
        if cur_y is None: cur_y = item[0]
        if item[0] != cur_y:
            yield cur_y, items
            cur_y, items = item[0], []
        items.append(item)
    if cur_y is not None:
        yield cur_y, items


class RowCursor:
    def __init__(self, manifest, y0, y1, role):
        self.y0, self.y1 = y0, y1
        self.it = iter(layer_rows(manifest, y0, y1, role))
        self.next = next(self.it, None)
    def take(self, y):
        if self.next is not None and self.next[0] < y:
            raise ValueError(f"layer row skipped: saw {self.next[0]}, expected {y}")
        if self.next is not None and self.next[0] == y:
            result = self.next[1]; self.next = next(self.it, None); return result
        return []


def rle_row(rows, runs, y):
    a, b = int(rows[y]), int(rows[y+1])
    q = runs[2*a:2*b]
    return q[0::2], q[1::2]


def row_code_at(ends, vals, xs):
    return vals[np.searchsorted(ends, xs, side='right')]


def assignment_codes(assignments, xs, columns=None):
    """Return the winning assignment code and presence mask at RLE starts.

    ``choose_assignments`` returns sorted, disjoint half-open spans. Using one
    vectorized search per row avoids a Python assignment scan for every RLE
    segment in the full-grid prefill and final composition passes.
    """
    xs = np.asarray(xs)
    codes = np.zeros(xs.shape, dtype=np.uint8)
    present = np.zeros(xs.shape, dtype=bool)
    if not xs.size or (columns is None and not assignments):
        return codes, present
    starts, stops, values = columns if columns is not None else assignment_arrays(assignments)
    if not starts.size:
        return codes, present
    idx = np.searchsorted(starts, xs, side='right') - 1
    present = idx >= 0
    safe = np.maximum(idx, 0)
    present &= xs < stops[safe]
    codes[present] = values[safe[present]]
    return codes, present


def assignment_arrays(assignments):
    """Return contiguous numeric assignment columns for vectorized row work."""
    if not assignments:
        empty = np.empty(0, dtype=np.uint32)
        return empty, empty, np.empty(0, dtype=np.uint8)
    starts = np.fromiter((int(a[0]) for a in assignments), dtype=np.uint32, count=len(assignments))
    stops = np.fromiter((int(a[1]) for a in assignments), dtype=np.uint32, count=len(assignments))
    values = np.fromiter((int(a[2]) for a in assignments), dtype=np.uint8, count=len(assignments))
    if np.any(starts >= stops) or np.any(starts[1:] < stops[:-1]):
        raise ValueError('assignments must be sorted, non-overlapping half-open spans')
    return starts, stops, values


def merge_row_cuts(*ends, assignments=(), extra_bounds=(), assignment_columns=None):
    """Build sorted unique row breakpoints using NumPy rather than Python sets.

    Full-grid RLE composition can encounter hundreds of millions of row
    breakpoints. Updating and sorting a Python set converts every uint32 run
    endpoint to a Python int, so use NumPy's native sort/unique path instead.
    All emitted cut positions remain the same half-open boundaries.
    """
    parts = [np.asarray([0, W], dtype=np.uint32)]
    parts.extend(np.asarray(x, dtype=np.uint32) for x in ends)
    if assignments or assignment_columns is not None:
        starts, stops, _ = assignment_columns if assignment_columns is not None else assignment_arrays(assignments)
        bounds = np.empty(starts.size + stops.size, dtype=np.uint32)
        bounds[0::2] = starts
        bounds[1::2] = stops
        parts.append(bounds)
    if len(extra_bounds):
        parts.append(np.asarray(extra_bounds, dtype=np.uint32))
    return np.unique(np.concatenate(parts))


def choose_assignments(spans, y, physical_ends, physical_vals):
    """Sweep only genuine overlap groups, retaining every source breakpoint.

    Isolated half-open spans have one unambiguous winner. Batched physical
    lookups avoid creating a NumPy query and event dictionary for each of the
    millions of ordinary coastal spans. Overlaps retain the full policy sweep.
    """
    if not spans:
        return [], []
    spans = sorted(spans, key=lambda z: (z[1], z[2], z[5]))
    starts = np.fromiter((s[1] for s in spans), dtype=np.uint32, count=len(spans))
    stops = np.fromiter((s[2] for s in spans), dtype=np.uint32, count=len(spans))
    groups = np.flatnonzero(np.r_[True, starts[1:] >= np.maximum.accumulate(stops)[:-1]])
    sizes = np.diff(np.r_[groups, len(spans)])
    overlapping = np.repeat(sizes > 1, sizes)
    isolated = np.flatnonzero(~overlapping)
    values = row_code_at(physical_ends, physical_vals, starts[isolated])
    bad = np.flatnonzero(values != 1)
    if len(bad):
        at = int(bad[0]); i = int(isolated[at]); x, z = int(starts[i]), int(stops[i])
        raise ValueError(f"water assignment overlaps physical land/nonwater row={y} x={x}:{z} (physical={int(values[at])})")
    if not np.any(overlapping):
        return [(s[1], s[2], s[3], s[4], s[5]) for s in spans], []
    vectorized = two_priority_assignments(spans, starts, stops, y, physical_ends, physical_vals)
    if vectorized is not None:
        return vectorized
    out = [(s[1], s[2], s[3], s[4], s[5]) for i, s in enumerate(spans) if not overlapping[i]]
    selected = [s for i, s in enumerate(spans) if overlapping[i]]
    resolved, conflicts = sweep_overlapping_assignments(selected, y, physical_ends, physical_vals)
    out.extend(resolved)
    out.sort(key=lambda s: s[0])
    return out, conflicts


def two_priority_assignments(spans, starts, stops, y, physical_ends, physical_vals):
    """Overlay two internally disjoint priority bands using interval lookups.

    This structural fast path is independent of layer names or geography. If
    either band overlaps itself, the general sweep retains all duplicate and
    same-priority rejection behavior. Every source endpoint remains a cut.
    """
    if any(len(s) < 11 or not isinstance(s[9], str) or not isinstance(s[10], (set, frozenset)) for s in spans):
        return None
    priorities = [int(s[8]) for s in spans]
    levels = sorted(set(priorities))
    if len(levels) != 2:
        return None
    groups = [np.flatnonzero(np.fromiter((p == level for p in priorities), dtype=bool, count=len(spans))) for level in levels]
    if any(np.any(starts[ids][1:] < stops[ids][:-1]) for ids in groups):
        return None
    cuts = np.unique(np.r_[starts, stops]); xx, zz = cuts[:-1], cuts[1:]
    owners = []
    for ids in groups:
        ix = np.searchsorted(starts[ids], xx, side='right') - 1
        safe = np.maximum(ix, 0)
        owners.append(np.where((ix >= 0) & (xx < stops[ids[safe]]), ids[safe], -1))
    lower, higher = owners; winner = np.where(higher >= 0, higher, lower)
    active = winner >= 0; both = (lower >= 0) & (higher >= 0)
    # Group equal permission sets, including distinct set objects supplied by
    # different parent layers. One check then covers many short higher/lower
    # intervals without a Python loop or full-row scan per physical fragment.
    layer_ids = np.fromiter((s[9] for s in spans), dtype=object, count=len(spans))
    by_object = {}; permission_groups = {}; permission_ids = np.empty(len(spans), dtype=np.int64)
    for i, span in enumerate(spans):
        key = id(span[10])
        if key not in by_object:
            allowed = frozenset(span[10])
            by_object[key] = permission_groups.setdefault(allowed, len(permission_groups))
        permission_ids[i] = by_object[key]
    higher_permission = permission_ids[np.maximum(higher, 0)]
    for allowed, group in permission_groups.items():
        selected = both & (higher_permission == group)
        if not np.any(selected):
            continue
        forbidden = [layer for layer in np.unique(layer_ids[lower[selected]]) if layer not in allowed]
        if forbidden:
            bad = selected & np.isin(layer_ids[np.maximum(lower, 0)], forbidden)
            i = int(np.flatnonzero(bad)[0]); low, high = int(lower[i]), int(higher[i])
            raise ValueError(f"undeclared priority override row={y} x={int(xx[i])}:{int(zz[i])}: {spans[low][9]} -> {spans[high][9]}")
    values = row_code_at(physical_ends, physical_vals, xx[active])
    if np.any(values != 1):
        at = int(np.flatnonzero(values != 1)[0]); i = int(np.flatnonzero(active)[at])
        raise ValueError(f"water assignment overlaps physical land/nonwater row={y} x={int(xx[i])}:{int(zz[i])} (physical={int(values[at])})")
    out = [(int(xx[i]), int(zz[i]), spans[winner[i]][3], spans[winner[i]][4], spans[winner[i]][5])
           for i in np.flatnonzero(active)]
    conflicts = [(int(xx[i]), int(zz[i]), spans[lower[i]][5], spans[higher[i]][5])
                 for i in np.flatnonzero(both)]
    return out, conflicts


def sweep_overlapping_assignments(spans, y, physical_ends, physical_vals):
    """Resolve sorted overlap groups with the original explicit-priority sweep."""
    events = defaultdict(lambda: [[], []])  # x -> (ending ids, starting ids)
    for i, s in enumerate(spans):
        events[s[1]][1].append(i); events[s[2]][0].append(i)
    cuts = sorted(events)
    physical_codes = row_code_at(physical_ends, physical_vals, np.asarray(cuts[:-1], dtype=np.uint32))
    active = set(); out = []; conflicts = []
    # priority is declared in each tile manifest's parent layer descriptor, inserted by caller.
    priorities = [int(s[8]) if len(s) > 8 else 0 for s in spans]
    for i, x in enumerate(cuts[:-1]):
        ending, starting = events[x]
        for j in ending: active.discard(j)
        for j in starting: active.add(j)
        z = cuts[i+1]
        if z <= x or not active: continue
        # A layer overlap is never silently resolved. The plan must make the precedence explicit.
        maxp = max(priorities[j] for j in active)
        winners = [j for j in active if priorities[j] == maxp]
        if len(winners) > 1:
            sigs = {(spans[j][3], spans[j][4], spans[j][5]) for j in winners}
            if len(sigs) != 1:
                raise ValueError(f"ambiguous same-priority overlap row={y} x={x}:{z}: {sigs}")
            raise ValueError(f"duplicate same-priority assignment overlap row={y} x={x}:{z}: {sigs}")
        winner = spans[winners[0]]
        # Ensure any overlap lost to a higher priority was explicitly allowed by that winner.
        if len(active) > 1:
            for j in active:
                if j == winners[0]: continue
                # The winner may override a lower-priority layer only when its
                # layer descriptor explicitly names that lower-priority layer.
                if spans[j][9] not in winner[10]:
                    raise ValueError(f"undeclared priority override row={y} x={x}:{z}: {spans[j][9]} -> {winner[9]}")
                conflicts.append((x, z, spans[j][5], winner[5]))
        pv = int(physical_codes[i])
        if pv != 1:
            raise ValueError(f"water assignment overlaps physical land/nonwater row={y} x={x}:{z} (physical={pv})")
        out.append((x, z, winner[3], winner[4], winner[5]))
    return out, conflicts


def add_layer_identity(spans, priority, layer_id, overrides):
    return [(*s, priority, layer_id, overrides) for s in spans]


def open_validated_rle(rows_path: Path, runs_path: Path, name: str):
    """Validate the RLE envelope before rows are read or narrowed to uint8."""
    if rows_path.stat().st_size != (H + 1) * 4 or runs_path.stat().st_size % 8:
        raise ValueError(f'{name} invalid RLE size')
    rows = np.memmap(rows_path, dtype='<u4', mode='r')
    runs = np.memmap(runs_path, dtype='<u4', mode='r')
    if (int(rows[0]) != 0 or int(rows[-1]) != len(runs) // 2
            or np.any(rows[1:] <= rows[:-1])):
        raise ValueError(f'{name} invalid RLE offsets')
    return rows, runs


def validate_rle_row(ends, values, name: str, row: int):
    if (not len(ends) or int(ends[0]) == 0 or int(ends[-1]) != W
            or np.any(ends[1:] <= ends[:-1])):
        raise ValueError(f'{name} invalid RLE endpoints on row {row}')
    allowed = (1, 17) if name == 'physical' else tuple(range(1, 11)) + tuple(range(17, 23))
    if np.any(~np.isin(values, allowed)):
        raise ValueError(f'{name} invalid RLE code on row {row}')
