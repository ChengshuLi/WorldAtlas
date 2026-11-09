"""Resolve regional island components, never individual cells.

This is a research rule. Input roots are ephemeral IDs from one pinned physical
component generation; source-authentication and selected-claim replay are the
caller's responsibility. It does not build or publish a map.
"""
from bisect import bisect_left
import hashlib
import json
from math import isfinite

ASIA = 18
OCEANIA = 22
SOURCE_ID = "anu-west-new-guinea-lydekker-ch08"
SOURCE_VERSION = "2025-4bcc38d0da4f-official"
SOURCE_PDF_SHA256 = "4bcc38d0da4f8062ebdc49c10af8e14c640215a249417700f7254526d45b8fec"
# Approximately 0.011 mm of longitude at the equator, solely numerical.
BOUNDARY_EPSILON_DEGREES = 1e-10


def verified_line(observation, line_pin):
    """Authenticate the Neon identity and exact canonical geometry bytes."""
    _require(isinstance(line_pin,dict) and set(line_pin)=={'line_id','geometry_sha256'} and
             isinstance(line_pin['line_id'],str) and line_pin['line_id'] and
             isinstance(line_pin['geometry_sha256'],str) and len(line_pin['geometry_sha256'])==64 and
             all(c in '0123456789abcdef' for c in line_pin['geometry_sha256']), 'invalid approved line pin')
    _require(isinstance(observation, dict) and observation.get("line_id") == line_pin['line_id'], "unexpected line identity")
    _require(observation.get("source_id") == SOURCE_ID and
             observation.get("source_version") == SOURCE_VERSION and
             observation.get("status") == "research" and
             isinstance(observation.get("provenance"), dict) and
             observation["provenance"].get("source_pdf_sha256") == SOURCE_PDF_SHA256,
             "line provenance mismatch")
    geometry = observation.get("geometry")
    raw = json.dumps(geometry, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    digest = hashlib.sha256(raw).hexdigest()
    _require(digest == line_pin["geometry_sha256"] and observation.get("geometry_sha256") == digest, "line geometry hash mismatch")
    return Line(geometry)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _root(value):
    return type(value) is int and 0 <= value < 0xffffffff


class Line:
    """A latitude-monotonic, continuous WGS84 trace; no extrapolation."""
    def __init__(self, geometry):
        _require(isinstance(geometry, dict) and geometry.get('type') == 'LineString', 'expected LineString')
        points = geometry.get('coordinates')
        _require(isinstance(points, list) and len(points) >= 2, 'missing line vertices')
        for point in points:
            _require(isinstance(point, (list, tuple)) and len(point) == 2 and
                     all(type(x) in (int, float) and isfinite(x) for x in point) and
                     -180 <= point[0] <= 180 and -90 <= point[1] <= 90, 'invalid vertex')
        _require(all(a[1] > b[1] for a, b in zip(points, points[1:])), 'line must run strictly north to south')
        _require(all(abs(a[0]-b[0]) < 180 for a,b in zip(points, points[1:])), 'dateline ambiguity')
        self.points = list(reversed(points))
        self.lats = [p[1] for p in self.points]

    def side(self, lon, lat):
        _require(type(lon) in (int, float) and type(lat) in (int, float) and
                 isfinite(lon) and isfinite(lat) and -180 <= lon <= 180 and
                 -90 <= lat <= 90, 'invalid center')
        cut = self.longitude(lat)
        if cut is None:
            return None
        if abs(lon - cut) <= BOUNDARY_EPSILON_DEGREES:
            return 'boundary'
        return 'west' if lon < cut else 'east'

    def longitude(self, lat):
        _require(type(lat) in (int, float) and isfinite(lat) and -90 <= lat <= 90, 'invalid latitude')
        if not self.lats[0] <= lat <= self.lats[-1]:
            return None
        i = bisect_left(self.lats, lat)
        if i == 0:
            cut = self.points[0][0]
        elif i == len(self.lats):
            cut = self.points[-1][0]
        else:
            a, b = self.points[i-1], self.points[i]
            cut = a[0] + (b[0]-a[0]) * ((lat-a[1])/(b[1]-a[1]))
        return cut


def resolve(components, selected, mainland_roots=(), pending_roots=()):
    """Return whole-root proposals and review reasons.

    components maps root to counts from a COMPLETE global scan: total,
    in_scope, west, east, boundary, outside_latitude. in_scope is a pinned
    regional window. Side counts partition in_scope exactly. selected maps
    roots to already authenticated and replayed selected affiliation codes,
    including authoritative group membership. Any selected claim wins, even
    across endpoints. Conflicting claims are errors. Components entirely or
    partially outside the region or latitude extent are not newly classified.
    Mainland witnesses are protected. The caller supplies pending_roots for
    documented unresolved group conflicts; those roots remain in review.
    Other unclaimed whole components may receive a line-side proposal. The
    caller must authenticate the generation, group evidence, and full scan.
    """
    _require(isinstance(components, dict) and isinstance(selected, dict), 'invalid inputs')
    _require(all(_root(r) for r in mainland_roots), 'invalid mainland root')
    protected = set(mainland_roots)
    _require(all(_root(r) for r in pending_roots), 'invalid pending root')
    pending = set(pending_roots)
    proposals, review = {}, {}
    for root, item in components.items():
        _require(_root(root) and isinstance(item, dict), 'invalid component')
        keys = ('total', 'in_scope', 'west', 'east', 'boundary', 'outside_latitude')
        _require(all(type(item.get(k)) is int and item[k] >= 0 for k in keys), 'invalid counts')
        _require(item['total'] > 0 and item['in_scope'] <= item['total'] and
                 sum(item[k] for k in keys[2:]) == item['in_scope'], 'inconsistent complete scan')
        codes = selected.get(root, [])
        _require(isinstance(codes, (list, tuple, set)) and all(type(c) is int and c in (ASIA,OCEANIA) for c in codes), 'invalid selected claims')
        _require(len(set(codes)) <= 1, 'conflicting selected claims')
        if root in protected:
            _require(not codes, 'selected claim intersects mainland witness')
            review[root] = 'protected_mainland'
        elif root in pending:
            review[root] = 'source_group_pending_review'
        elif codes:
            proposals[root] = {'code': next(iter(codes)), 'basis': 'selected_affiliation'}
        elif not item['in_scope']:
            continue
        elif item['in_scope'] != item['total']:
            review[root] = 'partly_outside_region'
        elif item['outside_latitude']:
            review[root] = 'outside_line_latitude'
        elif item['boundary'] or (item['west'] and item['east']):
            review[root] = 'crosses_or_touches_line'
        elif item['west'] or item['east']:
            proposals[root] = {'code': ASIA if item['west'] else OCEANIA, 'basis': 'whole_component_line_side'}
        else:
            raise ValueError('empty in-scope component')
    _require(set(selected).issubset(components), 'selected root missing from complete scan')
    return {'proposals': proposals, 'review': review}
