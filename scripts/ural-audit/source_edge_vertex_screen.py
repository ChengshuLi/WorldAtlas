#!/usr/bin/env python3
"""Compare line vertices with hash-pinned source polygons.

Exact matches are exact parsed coordinate pairs. Other vertices are compared to
WGS84 samples on nearby coordinate-linear source edges; this is not an exact
global nearest-edge search or proof of construction lineage.
"""
import argparse
import collections
import json
import math
import numpy as np
from pyproj import Geod
from shapely.geometry import box
from shapely.strtree import STRtree
from terrain_basin_screen import checked_shapes, digest_file

G = Geod(ellps='WGS84')


def rings(geometry):
    for polygon in getattr(geometry, 'geoms', [geometry]):
        yield polygon.exterior
        yield from polygon.interiors


def screen(line_path, line_sha, basins, bbox, skip, spacing, angular_filter):
    with open(line_path, 'rb') as f:
        if digest_file(f) != line_sha:
            raise ValueError('line checksum mismatch')
    with open(line_path) as f:
        line = json.load(f)
    if not line or not math.isfinite(spacing) or spacing <= 0 or not math.isfinite(angular_filter) or angular_filter <= 0:
        raise ValueError('invalid line, spacing or prefilter')
    if any(lo < 1 or hi < lo or hi > len(line) for lo, hi in skip):
        raise ValueError('invalid skipped ordinal range')
    selected = [i for i in range(1, len(line) + 1) if not any(lo <= i <= hi for lo, hi in skip)]
    lookup = collections.defaultdict(list)
    for i in selected:
        lookup[tuple(line[i-1])].append(i)
    features, source_counts, exact = [], [], set()
    for archive, sha, shp in basins:
        group = checked_shapes(archive, sha, shp, bbox)
        hit = set()
        scanned = 0
        for geom, _ in group:
            for ring in rings(geom):
                for point in ring.coords:
                    scanned += 1
                    hit.update(lookup.get(tuple(point), ()))
        exact.update(hit)
        features.extend(group)
        source_counts.append({'archive_sha256': sha, 'shapes': len(group), 'vertices': scanned, 'exact_ordinals': len(hit)})
    geoms = [x[0] for x in features]
    if not geoms:
        raise ValueError('no source polygons in bounds')
    tree = STRtree(geoms)
    results = []
    for ordinal in selected:
        if ordinal in exact:
            continue
        lon, lat = line[ordinal-1]
        d = angular_filter
        candidates, best = 0, None
        for index in tree.query(box(lon-d, lat-d, lon+d, lat+d)):
            for ring in rings(geoms[index]):
                xy = np.asarray(ring.coords)
                a, b = xy[:-1], xy[1:]
                mask = ((np.minimum(a[:, 0], b[:, 0]) <= lon+d) & (np.maximum(a[:, 0], b[:, 0]) >= lon-d)
                        & (np.minimum(a[:, 1], b[:, 1]) <= lat+d) & (np.maximum(a[:, 1], b[:, 1]) >= lat-d))
                for left, right in zip(a[mask], b[mask]):
                    _, _, length = G.inv(*left, *right)
                    n = max(1, math.ceil(length / spacing))
                    if n > 2000000:
                        raise ValueError('edge sample limit exceeded')
                    t = np.arange(n+1) / n
                    x, y = left[0] + (right[0]-left[0])*t, left[1] + (right[1]-left[1])*t
                    _, _, distances = G.inv(np.full(len(t), lon), np.full(len(t), lat), x, y)
                    distance = float(np.min(distances))
                    if not math.isfinite(distance):
                        raise ValueError('invalid geodesic')
                    candidates += 1
                    if best is None or distance < best:
                        best = distance
        results.append({'ordinal': ordinal, 'sampled_wgs84_m': best, 'candidate_segments': candidates})
    return {'line_sha256': line_sha, 'selected_count': len(selected), 'skipped_ordinal_ranges': skip,
            'exact_source_vertex_count': len(exact), 'sources': source_counts,
            'target_sample_step_wgs84_m': spacing, 'angular_prefilter_halfwidth_degrees': angular_filter,
            'unmatched_vertex_results': results,
            'caveat': 'Sampled WGS84 distances do not prove exact global nearest edges; angular box is a candidate prefilter. A nearby edge may be unrelated, and source match does not prove construction history or a selected geographic divide.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--line', required=True)
    p.add_argument('--line-sha', required=True)
    p.add_argument('--basin', nargs=3, action='append', required=True)
    p.add_argument('--bbox', nargs=4, type=float, required=True)
    p.add_argument('--skip', nargs=2, type=int, action='append', default=[])
    p.add_argument('--spacing', type=float, default=1)
    p.add_argument('--angular-filter', type=float, default=0.002)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    result = screen(a.line, a.line_sha, a.basin, a.bbox, a.skip, a.spacing, a.angular_filter)
    with open(a.output, 'x') as f:
        json.dump(result, f)
    print(json.dumps({'selected': result['selected_count'], 'exact': result['exact_source_vertex_count'],
                      'other': len(result['unmatched_vertex_results']), 'status': 'research only'}))
