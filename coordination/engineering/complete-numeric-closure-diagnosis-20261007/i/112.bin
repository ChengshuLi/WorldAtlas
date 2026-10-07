"""Complete source-relative comparison methods for issue1261; no polygon repair."""
import hashlib
import math
import struct
import numpy as np
from shapely import prepare, union_all
from shapely.affinity import translate
from shapely.geometry import Polygon, GeometryCollection, mapping

HEADER = struct.Struct('>3I4i2I2i')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class ValidityCache:
    """Actual immutable geometry-object checks, never caller-supplied true flags."""
    def __init__(self):
        self._rows = {}
        self.checks = 0
        self.hits = 0
    def check(self, geometry):
        identity = id(geometry)
        previous = self._rows.get(identity)
        if previous is not None and previous[0] is geometry:
            self.hits += 1
            return previous[1]
        valid = bool(geometry.is_valid)
        self.checks += 1
        # Keep the actual immutable object so a recycled id cannot certify a
        # different pointset. Translation produces its own separately checked
        # object; neither validity nor binary64 coordinates are assumed equal.
        self._rows[identity] = (geometry, valid)
        return valid


def checked_validity(geometry, cache):
    return cache.check(geometry) if cache is not None else bool(geometry.is_valid)


def decode_record(header, raw_points, ordinal, offset, validity=None):
    """Preserve native bodies; honor both GMT point rule and segment range."""
    values = HEADER.unpack(header)
    identity, count, flag, west, east, south, north, area, full_area, container, ancestor = values
    if len(raw_points) != count * 8:
        raise ValueError('Incomplete original coordinate bytes')
    native = np.frombuffer(raw_points, dtype='>i4').reshape(count, 2)
    coords = native.astype(np.float64)
    coords *= 1.0e-6
    seam = (flag >> 16) & 3
    threshold = 270000000 if ordinal == 0 else 180000000
    shifted = ((native[:, 0] > threshold) & bool(seam)) | (west > 180000000)
    coords[shifted, 0] -= 360.0
    if identity == 0:
        declared_range = 'GMT_IS_M180_TO_P270_RANGE'
    elif identity == 4:
        declared_range = 'GMT_IS_M180_TO_P180_RANGE'
    elif seam & 2:
        declared_range = 'GMT_IS_0_TO_P360_RANGE'
        # Apply the source segment's explicit range, never adjacent-point unwrap.
        coords[coords[:, 0] < 0.0, 0] += 360.0
    else:
        declared_range = 'GMT_IS_M180_TO_P180_RANGE'
    pointset_sha = digest(coords.astype('>f8').tobytes(order='C'))
    closed = count > 0 and bool(np.array_equal(native[0], native[-1]))
    level = flag & 255
    meta = dict(id=identity, ordinal=ordinal, native_offset=offset,
                native_record_bytes=44+len(raw_points), n=count, level=level,
                flag=flag, header_native_values=list(values), seam_flags=seam,
                source_flag=(flag >> 24) & 1, river_lake=(flag >> 25) & 1,
                container=container, ancestor=ancestor, declared_range=declared_range,
                record_sha256=digest(header+raw_points),
                coordinate_bytes_sha256=digest(raw_points),
                decoded_pointset_binary64_sha256=pointset_sha,
                native_closed=closed, geometry_issues=[])
    finite = bool(np.isfinite(coords).all())
    if not finite or not count:
        meta['geometry_issues'].append('nonfinite-or-empty-original-coordinates')
        return meta, None
    meta['decoded_pointset_bounds'] = [float(coords[:,0].min()),float(coords[:,1].min()),
                                       float(coords[:,0].max()),float(coords[:,1].max())]
    if level not in (1,2,3,4):
        meta['geometry_issues'].append('alternate-antarctic-level-context-only')
        return meta, None
    if not closed:
        meta['geometry_issues'].append('unclosed-native-ring-not-implicitly-closed')
        return meta, None
    geometry = Polygon(coords)
    meta['whole_original_geometry_valid'] = checked_validity(geometry, validity)
    if geometry.is_empty or not meta['whole_original_geometry_valid']:
        meta['geometry_issues'].append('invalid-original-source-polygon')
    return meta, geometry


def relation(candidate, source, source_id, periodic_offset=0, validity=None):
    """After conservative bbox selection, keep every tested record relation."""
    row = dict(source_id=source_id, periodic_offset=periodic_offset)
    if candidate.is_empty or not checked_validity(candidate, validity):
        row.update(status='unknown', issue='invalid-complete-candidate')
        return row, None
    if source.is_empty or not checked_validity(source, validity):
        row.update(status='unknown', issue='invalid-complete-source')
        return row, None
    try:
        source_covers = bool(source.covers(candidate))
        candidate_covers = bool(candidate.covers(source))
        intersects = bool(source.intersects(candidate))
        disjoint = bool(source.disjoint(candidate))
        row.update(source_covers_candidate=source_covers,
                   candidate_covers_source=candidate_covers,
                   intersects=intersects, disjoint=disjoint)
        if intersects == disjoint or ((source_covers or candidate_covers) and not intersects):
            row.update(status='unknown', issue='contradictory-whole-geometry-predicates')
            return row, None
        if source_covers:
            row.update(status='checked', witness='complete-candidate-reconstruction')
            return row, candidate
        if candidate_covers:
            row.update(status='checked', witness='complete-source-record-reconstruction')
            return row, source
        if not intersects:
            row.update(status='checked', witness='disjoint-after-explicit-predicate')
            return row, GeometryCollection()
        piece = candidate.intersection(source)
        row.update(status='checked', witness='complete-operation-pointset')
        if piece.is_empty:
            row.update(status='unknown', issue='intersects-with-empty-intersection')
        elif piece.geom_type in ('Polygon','MultiPolygon') and piece.area <= 0:
            row.update(status='unknown', issue='nonempty-polygon-zero-planar-area')
        row['witness_geometry'] = mapping(piece)
        return row, piece
    except Exception as error:
        row.update(status='unknown', issue='geometry-operation-failed',
                   exception_type=type(error).__name__, exception_message=str(error))
        return row, None


def alternating_support(candidate, by_level):
    """Exact source-relative support; retain hierarchy disagreement witnesses.

    Supplied positive polygon pieces must already have complete source chains.
    Unknown source/query/candidate context is retained by the outer record reader.
    """
    levels = {level: union_all(by_level.get(level, [])) for level in (1,2,3,4)}
    violations = {f'L{level}-outside-L{level-1}':levels[level].difference(levels[level-1])
                  for level in (2,3,4)}
    land = union_all([levels[1].difference(levels[2]), levels[3].difference(levels[4])])
    inland_water = union_all([levels[2].difference(levels[3]), levels[4]])
    exterior = candidate.difference(levels[1])
    footprint = union_all([land,inland_water,exterior])
    missing = candidate.difference(footprint)
    extra = footprint.difference(candidate)
    overlap = land.intersection(inland_water)
    return dict(mapped_land_support=land, mapped_inland_water_support=inland_water,
                outside_mapped_L1_context=exterior, hierarchy_disagreements=violations,
                missing_reconstruction=missing, extra_reconstruction=extra,
                contradictory_land_water_support=overlap)


def conservative_source_pairs(candidate, tree, source_ids):
    """Every multipart footprint part and each explicit periodic frame is queried.

    Selection has no exact intersects predicate and does not invent geometry for
    an invalid source. The caller separately retains invalid source envelopes.
    """
    pieces = list(candidate.geoms) if candidate.geom_type == 'MultiPolygon' else [candidate]
    pairs = set()
    for periodic_offset in (-360,0,360):
        for piece in pieces:
            frame_piece = translate(piece, xoff=-periodic_offset) if periodic_offset else piece
            for position in tree.query(frame_piece):
                pairs.add((source_ids[int(position)],periodic_offset))
    return sorted(pairs)


def full_container_relation(child, parent, validity=None):
    """Whole original source polygons in documented periodic coordinate frames."""
    if child is None or parent is None or not checked_validity(child, validity) or not checked_validity(parent, validity):
        return dict(status='unknown', issue='invalid-or-unconstructed-full-container-member')
    prepare(parent)
    observations = []
    for offset in (-360,0,360):
        shifted = translate(child,xoff=offset) if offset else child
        try:
            if not checked_validity(shifted, validity):
                observations.append(dict(child_periodic_offset=offset,issue="invalid-complete-translated-container-child"))
                continue
            covers = bool(parent.covers(shifted))
            observations.append(dict(child_periodic_offset=offset,parent_covers_child=covers))
            if covers:
                return dict(status='supported',child_periodic_offset=offset,
                            whole_member_observations=observations)
        except Exception as error:
            observations.append(dict(child_periodic_offset=offset,issue='container-operation-failed',
                                     exception_type=type(error).__name__,exception_message=str(error)))
    return dict(status='unknown',issue='no-supported-whole-source-container-frame',
                whole_member_observations=observations)
