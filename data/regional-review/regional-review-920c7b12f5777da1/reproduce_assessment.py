#!/usr/bin/env python3
"""Reproduce the scoped semantic and cross-vintage boundary screen for issue #376.

Requires Python 3.12, shapely 2.1.2, and pyshp 2.3.1. This is evidence triage,
not an atlas geometry change or a regional approval. Geometric ratios are planar
area ratios in geographic coordinates and are comparative diagnostics only.
"""
from __future__ import annotations
import csv, gzip, io, json, re, unicodedata, zipfile, hashlib
from collections import Counter
from pathlib import Path
from shapely.geometry import shape
from shapely import make_valid, union_all
import shapefile

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / 'data/regional-review/regional-review-920c7b12f5777da1'
SOURCE = PACKET / 'source'
FINDINGS = PACKET / 'findings'

def norm(value):
    value = unicodedata.normalize('NFKD', str(value).casefold())
    return ''.join(ch for ch in value if ch.isalnum())

def repaired(g):
    return g if g.is_valid else make_valid(g)

def read_features():
    wanted = json.loads((PACKET / 'scope.json').read_text())['member_location_ids']
    wanted_set = set(wanted)
    atlas = {}
    for part in json.loads((ROOT / 'data/world-index.json').read_text())['parts']:
        for feature in json.loads((ROOT / ('data/' + part)).read_text())['features']:
            if feature['id'] in wanted_set:
                atlas[feature['id']] = feature
    if set(atlas) != wanted_set or len(atlas) != len(wanted):
        raise SystemExit('scope IDs do not map one-to-one to current baseline features')
    adm2_doc = json.loads(gzip.open(SOURCE / 'geoboundaries-ven-adm2-2015-9469f09.geojson.gz', 'rt', encoding='utf-8').read())
    adm1_doc = json.loads(gzip.open(SOURCE / 'geoboundaries-ven-adm1-2020-9469f09.geojson.gz', 'rt', encoding='utf-8').read())
    adm2 = {f"gb:VEN:ADM2:{f['properties']['shapeID']}": f for f in adm2_doc['features']}
    return wanted, atlas, adm2_doc, adm1_doc, adm2

def read_igvsb():
    path = SOURCE / 'igvsb-municipal-boundaries-2024-provita.zip'
    if not path.exists():
        raise SystemExit('IGVSB archive is not retained because dataset-specific redistribution terms were not established. Review current terms, then explicitly restore with: sh restore_inputs.sh igvsb')
    with zipfile.ZipFile(path) as z:
        stem = next(n[:-4] for n in z.namelist() if n.endswith('.shp'))
        reader = shapefile.Reader(shp=io.BytesIO(z.read(stem+'.shp')),
                                  shx=io.BytesIO(z.read(stem+'.shx')),
                                  dbf=io.BytesIO(z.read(stem+'.dbf')),
                                  encoding='utf-8')
        fields = [f[0] for f in reader.fields[1:]]
        rows = []
        for idx, (rec, shp) in enumerate(zip(reader.records(), reader.shapes())):
            attrs = dict(zip(fields, rec))
            geom = repaired(shape(shp.__geo_interface__))
            rows.append({'index': idx, 'attrs': attrs, 'geom': geom})
    return rows

def main():
    wanted, atlas, adm2_doc, adm1_doc, adm2 = read_features()
    if len(adm2_doc['features']) != 335 or len(adm1_doc['features']) != 25:
        raise SystemExit('pinned source feature count changed')
    admin_source = json.loads((ROOT / 'data/administrative-sources.json').read_text())
    adm2_pin = admin_source['gb:VEN:ADM2']
    adm1_pin = admin_source['gb:VEN:ADM1']
    igvsb = read_igvsb()
    municipality_rows = [r for r in igvsb if norm(r['attrs'].get('nam','')).startswith('municipio')]
    conflict_rows = [r for r in igvsb if norm(r['attrs'].get('nam','')).startswith('zona')]
    overlap_zone_rows = [r for r in conflict_rows if 'sobreposicion' in norm(r['attrs'].get('nam',''))]
    no_jurisdiction_rows = [r for r in conflict_rows if 'sinjurisdiccion' in norm(r['attrs'].get('nam',''))]
    guayana_rows = [r for r in igvsb if norm(r['attrs'].get('nam','')).startswith('guayana')]
    adm1_geoms = [(f, repaired(shape(f['geometry']))) for f in adm1_doc['features']]
    adm1_by_name = {norm(f['properties']['shapeName']): (f,g) for f,g in adm1_geoms}
    source_features = {i:f for i,f in adm2.items()}
    source_geoms = {i:repaired(shape(f['geometry'])) for i,f in source_features.items()}
    resolve_sources = [json.loads(gzip.open(SOURCE / name, 'rt', encoding='utf-8').read()) for name in ('resolve-ven-ecoregions-query.geojson.gz', 'resolve-ecoregion-490-query.geojson.gz')]
    resolve_features = [f for source_doc in resolve_sources for f in source_doc['features']]
    resolve_by_id = {int(f['properties']['ECO_ID']): f for f in resolve_features}
    physical_ids = {i for i in wanted if i.startswith('atlas:physical:')}
    # The four existing physical labels are all backed by this single ADM2 feature.
    physical_backing = 'gb:VEN:ADM2:92452058B20928146308063'
    if physical_backing not in source_geoms:
        raise SystemExit('physical source-member feature missing from preserved ADM2 input')
    original = source_geoms[physical_backing]
    physical_geoms = [repaired(shape(atlas[i]['geometry'])) for i in sorted(physical_ids)]
    physical_union = union_all(physical_geoms)
    physical_unit_metrics = []
    for location_id in sorted(physical_ids):
        meta = atlas[location_id]['properties']['metadata']
        eco_id = int(str(meta['source_id']).split(':')[-1])
        eco_feature = resolve_by_id[eco_id]
        eco_geom = repaired(shape(eco_feature['geometry']))
        unit_geom = repaired(shape(atlas[location_id]['geometry']))
        clipped_eco = eco_geom.intersection(original)
        overlap = unit_geom.intersection(clipped_eco).area
        physical_unit_metrics.append({
            'location_id': location_id, 'source_id': meta['source_id'], 'resolve_name': eco_feature['properties']['ECO_NAME'],
            'atlas_fragment_area_covered_by_original_municipality_and_named_ecoregion': round(overlap / unit_geom.area, 8) if unit_geom.area else None,
            'atlas_fragment_outside_original_municipality_fraction': round(1 - unit_geom.intersection(original).area / unit_geom.area, 8) if unit_geom.area else None,
            'original_municipality_area_covered_by_fragment': round(unit_geom.intersection(original).area / original.area, 8) if original.area else None
        })
    physical_summary = {
        'atlas_physical_location_ids': sorted(physical_ids),
        'shared_original_source_member_id': physical_backing,
        'shared_original_source_name': source_features[physical_backing]['properties']['shapeName'],
        'resolve_ecoregion_ids': sorted({int(atlas[i]['properties']['metadata']['source_id'].split(':')[-1]) for i in physical_ids}),
        'resolve_records': [{'eco_id': eco, 'name': resolve_by_id[eco]['properties']['ECO_NAME'], 'license': resolve_by_id[eco]['properties']['LICENSE']} for eco in sorted(resolve_by_id)],
        'unit_metrics': physical_unit_metrics,
        'source_municipality_area_coverage_by_four_atlas_units': round(physical_union.intersection(original).area/original.area, 8),
        'four_atlas_units_inside_source_municipality_area': round(physical_union.intersection(original).area/physical_union.area, 8),
        'four_atlas_units_union_area_relative_to_source_municipality': round(physical_union.area/original.area, 8),
        'pairwise_overlap_area_degrees2': round(sum(physical_geoms[a].intersection(physical_geoms[b]).area for a in range(len(physical_geoms)) for b in range(a+1,len(physical_geoms))), 10)
    }
    # Map each Atlas province to the 2020 geoBoundaries ADM1 reference and test
    # each scoped ADM2 source geometry's containment in the expected province.
    parent_shapes = {}
    for i, feature in atlas.items():
        parent_id = feature['properties'].get('parent_id')
        if not parent_id or parent_id in parent_shapes:
            continue
        node = next((x for x in json.loads((ROOT/'data/hierarchy.json').read_text()) if x['id']==parent_id), None)
        parent_name = node.get('name') if node else parent_id
        matched = adm1_by_name.get(norm(parent_name))
        if matched:
            parent_shapes[parent_id] = {'name': parent_name, 'feature': matched[0], 'geom': matched[1]}
    official_names = {}
    for r in municipality_rows:
        n = norm(str(r['attrs'].get('nam','')))
        n = n.removeprefix('municipio')
        official_names.setdefault(n, []).append(r)
    output = []
    for location_id in wanted:
        feat = atlas[location_id]
        props = feat['properties']; meta = props.get('metadata', {})
        parent_id = props.get('parent_id')
        parent = parent_shapes.get(parent_id)
        if location_id in source_features:
            sf = source_features[location_id]
            geom = source_geoms[location_id]
            source_name = sf['properties']['shapeName']
            source_role = 'municipality (2015 geoBoundaries ADM2 / Municipios source collection)'
            same_name = official_names.get(norm(source_name), [])
            if same_name and parent:
                same_name = sorted(same_name, key=lambda r: geom.intersection(r['geom']).area, reverse=True)
            match = same_name[0] if same_name else None
            match_intersection = geom.intersection(match['geom']).area if match else 0.0
            parent_cover = geom.intersection(parent['geom']).area/geom.area if parent and geom.area else None
            parent_area_share = geom.intersection(parent['geom']).area/parent['geom'].area if parent and parent['geom'].area else None
            best_adm1 = None
            if geom.area:
                ranked_adm1 = sorted(((geom.intersection(g).area/geom.area, f['properties'].get('shapeName'), f['properties'].get('shapeID')) for f,g in adm1_geoms), reverse=True)
                best_adm1 = ranked_adm1[0]
            conflict_hits = []
            for r in conflict_rows:
                area = geom.intersection(r['geom']).area
                if geom.area and area/geom.area >= 0.0001:
                    conflict_hits.append({'name': str(r['attrs'].get('nam')), 'source_fraction': round(area/geom.area, 8), 'record_index': r['index']})
            same_name_iou = (geom.intersection(match['geom']).area/geom.union(match['geom']).area) if match and geom.union(match['geom']).area else None
            if norm(source_name) == norm('Zona en Reclamación'):
                decision = 'correction-needed'
                rationale = 'The 2015 ADM2 feature is explicitly named Zona en Reclamación, not a municipality. The 2016 IGVSB extract separates a Guayana Esequiba claim polygon, and the ICJ has ordered status-quo measures pending merits; no municipal identity or independent Venezuelan territorial status is established.'
            elif match and parent and best_adm1 and best_adm1[1] and norm(best_adm1[1]) == norm(parent['name']) and best_adm1[0] >= 0.98:
                decision = 'justified'
                rationale = 'At the role/parent level only: the source is a named Municipio in the 2015 ADM2 collection, a same-name 2016 IGVSB municipality exists, and independent 2020 ADM1 overlay places at least 98% of the source polygon in the issue-declared province. Boundary equivalence/completeness remains separately open.'
            else:
                decision = 'insufficient-evidence'
                if match and best_adm1:
                    rationale = f'A same-name IGVSB municipality is present in the 2016 comparator, but only {best_adm1[0]:.6f} of the 2015 source geometry overlaps its declared 2020 ADM1 parent in the WGS84 diagnostic; this misses the explicit 0.98 screen. The result is unresolved cross-vintage parent evidence, not proof that either edge is wrong.'
                else:
                    rationale = 'No exact normalized municipality-name match was established in the 2016 IGVSB comparator; parent overlap alone does not complete the source-unit crosswalk. Retain as unresolved pending a primary unit crosswalk and current source.'
            if conflict_hits:
                boundary_status = 'open: 2016 IGVSB source has explicit overlapping or unassigned municipal-boundary zone polygons intersecting this unit'
            elif match and same_name_iou is not None:
                boundary_status = 'open: same-name IGVSB feature is only a different-vintage comparison; no surveyed/legal edge proof or complete regional coverage certificate'
            else:
                boundary_status = 'open: no exact same-name 2016 IGVSB municipality crosswalk established'
            row = {
                'location_id': location_id, 'atlas_name': props.get('name'), 'classification': decision,
                'classification_scope': 'municipal role and adjacent province suitability; not complete boundary approval',
                'atlas_parent_id': parent_id, 'atlas_parent_name': parent['name'] if parent else None,
                'source_id': meta.get('source_id'), 'source_name': source_name, 'source_role': source_role,
                'source_shape_id': sf['properties'].get('shapeID'), 'source_year': adm2_pin.get('boundaryYearRepresented'),
                'source_license': adm2_pin.get('boundaryLicense'), 'source_license_detail': adm2_pin.get('licenseDetail'),
                'igvsb_2016_same_name_match': match['attrs'].get('nam') if match else None,
                'igvsb_2016_record_index': match['index'] if match else None,
                'igvsb_2016_year_from_embedded_metadata': '2016',
                'igvsb_2016_name_match_iou_comparative_only': round(same_name_iou,8) if same_name_iou is not None else None,
                'adm1_reference_source': 'gb:VEN:ADM1', 'adm1_reference_year': adm1_pin.get('boundaryYearRepresented'),
                'parent_geometry_containment_fraction': round(parent_cover,8) if parent_cover is not None else None,
                'source_geometry_type': geom.geom_type,
                'source_polygon_component_count': len(geom.geoms) if hasattr(geom, 'geoms') else 1,
                'largest_source_component_area_fraction': round((max(part.area for part in geom.geoms) if hasattr(geom, 'geoms') else geom.area)/geom.area,8) if geom.area else None,
                'source_area_fraction_of_expected_parent_reference': round(parent_area_share,8) if parent_area_share is not None else None,
                'best_adm1_by_area_fraction': round(best_adm1[0],8) if best_adm1 else None,
                'best_adm1_name': best_adm1[1] if best_adm1 else None,
                'material_igvsb_boundary_conflict_hits': conflict_hits,
                'boundary_status': boundary_status, 'rationale': rationale,
                'uncertainty': '2015/2016/2020 source vintages differ. The 2016 file itself identifies overlap/no-jurisdiction zones. This row is provisional semantic evidence only; legal boundary, current delimitation and local-source completeness remain unresolved.'
            }
        else:
            source_member = (meta.get('source_member_ids') or [None])[0]
            resolve_id = int(str(meta.get('source_id','')).split(':')[-1]) if str(meta.get('source_id','')).split(':')[-1].isdigit() else None
            rf = resolve_by_id.get(resolve_id)
            decision = 'insufficient-evidence'
            rationale = 'Atlas location is a RESOLVE 2017 ecological ecoregion fragment derived from a single source municipality. This supports a named physical description but does not establish that the fragment is itself a municipality or suitable as a peer in the municipal district tier. Engineering must resolve the intended tier/provenance and attribute inheritance.'
            row = {
                'location_id': location_id, 'atlas_name': props.get('name'), 'classification': decision,
                'classification_scope': 'municipal role and adjacent province suitability; not complete boundary approval',
                'atlas_parent_id': parent_id, 'atlas_parent_name': parent['name'] if parent else None,
                'source_id': meta.get('source_id'), 'source_name': rf['properties'].get('ECO_NAME') if rf else None,
                'source_role': 'ecoregion fragment (RESOLVE 2017), not a source municipality',
                'source_shape_id': source_member, 'source_year': '2017',
                'source_license': rf['properties'].get('LICENSE') if rf else 'CC-BY 4.0',
                'source_license_detail': 'ArcGIS item metadata says RESOLVE, Esri; source feature identifies the 2017 Ecoregions dataset and CC-BY 4.0.',
                'igvsb_2016_same_name_match': None, 'igvsb_2016_record_index': None,
                'igvsb_2016_year_from_embedded_metadata': '2016', 'igvsb_2016_name_match_iou_comparative_only': None,
                'adm1_reference_source': 'gb:VEN:ADM1', 'adm1_reference_year': adm1_pin.get('boundaryYearRepresented'),
                'parent_geometry_containment_fraction': None, 'best_adm1_by_area_fraction': None, 'best_adm1_name': None,
                'material_igvsb_boundary_conflict_hits': [],
                'boundary_status': 'open: physical fragments do not provide municipal legal boundaries', 'rationale': rationale,
                'uncertainty': 'The four fragments may be a deliberate physical subdivision of the very large Raúl Leoni source municipality; they must not inherit municipality-level facts by assumption. Their union/coverage and relation to the old source municipality are separately computed in physical-subdivision-summary.json.'
            }
        output.append(row)
    if len(output) != 188 or {r['location_id'] for r in output} != set(wanted):
        raise SystemExit('assessment does not cover exactly all 188 issue IDs')
    fields = list(output[0])
    with (FINDINGS/'location-assessments.jsonl').open('w') as f:
        for row in output: f.write(json.dumps(row, ensure_ascii=False, sort_keys=True)+'\n')
    summary = {
        'version': 1, 'issue': 376, 'date': '2026-10-06', 'region_id': json.loads((PACKET/'scope.json').read_text())['region_id'],
        'member_count': len(output), 'classifications': dict(Counter(r['classification'] for r in output)),
        'gb_adm2_scoped_rows': sum(r['source_id']=='gb:VEN:ADM2' for r in output),
        'resolve_physical_fragments': sum(r['source_id'] in {'resolve:464','resolve:466','resolve:490','resolve:572'} for r in output),
        'adm2_source_feature_count': len(adm2_doc['features']), 'adm1_source_feature_count': len(adm1_doc['features']),
        'igvsb_feature_count': len(igvsb), 'igvsb_municipio_feature_count': len(municipality_rows),
        'igvsb_named_boundary_issue_feature_count': len(conflict_rows), 'igvsb_guayana_esequiba_feature_count': len(guayana_rows),
        'igvsb_overlap_zone_feature_count': len(overlap_zone_rows),
        'igvsb_no_jurisdiction_zone_feature_count': len(no_jurisdiction_rows),
        'igvsb_scoped_rows_intersecting_boundary_issue_features': sum(bool(r.get('material_igvsb_boundary_conflict_hits')) for r in output),
        'screening_subsets': {
            'municipal_role_parent_justified': sum(r['source_id']=='gb:VEN:ADM2' and r['classification']=='justified' for r in output),
            'municipal_role_parent_insufficient': sum(r['source_id']=='gb:VEN:ADM2' and r['classification']=='insufficient-evidence' for r in output),
            'physical_fragments_insufficient': sum(r['source_role'].startswith('ecoregion fragment') and r['classification']=='insufficient-evidence' for r in output),
            'pseudo_territorial_unit_correction_needed': sum(r['classification']=='correction-needed' for r in output),
            'municipal_rows_intersecting_zone_features': sum(r['source_id']=='gb:VEN:ADM2' and bool(r.get('material_igvsb_boundary_conflict_hits')) for r in output),
            'zone_hit_rows_classified_justified_for_role_parent_only': sum(r['source_id']=='gb:VEN:ADM2' and r['classification']=='justified' and bool(r.get('material_igvsb_boundary_conflict_hits')) for r in output),
            'zone_hit_rows_classified_insufficient': sum(r['source_id']=='gb:VEN:ADM2' and r['classification']=='insufficient-evidence' and bool(r.get('material_igvsb_boundary_conflict_hits')) for r in output),
            'municipal_same_name_2016_match_but_parent_cover_below_0_98': sum(r['source_id']=='gb:VEN:ADM2' and r['classification']=='insufficient-evidence' and bool(r.get('igvsb_2016_same_name_match')) and (r.get('best_adm1_by_area_fraction') or 0)<.98 for r in output),
            'municipal_no_exact_normalized_name_match_in_2016_comparator': sum(r['source_id']=='gb:VEN:ADM2' and r['classification']=='insufficient-evidence' and not r.get('igvsb_2016_same_name_match') for r in output),
        },
        'issue_area_full_member_count': json.loads((PACKET/'scope.json').read_text())['area_scopes'][0]['full_area_location_count'],
        'issue_area_owned_member_count': json.loads((PACKET/'scope.json').read_text())['location_count'],
        'area_scope_partial': json.loads((PACKET/'scope.json').read_text())['area_scopes'][0]['partial'],
        'classification_limit': 'Justified applies only to source-backed municipal role and parent evidence at the declared source vintages. It does not certify exact boundaries, complete source coverage, regional interiors, the outer envelope or imports.',
        'igvsb_license_limit': 'Official 2016 IGVSB municipal-boundary content was retrieved from Provita Geoportal, whose site footer states CC BY 4.0. No dataset-specific license or source redistribution terms were identified in the embedded metadata; see source register.',
        'physical_subdivision': physical_summary,
        'provinces': [{**p, 'assessments': dict(Counter(r['classification'] for r in output if r['atlas_parent_id']==p['id']))} for p in json.loads((PACKET/'scope.json').read_text())['province_scopes']],
        'method': 'Exact ID crosswalk, metadata/source role reconciliation, 2015 ADM2-to-2020 ADM1 spatial overlay, named cross-vintage comparison to IGVSB municipal polygons, and direct intersection screen against IGVSB municipal-overlap/unassigned features. WGS84 planar area ratios are only spatial diagnostics, not legal accuracy measures.'
    }
    csv_fields = ['location_id','atlas_name','classification','classification_scope','atlas_parent_id','atlas_parent_name','source_id','source_name','source_role','source_year','source_license','source_shape_id','source_polygon_component_count','largest_source_component_area_fraction','source_area_fraction_of_expected_parent_reference','parent_geometry_containment_fraction','best_adm1_name','best_adm1_by_area_fraction','igvsb_2016_same_name_match','igvsb_2016_name_match_iou_comparative_only','material_igvsb_boundary_conflict_hits','boundary_status','rationale','uncertainty']
    with (FINDINGS/'location-assessments.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction='ignore')
        writer.writeheader()
        for row in output:
            flat = dict(row)
            flat['material_igvsb_boundary_conflict_hits'] = json.dumps(row.get('material_igvsb_boundary_conflict_hits', []), ensure_ascii=False, separators=(',',':'))
            writer.writerow(flat)
    granularity_screen = {
        'version': 1, 'issue': 376, 'date': '2026-10-06', 'scope_count': len(output),
        'source_multipart_adm2_features': [{'location_id':r['location_id'],'source_name':r['source_name'],'component_count':r['source_polygon_component_count'],'largest_component_area_fraction':r['largest_source_component_area_fraction']} for r in output if r.get('source_polygon_component_count',1)>1],
        'adm2_source_units_with_area_at_least_25_percent_of_expected_2020_adm1_parent': [{'location_id':r['location_id'],'source_name':r['source_name'],'atlas_parent_name':r['atlas_parent_name'],'planar_wgs84_fraction':r['source_area_fraction_of_expected_parent_reference']} for r in output if (r.get('source_area_fraction_of_expected_parent_reference') or 0)>=.25],
        'source_labels_with_autonomo': [{'location_id':r['location_id'],'source_name':r['source_name'],'atlas_parent_name':r['atlas_parent_name'],'classification':r['classification']} for r in output if 'autonomo' in norm(r.get('source_name',''))],
        'city_granularity': 'No city or urban-area boundary source is present in this issue input set; ADM2 municipio boundaries do not establish city extent or that a city split across municipalities is an atlas error.',
        'disconnected_feature_limit': 'Four scoped ADM2 geometries have multiple polygon components. Component counts do not identify islands, legal enclaves or errors; each needs an island/coastal/admin source crosswalk before classifying its components.',
        'same_tier_limit': '184 inputs are in a source collection labeled Municipios; four additional leaf records are ecological fragments sharing one municipal source member. There is no separate city/parish input in this packet. This supports an administrative-vs-physical distinction, not a decision to re-tier.',
        'large_unit_limit': 'Ten municipal polygons cover at least 25% of their corresponding 2020 ADM1 reference polygon in an unprojected WGS84 area ratio. This is a triage list only; municipality size can vary substantially and the measure is not an area-based validity rule.',
        'province_scopes': summary['provinces'],
        'neighbor_limit': 'Issue #375 owns the disjoint Venezuela workload complement. Cross-packet or neighboring-region conclusions require that evidence and a combined integration review.'
    }
    (FINDINGS/'granularity-screen.json').write_text(json.dumps(granularity_screen,ensure_ascii=False,indent=2)+'\n')
    (FINDINGS/'assessment-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (FINDINGS/'physical-subdivision-summary.json').write_text(json.dumps(physical_summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ('member_count','classifications','gb_adm2_scoped_rows','resolve_physical_fragments','igvsb_feature_count','igvsb_municipio_feature_count','igvsb_named_boundary_issue_feature_count','igvsb_guayana_esequiba_feature_count','igvsb_scoped_rows_intersecting_boundary_issue_features','physical_subdivision')},ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
