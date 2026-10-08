"""Version 1: longitude-first WGS84 source-edge areas and geodesic distances.

This diagnostic tooling never repairs an input or changes published footprints.
GeoJSON edges are interpreted as shortest, straight lon/lat segments, not great
circle arcs. Polar caps/hemisphere-scale rings require a separately reviewed method.
"""
import math
from pyproj import Geod, Transformer
from shapely.geometry import Polygon, box
from shapely.affinity import translate
from shapely import union_all
from ellipsoidal_area import area

VERSION = 'worldatlas-evidence-geometry-v1'
METHOD = {'version': VERSION, 'axis_order': 'longitude-latitude', 'crs': 'EPSG:4326',
          'area_method': 'WGS84 straight-source-edge ellipsoidal integral',
          'area_units': 'm2', 'distance_method': 'WGS84 inverse geodesic', 'distance_units': 'm'}
GEOD = Geod(ellps='WGS84')


def point(lon, lat):
    if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError('Expected finite longitude [-180,180], latitude [-90,90]')
    return lon, lat


def transform_point(lon, lat, target_crs):
    return Transformer.from_crs('EPSG:4326', target_crs, always_xy=True).transform(*point(lon, lat), errcheck=True)


def distance_m(a, b):
    return GEOD.inv(*point(*a), *point(*b))[2]


def _unwrap(ring):
    result = []
    for coordinate in ring.coords:
        if len(coordinate) != 2:
            raise ValueError('Only two-dimensional GeoJSON is supported')
        x, y = point(*coordinate)
        if abs(y) >= 90:
            raise ValueError('Polar-cap vertices require a separate reviewed method')
        if result:
            delta = x - result[-1][0]
            if math.isclose(abs(delta) % 360, 180, abs_tol=1e-12):
                raise ValueError('Ambiguous 180-degree edge requires explicit segmentation')
            x += 360 * round((result[-1][0] - x) / 360)
        result.append((x, y))
    if result[0] != result[-1]:
        raise ValueError('Ring winds around a pole; use a polar-cap method')
    return result


def canonical_land(geometry):
    if geometry.is_empty or geometry.geom_type not in ('Polygon', 'MultiPolygon'):
        raise ValueError('Expected nonempty Polygon or MultiPolygon land')
    pieces = []
    for p in ([geometry] if geometry.geom_type == 'Polygon' else geometry.geoms):
        outer = _unwrap(p.exterior)
        center = sum(x for x, _ in outer) / len(outer)
        holes = []
        for ring in p.interiors:
            hole = _unwrap(ring)
            shift = 360 * round((center - sum(x for x, _ in hole) / len(hole)) / 360)
            holes.append([(x + shift, y) for x, y in hole])
        q = Polygon(outer, holes)
        if not q.is_valid:
            raise ValueError('Invalid unwrapped land geometry; inspect a diagnostic clone, do not silently MakeValid')
        west, south, east, north = q.bounds
        if east - west >= 180 or north - south > 120:
            raise ValueError('Hemisphere-scale land exceeds v1 method scope; subdivide with reviewed evidence')
        for n in range(math.floor((west + 180) / 360), math.floor((east + 180) / 360) + 1):
            cut = q.intersection(box(-180 + 360*n, -90, 180 + 360*n, 90))
            if cut.area > 0:
                pieces.append(translate(cut, xoff=-360*n))
    result = union_all(pieces)
    if sum(area(piece) for piece in pieces) - area(result) > max(1e-6, area(result) * 1e-10):
        raise ValueError('Overlapping source multipart land; inspect instead of silently repairing')
    if result.is_empty or not result.is_valid or area(result) <= 0:
        raise ValueError('Land has no valid positive-area footprint')
    return result


def land_area_m2(geometry):
    return area(canonical_land(geometry))


def ownership_overlap(location, claims):
    """Strict >50% of entire land; union one polity's pieces before measuring.

    Contradictory positive-area claims remain unresolved. A small numerical
    threshold is recorded, not used to manufacture ownership for sparse sources.
    """
    land = canonical_land(location)
    total = area(land)
    groups = {}
    for entity, pieces in claims.items():
        if not isinstance(entity, str) or not entity:
            raise ValueError('Claims require stable entity IDs')
        groups[entity] = union_all([canonical_land(g) for g in pieces]).intersection(land)
    measured = {entity: area(g) for entity, g in groups.items()}
    shares = {entity: value / total for entity, value in measured.items()}
    coverage = area(union_all(list(groups.values()))) / total if groups else 0
    tolerance = 1e-8
    conflict = any(area(groups[a].intersection(groups[b])) / total > tolerance
                   for i, a in enumerate(groups) for b in list(groups)[i+1:])
    winners = [entity for entity, value in shares.items() if value > .5 + tolerance]
    owner = winners[0] if len(winners) == 1 and not conflict else None
    return {'owner': owner, 'status': 'derived' if owner else 'conflicting-claims' if conflict else 'no-majority',
            'denominator': 'entire-location-land', 'land_area_m2': total, 'coverage': coverage,
            'shares': dict(sorted(shares.items())), 'numerical_share_tolerance': tolerance, 'method': METHOD}

DRIFT_FIXTURE_MARKER = 'untrusted-materialized-helper'
