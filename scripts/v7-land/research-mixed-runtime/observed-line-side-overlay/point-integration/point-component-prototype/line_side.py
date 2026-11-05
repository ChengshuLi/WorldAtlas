"""A bounded, research-only test of a point against an observed line segment.

An observed segment is not a surveyed border.  Never extend it across a gap,
and require a human-selected safety margin for the schematic observation.
"""
import hashlib
import json
import math
from pyproj import Geod


def check(observation, point, expected_side, minimum_separation_m):
    def need(value, message):
        if not value:
            raise ValueError(message)

    need(isinstance(observation, dict), 'missing line observation')
    geometry = observation.get('geometry')
    need(isinstance(geometry, dict) and set(geometry) == {'type', 'coordinates'}
         and geometry['type'] == 'MultiLineString', 'invalid line geometry')
    encoded = json.dumps(geometry, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    need(digest == observation.get('geometry_sha256'), 'line geometry hash mismatch')
    need(isinstance(point, list) and len(point) == 2 and
         all(type(v) in (int, float) and math.isfinite(v) for v in point), 'invalid point')
    x, y = point
    need(-180 <= x <= 180 and -90 <= y <= 90, 'point outside geographic bounds')
    need(expected_side in ('west', 'east') and type(minimum_separation_m) in (int, float)
         and math.isfinite(minimum_separation_m) and 0 < minimum_separation_m <= 200000,
         'invalid side or review margin')
    lines = geometry['coordinates']
    need(isinstance(lines, list) and 0 < len(lines) <= 100, 'invalid segments')
    intersections = []
    for segment in lines:
        need(isinstance(segment, list) and 2 <= len(segment) <= 10000, 'invalid segment')
        # An endpoint has no margin against extending the trace beyond its frame.
        prev = None
        direction = None
        for p in segment:
            need(isinstance(p, list) and len(p) == 2 and
                 all(type(v) in (int, float) and math.isfinite(v) for v in p)
                 and -180 <= p[0] <= 180 and -90 <= p[1] <= 90, 'invalid vertex')
            if prev is not None:
                dy = p[1] - prev[1]
                need(dy != 0 and abs(p[0] - prev[0]) < 180, 'ambiguous horizontal or dateline segment')
                this_direction = 1 if dy > 0 else -1
                need(direction is None or direction == this_direction, 'nonmonotonic segment')
                direction = this_direction
                # Half-open intervals avoid counting a shared vertex twice.
                if min(prev[1], p[1]) <= y < max(prev[1], p[1]):
                    intersections.append(prev[0] + (p[0] - prev[0]) * (y - prev[1]) / dy)
            prev = p
        need(y != segment[0][1] and y != segment[-1][1], 'point latitude coincides with a segment endpoint')
    need(len(intersections) == 1, 'point latitude outside or ambiguous across visible segments')
    delta = x - intersections[0]
    need(0 < abs(delta) < 180, 'ambiguous point-to-line longitude')
    # This is distance to the same-latitude intersection, not minimum distance to the polyline.
    _, _, separation_m = Geod(ellps='WGS84').inv(x, y, intersections[0], y)
    need(math.isfinite(separation_m) and separation_m >= minimum_separation_m, 'same-latitude geodesic separation below review screen')
    side = 'east' if delta > 0 else 'west'
    need(side == expected_side, 'point on unexpected side')
    return {'method': 'observed_line_latitude_intersection_v1',
            'line_id': observation.get('line_id'), 'geometry_sha256': digest,
            'expected_side': expected_side, 'side': side,
            'minimum_separation_m': minimum_separation_m,
            'same_latitude_separation_m': round(separation_m, 3),
            'separation_method': 'WGS84_geodesic_to_same_latitude_intersection',
            'limitation': 'Approximate schematic line; side test is not a surveyed boundary or a whole-component identity proof.'}
