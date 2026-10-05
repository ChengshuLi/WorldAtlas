#!/usr/bin/env python3
"""Rebuild the exact 14-parent crosswalk from #443 scope and retained source polygons."""
import csv
import json
import pathlib
import unicodedata

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform, unary_union

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWN = ROOT / 'data/regional-review/argentina-adm2-source-revalidation-443'
PARENT = ROOT / 'data/regional-review/regional-review-7cf674a63057d43f'


def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))


def read_geo(path):
    with path.open(encoding='utf-8') as stream:
        return json.load(stream)['features']


with (PARENT / 'findings/scoped-province-review.csv').open(encoding='utf-8', newline='') as stream:
    parents = list(csv.DictReader(stream))
with (PARENT / 'findings/scoped-location-review.csv').open(encoding='utf-8', newline='') as stream:
    locations = list(csv.DictReader(stream))
old = read_geo(OWN / 'source/geoBoundaries-2006/geoBoundaries-ARG-ADM1-2006.geojson')
current = read_geo(OWN / 'source/Georef-current/provincias.geojson')
project = Transformer.from_crs('EPSG:4326', 'EPSG:6933', always_xy=True).transform
old_geoms = [(feature, transform(project, shape(feature['geometry']))) for feature in old]
current_by_name = {norm(feature['properties']['nombre']): feature for feature in current}
parent_ids = {row['province_id'] for row in parents}
child_counts = {key: sum(row['parent_id'] == key and row['location_id'].startswith('gb:ARG:ADM2:') for row in locations) for key in parent_ids}
old_by_name = {norm(feature['properties']['shapeName']): feature for feature in old}
results = []

for parent in parents:
    display = parent['atlas_name']
    official = parent['official_name_for_name_check']
    current_feature = current_by_name.get(norm(official))
    source_feature = old_by_name.get(norm(display))
    top_name = ''
    top_share = 0.0
    coverage = 0.0
    if current_feature:
        current_geom = transform(project, shape(current_feature['geometry']))
        hits = [(geom.intersection(current_geom).area, feature, geom) for feature, geom in old_geoms if geom.intersection(current_geom).area > 1]
        hits.sort(key=lambda row: row[0], reverse=True)
        if hits:
            top_name = hits[0][1]['properties']['shapeName']
            top_share = hits[0][0] / current_geom.area
            coverage = unary_union([row[2] for row in hits]).intersection(current_geom).area / current_geom.area
    results.append({
        'atlas_parent_id': parent['province_id'],
        'atlas_parent_name': display,
        'official_name_check': official,
        'scoped_parent_review_children_from_443': int(parent['scoped_child_count']),
        'direct_adm2_subjects_in_944': child_counts[parent['province_id']],
        'current_georef_exact_name_feature_id': current_feature['properties']['id'] if current_feature else '',
        'current_georef_exact_name_match_count': 1 if current_feature else 0,
        'current_georef_exact_feature_geometry_type': current_feature['geometry']['type'] if current_feature else '',
        '2006_adm1_source_id': source_feature['properties']['shapeID'] if source_feature else '',
        '2006_adm1_source_name': source_feature['properties']['shapeName'] if source_feature else '',
        '2006_source_exact_name_match': bool(source_feature and norm(source_feature['properties']['shapeName']) == norm(display)),
        '2006_feature_count': len(old),
        'current_national_province_count': len(current),
        'old_2006_top_overlap_source_name': top_name,
        'old_2006_top_overlap_share_of_current': f'{top_share:.9f}',
        'old_2006_union_coverage_of_current': f'{coverage:.9f}',
        'assessment': 'Name identity and current geometry crosswalk only; old source outline has no legal currentness certification.'
    })

assert len(results) == 14
path = OWN / 'findings/scoped-parent-review.csv'
with path.open('w', encoding='utf-8', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(results[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(results)
print(f'Rebuilt {len(results)} parent rows')
