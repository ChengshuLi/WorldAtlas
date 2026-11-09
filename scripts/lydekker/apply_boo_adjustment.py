#!/usr/bin/env python3
"""Reproduce the selected Boo adjustment from the smoothed Lydekker line."""
import argparse
import hashlib
import json
import math
from pathlib import Path

SMOOTHED_SHA256 = '0c3ada39efe778e42808a112d8cf264703b1966cf0dab1df8a002fcc0f2df94a'
ADJUSTED_SHA256 = '87514ff08498fa2e2a27bfe2f0a1026511b3c5f01acfbaecbf1f753392c33655'


def check_geometry(geometry, expected):
    data = json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise ValueError(f'geometry SHA-256 {actual}, expected {expected}')


def adjust_boo(geometry):
    coordinates = []
    for longitude, latitude in geometry['coordinates']:
        t = (latitude + 1.17) / 0.45
        if abs(t) < 1:
            # The smooth displacement vanishes at the edges of the band.
            longitude -= 0.30 * math.exp(1 - 1 / (1 - t * t))
        coordinates.append([longitude, latitude])
    return {'type': 'LineString', 'coordinates': coordinates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observation', required=True, type=Path, help='smoothed line JSON')
    parser.add_argument('--output', required=True, type=Path, help='output GeoJSON')
    args = parser.parse_args()
    geometry = json.loads(args.observation.read_text())['geometry']
    check_geometry(geometry, SMOOTHED_SHA256)
    adjusted = adjust_boo(geometry)
    check_geometry(adjusted, ADJUSTED_SHA256)
    feature = {'type': 'Feature', 'properties': {'method': 'smooth westward Boo adjustment'},
               'geometry': adjusted}
    args.output.write_text(json.dumps(feature, indent=2) + '\n')


if __name__ == '__main__':
    main()
