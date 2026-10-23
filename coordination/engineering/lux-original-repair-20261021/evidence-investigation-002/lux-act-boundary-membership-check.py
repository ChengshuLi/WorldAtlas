#!/usr/bin/env python3
"""Bounded point-membership comparison for the retained 624 LUX target cells."""
import hashlib
import json
from pathlib import Path
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[1]
ACT_PATH = Path('/tmp/lux-act-limadmin-20261005.geojson')
OBS_PATH = ROOT / 'inventory/lux-selected-owner-observation.json'
PARTS_PATH = ROOT / 'inventory/lux-source-contact-investigation-partitions.json'
SIG_PATH = ROOT / 'inventory/lux-official-canton-2026-exact-comparison.json'
OUT_PATH = ROOT / 'inventory/lux-act-official-boundary-adverse-comparison.json'
SIZE = 262166
EXPECTED_MD5 = 'b7efcb9fac2d724fe493e32713ff3977'

raw = ACT_PATH.read_bytes()
assert len(raw) == 1207257
assert hashlib.md5(raw).hexdigest() == EXPECTED_MD5
assert hashlib.sha256(raw).hexdigest() == '6c3128de3763704397d9a7c44ea04d952fd467fc88a368e2d188c236cbfbae83'
act = json.loads(raw)
observation = json.loads(OBS_PATH.read_text())
partitions = json.loads(PARTS_PATH.read_text())
sig = json.loads(SIG_PATH.read_text())
latitude = {(r['y'], r['x']): r['latitude'] for r in observation['keys']}
cantons = [(f['properties']['CANTON'], shape(f['geometry'])) for f in act['cantons']['features']]
national = shape(act['pays']['features'][0]['geometry'])

def inspect(rows):
    hits_by_canton = {}
    country_count = 0
    outside_cantons = 0
    overlap_count = 0
    memberships = {}
    for row in rows:
        x, y = row['x'], row['y']
        # Invert src/native-grid.js columnFraction: center longitude for column x.
        lon = (360 * x + 180 - 180 * SIZE) / SIZE
        point = Point(lon, latitude[(y, x)])
        hits = [name for name, geometry in cantons if geometry.covers(point)]
        memberships[(y, x)] = hits
        if len(hits) > 1:
            overlap_count += 1
        if hits:
            for name in hits:
                hits_by_canton[name] = hits_by_canton.get(name, 0) + 1
        else:
            outside_cantons += 1
        country_count += int(national.covers(point))
    return {
        'count': len(rows),
        'covered_by_act_canton_union': len(rows) - outside_cantons,
        'outside_act_canton_union': outside_cantons,
        'covered_by_act_national_polygon': country_count,
        'outside_act_national_polygon': len(rows) - country_count,
        'act_canton_counts': hits_by_canton,
        'multiple_canton_coverage': overlap_count,
        'memberships': memberships,
    }

foreign_keys = partitions['Belgian contact']['keys'] + partitions['German contacts']['keys']
lux_only_keys = partitions['LUX contacts only']['keys']
foreign_records = [{'x': x, 'y': y} for y, x in foreign_keys]
lux_records = [{'x': x, 'y': y} for y, x in lux_only_keys]
all_records = foreign_records + lux_records
all_result = inspect(all_records)
foreign_result = inspect(foreign_records)
lux_result = inspect(lux_records)
prior_outside = [r for r in sig['per_key'] if not r['canton_membership']]
prior_outside_result = inspect(prior_outside)
extra = []
for r in sig['per_key']:
    if r['source_groups'] != ['LUX'] or not r['canton_membership']:
        continue
    if not inspect([r])['covered_by_act_national_polygon']:
        extra.append([r['x'], r['y'], r['canton_membership'][0]['name']])

assert all_result['covered_by_act_canton_union'] == 594
assert all_result['outside_act_canton_union'] == 30
assert all_result['covered_by_act_national_polygon'] == 594
assert foreign_result['covered_by_act_canton_union'] == 26
assert foreign_result['covered_by_act_national_polygon'] == 26
assert prior_outside_result['count'] == 25
assert prior_outside_result['covered_by_act_national_polygon'] == 0
assert len(extra) == 5

result = json.loads(OUT_PATH.read_text())
result['execution_provenance'] = {
    'local_act_input_path': str(ACT_PATH),
    'local_act_input_bytes': len(raw),
    'local_act_input_md5': hashlib.md5(raw).hexdigest(),
    'local_act_input_sha256': hashlib.sha256(raw).hexdigest(),
    'runtime': {'python': '3.12.14 (bundled isolated venv, -I)', 'shapely': '2.1.2'},
    'invocation': 'native-scratch/worldatlas-physical-venv/bin/python -I inventory/lux-act-boundary-membership-check.py',
    'point_latitude_input': {
        'path': 'inventory/lux-selected-owner-observation.json',
        'one_latitude_per_original_key': True,
        'source_commit': observation['consumed_latitudes']['commit'],
        'source_path': observation['consumed_latitudes']['path'],
        'source_git_blob_oid': observation['consumed_latitudes']['git_blob_oid'],
        'source_sha256': observation['consumed_latitudes']['sha256'],
        'whole_body_consumed_by_original_observer': observation['consumed_latitudes']['whole_body_consumed']
    },
    'longitude_formula_source': {
        'commit': 'c107b2053841498763d92a38da3924b3fa04b077',
        'path': 'src/native-grid.js',
        'git_blob_oid': 'add4cef02bb5a790f22a9078fdf9bd51679059d3',
        'sha256': '3d20777f5896d28192e40428dd34cab89d47873a08bf073a17338c4ff97d43cd',
        'formula_reused': '(360*x + 180 - 180*size)/size, size=262166',
        'code_executed_in_this_comparison': False
    },
    'comparison_script': {
        'path': 'inventory/lux-act-boundary-membership-check.py',
        'method': 'parse ACT GeoJSON; Shapely covers() for cell-center Points against every ACT canton and the ACT pays polygon; compare counts against retained partitions and SIG-GR per-key membership',
        'no_observer_or_native_constructor_rerun': True
    }
}
# Elide all point-by-point geometry outputs; only exact mismatching key IDs are retained.
result['results']['all_original_keys'] = {k:v for k,v in all_result.items() if k != 'memberships'}
result['results']['26_foreign_contact_keys'] = {k:v for k,v in foreign_result.items() if k not in ('memberships','outside_act_canton_union','multiple_canton_coverage')}
result['results']['25_keys_outside_prior_SIG_GR_2026_canton_union'] = {
    'count': prior_outside_result['count'],
    'act_canton_covered': prior_outside_result['covered_by_act_canton_union'],
    'act_national_polygon_covered': prior_outside_result['covered_by_act_national_polygon'],
    'prior_comparison_file': 'inventory/lux-official-canton-2026-exact-comparison.json'
}
result['results']['additional_ACT_vs_SIG_GR_disagreement'] = {
    'count': len(extra),
    'source_partition': 'LUX-only',
    'prior_SIG_GR_canton_membership': 'inside',
    'ACT_canton_and_national_polygon_membership': 'outside',
    'keys_xy_canton': extra
}
result['results']['ACT_only_counts_for_all_598_LUX_only_source_contacts'] = {
    'covered_by_act_canton_union': lux_result['covered_by_act_canton_union'],
    'outside_act_canton_union': lux_result['outside_act_canton_union'],
    'covered_by_act_national_polygon': lux_result['covered_by_act_national_polygon'],
    'outside_act_national_polygon': lux_result['outside_act_national_polygon']
}
OUT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
print(json.dumps({'all': result['results']['all_original_keys'], 'foreign': result['results']['26_foreign_contact_keys'], 'prior_outside': result['results']['25_keys_outside_prior_SIG_GR_2026_canton_union'], 'additional': result['results']['additional_ACT_vs_SIG_GR_disagreement']}, sort_keys=True))
