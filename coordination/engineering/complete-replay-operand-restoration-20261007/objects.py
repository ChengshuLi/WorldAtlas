"""Complete inverse aliases; unmatched mappings are always ordinary full bodies."""
import json
from shapely.affinity import translate
from source import canonical, sha, require


def pointer(value, parts):
    for part in parts:
        require(type(part) in (str, int), 'Unsafe complete-object selector')
        if type(part) is int:
            require(type(value) is list and 0 <= part < len(value), 'Bad whole-object ordinal')
        else:
            require(type(value) is dict and part in value, 'Bad whole-object member')
        value = value[part]
    return value


class Objects:
    def __init__(self, products, loaded, records, native_aliases):
        self.products, self.loaded, self.records = products, loaded, records
        self.native_aliases = native_aliases
        self.verified_aliases = {}
        self.native = {}
        self.component = {}
        self.emitted = {}
        self.kernel = loaded['modules']['kernel']
        wanted = {(q['source_id'], q['periodic_offset']) for row, pin in
                  loaded['physical'].values() for q in row['query_relations']}
        for identity, offset in sorted(wanted):
            geometry = records[identity][1]
            if geometry is None:
                continue
            shifted = translate(geometry, xoff=offset) if offset else geometry
            value = self.kernel.ordinary_mapping(shifted)
            raw = canonical(value)
            key = sha(raw)
            alias = {'kind': 'complete-native-record-geometry', 'source_id': identity,
                     'periodic_offset': offset, 'original_native_record': native_aliases[identity],
                     'decoder': 'literal original comparison.decode_record then original periodic translate',
                     'whole_mapping_bytes': len(raw), 'whole_mapping_sha256': key}
            self.verify_alias(alias, raw)
            # Keep the exact canonical body for collision/container equality, not
            # merely its digest. These are in-memory source operands, not outputs.
            self.native.setdefault(key, []).append((raw, alias))

    def begin(self, identity):
        self.component = {}
        feature = self.loaded['state']['candidates'][identity]
        row, pin = self.loaded['physical'][identity]
        diagnosis = self.loaded['diagnoses'][identity]
        for kind, root in (('candidate', feature), ('physical', row), ('diagnosis', diagnosis)):
            def visit(value, parts):
                if isinstance(value, dict) and value.get('type') in (
                        'Polygon', 'MultiPolygon', 'GeometryCollection', 'LineString',
                        'MultiLineString', 'Point', 'MultiPoint', 'LinearRing'):
                    raw = canonical(value)
                    self.component.setdefault(sha(raw), []).append((raw, self.alias(kind, identity, parts, value)))
                    if value['type'] == 'GeometryCollection':
                        visit(value['geometries'], parts + ['geometries'])
                    return
                if isinstance(value, dict):
                    for key, child in value.items():
                        visit(child, parts + [key])
                elif isinstance(value, list):
                    for ordinal, child in enumerate(value):
                        if isinstance(child, (dict, list)):
                            visit(child, parts + [ordinal])
            visit(root, [])

    def alias(self, kind, identity, parts, value):
        raw = canonical(value)
        alias = {'kind': 'complete-original-object', 'component_id': identity,
                 'original_object': kind, 'selector': parts,
                 'whole_object_bytes': len(raw), 'whole_object_sha256': sha(raw)}
        if kind == 'physical':
            alias['original_whole_row'] = self.loaded['physical'][identity][1]
        elif kind == 'candidate':
            alias['complete_candidate_feature_sha256'] = self.loaded['state']['routing'][identity]['current_feature_sha256']
        self.verify_alias(alias, raw)
        return alias

    def verify_alias(self, alias, expected):
        key = canonical(alias)
        if key not in self.verified_aliases:
            reconstructed = canonical(self.resolve_alias(alias))
            require(reconstructed == expected, 'Executed inverse alias roundtrip differs')
            self.verified_aliases[key] = reconstructed
        require(self.verified_aliases[key] == expected, 'Previously verified inverse object changed')

    def retain(self, value):
        if isinstance(value, dict) and value.get('type') in (
                'Polygon', 'MultiPolygon', 'GeometryCollection', 'LineString',
                'MultiLineString', 'Point', 'MultiPoint', 'LinearRing'):
            raw = canonical(value)
            key = sha(raw)
            for original, alias in self.component.get(key, []) + self.native.get(key, []):
                if original == raw:
                    self.verify_alias(alias, raw)
                    return {'complete_inverse_alias': alias}
            if key in self.emitted:
                require(self.emitted[key] == raw, 'Whole geometry object digest collision')
            else:
                self.products.emit('geometry-objects', {'whole_geometry_sha256': key, 'geometry': value})
                self.emitted[key] = raw
            return {'complete_ordinary_geometry_sha256': key}
        if isinstance(value, dict):
            return {key: self.retain(child) for key, child in value.items()}
        if isinstance(value, list):
            return [self.retain(child) for child in value]
        return value

    def resolve_alias(self, alias):
        if alias['kind'] == 'complete-native-record-geometry':
            identity, offset = alias['source_id'], alias['periodic_offset']
            require(type(identity) is int and type(offset) in (int, float) and
                    offset in (-360, 0, 360), 'Bad native inverse alias identity/frame')
            require(alias['original_native_record'] == self.native_aliases[identity],
                    'Native inverse alias record binding differs')
            geometry = self.records[identity][1]
            value = self.kernel.ordinary_mapping(translate(geometry, xoff=offset) if offset else geometry)
            expected_bytes, expected_sha = alias['whole_mapping_bytes'], alias['whole_mapping_sha256']
        else:
            require(alias['kind'] == 'complete-original-object', 'Unknown inverse alias kind')
            identity, kind = alias['component_id'], alias['original_object']
            roots = {'candidate': self.loaded['state']['candidates'][identity],
                     'physical': self.loaded['physical'][identity][0],
                     'diagnosis': self.loaded['diagnoses'][identity]}
            require(kind in roots, 'Unknown original containing object')
            if kind == 'physical':
                require(alias['original_whole_row'] == self.loaded['physical'][identity][1],
                        'Physical inverse alias row binding differs')
            elif kind == 'candidate':
                require(alias['complete_candidate_feature_sha256'] ==
                        self.loaded['state']['routing'][identity]['current_feature_sha256'],
                        'Candidate inverse alias whole binding differs')
            value = pointer(roots[kind], alias['selector'])
            expected_bytes, expected_sha = alias['whole_object_bytes'], alias['whole_object_sha256']
        raw = canonical(value)
        require(len(raw) == expected_bytes and sha(raw) == expected_sha,
                'Complete inverse alias reconstructed bytes differ')
        return value
