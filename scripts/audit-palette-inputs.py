#!/usr/bin/env python3
"""Read-only pinned owner-name inventory and representative dated display maps.

These display keys are not replacement source entities. Unknown ownership remains
zero. The output is an engineering audit, not a geographic approval certificate.
"""
import argparse, array, bisect, collections, gzip, hashlib, json, pathlib, unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[1]
YEARS = [-3000, -1000, 1, 500, 1000, 1444, 1700, 1800, 1900, 1950, 1951, 2000, 2020]

def sha(value):
    return hashlib.sha256(value).hexdigest()

def read(path, expected=None):
    value = path.read_bytes()
    if expected is not None and sha(value) != expected:
        raise ValueError('Palette input hash mismatch: ' + str(path))
    return json.loads(gzip.decompress(value) if path.suffix == '.gz' else value)

def key(identity, name):
    return json.dumps([identity, unicodedata.normalize('NFC', name).strip()], ensure_ascii=False, separators=(',', ':'))

def audit(outdir):
    outdir = outdir.resolve()
    if not outdir.is_relative_to(ROOT / 'data' / 'engineering'):
        raise ValueError('Audit output must remain in an owned engineering evidence directory')
    source = ROOT / 'data' / 'ownership-history'
    index_path = source / 'index.json'
    index = read(index_path)
    grid_path = ROOT / 'data' / 'canonical-grid' / 'manifest.json'
    grid = read(grid_path)
    bounds = read(grid_path.parent / grid['bounds']['path'], grid['bounds']['sha256'])
    if any(row['index'] != i + 1 for i, row in enumerate(bounds)):
        raise ValueError('Noncanonical raster identity order')
    ids = {row['id']: i + 1 for i, row in enumerate(bounds)}
    if len(ids) != len(bounds):
        raise ValueError('Duplicate raster identity')
    names = array.array('h')
    for entry in index['evidence_parts']:
        values = read(source / entry['path'], entry['sha256'])
        names.extend(-1 if row[0] is None else row[0] for row in values)
    if len(names) != index['evidence_records']:
        raise ValueError('Incomplete owner-name evidence dictionary')
    counts = collections.Counter()
    envelopes = collections.defaultdict(lambda: [99999, -99999])
    owners = {year: [None] * (len(bounds) + 1) for year in YEARS}
    total = 0
    for entry in index['parts']:
        for location, intervals in read(source / entry['path'], entry['sha256']):
            if location not in ids:
                raise ValueError('Ownership subject absent from immutable grid')
            starts = [row[0] for row in intervals]
            for start, end, owner, status, evidence in intervals:
                if owner is None or names[evidence] < 0:
                    continue
                pair = (owner, names[evidence])
                counts[pair] += 1
                envelopes[pair][0] = min(envelopes[pair][0], start)
                envelopes[pair][1] = max(envelopes[pair][1], end)
                total += 1
            for year in YEARS:
                i = bisect.bisect_right(starts, year) - 1
                if i < 0 or year >= intervals[i][1]:
                    continue
                _, _, owner, status, evidence = intervals[i]
                if owner is None or names[evidence] < 0 or index['statuses_order'][status] != 'derived':
                    continue
                owners[year][ids[location]] = key(index['owner_ids'][owner], index['labels'][names[evidence]])
    groups = [{'owner_id': index['owner_ids'][o], 'source_name': index['labels'][n], 'intervals': count,
               'range_envelope': envelopes[(o, n)]} for (o, n), count in sorted(counts.items())]
    keys = sorted({key(row['owner_id'], row['source_name']) for row in groups})
    numbers = {value: i + 1 for i, value in enumerate(keys)}
    result = {'version': 1, 'source_index_sha256': sha(index_path.read_bytes()),
              'grid_manifest_sha256': sha(grid_path.read_bytes()), 'total_intervals_with_named_owner': total,
              'owner_names': groups, 'keys': keys, 'dates': [
                  {'year': year, 'owners': [numbers.get(value, 0) for value in owners[year]]} for year in YEARS],
              'notes': 'Range envelopes do not establish actual overlap or rename equivalence. Display keys preserve original owner IDs and source names; zero means unresolved, not uninhabited. Representative dates are an audit sample, not exhaustive historical approval.'}
    outdir.mkdir(parents=True, exist_ok=True)
    destination = outdir / 'source-owner-dated-display.json.gz'
    with destination.open('xb') as stream:
        stream.write(gzip.compress(json.dumps(result, ensure_ascii=False, separators=(',', ':')).encode(), mtime=0))
    print(json.dumps({'named_display_keys': len(keys), 'dates': len(YEARS), 'locations': len(bounds),
                      'source_sha256': result['source_index_sha256'], 'output': str(destination.relative_to(ROOT))}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--outdir', type=pathlib.Path, required=True)
    audit(parser.parse_args().outdir)
