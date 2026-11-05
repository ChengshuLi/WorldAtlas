"""Count exact binary64 coordinate matches; this does not prove lineage."""
import argparse
import hashlib
import json
from collections import defaultdict

import shapefile


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('line')
    p.add_argument('shp')
    args = p.parse_args()
    with open(args.line, encoding='utf-8') as f:
        line = json.load(f)
    normal = dict(line)
    normal['coordinates'] = [[float(v) for v in pt] for pt in line['coordinates']]
    canonical = json.dumps(normal, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    if hashlib.sha256(canonical).hexdigest() != '9f4ae3bc778ebbcd0258a19868acf0fa655763f5e849361196160fb4289c0d52':
        raise ValueError('selected line hash mismatch')
    if digest(args.shp) != 'aad745e7f15498fc99c34ad9ffc16271ec927cd1e3c223794747220a4dbe2203':
        raise ValueError('source shapefile hash mismatch')
    positions = defaultdict(list)
    for i, point in enumerate(line['coordinates']):
        positions[tuple(point)].append(i)
    matched = set()
    for geom in shapefile.Reader(shp=args.shp).iterShapes():
        x0, y0, x1, y1 = geom.bbox
        if x1 < 37 or x0 > 51 or y1 < 39 or y0 > 46:
            continue
        for point in geom.points:
            matched.update(positions.get(point, ()))
    print(json.dumps({'count': len(matched), 'total': len(line['coordinates']),
        'indices_0_1893': sum(i in matched for i in range(1894)),
        'indices_1894_2290': sum(i in matched for i in range(1894, 2291)),
        'index_2291': 2291 in matched,
        'duplicate_positions': sum(len(v)-1 for v in positions.values())}, indent=2))


if __name__ == '__main__':
    main()
