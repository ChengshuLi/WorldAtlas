#!/usr/bin/env python3
"""Identify prominent profile peaks as research candidates, never boundary decisions."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks
from terrain_screen import read_tiles, sample_point, transformer


def profile_peaks(samples, min_prominence, min_spacing_cells):
    """Return only interior peaks when the complete sampling window is valid."""
    if any(s['status'] != 'valid_mask_0' for s in samples):
        return []
    indices, properties = find_peaks(np.array([s['height_m'] for s in samples]),
                                     prominence=min_prominence, distance=min_spacing_cells)
    return [{**samples[int(i)], 'prominence_m': float(prominence)}
            for i, prominence in zip(indices, properties['prominences'])]


def profiles(features, line, section, minimum, maximum, epsg, tiles,
             half_width, step, prominence, spacing, require_stack=False):
    if half_width <= 0 or step <= 0 or half_width % step:
        raise ValueError('half-width must be a positive multiple of step')
    if prominence <= 0 or spacing <= 0:
        raise ValueError('peak prominence and spacing must be positive')
    forward, reverse = transformer(epsg)
    output = []
    for feature in features:
        p = feature['properties']
        distance = p['distance_along_section_m']
        if p['section'] != section or not minimum <= distance <= maximum:
            continue
        lon, lat = feature['geometry']['coordinates']
        x, y = forward.TransformPoint(lon, lat)[:2]
        index = p['source_edge_index']
        ax, ay = forward.TransformPoint(*line[index])[:2]
        bx, by = forward.TransformPoint(*line[index + 1])[:2]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        if not norm:
            raise ValueError('zero-length line edge')
        dx, dy = dx / norm, dy / norm
        samples = []
        for offset in range(-half_width, half_width + 1, step):
            x2, y2 = x - dy * offset, y + dx * offset
            lon2, lat2 = reverse.TransformPoint(x2, y2)[:2]
            samples.append({'offset_m': offset, **sample_point(tiles, lon2, lat2, require_stack)})
        peaks = profile_peaks(samples, prominence, math.ceil(spacing / step))
        nearest = min(peaks, key=lambda p: abs(p['offset_m'])) if peaks else None
        output.append({'distance_m': distance, 'center': [lon, lat],
                       'complete_mask_0_window': all(s['status'] == 'valid_mask_0' for s in samples),
                       'nearest_profile_peak': nearest, 'peak_count': len(peaks), 'samples': samples})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', required=True)
    parser.add_argument('--line', required=True)
    parser.add_argument('--tile', action='append', required=True)
    parser.add_argument('--require-stack', action='store_true')
    parser.add_argument('--section', type=int, required=True)
    parser.add_argument('--start-m', type=float, required=True)
    parser.add_argument('--end-m', type=float, required=True)
    parser.add_argument('--epsg', type=int, required=True)
    parser.add_argument('--half-width-m', type=int, default=1500)
    parser.add_argument('--step-m', type=int, default=25)
    parser.add_argument('--prominence-m', type=float, default=10)
    parser.add_argument('--peak-spacing-m', type=float, default=100)
    parser.add_argument('--output', required=True)
    a = parser.parse_args()
    if a.start_m > a.end_m:
        raise ValueError('start must precede end')
    line = json.loads(Path(a.line).read_text())
    if line.get('type') != 'LineString':
        raise ValueError('line must be a GeoJSON LineString geometry')
    features = json.loads(Path(a.samples).read_text())['features']
    result = profiles(features, line['coordinates'], a.section, a.start_m, a.end_m,
                      a.epsg, read_tiles(a.tile), a.half_width_m, a.step_m,
                      a.prominence_m, a.peak_spacing_m, a.require_stack)
    output = {'method': 'Interior profile peaks are local screening candidates, not connected ridges or proven watersheds. Full valid mask-0 window required.',
              'samples': result}
    Path(a.output).write_text(json.dumps(output, indent=2) + '\n')


if __name__ == '__main__':
    main()
