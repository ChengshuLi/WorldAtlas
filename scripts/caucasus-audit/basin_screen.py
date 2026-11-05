"""Research-only normal-offset comparison against HydroBASINS polygons.

Distances and perpendicular offsets use WGS84 geodesics. Distinct modeled terminals
do not prove a particular watershed. Do not publish input or output data as code.
"""
import argparse
import json
import math
from collections import Counter

import shapefile
from geodesic_line import GeodesicLine, GEOD
from shapely.geometry import LineString, Point, shape
from shapely.strtree import STRtree


def terminal(records, key):
    seen = set()
    while key and key in records and key not in seen:
        seen.add(key)
        downstream = records[key]['NEXT_DOWN']
        if not downstream:
            return key
        key = downstream
    return None


def run(args):
    reader = shapefile.Reader(args.basins)
    fields = [f[0] for f in reader.fields[1:]]
    records = {}
    for row in reader.iterRecords():
        record = dict(zip(fields, row))
        records[record['HYBAS_ID']] = record
    coords = json.load(open(args.line, encoding='utf-8'))['coordinates']
    line = GeodesicLine(coords)
    xmin, ymin, xmax, ymax = args.bounds
    sxmin, symin, sxmax, symax = args.source_bounds
    features = []
    for row in reader.iterShapeRecords():
        b = row.shape.bbox
        if b[2] < sxmin or b[0] > sxmax or b[3] < symin or b[1] > symax:
            continue
        record = dict(zip(fields, row.record))
        features.append((shape(row.shape.__geo_interface__), record['HYBAS_ID']))
    polygons = [feature[0] for feature in features]
    if not polygons:
        raise ValueError('no source polygons intersect --source-bounds')
    index = STRtree(polygons)

    def lookup(x, y):
        point = Point(x, y)
        matches = [features[int(i)][1] for i in index.query(point)
                   if polygons[int(i)].covers(point)]
        return matches[0] if len(matches) == 1 else None

    counts = {distance: Counter() for distance in args.offset}
    for station in range(math.floor(line.length / args.spacing) + 1):
        position = station * args.spacing
        lon, lat = line.point(position)
        if not xmin <= lon <= xmax or not ymin <= lat <= ymax:
            continue
        before = line.point(max(0, position - args.normal_half_window))
        after = line.point(min(line.length, position + args.normal_half_window))
        azimuth, _, separation = GEOD.inv(*before, *after)
        if not math.isfinite(separation) or separation <= 0:
            for count in counts.values():
                count['undefined_normal'] += 1
            continue
        for distance, count in counts.items():
            left = GEOD.fwd(lon, lat, azimuth-90, distance)[:2]
            right = GEOD.fwd(lon, lat, azimuth+90, distance)[:2]
            if any(not (sxmin <= x <= sxmax and symin <= y <= symax)
                   for x, y in (left, right)):
                raise ValueError('an offset lies outside --source-bounds')
            first, second = lookup(*left), lookup(*right)
            if first is None or second is None:
                count['missing_or_multiple_polygon'] += 1
                continue
            a, b = terminal(records, first), terminal(records, second)
            if a is None or b is None:
                count['unresolved_downstream_chain'] += 1
            else:
                count['same_terminal' if a == b else 'different_terminal'] += 1
    return {str(distance): dict(count) for distance, count in counts.items()}


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('expected a positive finite number')
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--line', required=True, help='GeoJSON LineString geometry')
    parser.add_argument('--basins', required=True, help='HydroBASINS shapefile')
    parser.add_argument('--bounds', nargs=4, type=float, required=True,
                        metavar=('WEST', 'SOUTH', 'EAST', 'NORTH'))
    parser.add_argument('--source-bounds', nargs=4, type=float, required=True,
                        metavar=('WEST', 'SOUTH', 'EAST', 'NORTH'),
                        help='expanded source window covering all offsets')
    parser.add_argument('--spacing', type=positive, default=500)
    parser.add_argument('--offset', type=positive, action='append', required=True)
    parser.add_argument('--normal-half-window', type=positive, default=25)
    args = parser.parse_args()
    if args.bounds[0] >= args.bounds[2] or args.bounds[1] >= args.bounds[3]:
        parser.error('bounds must be ordered west south east north')
    if args.source_bounds[0] >= args.source_bounds[2] or args.source_bounds[1] >= args.source_bounds[3]:
        parser.error('source bounds must be ordered west south east north')
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
