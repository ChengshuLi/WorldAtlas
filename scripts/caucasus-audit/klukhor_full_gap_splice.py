"""Build unselected Klukhor gap splice alternatives from research geometry."""
import json

from geodesic_line import GeodesicLine


def nearest_source_location(source_coords, query_lonlat):
    """Return an unambiguous WGS84 nearest point on a coordinate-linear source."""
    result = GeodesicLine(source_coords).closest(query_lonlat)
    if result['ambiguous']:
        raise ValueError('bridge endpoint has ambiguous WGS84 nearest location')
    return result


def validated_splice_measures(source_geometry, source_coords, start_point, end_point):
    """Require exact topological joins, WGS84 unambiguity, and forward order.

    The geometry distance calls are exact coordinate-space coincidence tests,
    not physical distance measurements. No geographic tolerance or connector
    is inferred; any off-line endpoint fails closed. The geometry projection
    converts known on-line points to substring measures only.
    """
    if source_geometry.distance(start_point) != 0.0:
        raise ValueError('splice start is not topologically on the source')
    if source_geometry.distance(end_point) != 0.0:
        raise ValueError('bridge endpoint is not topologically on the source')
    source = GeodesicLine(source_coords)
    start = source.closest((start_point.x, start_point.y))
    end = source.closest((end_point.x, end_point.y))
    if start['ambiguous'] or end['ambiguous']:
        raise ValueError('splice source location is ambiguous under WGS84')
    start_measure = source_geometry.project(start_point)
    end_measure = source_geometry.project(end_point)
    if not start_measure < end_measure or not start['station_m'] < end['station_m']:
        raise ValueError('splice source endpoints are not ordered')
    return start_measure, end_measure, end


def require_exact_join(left, right, message):
    """Reject a proposed join unless the two coordinates coincide exactly."""
    if tuple(left) != tuple(right):
        raise ValueError(message)


def assemble_splice_coordinates(prefix, interface, bridge, suffix):
    """Assemble coordinate sequences only across exact existing junctions."""
    if not prefix or not interface or not bridge or not suffix:
        raise ValueError('splice components must be non-empty')
    require_exact_join(prefix[-1], interface[0], 'prefix/interface junction is not exact')
    require_exact_join(interface[-1], bridge[0], 'interface/bridge junction is not exact')
    require_exact_join(bridge[-1], suffix[0], 'bridge/suffix junction is not exact')
    cut = list(interface) + list(bridge)[1:]
    full = list(prefix) + cut[1:] + list(suffix)[1:]
    return cut, full


def main():
    from shapely.geometry import LineString, Point, shape, mapping
    from shapely.ops import substring

    source_coords = json.load(open('caucasus-anapa-abin-combined-candidate.json'))['coordinates']
    src = LineString(source_coords)
    geom = shape(json.load(open('klukhor-jaxa-interface-research.json'))['features'][0]['geometry'])
    cross = src.intersection(geom)
    points = sorted([p for p in getattr(cross, 'geoms', [cross]) if p.geom_type == 'Point'], key=src.project)
    start = points[0]
    start_measure = src.project(start)
    prefix = substring(src, 0, start_measure)
    interface = substring(geom, geom.project(start), 0)
    require_exact_join(src.coords[0], prefix.coords[0], 'prefix does not preserve source start')
    for weight in (0, 1, 4):
        bridge = shape(json.load(open('klukhor-north-gap-%d-research.json' % weight)))
        bridge_end = Point(bridge.coords[-1])
        _, end_measure, _ = validated_splice_measures(src, source_coords, start, bridge_end)
        suffix = substring(src, end_measure, src.length)
        old = substring(src, start_measure, end_measure)
        cut_coords, full_coords = assemble_splice_coordinates(
            list(prefix.coords), list(interface.coords), list(bridge.coords), list(suffix.coords))
        cut = LineString(cut_coords)
        full = LineString(full_coords)
        require_exact_join(full.coords[0], src.coords[0], 'splice changed the source start endpoint')
        require_exact_join(full.coords[-1], src.coords[-1], 'splice changed the source end endpoint')
        print('weight', weight, 'old', round(GeodesicLine(list(old.coords)).length),
              'new', round(GeodesicLine(list(cut.coords)).length), 'cut simple', cut.is_simple,
              'full simple', full.is_simple,
              'preserved endpoints', full.coords[0] == src.coords[0] and full.coords[-1] == src.coords[-1])
        if full.is_simple and cut.is_simple:
            for path, geometry in [('klukhor-gap-old-%d-research.json' % weight, old),
                                   ('klukhor-gap-cut-%d-research.json' % weight, cut),
                                   ('klukhor-gap-full-%d-research.json' % weight, full)]:
                json.dump(mapping(geometry), open(path, 'w'))


if __name__ == '__main__':
    main()
