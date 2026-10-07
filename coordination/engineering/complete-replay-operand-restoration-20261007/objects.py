"""Complete inverse aliases; unmatched mappings are always ordinary full bodies."""
import json
import gzip
import io
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
            # The digest is a lookup index only. Every selected alias is resolved
            # and compared with complete canonical bytes before use.
            self.native.setdefault(key, []).append(alias)
            # Reconstruction was checked in full above; native index retains only
            # selectors/pins. Do not keep a second full source serialization.
            self.verified_aliases.clear()

    def begin(self, identity):
        # Prior component feature/physical/diagnosis bodies must not accumulate.
        self.verified_aliases.clear()
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
                    key = sha(raw)
                    previous = self.component.get(key, [])
                    if previous:
                        require(previous[0][0] == raw, 'Whole original object digest collision')
                        raw = previous[0][0]  # Share exact immutable bytes, not a copy.
                    self.component.setdefault(key, []).append((raw, self.alias(kind, identity, parts, value, raw=raw)))
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

    def alias(self, kind, identity, parts, value, *, raw=None):
        raw = canonical(value) if raw is None else raw
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
            self._accept_resolved(alias, expected, self._resolved_bytes(alias))
        require(self.verified_aliases[key] == expected, 'Previously verified inverse object changed')

    def _accept_resolved(self, alias, expected, reconstructed):
        require(reconstructed == expected, 'Executed inverse alias roundtrip differs')
        key = canonical(alias)
        if key not in self.verified_aliases:
            self.verified_aliases[key] = expected  # Share the checked immutable body.
        require(self.verified_aliases[key] == expected, 'Previously verified inverse object changed')

    def retain(self, value):
        if isinstance(value, dict) and value.get('type') in (
                'Polygon', 'MultiPolygon', 'GeometryCollection', 'LineString',
                'MultiLineString', 'Point', 'MultiPoint', 'LinearRing'):
            raw = canonical(value)
            key = sha(raw)
            for original, alias in self.component.get(key, []):
                if original == raw:
                    self.verify_alias(alias, raw)
                    return {'complete_inverse_alias': alias}
            for alias in self.native.get(key, []):
                original = self._resolved_bytes(alias)
                if original == raw:
                    self._accept_resolved(alias, raw, original)
                    return {'complete_inverse_alias': alias}
            if key in self.emitted:
                require(self._emitted_bytes(key) == raw, 'Whole geometry object digest collision')
            else:
                row = {'whole_geometry_sha256': key, 'geometry': value}
                row_raw = canonical(row)
                self.products.emit('geometry-objects', row)
                # Products.emit may flush first. The newly emitted complete row
                # is now at the end of the current bounded scientific buffer.
                kind = 'geometry-objects'
                self.emitted[key] = {
                    'ordinal': self.products.ordinals[kind],
                    'offset': len(self.products.buffers[kind]) - len(row_raw),
                    'bytes': len(row_raw), 'sha256': sha(row_raw)}
            return {'complete_ordinary_geometry_sha256': key}
        if isinstance(value, dict):
            return {key: self.retain(child) for key, child in value.items()}
        if isinstance(value, list):
            return [self.retain(child) for child in value]
        return value

    def _emitted_bytes(self, key):
        locator = self.emitted[key]
        kind = 'geometry-objects'
        ordinal = locator['ordinal']
        if ordinal == self.products.ordinals[kind] and kind in self.products.buffers:
            body = self.products.buffers[kind]
        else:
            name = f'{kind}-{ordinal:03}.jsonl.gz'
            matches = [pin for pin in self.products.outputs if pin['path'] == name]
            require(len(matches) == 1, 'Missing/duplicate emitted whole shard descriptor')
            pin = matches[0]
            require(0 <= pin['bytes'] <= 33554432 and
                    0 <= pin['uncompressed_bytes'] <= 33554432, 'Emitted shard bound differs')
            target = self.products.directory / name
            require(target.is_file() and not any(part.is_symlink() for part in
                    (target, *target.parents)), 'Emitted shard must remain ordinary without symlink ancestors')
            with target.open('rb') as stream:
                encoded = stream.read(pin['bytes'] + 1)
            require(len(encoded) == pin['bytes'] and sha(encoded) == pin['sha256'],
                    'Emitted whole encoded shard changed')
            with gzip.GzipFile(fileobj=io.BytesIO(encoded)) as stream:
                body = stream.read(pin['uncompressed_bytes'] + 1)
            require(len(body) == pin['uncompressed_bytes'] and
                    sha(body) == pin['uncompressed_sha256'], 'Emitted whole decoded shard changed')
        start, length = locator['offset'], locator['bytes']
        require(0 <= start and 0 <= length <= 33554432 and start + length <= len(body),
                'Emitted complete row locator escaped shard')
        row_raw = bytes(body[start:start + length])
        require(sha(row_raw) == locator['sha256'], 'Emitted complete geometry row changed')
        row = json.loads(row_raw)
        require(row['whole_geometry_sha256'] == key, 'Emitted geometry identity changed')
        return canonical(row['geometry'])

    def resolve_alias(self, alias):
        value, _ = self._resolved(alias)
        return value

    def _resolved_bytes(self, alias):
        value, raw = self._resolved(alias)
        # Drop the newly rebuilt mapping before another large full-byte check.
        del value
        return raw

    def _resolved(self, alias):
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
        return value, raw
