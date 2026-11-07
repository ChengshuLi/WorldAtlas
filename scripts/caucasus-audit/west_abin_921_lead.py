"""Screen an OSM summit against the selected line and complete Abin alternative.

The summit's identity and relation to the published 921.5 m peak are not
independently verified. This is a geographic lead, not a boundary decision.
"""
import hashlib
import json
import sys
from pathlib import Path
from geodesic_line import GeodesicLine, distance

PINS = ('081f5909935023255cf9f0b13f06102aaa97cc19a15715b6cabb9964b7a20f25',
        '55ff28e152ad22dff2d5c3389ab270e8b583bf48d2840210b418953e075832b7')
PEAK = (38.3115831, 44.5966511)  # OSM node 13276920139, ele=921 m
JOIN = (38.31791666666666, 44.59583333333336)


def main(paths):
    if len(paths) != 2:
        raise ValueError('expected selected and full alternative files')
    report = {'peak_to_join_m': distance(PEAK, JOIN), 'lines': []}
    for name, expected in zip(paths, PINS):
        raw = Path(name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('geometry input hash mismatch')
        line = GeodesicLine(json.loads(raw)['coordinates'])
        nearest = line.closest(PEAK)
        report['lines'].append({'geometry_file_sha256': expected, 'nearest': nearest,
                                'samples': [{'offset_m': d, 'point': line.point(nearest['station_m'] + d)}
                                            for d in (-1000, -500, 0, 500, 1000, 2000)]})
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == '__main__':
    main(sys.argv[1:])
