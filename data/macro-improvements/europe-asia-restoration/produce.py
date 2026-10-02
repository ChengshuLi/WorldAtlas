#!/usr/bin/env python3
"""Reproduce a sparse, staged patch from pinned sources; never modify the atlas."""
import argparse, copy, gzip, hashlib, json, pathlib, subprocess, sys, tarfile
import xml.etree.ElementTree as ET
from shapely import STRtree, from_wkb, normalize
from shapely.geometry import Polygon, shape, mapping, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from pyproj import Geod
sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GEOD = Geod(ellps='WGS84')
TIERS = ['location', 'province', 'area', 'region', 'subcontinent', 'continent']


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def document(path):
    raw = pathlib.Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def land_area(g):
    if g.is_empty:
        return 0
    if g.geom_type == 'Polygon':
        return abs(GEOD.geometry_area_perimeter(orient(g, 1))[0])
    return sum(land_area(part) for part in g.geoms)


def archive_bytes(archive, name):
    member = archive.getmember(name)
    if not member.isfile() or member.name != name or '..' in pathlib.PurePosixPath(name).parts:
        raise ValueError('Unsafe retained source member')
    return archive.extractfile(member).read()


def whole_water_mask(xml, coast_rings):
    """Closed OSM coast-water, tagged-water and complete relation masks."""
    nodes = {n.attrib['id']: (float(n.attrib['lon']), float(n.attrib['lat'])) for n in xml.findall('node')}
    ways = {w.attrib['id']: w for w in xml.findall('way')}
    masks = [Polygon(r['coordinates']) for r in coast_rings if r['land_on_left_signed_area_km2'] < 0]
    lineage = []
    for w in ways.values():
        tags = {t.attrib['k']: t.attrib['v'] for t in w.findall('tag')}
        if tags.get('natural') != 'water' and tags.get('landuse') != 'reservoir':
            continue
        refs = [n.attrib['ref'] for n in w.findall('nd')]
        if len(refs) < 4 or refs[0] != refs[-1] or any(n not in nodes for n in refs):
            raise ValueError('Incomplete source inland-water way')
        polygon = Polygon([nodes[n] for n in refs])
        if not polygon.is_valid:
            raise ValueError('Invalid source water polygon')
        masks.append(polygon)
        lineage.append({'kind': 'closed-water-way', 'id': w.attrib['id'], 'version': w.attrib.get('version'), 'timestamp': w.attrib.get('timestamp')})

    def assemble(rel, role):
        pending = []
        for m in rel.findall('member'):
            if m.attrib.get('type') != 'way' or m.attrib.get('role', 'outer') != role:
                continue
            w = ways.get(m.attrib['ref'])
            if w is None:
                raise ValueError('Incomplete source water relation')
            refs = [n.attrib['ref'] for n in w.findall('nd')]
            if any(n not in nodes for n in refs):
                raise ValueError('Missing water relation nodes')
            pending.append(refs)
        polygons = []
        while pending:
            chain = pending.pop()
            while chain[0] != chain[-1]:
                for i, other in enumerate(pending):
                    if chain[-1] == other[0]:
                        chain.extend(other[1:])
                    elif chain[-1] == other[-1]:
                        chain.extend(other[-2::-1])
                    elif chain[0] == other[-1]:
                        chain = other[:-1] + chain
                    elif chain[0] == other[0]:
                        chain = other[:0:-1] + chain
                    else:
                        continue
                    pending.pop(i)
                    break
                else:
                    raise ValueError('Open source water relation ring')
            polygon = Polygon([nodes[n] for n in chain])
            if not polygon.is_valid:
                raise ValueError('Invalid source water relation ring')
            polygons.append(polygon)
        return polygons

    for rel in xml.findall('relation'):
        tags = {t.attrib['k']: t.attrib['v'] for t in rel.findall('tag')}
        if tags.get('natural') != 'water' and tags.get('water') not in ['lake', 'pond', 'reservoir', 'lagoon']:
            continue
        outer, inner = assemble(rel, 'outer'), assemble(rel, 'inner')
        if not outer:
            raise ValueError('Water relation has no outer')
        masks.append(unary_union(outer).difference(unary_union(inner)))
        lineage.append({'kind': 'water-relation', 'id': rel.attrib['id'], 'version': rel.attrib.get('version'), 'timestamp': rel.attrib.get('timestamp'), 'outer_count': len(outer), 'inner_count': len(inner)})
    return nodes, ways, masks, lineage


def source_geometry(candidate, query, archive):
    raw = gzip.decompress(archive_bytes(archive, candidate['geometry_path']))
    if digest(raw) != candidate['geometry_wkb_sha256']:
        raise ValueError('Retained candidate geometry hash changed')
    retained = from_wkb(raw)
    xml_raw = gzip.decompress(archive_bytes(archive, query['original_path']))
    if digest(xml_raw) != candidate['source_xml_sha256'] or digest(xml_raw) != query['original_sha256']:
        raise ValueError('Original OSM source bytes changed')
    xml = ET.fromstring(xml_raw)
    nodes, ways, masks, water_lineage = whole_water_mask(xml, query['closed_rings'])
    matching = [r for r in query['closed_rings'] if r['way_versions'] == candidate['source_way_versions']]
    if len(matching) != 1:
        raise ValueError('Source coastline identity is ambiguous')
    ring = matching[0]
    # Validate a directed complete shoreline from original ways, not an index assertion.
    pending = []
    for version in ring['way_versions']:
        w = ways.get(version['id'])
        if w is None or any(w.attrib.get(k) != version[k] for k in ['version', 'timestamp']):
            raise ValueError('Original source way version changed')
        refs = [n.attrib['ref'] for n in w.findall('nd')]
        if any(n not in nodes for n in refs):
            raise ValueError('Missing coastline nodes')
        pending.append(refs)
    chain = pending.pop()
    while pending:
        for i, refs in enumerate(pending):
            if chain[-1] == refs[0]:
                chain.extend(refs[1:])
            elif refs[-1] == chain[0]:
                chain = refs[:-1] + chain
            else:
                continue
            pending.pop(i)
            break
        else:
            raise ValueError('Source coastlines are not a directed endpoint chain')
    if chain[0] != chain[-1]:
        raise ValueError('Source coastline is not closed')
    polygon = Polygon([nodes[n] for n in chain])
    signed = GEOD.geometry_area_perimeter(polygon)[0]
    if not polygon.is_valid or signed <= 0 or not box(*query['requested_bbox']).covers(polygon):
        raise ValueError('Invalid, water-oriented or clipped complete source coastline')
    if normalize(polygon).wkb != normalize(Polygon(ring['coordinates'])).wkb:
        raise ValueError('Coastline index differs from original source nodes')
    contained = [g for g in masks if polygon.covers(g)]
    dry = polygon.difference(unary_union(contained))
    if not dry.is_valid or dry.is_empty or normalize(dry).wkb != normalize(retained).wkb:
        raise ValueError('Retained dry land differs from original shoreline/water mask')
    if len(contained) != candidate['subtracted_closed_water_rings']:
        raise ValueError('Source water exclusion count changed')
    return dry, {'source_xml_sha256': digest(xml_raw), 'source_way_versions': ring['way_versions'], 'source_geometry_sha256': digest(raw), 'subtracted_water_masks': len(contained), 'water_lineage': water_lineage, 'dry_land_m2': land_area(dry), 'license': 'OpenStreetMap contributors, ODbL 1.0', 'attribution': 'https://www.openstreetmap.org/copyright', 'source_url': candidate['source_url'], 'supported_from': 2026, 'supported_to': 2027, 'status': 'modern reference; source edit timestamps are not historical effective intervals'}


def load_baseline(directory, pins):
    directory = pathlib.Path(directory).resolve()
    raw_index = (directory / 'world-index.json').read_bytes()
    hierarchy_raw = (directory / 'hierarchy.json').read_bytes()
    if digest(hierarchy_raw) != pins['hierarchy_sha256']:
        raise ValueError('Baseline hierarchy changed; coordinated repin required')
    features, part_hashes = [], {}
    for part in json.loads(raw_index)['parts']:
        path = (directory / part).resolve()
        if not path.is_relative_to(directory):
            raise ValueError('Unsafe baseline part')
        raw = path.read_bytes()
        part_hashes[part] = digest(raw)
        features.extend(json.loads(raw)['features'])
    ids = [f['id'] for f in features]
    if len(ids) != pins['locations'] or len(set(ids)) != len(ids):
        raise ValueError('Baseline location inventory changed or duplicated')
    # Same hash implementation as publication, including JS number/string ordering.
    command = "import fs from 'node:fs';import {footprintHash} from './scripts/check-prepared.mjs';const p=process.argv[1];const f=JSON.parse(fs.readFileSync(p+'/world-index.json')).parts.flatMap(x=>JSON.parse(fs.readFileSync(p+'/'+x)).features);console.log(footprintHash(f));"
    fp = subprocess.check_output(['node', '--input-type=module', '-e', command, str(directory)], cwd=ROOT, text=True).strip()
    if fp != pins['footprints_sha256']:
        raise ValueError('Baseline footprint pin changed')
    return features, json.loads(hierarchy_raw), {'world-index.json': digest(raw_index), 'hierarchy.json': digest(hierarchy_raw), **part_hashes}


def centre_counts(features):
    command = "import {createGridIndex,rasterize} from './src/pixel-grid.js';let s='';for await(const c of process.stdin)s+=c;console.log(JSON.stringify(JSON.parse(s).map(f=>{const i=createGridIndex([f]),b=i[0].bounds,x=Math.floor(b[0]),y=Math.floor(b[1]),w=Math.ceil(b[2])-x+1,h=Math.ceil(b[3])-y+1;let n=0;for(const v of rasterize(i,{x,y,width:w,height:h}))if(v)n++;return {id:f.id,cell_centres:n};})));"
    return json.loads(subprocess.check_output(['node', '--input-type=module', '-e', command], input=encoded(features), cwd=ROOT))


def produce(baseline, output):
    output = pathlib.Path(output).resolve()
    baseline = pathlib.Path(baseline).resolve()
    if output.exists() or output == baseline or output.is_relative_to(baseline) or baseline.is_relative_to(output):
        raise ValueError('Output must be fresh and separate from baseline')
    inputs = document(HERE / 'source-inputs.json')
    for name, expected in inputs['owned_source_files'].items():
        if digest((HERE / name).read_bytes()) != expected:
            raise ValueError('Owned source bytes changed: ' + name)
    if digest((HERE / 'decisions.json.gz').read_bytes()) != inputs['decisions_sha256']:
        raise ValueError('Territorial decisions changed')
    registry = document(HERE / 'sources/physical-identity-inventory.json.gz')['entities']
    evaluation = ROOT / inputs['evaluation_directory']
    for name, expected in inputs['evaluation_files'].items():
        if digest((evaluation / name).read_bytes()) != expected:
            raise ValueError('Pinned source evaluation changed: ' + name)
    for source in inputs['original_collections']:
        raw = gzip.decompress((HERE / source['path']).read_bytes())
        if digest(raw) != source['original_sha256']:
            raise ValueError('Original source collection changed')
    before, units, raw_pins = load_baseline(baseline, inputs['baseline'])
    existing = {f['id']: f for f in before}
    by_unit = {u['id']: u for u in units}
    plan = document(HERE / 'decisions.json.gz')
    queries = {q['name']: q for q in document(evaluation / 'modern-coastline-index.json')}
    geometric_inventory = [shape(f['geometry']) for f in before]
    tree = STRtree(geometric_inventory)
    updates, additions, added_units, archives, source_proofs, holds, grid_features = [], [], [], [], [], [], []
    patch_geometries = []
    with tarfile.open(evaluation / 'geometry-and-modern-sources.tar.gz') as archive:
        for group in plan['location_decisions']:
            if group['group_key'] == 'Minamitorishima':
                raise ValueError('Marcus is excluded from this issue')
            identifier = group['existing_location_id'] or group['chain'][0]['id']
            parent = group['chain'][1]['id']
            dry_parts = []
            for candidate in group['staged_components']:
                dry, proof = source_geometry(candidate, queries[candidate['query']], archive)
                proof.update({'location_id': identifier, 'query': candidate['query'], 'geometry_path': candidate['geometry_path']})
                source_proofs.append(proof)
                dry_parts.append(dry)
                grid_features.append({'id': candidate['geometry_wkb_sha256'], 'geometry': mapping(dry)})
            modern = unary_union(dry_parts)
            if group['existing_location_id']:
                old = existing.get(identifier)
                if old is None or old['properties']['parent_id'] != parent:
                    raise ValueError('Existing identity/parent changed')
                feature = copy.deepcopy(old)
                # Partial existing West Island / Diego Garcia are explicitly replaced
                # by coherent whole-island dry sources; other original components stay.
                geometry = modern if group['group_key'] in ['CocosSouth', 'DiegoGarcia'] else unary_union([shape(old['geometry']), modern])
                feature['geometry'] = mapping(geometry)
                archives.append(old)
                updates.append({'location_id': identifier, 'before_feature_sha256': digest(encoded(old)), 'after_feature': feature, 'identity_action': 'retain exact stable ID and properties; version footprint only'})
            else:
                if identifier in existing or any(x['properties'].get('name', '').casefold() == 'fugloy' for x in existing.values()) or any(x['id'] == identifier or (x.get('name') or '').casefold() == 'fugloy' for x in registry):
                    raise ValueError('Creation duplicates a physical identity')
                province = group['chain'][1]
                if province['id'] in by_unit:
                    raise ValueError('Proposed new group already exists')
                new_unit = {'id': province['id'], 'name': province['name'], 'level': 'province', 'parent_id': group['chain'][2]['id'], 'metadata': {'source_url': 'https://www.fugloy.fo/', 'basis': 'Sourced remote island municipality; documented coextensive exception', 'reference_only': True, 'regional_interior_status': 'open'}}
                added_units.append(new_unit)
                by_unit[new_unit['id']] = new_unit
                feature = {'type': 'Feature', 'id': identifier, 'properties': {'id': identifier, 'name': 'Fugloy', 'parent_id': parent, 'reference_owner': None, 'metadata': {'source_id': 'OSM:whole-island:Fugloy', 'source_name': 'OpenStreetMap contributors', 'source_url': group['staged_components'][0]['source_url'], 'license': 'ODbL 1.0', 'reference_year': '2026', 'location_basis': 'Complete named island dry-land source at retained comparison floor', 'habitation': None, 'rank': None, 'regional_interior_status': 'open', 'source_identity': 'Fugloy'}} , 'geometry': mapping(modern)}
                additions.append({'location_id': identifier, 'after_feature': feature, 'identity_review': {'status': 'distinct-new-territory', 'evidence_url': 'https://www.fugloy.fo/', 'rationale': 'No current/archived Fugloy location identity found. Official municipality and independent Norðoyar grouping distinguish it from Eysturoy; modern owner is not the parent rule.', 'same_name_existing_ids': [], 'archived_and_current_registry_entities_reviewed': len(registry), 'registry_inventory_sha256': inputs['owned_source_files']['sources/physical-identity-inventory.json.gz']}})
                geometry = modern
            if geometry.is_empty or not geometry.is_valid:
                raise ValueError('Proposed grouped footprint is invalid')
            p = parent
            for row in group['chain'][1:]:
                u = by_unit.get(p)
                if not u or u['level'] != row['level'] or u['id'] != row['id']:
                    raise ValueError('Incomplete or changed adjacent-tier chain')
                p = u.get('parent_id')
            if p is not None:
                raise ValueError('Continent must have no parent')
            for i in tree.query(geometry, predicate='intersects'):
                if before[int(i)]['id'] != identifier and land_area(geometry.intersection(geometric_inventory[int(i)])) > .001:
                    raise ValueError('Proposed footprint overlaps unrelated baseline land: ' + before[int(i)]['id'])
            patch_geometries.append((identifier, geometry))
            holds.append({'location_id': identifier, 'query_scope': group['queries'], 'remaining': group['holds'], 'completion': 'Finite compared components only; smaller unassociated rings and complete regional interior remain open', 'installation_authorized': False})
    for i, (identifier, geometry) in enumerate(patch_geometries):
        for other, g in patch_geometries[i + 1:]:
            if land_area(geometry.intersection(g)) > .001:
                raise ValueError('Restoration groups overlap: ' + identifier + '/' + other)
    cells = centre_counts(grid_features)
    if any(row['cell_centres'] <= 0 for row in cells):
        raise ValueError('Accepted component disappears on the canonical grid')
    patch = {'version': 1, 'schema': 'worldatlas:sparse-geography-patch:v1', 'issue': 505, 'status': 'staged-source-candidate; coordinated integration required', 'baseline': {**inputs['baseline'], 'raw_file_sha256': raw_pins}, 'updates': updates, 'creations': additions, 'added_units': added_units, 'source_proofs': source_proofs, 'holds': holds, 'historical_claims_transferred': False, 'source_scope': 'Eight non-Marcus modern query domains; >=0.1 km² validated whole dry-land components, grouped into named territories. Chagos explicitly partial.', 'invalidation_required': ['spatial ownership', 'environment summaries', 'prepared/runtime geography', 'canonical grid', 'ancestor footprints', 'geographic certificates and historical content scopes'], 'source_evaluation_sha256': inputs['evaluation_files']['modern-candidate-review.json']}
    output.mkdir(parents=True)
    # Shared sparse interface: publisher composes these independent deltas before
    # invoking the existing retained-ID and pure-creation receipt contracts.
    wrapper = {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'id': 'osm:whole-named-island:fugloy',
         'properties': {'name': 'Fugloy'}, 'geometry': additions[0]['after_feature']['geometry']}]}
    wrapper_raw = encoded(wrapper)
    (output / 'creation-source.geojson').write_bytes(wrapper_raw)
    fugloy_chain = next(g['chain'] for g in plan['location_decisions'] if g['group_key'] == 'FugloyWide')
    fugloy_source = next(p for p in source_proofs if p['query'] == 'FugloyWide')
    creation_proof = {'location_id': additions[0]['location_id'],
        'parent_chain': [u['id'] for u in fugloy_chain[1:]],
        'source': {'path': 'creation-source.geojson', 'sha256': digest(wrapper_raw),
            'identity': 'osm:whole-named-island:fugloy',
            'url': fugloy_source['source_url'], 'license': fugloy_source['license'],
            'attribution': fugloy_source['attribution'], 'supported_from': 2026,
            'supported_to': 2027, 'original_archive': {
                'path': str((evaluation / 'geometry-and-modern-sources.tar.gz').relative_to(ROOT)),
                'raw_sha256': inputs['evaluation_files']['geometry-and-modern-sources.tar.gz'],
                'source_xml_raw_sha256': fugloy_source['source_xml_sha256']}},
        'identity_review': additions[0]['identity_review']}
    patch.update({'input_geography_version': 3,
        'input_hierarchy_sha256': inputs['baseline']['hierarchy_sha256'],
        'input_part_sha256': {p: h for p, h in raw_pins.items() if p not in ['world-index.json', 'hierarchy.json']},
        'operations': [{'id': row['location_id'], 'kind': 'retained-id-footprint-restoration',
            'before_geometry_sha256': digest(encoded(existing[row['location_id']]['geometry'])),
            'after_geometry_sha256': digest(encoded(row['after_feature']['geometry'])),
            'parent_chain': [u['id'] for u in next(g['chain'] for g in plan['location_decisions'] if g['existing_location_id'] == row['location_id'])[1:]],
            'history_transfer': False} for row in updates],
        'existing_location_updates': [u['after_feature'] for u in updates],
        'existing_group_updates': [], 'added_features': [a['after_feature'] for a in additions],
        'added_groups': added_units, 'creation_proofs': [creation_proof],
        'source_checks': source_proofs, 'history_transfer': False,
        'publication_ready': False, 'archive_path': 'before-features.json.gz'})
    (output / 'creation-proofs.json').write_bytes(encoded([creation_proof]) + b'\n')
    (output / 'patch.json.gz').write_bytes(gzip.compress(encoded(patch), mtime=0))
    (output / 'before-features.json.gz').write_bytes(gzip.compress(encoded(archives), mtime=0))
    proof = {'version': 1, 'baseline_locations': len(before), 'unchanged_baseline_locations': len(before) - len(updates), 'updated_existing_locations': len(updates), 'created_locations': len(additions), 'new_groups': len(added_units), 'source_components': len(source_proofs), 'all_chains_complete': True, 'unrelated_land_overlap_m2': 0, 'all_component_grid_centres': cells, 'grid_recompiled': False, 'historical_claims_transferred': False, 'baseline_files_modified': False, 'sources_reconstructed_from_original_XML': True, 'patch_sha256': digest((output / 'patch.json.gz').read_bytes()), 'before_features_sha256': digest((output / 'before-features.json.gz').read_bytes())}
    (output / 'validation.json').write_bytes(encoded(proof) + b'\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=pathlib.Path, default=ROOT / 'data')
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    print(json.dumps(produce(args.baseline, args.output)))
