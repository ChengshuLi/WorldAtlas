#!/usr/bin/env python3
"""Assemble the two Arctic terrain replacements into the pinned fallback line.

Research-only northern excerpt; NOT a complete source-derived boundary.
"""
import argparse, hashlib, json
from pathlib import Path
from shapely.geometry import LineString

PINS = [
    '0a1aee04c5d60fec6f039b709720f2c7e4ae7f2522d8224fdfe0d9086978ccb4',
    'd07c10176b68d740c3f6c7d584badc5367b974d2704cb28ea2933ed784ea22b6',
    'f04de00934fcbd59bb68e1385997b0650a8e879c2fdf4f53dc13a467a5b955bd',
]


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''): h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source'); p.add_argument('gap00'); p.add_argument('gap02'); p.add_argument('output_directory', type=Path)
    a = p.parse_args(); paths = [a.source,a.gap00,a.gap02]
    if [sha(x) for x in paths] != PINS: raise ValueError('pinned input mismatch')
    source, gap00, gap02 = [json.loads(Path(x).read_text()) for x in paths]
    if len(source) != 4954: raise ValueError('unexpected fallback length')
    for candidate, gap in [(gap00,'00'),(gap02,'02')]:
        if candidate['gap'] != gap or candidate['product'] != 'arctic' or candidate['status'] != 'exploratory-not-selected':
            raise ValueError('unexpected candidate provenance')
        if candidate['coordinates'][0] != candidate['north']['point'] or candidate['coordinates'][-1] != candidate['south']['point']:
            raise ValueError('interface endpoints do not match source crossings')
    i,j = gap00['north']['source_segment_index'],gap00['south']['source_segment_index']
    k,l = gap02['north']['source_segment_index'],gap02['south']['source_segment_index']
    if not 0 <= i < j < k < l < len(source)-1: raise ValueError('invalid source cut order')
    coords = source[:i+1] + gap00['coordinates'] + source[j+1:k+1] + gap02['coordinates'] + source[l+1:]
    if not LineString(coords).is_simple: raise ValueError('assembled candidate self-intersects')
    geometry = {'type':'LineString','coordinates':coords}
    digest = hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(',',':'), allow_nan=False).encode()).hexdigest()
    if [sha(x) for x in paths] != PINS: raise ValueError('input changed during assembly')
    a.output_directory.mkdir(parents=True, exist_ok=False)
    with (a.output_directory/'geometry.json').open('x') as f: json.dump(geometry, f, sort_keys=True, separators=(',',':'), allow_nan=False); f.write('\n')
    report = {'status':'research-not-selected','geometry_sha256':digest,'coordinate_count':len(coords),'source_cuts':[i,j,k,l],
              'input_sha256':PINS,'method':'15 m ArcticDEM D8 interfaces intersect and replace two gaps in the pinned historical fallback northern line',
              'limitations':['Only the northern excerpt is assembled; spring connection, full river and closure are absent.',
                             'The adjoining line remains historical fallback and is not a complete raw-source derivation.',
                             'Nearest crossing, terrain model, outlet crosswalk and resolution require final independent geographic review.',
                             'No selected data is written to Neon and no map is built.']}
    with (a.output_directory/'report.json').open('x') as f: json.dump(report,f,sort_keys=True,indent=2,allow_nan=False); f.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'limitations'},sort_keys=True))


if __name__ == '__main__': main()
