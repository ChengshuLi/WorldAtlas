#!/usr/bin/env python3
"""Compose a staged full V7 grid from independently generated water-assignment layers.

Inputs are immutable V2, V6 (read for land values only), and the physical mask.
Water assignments arrive as row/span JSONL tiles, keyed by semantic rule/member IDs.
This tool never publishes and never writes any source input.
"""
from __future__ import annotations
import argparse, gzip, hashlib, heapq, json, os
from collections import defaultdict
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exclusive_outputs import create_binary_exclusive, create_directory_exclusive, create_gzip_text_exclusive, create_text_exclusive, create_run_directory, write_json_exclusive
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
    if m.get('schema') not in ('worldatlas-full-water-assignment-tiles-v1',
                               'worldatlas-land-provenance-tiles-v1'):
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
                    if role == 'land_provenance':
                        fr = int(s.get('from_code', -1)); to = int(s.get('to_code', code))
                        owner = s.get('member_id') or s.get('source_member_id')
                        rule = s.get('rule_id', 'inherited-v6-land-exception')
                        if not (17 <= fr <= 22 and 17 <= to <= 22 and fr != to and owner):
                            raise ValueError(f"invalid land provenance span: {s}")
                        yield (y, x0, x1, to, rule, owner, fr, to)
                    else:
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


def v2_diff_identity(rule, member, from_code, to_code):
    """Give fresh-ocean changes honest pairwise source/target identities.

    The seed-fill layer assigns each residual cell by its resulting ocean, not
    by a particular divider arc. When that result changes a V2 water code,
    attribute the V2→V7 exception to the old/new code pair. This avoids
    implying that a changed cell came from one specific arc when the source
    only supports the four-ocean partition as a whole.
    """
    if (rule == 'fresh-ocean-seed-floodfill-v1' and
            1 <= int(from_code) <= 10 and 7 <= int(to_code) <= 10 and
            int(from_code) != int(to_code)):
        return ('fresh-ocean-seed-partition-reassignment-v1',
                f'ocean-repartition-v2-{int(from_code)}-to-v7-{int(to_code)}')
    return rule, member


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True, help='JSON plan with V2/V6/physical RLE paths and water/land layer manifests')
    ap.add_argument('--out', required=True, help='new isolated output directory outside the input tree')
    ap.add_argument('--input-root', required=True, help='root of the extracted recovery inputs')
    ap.add_argument('--row-start', type=int, default=0); ap.add_argument('--row-end', type=int, default=H)
    args = ap.parse_args()
    out = Path(args.out).resolve(); input_root = Path(args.input_root).resolve()
    if not input_root.is_dir(): raise ValueError('input root must be an existing directory')
    if out.is_relative_to(input_root) or input_root.is_relative_to(out):
        raise ValueError('output must be outside the input tree')
    create_directory_exclusive(out)
    y0, y1 = args.row_start, args.row_end
    if not 0 <= y0 < y1 <= H: raise ValueError('invalid row range')
    plan_path = Path(args.plan).resolve(); plan = json.loads(plan_path.read_text())
    if plan.get('schema') != 'worldatlas-v7-full-grid-composition-plan-v1': raise ValueError('wrong plan schema')
    if plan.get('grid', {}).get('width') != W or plan.get('grid', {}).get('height') != H: raise ValueError('plan grid mismatch')
    rles = {}
    for key in ('physical', 'v2', 'v6'):
        ent = plan['rle_inputs'][key]; rp = resolve_input(ent['rows_path'], plan_path.parent, input_root); up = resolve_input(ent['runs_path'], plan_path.parent, input_root)
        if sha256(rp) != ent['rows_sha256'] or sha256(up) != ent['runs_sha256']:
            raise ValueError(f'{key} RLE hash mismatch')
        rles[key] = open_validated_rle(rp, up, key)
    layers=[]
    for ent in plan.get('water_layers', []):
        mp, m = read_pinned_manifest(ent, plan_path, input_root); m['_tiles'] = m['tiles'];
        layers.append((ent, m))
    for ent, _ in layers:
        if not isinstance(ent.get('priority'), int): raise ValueError('each water layer needs explicit integer priority')
    lp = plan.get('land_provenance')
    land_cursor = None
    if lp:
        mp, m = read_pinned_manifest(lp, plan_path, input_root); m['_tiles'] = m['tiles']
        land_cursor = RowCursor(m, y0, y1, 'land_provenance')
    cursors = [(ent, RowCursor(m, y0, y1, 'water')) for ent,m in layers]
    pr, pu = rles['physical']; v2r, v2u = rles['v2']; v6r, v6u = rles['v6']
    raw_rows = out/'rows.u32le'; raw_runs = out/'runs.u32le'; diffp = out/'v2-diff-spans.jsonl.gz'
    counts = defaultdict(int); delta = defaultdict(lambda: {'cells':0,'intervals':0,'transitions':defaultdict(int)})
    conflict_cells=0; runs_written=0; changed_cells=0; changed_intervals=0; physical_water=0; assigned_water=0
    with create_binary_exclusive(raw_rows) as yf, create_binary_exclusive(raw_runs) as rf, create_gzip_text_exclusive(diffp,encoding='utf8') as df:
        yf.write(np.asarray([0],dtype='<u4').tobytes())
        for y in range(y0,y1):
            pe,pv = rle_row(pr,pu,y); v6e,v6v = rle_row(v6r,v6u,y); v2e,v2v = rle_row(v2r,v2u,y)
            pe=np.asarray(pe,dtype=np.uint32);pv=np.asarray(pv,dtype=np.uint32);v6e=np.asarray(v6e,dtype=np.uint32);v6v=np.asarray(v6v,dtype=np.uint32);v2e=np.asarray(v2e,dtype=np.uint32);v2v=np.asarray(v2v,dtype=np.uint32)
            for name, ends, values in (('physical', pe, pv), ('v2', v2e, v2v), ('v6', v6e, v6v)):
                validate_rle_row(ends, values, name, y)
            candidate_spans=[]
            for ent,cur in cursors:
                ss=cur.take(y)
                candidate_spans.extend(add_layer_identity(
                    ss, int(ent['priority']), str(ent.get('layer_id', ent['manifest_path'])),
                    set(ent.get('overrides', []))))
            assignments, conflicts = choose_assignments(candidate_spans,y,pe,pv)
            conflict_cells += sum(b-a for a,b in {(a,b) for a,b,_,_ in conflicts})
            land_spans=land_cursor.take(y) if land_cursor else []
            # All relevant boundaries, including source identity and old V2, define atomic intervals.
            cuts={0,W};cuts.update(map(int,pe));cuts.update(map(int,v6e));cuts.update(map(int,v2e))
            for a,b,_,_,_ in assignments: cuts.add(a);cuts.add(b)
            for s in land_spans: cuts.update((s[1],s[2]))
            xx=np.asarray(sorted(cuts),dtype=np.uint32); starts=xx[:-1]; ends=xx[1:]
            phys=row_code_at(pe,pv,starts).astype(np.uint8); old=row_code_at(v2e,v2v,starts).astype(np.uint8); land=row_code_at(v6e,v6v,starts).astype(np.uint8)
            outcodes=np.empty(len(starts),dtype=np.uint8); owners=[None]*len(starts); rules=[None]*len(starts)
            ai=0; li=0
            for j,x in enumerate(starts.tolist()):
                z=int(ends[j])
                while ai<len(assignments) and assignments[ai][1] <= x: ai+=1
                assign=assignments[ai] if ai<len(assignments) and assignments[ai][0] <= x < assignments[ai][1] else None
                while li<len(land_spans) and land_spans[li][2] <= x: li+=1
                lspan=land_spans[li] if li<len(land_spans) and land_spans[li][1] <= x < land_spans[li][2] else None
                if lspan is not None and phys[j] != 17:
                    raise ValueError(f"land provenance overlaps physical water/nonland row={y} x={x}:{z}")
                if phys[j] == 17:
                    if assign is not None: raise ValueError(f"water-layer assignment on land row={y} x={x}:{z}")
                    if not 17 <= land[j] <= 22: raise ValueError(f"unassigned land code row={y} x={x}:{z} code={land[j]}")
                    outcodes[j]=land[j]
                    if lspan is not None:
                        if lspan[6] != int(old[j]) or lspan[7] != int(land[j]):
                            raise ValueError(f"land owner from/to mismatch row={y} x={x}:{z}")
                        owners[j],rules[j]=lspan[5],lspan[4]
                elif phys[j] == 1:
                    physical_water += z-x
                    if assign is None: raise ValueError(f"unassigned physical water row={y} x={x}:{z}")
                    outcodes[j]=assign[2];owners[j],rules[j]=assign[4],assign[3];assigned_water += z-x
                    if not 1 <= outcodes[j] <= 10: raise ValueError(f"invalid water code row={y} x={x}:{z}")
                else:
                    raise ValueError(f"unexpected physical mask code {phys[j]} at row={y} x={x}:{z}")
            lens=(ends-starts).astype(np.uint64)
            for c in np.unique(outcodes): counts[int(c)] += int(lens[outcodes==c].sum())
            # Emit candidate RLE, coalescing adjacent equal codes.
            mask=np.r_[True,outcodes[1:]!=outcodes[:-1]]
            vstarts=np.flatnonzero(mask); vend_idx=np.r_[vstarts[1:],len(outcodes)]
            rowvals=outcodes[vstarts].astype('<u4'); rowends=ends[vend_idx-1].astype('<u4')
            inter=np.column_stack((rowends,rowvals)).astype('<u4').ravel()
            rf.write(inter.tobytes()); runs_written += len(rowvals)
            yf.write(np.asarray([runs_written],dtype='<u4').tobytes())
            # Emit V2 changes with owner attribution. Each atomic segment is already identity-stable.
            for j in np.flatnonzero(outcodes != old):
                a=int(starts[j]);b=int(ends[j]);fr=int(old[j]);to=int(outcodes[j]);owner=owners[j];rule=rules[j]
                if not owner or not rule: raise ValueError(f"changed V2 cell lacks source owner row={y} x={a}:{b} {fr}->{to}")
                rule, owner = v2_diff_identity(rule, owner, fr, to)
                rec={'row':y,'start':a,'end':b,'from_code':fr,'to_code':to,'rule_id':rule,'member_id':owner}
                df.write(json.dumps(rec,separators=(',',':'))+'\n')
                changed_cells += b-a;changed_intervals += 1
                d=delta[owner];d['cells']+=b-a;d['intervals']+=1;d['transitions'][f'{fr}->{to}']+=b-a
    report={'schema':'worldatlas-v7-full-grid-composition-audit-v1','status':'staged-not-published',
        'plan_sha256':sha256(plan_path),'grid':GRID,'row_range':[y0,y1],
        'input_rle_sha256':{k:{'rows':plan['rle_inputs'][k]['rows_sha256'],'runs':plan['rle_inputs'][k]['runs_sha256']} for k in ('physical','v2','v6')},
        'input_layer_manifests':[{'id':ent.get('layer_id'),'manifest_sha256':sha256(resolve_input(ent['manifest_path'], plan_path.parent, input_root)),'priority':ent['priority']} for ent,_ in layers],
        'output':{'rows_sha256':sha256(raw_rows),'runs_sha256':sha256(raw_runs),'v2_diff_spans_sha256':sha256(diffp),'rle_run_count':runs_written},
        'counts_by_code':{str(k):v for k,v in sorted(counts.items())},'physical_water_cells':physical_water,'assigned_water_cells':assigned_water,
        'v2_diff_cells':changed_cells,'v2_diff_intervals':changed_intervals,'resolved_overlap_cells':conflict_cells,
        'delta_owner_summary':{k:{'cells':v['cells'],'intervals':v['intervals'],'transitions':dict(sorted(v['transitions'].items()))} for k,v in sorted(delta.items())},
        'v6_water_label_inheritance':'none; V6 codes read only where physical mask is land',
        'immutable_inputs_written':False}
    write_json_exclusive(out/'composition-audit.json',report)
    print(json.dumps(report,indent=2))

if __name__ == '__main__': main()
