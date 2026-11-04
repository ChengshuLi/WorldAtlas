#!/usr/bin/env python3
"""Compare pinned baseline and V7 grids; write exact, 8-connected land mismatch clusters.

Output is diagnostic SQLite plus a completion manifest, never executable overrides.
All coordinates are row and half-open column intervals on the input grid.
"""
import argparse
import hashlib
import json
import math
import sqlite3
import shutil
import sys
from collections import Counter
from pathlib import Path

import numpy as np

VERSION = 'shared-land-8-connected-wrap-v1'
# Storage encodings for the independent physical stream and unclassified water.
PHYSICAL_WATER, PHYSICAL_LAND, UNCLASSIFIED_WATER = 1, 17, 0


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def pin(spec):
    if set(spec) != {'path', 'sha256'} or not isinstance(spec['path'], str) or not isinstance(spec['sha256'], str):
        raise ValueError('expected {path, sha256} input pin')
    p = Path(spec['path']).resolve(strict=True)
    if digest(p) != spec['sha256']:
        raise ValueError('hash mismatch: ' + str(p))
    return p


def grid(rows, runs, width, height):
    rows = np.memmap(rows, mode='r', dtype='<u4')
    runs = np.memmap(runs, mode='r', dtype='<u4')
    if len(rows) != height + 1 or len(runs) % 2 or int(rows[0]) != 0 or int(rows[-1]) != len(runs) // 2 or np.any(rows[1:] <= rows[:-1]):
        raise ValueError('invalid RLE offsets')
    return rows, runs.reshape(-1, 2)


def row(g, y, width, allowed):
    offsets, pairs = g
    r = pairs[int(offsets[y]):int(offsets[y + 1])]
    ends, codes = r[:, 0], r[:, 1]
    if not len(ends) or int(ends[0]) <= 0 or int(ends[-1]) != width or np.any(ends[1:] <= ends[:-1]) or np.any(~np.isin(codes, list(allowed))):
        raise ValueError(f'invalid grid row {y}')
    return ends, codes


class Components:
    """Disk-backed union-find. RAM usage depends on a row, not global cell count."""
    def __init__(self, db):
        self.db = db
        self.next_id = 1

    def new(self):
        n = self.next_id
        self.next_id += 1
        self.db.execute('INSERT INTO parent VALUES (?, ?)', (n, n))
        return n

    def find(self, n):
        trail = []
        while True:
            p = self.db.execute('SELECT parent FROM parent WHERE id=?', (n,)).fetchone()[0]
            if p == n:
                break
            trail.append(n)
            n = p
        self.db.executemany('UPDATE parent SET parent=? WHERE id=?', ((n, i) for i in trail))
        return n

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.db.execute('UPDATE parent SET parent=? WHERE id=?', (min(a, b), max(a, b)))


def build(config_path, output):
    config_path, output = Path(config_path).resolve(), Path(output).resolve()
    raw = config_path.read_bytes()
    cfg = json.loads(raw)
    keys = {'schema', 'grid', 'candidate_rows', 'candidate_runs', 'reference_rows', 'reference_runs', 'physical_rows', 'physical_runs', 'provenance', 'minimum_free_bytes'}
    if set(cfg) != keys or cfg['schema'] != 'list1-land-clusters-config-v1':
        raise ValueError('invalid config keys or schema')
    if type(cfg['minimum_free_bytes']) is not int or cfg['minimum_free_bytes'] < 0:
        raise ValueError('invalid minimum free space')
    g = cfg['grid']
    if set(g) != {'width', 'height', 'step', 'west', 'north'}:
        raise ValueError('invalid grid')
    w, h = g['width'], g['height']
    if (type(w) is not int or type(h) is not int or w < 1 or h < 1 or g['west'] != -180 or g['north'] != 90 or type(g['step']) not in (int, float) or not math.isfinite(g['step']) or g['step'] != 360 / w or 90 - h * g['step'] < -90 - 1e-8):
        raise ValueError('invalid global grid geometry')
    if not isinstance(cfg['provenance'], dict) or not {'candidate_report', 'reference_audit', 'physical_report', 'decision_snapshot', 'reference_manifest'} <= set(cfg['provenance']):
        raise ValueError('candidate, physical, V7 audit, Neon snapshot and V7 manifest pins required')
    names = ('candidate_rows', 'candidate_runs', 'reference_rows', 'reference_runs', 'physical_rows', 'physical_runs')
    paths = {n: pin(cfg[n]) for n in names}
    provenance = {n: pin(v) for n, v in cfg['provenance'].items()}
    candidate_report = json.loads(provenance['candidate_report'].read_bytes())
    if (candidate_report.get('schema') != 'simple-v2-land-report-v1' or candidate_report.get('status') != 'research-not-published'
        or candidate_report.get('grid') != g
        or candidate_report.get('output_rows_sha256') != cfg['candidate_rows']['sha256']
        or candidate_report.get('output_runs_sha256') != cfg['candidate_runs']['sha256']
        or any(candidate_report.get('inputs', {}).get(n, {}).get('sha256') != cfg[n]['sha256'] for n in ('physical_rows', 'physical_runs'))
        or candidate_report.get('inputs', {}).get('physical_report', {}).get('sha256') != cfg['provenance']['physical_report']['sha256']
        or candidate_report.get('decision_snapshot_sha256') != cfg['provenance']['decision_snapshot']['sha256']):
        raise ValueError('candidate report does not bind grid, outputs and physical inputs')
    physical_report = json.loads(provenance['physical_report'].read_bytes())
    if (physical_report.get('status') != 'candidate-only' or physical_report.get('grid') != g
        or physical_report.get('output_sha256', {}).get('rows.u32le') != cfg['physical_rows']['sha256']
        or physical_report.get('output_sha256', {}).get('runs.u32le') != cfg['physical_runs']['sha256']):
        raise ValueError('physical report does not bind candidate grid and outputs')
    snapshot = json.loads(provenance['decision_snapshot'].read_bytes())
    decision = snapshot.get('decision_revision', {})
    entity_revision = snapshot.get('entity_revision', {})
    status = decision.get('status')
    if (snapshot.get('source') != 'neon-export'
        or (snapshot.get('schema'),status) not in (('worldatlas-geography-decision-draft-evidence-v1','draft'),('worldatlas-geography-decision-export-v1','accepted'))
        or not decision.get('id') or entity_revision.get('id') != decision.get('entity_revision') or entity_revision.get('status') != status):
        raise ValueError('invalid decision snapshot metadata')
    reference_manifest = json.loads(provenance['reference_manifest'].read_bytes())
    version = reference_manifest.get('versions', {}).get('v7', {})
    if (reference_manifest.get('west') != g['west'] or reference_manifest.get('north') != g['north'] or reference_manifest.get('step') != g['step']
        or version.get('width') != w or version.get('height') != h
        or version.get('local_grid', {}).get('rows_sha256') != cfg['reference_rows']['sha256']
        or version.get('local_grid', {}).get('runs_sha256') != cfg['reference_runs']['sha256']):
        raise ValueError('V7 category manifest grid or output binding mismatch')
    entities = snapshot.get('entities')
    if not isinstance(entities,list) or not entities: raise ValueError('missing decision entities')
    entity_names = {}
    for entity in entities:
        if (not isinstance(entity,dict) or type(entity.get('id')) not in (int,str) or entity['id'] in entity_names
            or not isinstance(entity.get('name'),str) or not entity['name'].strip()):
            raise ValueError('invalid decision entities')
        entity_names[entity['id']] = entity['name']
    def classes(items, code_key, entity_names=None):
        if not isinstance(items,list) or not 1 <= len(items) <= 256: raise ValueError('invalid category mappings')
        result = {}
        for item in items:
            code = item.get(code_key); physical = item.get('physical_class')
            name = item.get('name') if entity_names is None else entity_names.get(item.get('entity_id'))
            if (type(code) is not int or not 0 < code <= 0xffffffff or code in result or physical not in ('land','water')
                or not isinstance(name,str) or not name.strip()): raise ValueError('invalid category mapping')
            result[code] = {'name':name,'physical_class':physical}
        if {v['physical_class'] for v in result.values()} != {'land','water'}: raise ValueError('both category classes required')
        return result
    ref_classes = classes(reference_manifest.get('categories'),'id')
    cand_classes = classes(snapshot.get('category_bindings'),'code',entity_names)
    if cand_classes != ref_classes: raise ValueError('candidate and V7 category code/name/class mappings differ')
    land = {k for k,v in cand_classes.items() if v['physical_class']=='land'}
    water = set(cand_classes)-land
    reference_audit = json.loads(provenance['reference_audit'].read_bytes())
    if (reference_audit.get('schema') != 'worldatlas-v7-full-grid-composition-audit-v1' or reference_audit.get('status') != 'staged-not-published'
        or reference_audit.get('output', {}).get('rows_sha256') != cfg['reference_rows']['sha256']
        or reference_audit.get('output', {}).get('runs_sha256') != cfg['reference_runs']['sha256']
        or reference_audit.get('grid', {}).get('width') != w or reference_audit.get('grid', {}).get('height') != h
        or reference_audit.get('grid', {}).get('angular_step_deg') != g['step']):
        raise ValueError('V7 audit does not bind grid and reference outputs')
    if output.exists() or any(output == p or p.is_relative_to(output) or output.is_relative_to(p.parent) for p in [config_path, *paths.values(), *provenance.values()]):
        raise ValueError('output must be new and outside input directories')
    identity_input = {'algorithm': VERSION, 'grid': g, 'inputs': {n: cfg[n]['sha256'] for n in names}, 'provenance': {n: v['sha256'] for n, v in sorted(cfg['provenance'].items())}}
    identity = hashlib.sha256(json.dumps(identity_input, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    code_sha = digest(__file__)
    cg = grid(paths['candidate_rows'], paths['candidate_runs'], w, h)
    rg = grid(paths['reference_rows'], paths['reference_runs'], w, h)
    pg = grid(paths['physical_rows'], paths['physical_runs'], w, h)
    output.mkdir(parents=True, exist_ok=False)
    def check_space():
        if shutil.disk_usage(output).free < cfg['minimum_free_bytes']:
            raise OSError('free disk space below configured floor')
    check_space()
    db = sqlite3.connect(output / 'clusters.sqlite')
    try:
        db.executescript('''PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL;
            CREATE TABLE parent (id INTEGER PRIMARY KEY, parent INTEGER NOT NULL);
            CREATE TABLE spans (row INTEGER NOT NULL, start INTEGER NOT NULL, end INTEGER NOT NULL, reference INTEGER NOT NULL, candidate INTEGER NOT NULL, label INTEGER NOT NULL);
            CREATE TABLE clusters (root INTEGER PRIMARY KEY, cluster_id TEXT NOT NULL UNIQUE, cells INTEGER NOT NULL, first_row INTEGER NOT NULL, first_col INTEGER NOT NULL, min_row INTEGER NOT NULL, max_row INTEGER NOT NULL, min_col INTEGER NOT NULL, max_col INTEGER NOT NULL, membership_sha256 TEXT NOT NULL);
        ''')
        uf = Components(db)
        counts = Counter()
        previous = []
        for y in range(h):
            ce, cv = row(cg, y, w, land | {UNCLASSIFIED_WATER})
            re, rv = row(rg, y, w, land | water)
            pe, pv = row(pg, y, w, {PHYSICAL_WATER, PHYSICAL_LAND})
            ends = np.union1d(np.union1d(ce, re), pe)
            starts = np.r_[np.uint32(0), ends[:-1]]
            c = cv[np.searchsorted(ce, starts, side='right')]
            r = rv[np.searchsorted(re, starts, side='right')]
            p = pv[np.searchsorted(pe, starts, side='right')]
            candidate_land = np.isin(c, list(land))
            reference_land = np.isin(r, list(land))
            if np.any(candidate_land != (p == PHYSICAL_LAND)):
                raise ValueError(f'candidate/physical mask mismatch at row {y}')
            lengths = ends.astype(np.int64) - starts.astype(np.int64)
            shared = candidate_land & reference_land
            counts['shared_land'] += int(lengths[shared].sum())
            counts['matching'] += int(lengths[shared & (c == r)].sum())
            counts['candidate_land_reference_water'] += int(lengths[candidate_land & ~reference_land].sum())
            counts['candidate_water_reference_land'] += int(lengths[(c == UNCLASSIFIED_WATER) & reference_land].sum())
            differing = shared & (c != r)
            counts['mismatch'] += int(lengths[differing].sum())
            # One provisional label per horizontally connected run, independent of transition.
            intervals = []
            for a, b, ref, cand in zip(starts[differing], ends[differing], r[differing], c[differing]):
                a, b, ref, cand = int(a), int(b), int(ref), int(cand)
                if intervals and intervals[-1][1] == a:
                    intervals[-1][1] = b
                    label = intervals[-1][2]
                else:
                    label = uf.new()
                    intervals.append([a, b, label])
                db.execute('INSERT INTO spans VALUES (?, ?, ?, ?, ?, ?)', (y, a, b, ref, cand, label))
            # Full wrap within the row and diagonal adjacency across row boundary.
            if len(intervals) > 1 and intervals[0][0] == 0 and intervals[-1][1] == w:
                uf.union(intervals[0][2], intervals[-1][2])
            j = 0
            for a, b, label in intervals:
                while j < len(previous) and previous[j][1] < a:
                    j += 1
                k = j
                while k < len(previous) and previous[k][0] <= b:
                    uf.union(label, previous[k][2])
                    k += 1
            if intervals and previous:
                if intervals[0][0] == 0 and previous[-1][1] == w:
                    uf.union(intervals[0][2], previous[-1][2])
                if intervals[-1][1] == w and previous[0][0] == 0:
                    uf.union(intervals[-1][2], previous[0][2])
            previous = intervals
            if y % 1000 == 999:
                db.commit()
                check_space()
        db.commit()
        # Compress on disk, avoiding materializing all labels or spans in memory.
        for n in range(1, uf.next_id):
            uf.find(n)
            if n % 10000 == 0:
                db.commit()
                check_space()
        db.commit()
        check_space()
        db.executescript('CREATE INDEX spans_label ON spans(label); CREATE INDEX spans_row ON spans(row); CREATE INDEX parent_root ON parent(parent);')
        check_space()
        db.execute('CREATE TABLE resolved AS SELECT s.row, s.start, s.end, s.reference, s.candidate, p.parent AS root FROM spans s JOIN parent p ON p.id=s.label')
        check_space()
        db.executescript('CREATE INDEX resolved_order ON resolved(root,row,start,end,reference,candidate); CREATE INDEX resolved_row ON resolved(row);')
        cursor = db.execute('SELECT root,row,start,end,reference,candidate FROM resolved ORDER BY root,row,start,end,reference,candidate')
        current = None
        stat = None
        mh = None
        def finish():
            if stat is None:
                return
            root, cells, first_row, first_col, minrow, maxrow, mincol, maxcol = stat
            cluster_id = hashlib.sha256((identity + ':' + mh.hexdigest()).encode()).hexdigest()
            db.execute('INSERT INTO clusters VALUES (?,?,?,?,?,?,?,?,?,?)', (root, cluster_id, cells, first_row, first_col, minrow, maxrow, mincol, maxcol, mh.hexdigest()))
        for root, y, a, b, ref, cand in cursor:
            if root != current:
                finish()
                current, mh = root, hashlib.sha256()
                stat = [root, 0, y, a, y, y, a, b - 1]
            stat[1] += b - a
            stat[5] = y
            stat[6] = min(stat[6], a)
            stat[7] = max(stat[7], b - 1)
            mh.update(f'{y}\t{a}\t{b}\t{ref}\t{cand}\n'.encode())
        finish()
        db.commit()
        check_space()
        total, nclusters = db.execute('SELECT COALESCE(SUM(cells),0),COUNT(*) FROM clusters').fetchone()
        if total != counts['mismatch']:
            raise ValueError('mismatch cluster accounting failure')
        db.execute('DROP TABLE spans')
        db.execute('DROP TABLE parent')
        db.commit()
        for n in names:
            pin(cfg[n])
        for spec in cfg['provenance'].values():
            pin(spec)
        if config_path.read_bytes() != raw or digest(__file__) != code_sha:
            raise ValueError('config or code changed during comparison')
        report = {'schema': 'list1-land-clusters-report-v1', 'status': 'diagnostic-complete-not-an-override', 'algorithm': VERSION, 'adjacency': '8-neighbor cells; longitude wraps at the antimeridian', 'comparison_sha256': identity, 'identity_inputs': identity_input, 'config_sha256': hashlib.sha256(raw).hexdigest(), 'code_sha256': code_sha, 'counts': dict(counts), 'clusters': nclusters, 'database_sha256': digest(output / 'clusters.sqlite'), 'limitations': ['Clusters are diagnostics, not geographic source features or executable corrections.', 'Physical-mask disagreements are counted separately and excluded from clusters.', 'Longitude min/max are naive bounds; use exact spans for dateline-aware discovery.']}
        with (output / 'report.json').open('x') as f:
            json.dump(report, f, indent=2, sort_keys=True)
            f.write('\n')
        return report
    finally:
        db.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('config')
    ap.add_argument('output_directory')
    args = ap.parse_args()
    try:
        print(json.dumps(build(args.config, args.output_directory), indent=2))
    except Exception as exc:
        print('error: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
