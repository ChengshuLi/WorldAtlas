"""Stage a bilateral, source-clipped candidate. Never install or approve it."""
import argparse
import copy
import gzip
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from shapely import union_all
from shapely.geometry import shape, mapping, LineString, MultiPolygon, GeometryCollection
from evidence.immutable import Baseline, canonical_json, sha256

PREVIOUS = 'coordination/engineering/iran-pakistan-native-seam-971-20261005-local09/reproduce.py'
spec = importlib.util.spec_from_file_location('reviewed_native_comparison', ROOT / PREVIOUS)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def separate_polygonal_result(geometry):
    """Separate representations by geometry type, preserving every remainder."""
    polygons, other = [], []
    def collect(g):
        if g.is_empty:
            return
        if g.geom_type == 'Polygon':
            polygons.append(g)
        elif g.geom_type in ('MultiPolygon', 'GeometryCollection'):
            for child in g.geoms:
                collect(child)
        else:
            other.append(g)
    collect(geometry)
    if not polygons:
        raise ValueError('No areal candidate polygon')
    candidate = polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)
    return native.valid_polygon(candidate), GeometryCollection(other)


def build_candidate(component, current, sources):
    """Allocate only exact source intersections in the retained missing component."""
    native.valid_polygon(component)
    if set(current) != set(sources) or set(current) != {'IRN', 'PAK'}:
        raise ValueError('Both exact neighbors are required')
    for g in list(current.values()) + list(sources.values()):
        native.valid_polygon(g)
    source_union = union_all(list(sources.values()))
    if not source_union.covers(component):
        raise ValueError('Joint sources do not cover the entire retained component')
    if sources['IRN'].intersection(sources['PAK']).intersection(component).area > 0:
        raise ValueError('Sources contradict each other inside the component')
    existing_union = union_all(list(current.values()))
    additions = {country: component.intersection(g).difference(existing_union)
                 for country, g in sources.items()}
    joined = {country: current[country].union(addition) for country, addition in additions.items()}
    split = {country: separate_polygonal_result(geometry) for country, geometry in joined.items()}
    candidates = {country: pieces[0] for country, pieces in split.items()}
    proof = {}
    for country, candidate in candidates.items():
        change = candidate.difference(current[country])
        proof[country] = {
            'source_clipped_addition': native.measured_geometry(additions[country]),
            'actual_added_coverage': native.measured_geometry(change),
            'lost_existing_coverage': native.measured_geometry(current[country].difference(candidate)),
            'added_outside_component': native.measured_geometry(change.difference(component)),
            'added_outside_named_source': native.measured_geometry(change.difference(sources[country])),
            'nonpolygon_join_remnants': native.measured_geometry(split[country][1]),
            'full_union_before_representation_separation': native.measured_geometry(joined[country]),
            'candidate_valid': candidate.is_valid}
    combined = union_all(list(candidates.values()))
    prior_overlap = current['IRN'].intersection(current['PAK'])
    overlap = candidates['IRN'].intersection(candidates['PAK'])
    return candidates, {
        'neighbors': proof,
        'candidate_covers_entire_component': combined.covers(component),
        'candidate_component_uncovered': native.measured_geometry(component.difference(combined)),
        'new_neighbor_overlap': native.measured_geometry(overlap.difference(prior_overlap)),
        'baseline_neighbor_overlap': native.measured_geometry(prior_overlap),
        'partition_covers_entire_component': union_all(list(additions.values()) + [existing_union]).covers(component)}


def source_agreement(left, right):
    def elements(response):
        return {(e['type'], e['id']): e for e in response['elements']}
    a, b = elements(left), elements(right)
    shared_ways = sorted(key[1] for key in a.keys() & b.keys() if key[0] == 'way')
    if not shared_ways:
        raise ValueError('No shared original source ways')
    shared_nodes = set()
    for identity in shared_ways:
        if a[('way', identity)] != b[('way', identity)]:
            raise ValueError('Shared boundary way version/coordinates differ')
        shared_nodes.update(a[('way', identity)]['nodes'])
    for identity in sorted(shared_nodes):
        if a[('node', identity)] != b[('node', identity)]:
            raise ValueError('Shared boundary node version/coordinates differ')
    return {'shared_way_ids': shared_ways, 'shared_node_count': len(shared_nodes),
            'original_shared_elements_identical': True}


def propose(repo, commit, registry):
    base = Baseline(repo, registry['baseline_commit'], registry['baseline_files'])
    originals = Baseline(repo, commit, registry['source_files'])
    # The imported reviewed helper must equal its pinned baseline bytes.
    if (ROOT / PREVIOUS).read_bytes() != base.read(PREVIOUS):
        raise ValueError('Reviewed comparison helper differs from immutable baseline')
    features = json.loads(gzip.decompress(base.read(registry['component_path'])))['features']
    matches = [f for f in features if f.get('id') == native.COMPONENT_ID]
    if len(matches) != 1 or sha256(canonical_json(matches[0])) != registry['component_feature_sha256']:
        raise ValueError('Retained full component identity/hash mismatch')
    component_feature = matches[0]
    component = native.valid_polygon(shape(component_feature['geometry']))
    panjgur = json.loads(base.read(registry['panjgur_source_path']))
    saravan = json.loads(originals.read(registry['saravan_source_path']))
    agreement = source_agreement(saravan, panjgur)
    sources, assembly = {}, {}
    sources['IRN'], assembly['IRN'] = native.assemble_osm_boundary(saravan, 6555069)
    sources['PAK'], assembly['PAK'] = native.assemble_osm_boundary(panjgur, 3229274)
    parents = []
    pan_elements = {(e['type'], e['id']): e for e in panjgur['elements']}
    intersecting_ways = []
    for identity in agreement['shared_way_ids']:
        way = pan_elements[('way', identity)]
        line = LineString([(pan_elements[('node', n)]['lon'], pan_elements[('node', n)]['lat']) for n in way['nodes']])
        if line.intersects(component):
            intersecting_ways.append(identity)
    if sorted(int(identity) for identity in registry['parent_relation_paths']) != intersecting_ways:
        raise ValueError('Parent-relation evidence must cover every component-intersecting shared way')
    for way_id, path in registry['parent_relation_paths'].items():
        response = json.loads(originals.read(path))
        relations = {e['id']: e for e in response['elements'] if e['type'] == 'relation'}
        for identity in [6555069, 3229274, 304938, 307573]:
            if identity not in relations:
                raise ValueError('Missing original administrative parent relation')
            if not any(m['type'] == 'way' and m['ref'] == int(way_id) and m.get('role') == 'outer'
                       for m in relations[identity]['members']):
                raise ValueError('Declared parent does not contain the exact shared outer way')
        parents.append({'path': path, 'way_id': int(way_id), 'relation_ids': sorted(relations)})
    current, original_features = {}, {}
    for country, identity in native.SUBJECTS.items():
        values = json.loads(base.read(registry['subject_files'][country]))['features']
        matches = [f for f in values if f.get('id', f.get('properties', {}).get('id')) == identity]
        if len(matches) != 1:
            raise ValueError('Exact current identity absent or duplicated')
        original_features[country] = matches[0]
        current[country] = native.valid_polygon(shape(matches[0]['geometry']))
    candidates, proof = build_candidate(component, current, sources)
    after = []
    preservation = []
    for country in sorted(candidates):
        old = original_features[country]
        new = copy.deepcopy(old)
        new['geometry'] = mapping(candidates[country])
        after.append(new)
        preservation.append({'id': native.SUBJECTS[country], 'original_feature_sha256': sha256(canonical_json(old)),
                             'candidate_feature_sha256': sha256(canonical_json(new)),
                             'properties_unchanged': old['properties'] == new['properties'],
                             'parent_id_unchanged': old['properties']['parent_id'] == new['properties']['parent_id'],
                             'original_feature': old})
    return {'version': 'worldatlas-saravan-panjgur-joint-candidate-v1',
            'status': 'offline-unapproved-candidate', 'baseline_commit': registry['baseline_commit'],
            'evaluation_commit': commit, 'component_id': native.COMPONENT_ID,
            'original_component_feature_sha256': registry['component_feature_sha256'],
            'original_component_properties': component_feature['properties'],
            'source_agreement': agreement, 'source_assembly': assembly, 'source_parent_relations': parents,
            'current_sources_component_union_covers': union_all(list(sources.values())).covers(component),
            'proof': proof, 'preserved_before_features': preservation,
            'candidate': {'type': 'FeatureCollection', 'features': after},
            'physical_classification': 'unknown', 'history_transfer': False,
            'geographic_approval': 'unapproved', 'installation_ready': False,
            'metadata_policy': 'Candidate retains baseline properties to inspect identity/history preservation. Installation requires explicit mixed-source footprint provenance; unchanged old metadata must not certify candidate coordinates.',
            'limits': registry['limits']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--registry', required=True)
    parser.add_argument('--registry-sha256', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists() or out.is_symlink():
        raise ValueError('Refuse to overwrite existing output')
    descriptor = json.loads(args.registry)
    if descriptor['sha256'] != args.registry_sha256:
        raise ValueError('Registry pin differs from command')
    inputs = Baseline(args.repo, args.commit, [descriptor])
    registry = json.loads(inputs.read(descriptor['path']))
    result = propose(args.repo, args.commit, registry)
    with out.open('xb') as stream:
        stream.write(canonical_json(result))


if __name__ == '__main__':
    main()
