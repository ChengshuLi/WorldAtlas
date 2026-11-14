"""Disk-backed unseeded-water candidate classifier.

Rows and component summaries are indexed in a fresh SQLite work file. The
source partition and output are streamed. No application-imposed memory cap
is enforced; actual memory use depends on inputs and algorithm workload.
"""

import hashlib, json, math, sqlite3, struct
import time
from pathlib import Path
import numpy as np
from worldatlas.map_build.water import closed_water_core as core
from worldatlas.map_build.water import interval_nearest
from worldatlas.map_build.water import partition_json_stream
from worldatlas.map_build.water.partition_json_stream import read_partition
from worldatlas.map_build.execution.outputs import (
    create_directory_exclusive,
    create_gzip_text_exclusive,
    write_json_exclusive,
)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def open_database(path):
    db = sqlite3.connect(path)
    db.execute('PRAGMA journal_mode=OFF')
    db.execute('PRAGMA synchronous=OFF')
    db.execute('PRAGMA temp_store=FILE')
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
 CREATE TABLE components(root INTEGER PRIMARY KEY, expected INTEGER NOT NULL, reported_cut INTEGER NOT NULL,
   boundary_entities TEXT NOT NULL DEFAULT '[]', unknown INTEGER NOT NULL DEFAULT 0, crop_edge INTEGER NOT NULL DEFAULT 0,
   cut INTEGER NOT NULL DEFAULT 0, method TEXT, code INTEGER);
 CREATE TABLE spans(y INTEGER NOT NULL, a INTEGER NOT NULL, b INTEGER NOT NULL, root INTEGER NOT NULL REFERENCES components(root),
   PRIMARY KEY(y,a)) WITHOUT ROWID;
 CREATE TABLE mixed(y INTEGER NOT NULL, a INTEGER NOT NULL, b INTEGER NOT NULL, code INTEGER NOT NULL, root INTEGER NOT NULL,
   PRIMARY KEY(y,a)) WITHOUT ROWID;
 ''')
    return db


def ingest_partition(db, path, width, height, snapshot_sha, inputs):
    def insert(c):
        if 'ocean_code' not in c or (
            c['ocean_code'] is not None
            and (type(c['ocean_code']) is not int or not 0 < c['ocean_code'] < 2**32)
        ):
            raise ValueError('invalid component ocean code')
        if c['ocean_code'] is not None:
            return
        root, count, cut = (
            c.get('component_root'),
            c.get('cell_count'),
            c.get('source_barrier_contact_edge_count'),
        )
        if any(type(x) is not int for x in (root, count, cut)) or not (
            0 <= root < 2**32 and count > 0 and cut >= 0
        ):
            raise ValueError('invalid unseeded component metadata')
        try:
            db.execute(
                'INSERT INTO components(root,expected,reported_cut) VALUES(?,?,?)',
                (root, count, cut),
            )
        except sqlite3.IntegrityError as e:
            raise ValueError('duplicate component root') from e

    meta = read_partition(path, insert)
    if (
        meta.get('schema') != 'fresh-ocean-run-partition-v1'
        or meta.get('grid', {}).get('W') != width
        or meta.get('grid', {}).get('H') != height
    ):
        raise ValueError('partition schema or grid mismatch')
    pin = meta.get('inputs', {})
    if (
        pin.get('decision_snapshot_sha256') != snapshot_sha
    ):
        raise ValueError('partition snapshot mismatch')
    for key in (
        'physical_rows_sha256',
        'physical_runs_sha256',
        'prefill_rows_sha256',
        'prefill_runs_sha256',
        'prefill_audit_sha256',
        'source_cut_edges_sha256',
    ):
        if pin.get(key) != inputs.get(key):
            raise ValueError(f'partition input mismatch: {key}')
    return meta


def ingest_spans(db, rows_path, spans_path, width, height, meta, batch_size=4096):
    raw = Path(rows_path).read_bytes()
    if len(raw) != (height + 1) * 8:
        raise ValueError('unseeded offset size mismatch')
    offsets = struct.unpack('<%dQ' % (height + 1), raw)
    size = Path(spans_path).stat().st_size
    if (
        offsets[0] != 0
        or offsets[-1] * 12 != size
        or any(a > b for a, b in zip(offsets, offsets[1:]))
    ):
        raise ValueError('invalid unseeded offsets')
    batch = []
    cells = 0
    try:
        with Path(spans_path).open('rb') as f:
            for y in range(height):
                prev = 0
                for _ in range(offsets[y + 1] - offsets[y]):
                    raw = f.read(12)
                    if len(raw) != 12:
                        raise ValueError('truncated unseeded span')
                    a, b, root = struct.unpack('<III', raw)
                    if not (0 <= a < b <= width) or a < prev:
                        raise ValueError('invalid or overlapping unseeded span')
                    prev = b
                    cells += b - a
                    batch.append((y, a, b, root))
                    if len(batch) >= batch_size:
                        db.executemany('INSERT INTO spans VALUES(?,?,?,?)', batch)
                        batch.clear()
            if batch:
                db.executemany('INSERT INTO spans VALUES(?,?,?,?)', batch)
    except sqlite3.IntegrityError as e:
        raise ValueError('unseeded spans reference unknown roots or overlap') from e
    if cells != meta.get('unseeded_cell_count') or offsets[-1] != meta.get('unseeded_span_count'):
        raise ValueError('partition unseeded totals mismatch')
    db.execute('CREATE INDEX spans_root_y ON spans(root,y,a)')
    # Both the sum and root count must match; no component may be omitted.
    missing = db.execute(
        '''SELECT c.root FROM components c LEFT JOIN (SELECT root,SUM(b-a) n FROM spans GROUP BY root) s
  ON c.root=s.root WHERE s.n IS NULL OR s.n!=c.expected LIMIT 1'''
    ).fetchone()
    if missing:
        raise ValueError(f'unseeded component size mismatch: {missing[0]}')
    return cells, offsets[-1]


def classify_boundaries(db, physical, prefill, width, height, pairs, batch_cells=4096):
    """Intersect RLE intervals over the exact three-row boundary stencil.

    Boundary summaries need code presence, not one record per cell. Split at
    every class or component transition, so each checked interval has constant
    physical/prefill codes and ownership. Full visited rows are still validated.
    """
    water_to_entity = {w: e for e, _, w in pairs}
    land_to_entity = {l: e for e, l, _ in pairs}
    code_to_entity = {**water_to_entity, **land_to_entity}
    water_codes, land_codes = list(water_to_entity), list(land_to_entity)
    class_rows = {}
    index_rows = {}

    def classes(y):
        if y in class_rows:
            return class_rows[y]

        def read(grid):
            rows, runs = grid
            first, last = int(rows[y]), int(rows[y + 1])
            ends, values = runs[2 * first : 2 * last : 2], runs[2 * first + 1 : 2 * last : 2]
            if (
                not len(ends)
                or int(ends[0]) <= 0
                or int(ends[-1]) != width
                or np.any(ends[1:] <= ends[:-1])
            ):
                raise ValueError(f'invalid RLE row {y}')
            return ends, values

        pe, pv = read(physical)
        qe, qv = read(prefill)
        ends = np.union1d(pe, qe)
        starts = np.r_[0, ends[:-1]]
        p = pv[np.searchsorted(pe, starts, side='right')]
        q = qv[np.searchsorted(qe, starts, side='right')]
        if (
            np.any(~np.isin(p, [1, 17]))
            or np.any((p == 17) & ~np.isin(q, land_codes))
            or np.any((p == 1) & ~np.isin(q, [0, *water_codes]))
        ):
            raise ValueError(f'invalid physical/prefill relationship at row {y}')
        class_rows[y] = (ends, p, q)
        return ends, p, q

    def row_index(y):
        if y in index_rows:
            return index_rows[y]
        rows = db.execute('SELECT a,b,root FROM spans WHERE y=? ORDER BY a', (y,)).fetchall()
        data = (
            tuple(
                np.fromiter((r[i] for r in rows), dtype=np.int64, count=len(rows)) for i in range(3)
            )
            if rows
            else None
        )
        index_rows[y] = data
        return data

    def owners(y, x):
        data = row_index(y)
        if data is None:
            return np.full(len(x), -1, dtype=np.int64)
        starts, ends, roots = data
        ix = np.searchsorted(starts, x, side='right') - 1
        safe = np.maximum(ix, 0)
        return np.where((ix >= 0) & (x < ends[safe]), roots[safe], -1)

    def classify_row(y, data):
        starts, ends, roots = data
        ce, p, q = classes(y)
        updates = {}
        crop = int(y == 0 or y == height - 1)

        def accumulate_values(ids, values):
            for value in np.unique(values):
                entity = code_to_entity.get(int(value))
                for root in np.unique(ids[values == value]):
                    record = updates.setdefault(int(root), [set(), 0, 0])
                    if entity is not None:
                        record[0].add(entity)
                    record[1] |= int(value == 0)
                    record[2] |= crop

        def accumulate(ids, ny, x):
            external = owners(ny, x) != ids
            if not np.any(external):
                return
            ne, _, nq = classes(ny)
            accumulate_values(ids[external], nq[np.searchsorted(ne, x[external], side='right')])

        # Check every constant-code segment of the listed component spans.
        cuts = np.unique(np.concatenate((starts, ends, ce)))
        xx = cuts[:-1]
        rr = owners(y, xx)
        selected = rr >= 0
        ci = np.searchsorted(ce, xx[selected], side='right')
        if np.any(p[ci] != 1) or np.any(q[ci] != 0):
            raise ValueError('component contains non-residual water')
        # Horizontal boundary cells only: interiors have the same component root.
        for at in range(0, len(starts), batch_cells):
            sub = slice(at, min(at + batch_cells, len(starts)))
            ids = roots[sub]
            accumulate(ids, y, (starts[sub] - 1) % width)
            accumulate(ids, y, ends[sub] % width)
            if crop:
                for root in ids:
                    updates.setdefault(int(root), [set(), 0, 0])[2] = 1
        for ny in (y - 1, y + 1):
            if not 0 <= ny < height:
                continue
            adjacent = row_index(ny)
            # First prove whether any vertical boundary is external. A fully
            # shared component interior does not consume the adjacent classes.
            pieces = [starts, ends]
            if adjacent is not None:
                pieces.extend(adjacent[:2])
            cuts = np.unique(np.concatenate(pieces))
            xx = cuts[:-1]
            rr = owners(y, xx)
            external = (rr >= 0) & (owners(ny, xx) != rr)
            if not np.any(external):
                continue
            ne, _, nq = classes(ny)
            # Neighbor class transitions can occur inside any component span.
            cuts = np.union1d(cuts, ne)
            xx = cuts[:-1]
            rr = owners(y, xx)
            external = (rr >= 0) & (owners(ny, xx) != rr)
            accumulate_values(rr[external], nq[np.searchsorted(ne, xx[external], side='right')])
        records = []
        for root, (entities, unknown, crop_edge) in updates.items():
            old = db.execute(
                'SELECT boundary_entities FROM components WHERE root=?', (root,)
            ).fetchone()
            if old is None:
                raise ValueError('boundary references an unknown component')
            merged = sorted(set(json.loads(old[0])) | entities)
            records.append((json.dumps(merged), unknown, crop_edge, root))
        db.executemany(
            'UPDATE components SET boundary_entities=?,unknown=MAX(unknown,?),crop_edge=MAX(crop_edge,?) WHERE root=?',
            records,
        )

    for y in range(height):
        # Only y-1, y and y+1 can participate in this row's four-neighbor
        # checks. Earlier rows have no future consumer, including across gaps.
        class_rows.pop(y - 2, None)
        index_rows.pop(y - 2, None)
        data = row_index(y)
        if data is not None:
            classify_row(y, data)


def mark_cut_contacts(db, path, width, height, batch_size=4096):
    from bisect import bisect_right

    rows = {}

    def row(y):
        if y in rows:
            return rows[y]
        spans = db.execute('SELECT a,b,root FROM spans WHERE y=? ORDER BY a', (y,)).fetchall()
        rows[y] = ([z[0] for z in spans], spans)
        return rows[y]

    def owner(y, x):
        starts, spans = row(y)
        i = bisect_right(starts, x) - 1
        return spans[i][2] if i >= 0 and x < spans[i][1] else None

    batch = []
    prev = None
    with Path(path).open('rb') as f:
        while True:
            raw = f.read(12)
            if not raw:
                break
            if len(raw) != 12:
                raise ValueError('truncated barrier edge')
            k, y, x = record = struct.unpack('<III', raw)
            if prev is not None and record <= prev:
                raise ValueError('barrier edges not unique and sorted')
            prev = record
            if k == 0 and y < height and x < width - 1:
                pts = ((y, x), (y, x + 1))
            elif k == 1 and y < height - 1 and x < width:
                pts = ((y, x), (y + 1, x))
            elif k == 2 and y < height and x == 0:
                pts = ((y, width - 1), (y, 0))
            else:
                raise ValueError('barrier edge outside grid')
            # Edges are sorted by kind, row and column. Keep only the current
            # endpoints' rows; row order starts again when the edge kind changes.
            needed = {pt[0] for pt in pts}
            for old in tuple(rows):
                if old not in needed:
                    del rows[old]
            batch.extend((r,) for r in {owner(*pt) for pt in pts} - {None})
            if len(batch) >= batch_size:
                db.executemany('UPDATE components SET cut=1 WHERE root=?', batch)
                batch.clear()
    if batch:
        db.executemany('UPDATE components SET cut=1 WHERE root=?', batch)
    if db.execute('SELECT root FROM components WHERE reported_cut>0 AND cut=0 LIMIT 1').fetchone():
        raise ValueError('independent barrier scan contradicts partition')


def assign_components(
    db, physical, land, width, height, pairs, tolerance, pad, chunk, pending_file, shores=None
):
    step = 360 / width
    last = -1
    pending_cells = assigned_cells = 0
    pending_count = direct_count = mixed_count = 0
    # Page by stable root key to avoid retaining all components or modifying an active cursor.
    cache_key = None
    edges = indexes = None
    with create_gzip_text_exclusive(pending_file, encoding='utf8') as pf:
        while True:
            batch = db.execute(
                'SELECT root,expected,reported_cut,boundary_entities,unknown,crop_edge,cut FROM components WHERE root>? ORDER BY root LIMIT 256',
                (last,),
            ).fetchall()
            if not batch:
                break
            for root, expected, reported, raw_entities, unknown, crop_edge, cut in batch:
                entities = set(json.loads(raw_entities))
                last = root
                reason = (
                    'pending-source-cut-contact'
                    if cut
                    else (
                        'pending-grid-crop-edge'
                        if crop_edge
                        else (
                            'pending-unknown-zero-boundary'
                            if unknown
                            else 'pending-no-boundary-continent' if not entities else None
                        )
                    )
                )
                if reason:
                    pf.write(
                        json.dumps(
                            {'component_root': root, 'reason': reason, 'cells': expected},
                            separators=(',', ':'),
                        )
                        + '\n'
                    )
                    db.execute('UPDATE components SET method=? WHERE root=?', (reason, root))
                    pending_cells += expected
                    pending_count += 1
                    continue
                participants = [p for p in pairs if p[0] in entities]
                if not participants or entities != {p[0] for p in participants}:
                    raise ValueError('unknown boundary participant entity')
                if len(participants) == 1:
                    db.execute(
                        "UPDATE components SET method='direct',code=? WHERE root=?",
                        (participants[0][2], root),
                    )
                    assigned_cells += expected
                    direct_count += 1
                    continue
                bbox = db.execute(
                    'SELECT MIN(a),MAX(b),MIN(y),MAX(y)+1 FROM spans WHERE root=?', (root,)
                ).fetchone()
                crop = (
                    (0, width, 0, height)
                    if shores is not None
                    else core.shore.crop_bounds(bbox, width, height, step, pad)
                )
                key = (tuple(crop), tuple(p[1] for p in participants))
                if shores is not None:
                    indexes = shores.indexes
                elif key != cache_key:
                    # Release the prior tree before constructing a different one.
                    edges = indexes = None
                    cache_key = None
                    edges = core.shore.centers_for_crop(
                        physical, land, crop, width, height, step, [p[1] for p in participants]
                    )
                    indexes = core.shore.make_indexes(edges, participants)
                    cache_key = key
                source = db.execute('SELECT y,a,b FROM spans WHERE root=? ORDER BY y,a', (root,))
                produced = 0
                staged = []
                while True:
                    records = source.fetchmany(1024)
                    if not records:
                        break
                    for y, a, b in records:
                        for start in range(a, b, chunk):
                            end = min(start + chunk, b)
                            # The same exact WGS84 distance and tie rules certify whole intervals;
                            # uncertain leaves retain the complete-input point classifier. Keep the
                            # original source/chunk boundaries so serialized spans remain identical.
                            assignments, _ = interval_nearest.classify_row(
                                y,
                                [(start, end)],
                                crop,
                                width,
                                height,
                                step,
                                participants,
                                tolerance,
                                indexes,
                            )
                            for aa, bb, code in assignments:
                                staged.append((y, aa, bb, code, root))
                                produced += bb - aa
                                if len(staged) >= 4096:
                                    db.executemany('INSERT INTO mixed VALUES(?,?,?,?,?)', staged)
                                    staged.clear()
                if staged:
                    db.executemany('INSERT INTO mixed VALUES(?,?,?,?,?)', staged)
                if produced != expected:
                    raise ValueError('mixed component cell count mismatch')
                db.execute("UPDATE components SET method='mixed' WHERE root=?", (root,))
                assigned_cells += produced
                mixed_count += 1
    return {
        'assigned_cells': assigned_cells,
        'pending_cells': pending_cells,
        'pending_components': pending_count,
        'direct_components': direct_count,
        'mixed_components': mixed_count,
    }


def write_assignments(db, path, decision_id, width, height, water_codes):
    query = '''SELECT s.y,s.a,s.b,c.code,s.root FROM spans s JOIN components c ON c.root=s.root WHERE c.method='direct'
          UNION ALL SELECT y,a,b,code,root FROM mixed ORDER BY 1,2'''
    count = spans = 0
    last_y = -1
    last_end = 0
    first = True
    with create_gzip_text_exclusive(path, encoding='utf8') as f:
        for y, a, b, code, root in db.execute(query):
            if (
                not (0 <= y < height and 0 <= a < b <= width and code in water_codes)
                or y < last_y
                or (y == last_y and a < last_end)
            ):
                raise ValueError('invalid or overlapping closed-water output')
            if y != last_y:
                if last_y >= 0:
                    f.write(']}\n')
                f.write('{"row":' + str(y) + ',"spans":[')
                last_y = y
                last_end = 0
                first = True
            if not first:
                f.write(',')
            rec = {
                'start': a,
                'end': b,
                'code': code,
                'rule_id': 'closed-water-policy-v1',
                'member_id': f'{decision_id}-component-{root}',
            }
            f.write(json.dumps(rec, separators=(',', ':')))
            first = False
            last_end = b
            count += b - a
            spans += 1
        if last_y >= 0:
            f.write(']}\n')
    return count, spans


def run(
    snapshot,
    snapshot_sha,
    physical,
    prefill,
    land,
    partition_path,
    component_rows,
    component_spans,
    barrier_edges,
    out,
    width,
    height,
    pad,
    inputs,
    *,
    chunk=5000,
    verify_inputs=None,
    processing_started=None,
    shores=None,
):
    if processing_started is None:
        processing_started = time.perf_counter()
    if chunk <= 0 or not math.isfinite(pad) or pad <= 0:
        raise ValueError('invalid chunk or halo')
    decision, pairs, tolerance = core.policy(snapshot)
    if shores is not None and (
        (shores.grid.width, shores.grid.height) != (width, height) or shores.pairs != pairs
    ):
        raise ValueError(
            'enclosed-water policy and shoreline index use different grids or bindings'
        )
    code_paths = {
        'streaming_closed_water': Path(__file__),
        'partition_json_stream': Path(partition_json_stream.__file__),
        'closed_water_core': Path(core.__file__),
        'shared_nearest': Path(core.shore.__file__),
        'interval_nearest': Path(interval_nearest.__file__),
    }
    code_pins = {name: sha(path) for name, path in code_paths.items()}
    out = Path(out)
    create_directory_exclusive(out)
    db = open_database(out / 'work.sqlite3')
    stage_seconds = {}

    def measure(name, action, *args):
        started = time.perf_counter()
        result = action(*args)
        stage_seconds[name] = time.perf_counter() - started
        return result

    try:
        meta = measure(
            'ingest_partition',
            ingest_partition,
            db,
            partition_path,
            width,
            height,
            snapshot_sha,
            inputs,
        )
        cells, nspans = measure(
            'ingest_spans', ingest_spans, db, component_rows, component_spans, width, height, meta
        )
        measure(
            'classify_boundaries', classify_boundaries, db, physical, prefill, width, height, pairs
        )
        measure('mark_cut_contacts', mark_cut_contacts, db, barrier_edges, width, height)
        stats = measure(
            'assign_components',
            assign_components,
            db,
            physical,
            land,
            width,
            height,
            pairs,
            tolerance,
            pad,
            chunk,
            out / 'pending-components.jsonl.gz',
            shores,
        )
        count, output_spans = measure(
            'write_assignments',
            write_assignments,
            db,
            out / 'closed-water-assignments.jsonl.gz',
            decision['id'],
            width,
            height,
            {p[2] for p in pairs},
        )
        if count != stats['assigned_cells'] or count + stats['pending_cells'] != cells:
            raise ValueError('closed-water cell conservation failed')
        db.commit()
        db.close()
        db = None
        if verify_inputs:
            verify_inputs()
        manifest = {
            'schema': 'worldatlas-full-water-assignment-tiles-v1',
            'status': (
                'partial'
                if stats['pending_cells']
                else 'completed_unverified_candidate_not_published'
            ),
            'grid': {
                'width': width,
                'height': height,
                'angular_step_deg': 360 / width,
                'row_convention': 'north-to-south; cell centers; half-open [start,end) x spans',
            },
            'coverage': {
                'complete': not stats['pending_cells'],
                'meaning': 'classified listed unseeded components; geographic and upstream partition correctness remain unverified',
            },
            'source': {
                **inputs,
                'decision_id': decision['id'],
                'policy_definition': decision['definition'],
                'policy_sha256': snapshot_sha,
                'decision_snapshot_sha256': snapshot_sha,
            },
            **stats,
            'input_span_count': nspans,
            'span_count': output_spans,
            'pending_file': {
                'path': 'pending-components.jsonl.gz',
                'sha256': sha(out / 'pending-components.jsonl.gz'),
            },
            'work_database': {
                'path': 'work.sqlite3',
                'sha256': sha(out / 'work.sqlite3'),
                'purpose': 'disk-backed row/component and mixed-output index',
            },
            'algorithm_parameters': {'classification_chunk': chunk},
            'processing_stage_elapsed_seconds': stage_seconds,
            'algorithm_sha256': code_pins['streaming_closed_water'],
            'code_sha256': code_pins,
            'tiles': [
                {
                    'core_rows': [0, height],
                    'core_cols': [0, width],
                    'span_file': {
                        'path': 'closed-water-assignments.jsonl.gz',
                        'sha256': sha(out / 'closed-water-assignments.jsonl.gz'),
                    },
                }
            ],
        }
        manifest['processing_elapsed_seconds'] = time.perf_counter() - processing_started
        write_json_exclusive(out / 'manifest.json', manifest, indent=2)
        return manifest
    finally:
        if db is not None:
            db.close()
