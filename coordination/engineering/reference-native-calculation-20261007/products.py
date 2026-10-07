"""Scoped compact-reference continuation; all numerical functions stay literal."""
from collections import Counter, defaultdict
import copy
import gzip
import hashlib
import json
from pathlib import Path
import shutil

TARGETS = frozenset(('atlas:physical:CAN-103:QUE', 'atlas:physical:CAN-114:NFL'))
INTERVALS = {('climate', 1901, 1931), ('climate', 1931, 1961),
             ('climate', 1961, 1991), ('climate', 1991, 2021),
             ('climate', 2026, 2027), ('vegetation', 2026, 2027),
             ('topography', 2026, 2027)}


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def file_sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_gzip(p, value):
    p.write_bytes(gzip.compress(dumps(value).encode(), mtime=0))
    return file_sha(p)


def records(index, bodies, ids):
    old = defaultdict(list)
    if index['version'] != 2 or index['locations'] != 49625 or len(ids) != 49625:
        raise ValueError('Complete original reference/location codec required')
    if len(index['parts']) != len(set(index['parts'])):
        raise ValueError('Duplicate original reference part')
    for name in index['parts']:
        if name not in bodies or hashlib.sha256(bodies[name]).hexdigest() != index['parts_sha256'][name]:
            raise ValueError('Original reference whole part drift')
        for id, rows in json.loads(gzip.decompress(bodies[name])):
            if id not in ids or not isinstance(rows, list):
                raise ValueError('Foreign original reference identity')
            old[id].extend(rows)
    if sum(map(len, old.values())) != index['records']:
        raise ValueError('Complete original record count')
    for id, rows in old.items():
        seen = set()
        for row in rows:
            if (not isinstance(row, list) or len(row) != 4 or
                    type(row[0]) is not int or not 0 <= row[0] < len(index['types']) or
                    type(row[1]) is not int or not 0 <= row[1] < len(index['values'])):
                raise ValueError('Original tuple/category drift')
            t = index['types'][row[0]]; key = (t['attribute'], t['valid_from'], t['valid_to'])
            if key in seen:
                raise ValueError('Duplicate original identity/attribute/interval')
            seen.add(key)
        if id in TARGETS and seen != INTERVALS:
            raise ValueError('All fourteen original target tuple identities required')
    return dict(old)


def validate_fresh(index, fresh, missing):
    if set(fresh) != TARGETS:
        raise ValueError('Exact two target identities required')
    for id, rows in fresh.items():
        seen = set()
        for row in rows:
            if len(row) != 4 or type(row[0]) is not int or type(row[1]) is not int or not 0 <= row[0] < len(index['types']) or not 0 <= row[1] < len(index['values']):
                raise ValueError('Fresh tuple/category bounds')
            t = index['types'][row[0]]; key = (t['attribute'], t['valid_from'], t['valid_to'])
            if key not in INTERVALS or key in seen or t['method'] != 'reference':
                raise ValueError('Fresh interval/identity drift')
            for value in row[2:]:
                if type(value) not in (int, float) or not 0 <= value <= 1:
                    raise ValueError('Fresh share/coverage invalid')
            seen.add(key)
        for attribute, begin, end in INTERVALS - seen:
            reason_key = 'climate:' + str(1991 if begin == 2026 else begin) if attribute == 'climate' else attribute
            if not missing.get(reason_key, {}).get(id):
                raise ValueError('Missing target tuple has no literal scientific reason')


def merge(helper, references, bodies, original, index, fresh, missing, evidence,
          ids, receipt_sha, after_hash, geography_sha, output, source_proof):
    """Same compact merge fields as the stock prepare, without extra ZIP reads."""
    if output.exists():
        raise ValueError('Fresh product destination required')
    if index['types'][:len(original['types'])] != original['types'] or index['values'][:len(original['values'])] != original['values']:
        raise ValueError('Original source/category prefix must stay exact')
    old = records(original, bodies, ids); validate_fresh(index, fresh, missing)
    output.mkdir(parents=True)
    # Exact originals not overwritten by the active index remain independently
    # retained. Prior receipts are chained through the existing stock helper.
    previous = ['prior-archives', 'incremental-receipt.json',
                'migration-before-records.json.gz', 'migration-new-evidence.json.gz']
    prior = helper.OWN.retain_prior_archives(references, output, original, previous)
    parts = []; active = defaultdict(list); reused = 0
    for name in original['parts']:
        rows = json.loads(gzip.decompress(bodies[name]))
        kept = [[id, rs] for id, rs in rows if id not in TARGETS]
        if not kept:
            continue
        p = output / name; p.parent.mkdir(parents=True, exist_ok=True)
        if kept == rows:
            p.write_bytes(bodies[name])
        else:
            write_gzip(p, kept)
        parts.append(name)
        for id, rs in kept:
            active[id].extend(rs); reused += len(rs)
    changed = [[id, rows] for id, rows in sorted(fresh.items()) if rows]
    if changed:
        name = 'incremental-' + receipt_sha[:16] + '-delta-0.json.gz'
        if name in parts:
            raise ValueError('Fresh delta collides with original part')
        write_gzip(output / name, changed); parts.append(name)
    for id, rs in fresh.items():
        active[id].extend(rs)
    for id in ids - TARGETS:
        if active.get(id, []) != old.get(id, []):
            raise ValueError('Unchanged original tuple altered')
    archived = [[id, old[id]] for id in sorted(TARGETS)]
    archive_sha = write_gzip(output / 'migration-before-records.json.gz', archived)
    write_gzip(output / 'migration-new-evidence.json.gz', evidence)
    counts = Counter(); absent = {str(y): [] for y in (1901, 1931, 1961, 1991)}
    for id in sorted(ids):
        seen = set()
        for ti, vi, share, coverage in active.get(id, []):
            t = index['types'][ti]; counts[(t['attribute'], t['valid_from'], t['status'])] += 1
            seen.add((t['attribute'], t['valid_from']))
        for y in absent:
            if ('climate', int(y)) not in seen:
                absent[y].append(id)
    count = sum(map(len, active.values()))
    report = {'version': 1, 'before_footprints_sha256': original['footprints_sha256'],
              'after_footprints_sha256': after_hash, 'original_index_sha256': hashlib.sha256(bodies['index.json']).hexdigest(),
              'migration_receipt_sha256': receipt_sha, 'sources': source_proof,
              'changed_ids': sorted(TARGETS), 'added_ids': [], 'removed_ids': [],
              'reused_locations': 49623, 'recomputed_locations': 2, 'unknown_changed': False,
              'reused_records': reused, 'derived_records': sum(map(len, fresh.values())),
              'archive': {'path': 'migration-before-records.json.gz', 'sha256': archive_sha, 'locations': 2, 'records': 14},
              'missing_changed': missing, 'historical_claims_transferred': False,
              'source_intervals_unchanged': True, 'source_dictionaries_prefix_preserved': True,
              'after_records': count, 'retained_prior_archives': prior,
              'calculation_entry': 'literal unchanged summarize_changed; ZIP custody belongs to actual merged PR1412'}
    (output / 'incremental-receipt.json').write_text(dumps(report))
    index.update(parts=parts, parts_sha256={n:file_sha(output/n) for n in parts},
                 records=count, locations=49625, represented_locations=sum(bool(v) for v in active.values()),
                 footprints_sha256=after_hash,
                 climate_counts={str(y):counts[('climate',y,'reference')] for y in (1901,1931,1961,1991)},
                 missing_climate=absent, vegetation_references=counts[('vegetation',2026,'reference')],
                 unknown_source_records=counts[('vegetation',2026,'unknown')],
                 incremental_preparation={'receipt':'incremental-receipt.json','receipt_sha256':file_sha(output/'incremental-receipt.json'),
                    **{k:report[k] for k in ('original_index_sha256','reused_locations','recomputed_locations','reused_records','derived_records')}})
    index['merged_sources']['topography-reference']['records'] = counts[('topography',2026,'reference')]
    index['inputs'].setdefault('original_preparation_geography',index['inputs'].get('geography'))
    index['inputs'].update(geography=geography_sha,footprints_sha256=after_hash,incremental_migration_sha256=receipt_sha)
    if 'vegetation_numerical_review' in index:
        index['vegetation_numerical_review_applicability'] = 'Original review retained for unchanged IDs; changed footprints covered by native calculation receipt'
    (output/'index.json').write_text(dumps(index))
    return report
