"""Reprepare only RESOLVE biome references with precise WGS84 surface integration."""
import collections
import gc
import gzip
import hashlib
import json
import math
import pathlib
import subprocess

from shapely import STRtree, make_valid, prepare, union_all
from shapely.geometry import shape
from ellipsoidal_area import area

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
REFERENCES = DATA / 'reference-attributes'
SOURCE = ROOT / '.cache/semantic/resolve-ecoregions.geojson'
RECEIPTS = DATA / 'vegetation-numerical-review'
CACHE = ROOT / '.cache/research/vegetation-precise'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_gzip(path, value):
    path.write_bytes(gzip.compress(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode(), mtime=0))


def footprint_hash():
    return subprocess.check_output(['node', 'scripts/stamp-prepared.mjs', '--hash'], cwd=ROOT, text=True).strip()


def chosen_summary(location, source_indexes, source_geometries, features):
    total = area(location)
    if total <= 0:
        return None, {'reason': 'empty_land_footprint'}
    clips = collections.defaultdict(list)
    for j in source_indexes:
        j = int(j)
        original = source_geometries[j]
        local = location if original.covers(location) else original.intersection(location)
        if not local.is_empty:
            clips[features[j]['properties']['BIOME_NAME']].append(local)
    if not clips:
        return None, {'reason': 'no_source_land_overlap'}
    groups = {}
    for biome, parts in clips.items():
        groups[biome] = location if any(p is location for p in parts) else parts[0] if len(parts) == 1 else union_all(parts)
    covered = location if any(g is location for g in groups.values()) else union_all(list(groups.values()))
    coverage = 1.0 if covered is location else area(covered) / total
    if coverage > 1 + 1e-9:
        raise ValueError('Source intersection area exceeds whole location footprint')
    if coverage < .5:
        return None, {'reason': 'less_than_half_land_footprint_supported', 'coverage': round(coverage, 12)}
    covered_area = min(1.0, coverage) * total
    sizes = {name: total if geom is location else area(geom) for name, geom in groups.items()}
    # Preserve one categorical summary; equal-area source ties have deterministic name order.
    biome = min(sizes, key=lambda name: (-sizes[name], str(name)))
    share = sizes[biome] / covered_area
    if share > 1 + 1e-9:
        raise ValueError('Biome area exceeds covered footprint union')
    overlap = max(0.0, math.fsum(sizes.values()) - covered_area) / total
    return {'source_value': biome, 'value': None if biome in (None, '', 'N/A', 'Unknown', 'No data') else biome,
            'status': 'unknown' if biome in (None, '', 'N/A', 'Unknown', 'No data') else 'reference',
            'share': round(min(1.0, share), 12), 'coverage': round(min(1.0, coverage), 12)}, {
            'source_biome_overlap_share': round(overlap, 12),
            'source_record_ids': sorted(str(features[int(j)]['properties']['ECO_ID']) for j in source_indexes),
            'competing_classes': [[name, round(min(1.0, sizes[name]/covered_area), 12)] for name in sorted(sizes, key=str)]}


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    RECEIPTS.mkdir(exist_ok=True)
    original_index_bytes = (REFERENCES / 'index.json').read_bytes()
    original_index_hash = hashlib.sha256(original_index_bytes).hexdigest()
    index = json.loads(original_index_bytes)
    if index['version'] != 2:
        raise ValueError('Selective vegetation audit requires current merged reference codec v2')
    expected = footprint_hash()
    if expected != index['footprints_sha256']:
        raise ValueError('Reference footprint snapshot differs from current locations')
    vegetation_types = {i for i, t in enumerate(index['types']) if t['attribute'] == 'vegetation'}
    if any(index['types'][i]['valid_from'] != 2026 or index['types'][i]['valid_to'] != 2027 for i in vegetation_types):
        raise ValueError('Unexpected vegetation intervals: do not overwrite other dated evidence')
    known_type = next(i for i in vegetation_types if index['types'][i]['status'] == 'reference')
    unknown_type = next(i for i in vegetation_types if index['types'][i]['status'] == 'unknown')
    old = {}
    untouched_before = hashlib.sha256()
    old_nonvegetation_count = 0
    for part in index['parts']:
        for location_id, records in json.loads(gzip.decompress((REFERENCES / part).read_bytes())):
            unchanged = []
            for item in records:
                if item[0] in vegetation_types:
                    if location_id in old:
                        raise ValueError('Duplicate resolved source biome before preparation')
                    old[location_id] = {'value': index['values'][item[1]], 'status': index['types'][item[0]]['status'], 'share': item[2], 'coverage': item[3]}
                else:
                    unchanged.append(item)
                    old_nonvegetation_count += 1
            if unchanged:
                untouched_before.update(json.dumps([location_id, unchanged], separators=(',', ':')).encode())
    source = read(SOURCE)['features']
    original_geometries = [shape(f['geometry']) for f in source]
    invalid_count = sum(not g.is_valid for g in original_geometries)
    geoms = [make_valid(g) for g in original_geometries]
    del original_geometries
    prepare(geoms)
    tree = STRtree(geoms)
    summaries = {}
    changes = []
    receipts = []
    receipt_parts = []
    missing_reasons = collections.Counter()
    known = 0
    unknown = 0
    scanned = 0
    max_share_difference = 0.0
    differences_over_1e6 = 0
    overlaps = []
    def save_receipts():
        if receipts:
            name = f'locations-{len(receipt_parts)}.json.gz'
            write_gzip(RECEIPTS / name, receipts)
            receipt_parts.append(name)
            receipts.clear()
    for path in read(DATA / 'world-index.json')['parts']:
        features = read(DATA / path)['features']
        for feature in features:
            geometry = shape(feature['geometry'])
            candidates = [int(j) for j in tree.query(geometry) if geoms[int(j)].intersects(geometry)]
            summary, evidence = chosen_summary(geometry, candidates, geoms, source)
            location_id = feature['id']
            previous = old.get(location_id)
            scanned += 1
            if summary:
                summaries[location_id] = summary
                known += summary['status'] == 'reference'
                unknown += summary['status'] == 'unknown'
                if evidence['source_biome_overlap_share'] > 1e-6:
                    overlaps.append({'location_id': location_id, **evidence})
            else:
                missing_reasons[evidence['reason']] += 1
            if previous and summary:
                delta = abs(previous['share'] - summary['share'])
                max_share_difference = max(max_share_difference, delta)
                differences_over_1e6 += delta > 1e-6
            changed_category = (previous or {}).get('value') != (summary or {}).get('value') or (previous is None) != (summary is None) or (previous or {}).get('status') != (summary or {}).get('status')
            if changed_category:
                changes.append({'location_id': location_id, 'previous': previous, 'resolved': summary, 'evidence': evidence})
            receipts.append({'location_id': location_id, 'previous': previous, 'resolved': summary, 'evidence': evidence, 'category_changed': changed_category})
            if len(receipts) == 1500:
                save_receipts()
            if scanned % 5000 == 0:
                print(f'Vegetation precise audit {scanned}: {known} known, {unknown} source unknown', flush=True)
        del features
    save_receipts()
    # Release source geometry before the independent final footprint hash check.
    del tree, geoms, source, geometry
    gc.collect()
    if footprint_hash() != expected:
        raise ValueError('Footprints changed during vegetation audit')
    if digest(REFERENCES / 'index.json') != original_index_hash:
        raise ValueError('Merged reference table changed during selective audit; staged receipt retained, no overwrite')
    metadata = {'aggregation': 'Largest covered potential-natural biome by precise WGS84 ellipsoidal surface area; source polygons unioned per biome, footprint coverage is the source union divided by the entire location land footprint',
                'area_method': 'WGS84 latitude-strip boundary integral, 16-point Gauss-Legendre quadrature for straight longitude/latitude source edges',
                'area_algorithm_sha256': digest(ROOT / 'scripts/ellipsoidal_area.py'),
                'source_geometry_sha256': digest(SOURCE),
                'coverage_rule': 'At least half the entire location land footprint must be covered; source N/A is an explicit unknown value'}
    for i in vegetation_types:
        index['types'][i]['metadata'].update(metadata)
    original_values = list(index['values'])
    for summary in summaries.values():
        if summary['value'] not in index['values']:
            index['values'].append(summary['value'])
    values = {value: i for i, value in enumerate(index['values'])}
    assigned = set()
    new_part_hashes = {}
    untouched_after = hashlib.sha256()
    final_record_count = 0
    represented = set()
    stage = CACHE / 'parts'
    stage.mkdir(exist_ok=True)
    for part in index['parts']:
        rows = []
        for location_id, records in json.loads(gzip.decompress((REFERENCES / part).read_bytes())):
            unchanged = [item for item in records if item[0] not in vegetation_types]
            if unchanged:
                untouched_after.update(json.dumps([location_id, unchanged], separators=(',', ':')).encode())
            updated = list(unchanged)
            if location_id not in assigned and location_id in summaries:
                s = summaries[location_id]
                updated.append([unknown_type if s['status'] == 'unknown' else known_type, values[s['value']], s['share'], s['coverage']])
                assigned.add(location_id)
            if updated:
                rows.append([location_id, updated])
                final_record_count += len(updated)
                represented.add(location_id)
        write_gzip(stage / part, rows)
        new_part_hashes[part] = digest(stage / part)
    # Newly supported rows may belong to locations without another reference record.
    remaining = [[location_id, [[unknown_type if s['status'] == 'unknown' else known_type, values[s['value']], s['share'], s['coverage']]]]
                 for location_id, s in summaries.items() if location_id not in assigned]
    new_parts = list(index['parts'])
    for start in range(0, len(remaining), 1500):
        part = f'vegetation-precise-new-{start//1500}.json.gz'
        rows = remaining[start:start+1500]
        write_gzip(stage / part, rows)
        new_parts.append(part)
        new_part_hashes[part] = digest(stage / part)
        final_record_count += len(rows)
        represented.update(row[0] for row in rows)
    if untouched_before.digest() != untouched_after.digest():
        raise ValueError('A non-vegetation reference changed')
    if final_record_count != old_nonvegetation_count + known + unknown:
        raise ValueError('Reference count mismatch')
    if index['values'][:len(original_values)] != original_values:
        raise ValueError('Original value index meanings changed')
    receipt = {'version': 1, 'status': 'validated-selective-repreparation', 'scanned_locations': scanned, 'previous_vegetation_records': len(old), 'known_vegetation_references': known,
               'unknown_source_records': unknown, 'unsupported_locations': scanned-known-unknown, 'unsupported_reasons': dict(missing_reasons),
               'category_or_support_changes': changes, 'share_difference_maximum': max_share_difference,
               'share_differences_over_1e-6': differences_over_1e6, 'source_biome_overlap_locations': overlaps,
               'source_features': 847, 'invalid_source_features_repaired': invalid_count, 'source_geometry_sha256': digest(SOURCE),
               'area_algorithm_sha256': digest(ROOT / 'scripts/ellipsoidal_area.py'), 'preparation_algorithm_sha256': digest(pathlib.Path(__file__)),
               'footprints_sha256_before': expected, 'footprints_sha256_after': expected,
               'original_reference_index_sha256': original_index_hash, 'unchanged_nonvegetation_records': old_nonvegetation_count,
               'unchanged_nonvegetation_sha256_before': untouched_before.hexdigest(), 'unchanged_nonvegetation_sha256_after': untouched_after.hexdigest(),
               'supported_interval': [2026,2027], 'source_year': 2017, 'receipt_parts': receipt_parts,
               'receipt_parts_sha256': {p:digest(RECEIPTS/p) for p in receipt_parts}}
    index.update(parts=new_parts, parts_sha256=new_part_hashes, records=final_record_count, vegetation_references=known, unknown_source_records=unknown, represented_locations=len(represented))
    index['inputs']['vegetation_area_algorithm'] = receipt['area_algorithm_sha256']
    index['vegetation_numerical_review'] = 'vegetation-numerical-review/index.json'
    # Publish fully validated staged parts; index is replaced last.
    for part in new_parts:
        (REFERENCES / part).write_bytes((stage / part).read_bytes())
    (REFERENCES / 'index.json').write_text(json.dumps(index, ensure_ascii=False, separators=(',', ':')))
    receipt['updated_reference_index_sha256'] = digest(REFERENCES / 'index.json')
    (RECEIPTS / 'index.json').write_text(json.dumps(receipt, ensure_ascii=False, separators=(',', ':')))
    print(json.dumps({k:receipt[k] for k in ['scanned_locations','previous_vegetation_records','known_vegetation_references','unknown_source_records','unsupported_locations','share_difference_maximum','share_differences_over_1e-6','unchanged_nonvegetation_records']}), flush=True)


if __name__ == '__main__':
    main()
