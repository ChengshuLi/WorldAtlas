#!/usr/bin/env python3
"""Sample a supplied LineString at equal projected intervals for terrain screening."""
import argparse
import json
import math
from pathlib import Path
from terrain_screen import transformer


def generate(coordinates, start, end, section, spacing, epsg):
    if not (0 <= start < end < len(coordinates)):
        raise ValueError('start and end must be ordered, valid vertex indices')
    if spacing <= 0:
        raise ValueError('spacing must be positive')
    forward, reverse = transformer(epsg)
    points = [forward.TransformPoint(*p)[:2] for p in coordinates]
    lengths = [math.dist(points[i], points[i + 1]) for i in range(start, end)]
    if any(length == 0 for length in lengths):
        raise ValueError('zero-length input edge')
    total = sum(lengths)
    edge = start
    edge_start = 0.0
    position = 0.0
    features = []
    while position <= total:
        while edge < end - 1 and edge_start + lengths[edge - start] < position:
            edge_start += lengths[edge - start]
            edge += 1
        frac = min(1.0, (position - edge_start) / lengths[edge - start])
        a, b = points[edge], points[edge + 1]
        x = a[0] + frac * (b[0] - a[0])
        y = a[1] + frac * (b[1] - a[1])
        lon, lat = reverse.TransformPoint(x, y)[:2]
        features.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
                         'properties': {'section': section, 'source_edge_index': edge,
                                        'distance_along_section_m': position}})
        position += spacing
    return {'type': 'FeatureCollection', 'features': features}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--line', required=True, help='GeoJSON LineString geometry')
    parser.add_argument('--start-vertex', type=int, required=True)
    parser.add_argument('--end-vertex', type=int, required=True)
    parser.add_argument('--section', type=int, required=True)
    parser.add_argument('--spacing-m', type=float, default=500)
    parser.add_argument('--epsg', type=int, required=True, help='Projected CRS with metre units')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.line).read_text())
    if data.get('type') != 'LineString':
        raise ValueError('line must be a GeoJSON LineString geometry')
    result = generate(data['coordinates'], args.start_vertex, args.end_vertex,
                      args.section, args.spacing_m, args.epsg)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
