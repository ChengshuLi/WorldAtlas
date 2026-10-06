#!/usr/bin/env python3
"""Measure locally exported BDADMIN polygons with WorldAtlas v1 geography helpers."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from evidence.geometry import METHOD, VERSION, land_area_m2


def run(exports, comparison):
    comparison_path = Path(comparison)
    comparison = json.loads(comparison_path.read_text())
    output = []
    for item in comparison['area_helper_inputs']:
        path = Path(exports) / item['path']
        raw = path.read_bytes()
        if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('Temporary export hash mismatch: ' + item['path'])
        feature = json.loads(raw)
        value = land_area_m2(shape(feature['geometry']))
        output.append({'subject_id': item['subject_id'], 'feature_id': feature['id'],
                       'area_m2': value, 'unit': 'm2', 'input_bytes': len(raw),
                       'input_sha256': item['sha256'], 'source_archive_sha256': comparison['source_archive']['sha256']})
    return {'version': VERSION, 'helper_version': VERSION, 'method': METHOD,
            'comparison_result_sha256': hashlib.sha256(comparison_path.read_bytes()).hexdigest(),
            'areas': output}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exports', required=True, type=Path)
    parser.add_argument('--comparison', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    comparison_path = args.comparison
    result = run(args.exports, comparison_path)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, indent=2, sort_keys=True))
