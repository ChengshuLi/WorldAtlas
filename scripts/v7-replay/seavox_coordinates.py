"""In-process Arrow fixed-15 candidate, certified by the selected geometry hash.

The existing scalar roundoff cleanup is expressed as ordinary array operations.
Unsupported numeric formats retain the scalar/OGR path; no input is omitted.
"""
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc


def ring_coordinates(points, dimension):
    if not len(points):
        return []
    values = np.asarray(points, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] < dimension:
        return None
    values = np.ascontiguousarray(values[:, :dimension])
    if not np.isfinite(values).all() or np.any(np.abs(values) >= 1000):
        return None
    # Decimal conversion performs the same fixed-15 rounding without a Python
    # formatter call for every ordinate. The geometry hash remains authoritative.
    decimal = pc.cast(pa.array(values.reshape(-1)), pa.decimal128(38, 15))
    text = pc.cast(decimal, pa.string())
    zeros_five = pc.match_substring_regex(text, '00000.$')
    zeros_seven = pc.and_not(pc.match_substring_regex(text, '0000000..$'), zeros_five)
    zero_case = pc.or_(zeros_five, zeros_seven)
    nines_five = pc.and_not(pc.match_substring_regex(text, '99999.$'), zero_case)
    nines_seven = pc.and_not(pc.match_substring_regex(text, '9999999..$'), pc.or_(zero_case, nines_five))
    rounded = pc.if_else(zeros_five, pc.round(decimal, ndigits=14, round_mode='towards_zero'),
        pc.if_else(zeros_seven, pc.round(decimal, ndigits=7, round_mode='towards_zero'),
            pc.if_else(nines_five, pc.round(decimal, ndigits=9, round_mode='half_to_even'),
                pc.if_else(nines_seven, pc.round(decimal, ndigits=6, round_mode='half_to_even'), decimal))))
    result = pc.cast(pc.cast(rounded, pa.string()), pa.float64()).to_numpy().copy()
    # Decimal has no signed zero, while canonical GeoJSON distinguishes -0.0.
    zero = result == 0
    result[zero] = np.copysign(0.0, values.reshape(-1)[zero])
    # Arrow prints tiny decimals in scientific notation. Its suffix is not the
    # fixed-15 suffix inspected above; retain the original scalar conversion
    # for those ordinates only, rather than forcing a whole-feature OGR fallback.
    scientific = pc.match_substring_regex(text, '[eE]').to_numpy(zero_copy_only=False)
    special = np.flatnonzero(scientific & (values.reshape(-1) != 0))
    if len(special):
        from extract_seavox_feature import geojson_coordinate
        for index in special:
            result[index] = geojson_coordinate(float(values.reshape(-1)[index]))
    return result.reshape(values.shape).tolist()


def geometry_coordinates(geometry):
    """Batch all rings of one feature, preserving polygon/ring/vertex order."""
    name = geometry.GetGeometryName()
    if name == 'POLYGON':
        polygons = [geometry]
    elif name == 'MULTIPOLYGON':
        polygons = [geometry.GetGeometryRef(index) for index in range(geometry.GetGeometryCount())]
        if any(polygon.GetGeometryName() != 'POLYGON' for polygon in polygons):
            return None
    else:
        return None
    coordinates, groups = [], {}
    for polygon_index, polygon in enumerate(polygons):
        dimension = 3 if polygon.Is3D() else 2
        coordinates.append([None] * polygon.GetGeometryCount())
        for ring_index in range(polygon.GetGeometryCount()):
            points = polygon.GetGeometryRef(ring_index).GetPoints()
            values = (np.asarray(points, dtype=np.float64)[:, :dimension] if points
                      else np.empty((0, dimension), dtype=np.float64))
            groups.setdefault(dimension, []).append((polygon_index, ring_index, values))
    for dimension, rings in groups.items():
        # One in-process conversion per dimension, not thousands of tiny kernel
        # invocations. This is full-feature batching, never an input cutoff.
        converted = ring_coordinates(np.concatenate([values for _, _, values in rings]), dimension)
        if converted is None:
            return None
        offset = 0
        for polygon_index, ring_index, values in rings:
            coordinates[polygon_index][ring_index] = converted[offset:offset + len(values)]
            offset += len(values)
    return {'type': 'Polygon' if name == 'POLYGON' else 'MultiPolygon',
            'coordinates': coordinates[0] if name == 'POLYGON' else coordinates}
