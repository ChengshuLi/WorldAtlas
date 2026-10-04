#!/usr/bin/env python3
"""Rebuild the 58 flagged BC 2016 ADM3 to 2021 CSD evidence rows."""
import csv, hashlib, io, json, zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
BASE = Path('data/regional-review/regional-review-4254da254d94f450')
ASSESSMENT = BASE / 'assessment.json'
ZIP = ROOT / 'sources/2021_92-156-X_DB_ID.zip'
OUT = ROOT / 'crosswalk-assessment.json'
REGISTRY = ROOT / 'subjects.geojson'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    assessment = json.loads(ASSESSMENT.read_text())
    flagged = []
    for loc in assessment['locations']:
        if not loc['location_id'].startswith('atlas:district:CAN-'):
            continue
        parent_cd = loc['location_id'].split(':')[2][4:]
        for m in loc['source_identity_and_vintage']['members']:
            if m['name_matches_2021_csd_within_cd'] == 0 or m['name_matches_2021_csd_within_cd'] > 1 or m['overlap_pct'] < 95:
                flagged.append((parent_cd, loc['location_id'], m))
    assert len(flagged) == 58 and len({x[2]['source_shape_id'] for x in flagged}) == 58
    # The official file provides one row per 2021/2016 dissemination-block ID pair.
    # CSDUID is the first seven digits of each DBUID; aggregate pairs without area inference.
    with zipfile.ZipFile(ZIP) as z:
        name = next(n for n in z.namelist() if n.endswith('.csv'))
        rows = csv.DictReader(io.TextIOWrapper(z.open(name), encoding='utf-8-sig', newline=''))
        transitions = defaultdict(Counter)
        for row in rows:
            new_db, old_db = row['DBUID2021_IDIDU2021'], row['DBUID2016_IDIDU2016']
            if new_db.startswith('59') and old_db.startswith('59'):
                new_csd, old_csd = new_db[:7], old_db[:7]
                transitions[new_csd][(old_csd, row['DBRELFLAG_IDINDREL'])] += 1
    records = []
    for cd, parent_id, m in sorted(flagged, key=lambda x: x[2]['source_shape_id']):
        uid = m['best_2021_csd_id']
        # Candidate and exact correspondence remain distinct evidence layers.
        t = transitions.get(uid, Counter()) if uid else Counter()
        old_codes = sorted({old for old, _ in t})
        if m['name_matches_2021_csd_within_cd'] == 1:
            disposition = 'unique-name-candidate; geometry exception unresolved'
            basis = 'One normalized name match in same 2021 Census Division; official 2021 UID is candidate. The <95% overlay is unresolved and does not prove boundary change.'
        elif m['name_matches_2021_csd_within_cd'] > 1:
            disposition = 'ambiguous-name-candidates; spatial candidate only'
            basis = 'Multiple same-name 2021 CSDs in same Census Division; retained best-overlap UID ranks a candidate only and does not resolve source identity.'
        else:
            disposition = 'no-name-match; spatial candidate only'
            basis = 'No normalized name match in same Census Division; retained best-overlap UID is a candidate only and does not resolve source identity.'
        if uid and len(old_codes) == 1:
            transition_note = 'The official DB correspondence rows for the candidate 2021 CSD prefix all point to one 2016 CSDUID; this corroborates statistical-area continuity only, not source-feature identity.'
        elif uid and len(old_codes) > 1:
            transition_note = 'The official DB correspondence rows for the candidate 2021 CSD prefix point to multiple 2016 CSDUIDs; the statistical successor is many-to-many at this candidate and remains unresolved.'
        elif uid:
            transition_note = 'No British Columbia DB correspondence rows were found for the candidate UID; successor linkage unresolved.'
        else:
            transition_note = 'No retained 2021 UID candidate; successor linkage unresolved.'
        records.append({
            'source_id': 'geoBoundaries:CAN:ADM3:' + m['source_shape_id'],
            'source_shape_id': m['source_shape_id'], 'source_name_2016': m['source_name'],
            'parent_context': {'atlas_group_id': parent_id, 'census_division_uid': cd},
            'screen_flags': {'normalized_name_matches_2021_csd_within_cd': m['name_matches_2021_csd_within_cd'], 'best_overlay_pct_of_2016_shape': m['overlap_pct']},
            'candidate_2021_csd': None if uid is None else {'csduid': uid, 'name': m['best_2021_csd_name']},
            'official_2021_db_correspondence': {'previous_2016_csd_uids': old_codes, 'db_pair_counts_by_relation_flag': {flag: sum(count for (old, f), count in t.items() if f == flag) for flag in sorted({f for _, f in t})}, 'total_db_pairs': sum(t.values()), 'interpretation': transition_note},
            'assessment': {'disposition': disposition, 'basis': basis, 'unresolved': disposition != 'unique-name-candidate; geometry exception unresolved' or m['overlap_pct'] < 95 or len(old_codes) != 1, 'successor_mapping_status': 'candidate; direct source-feature-to-StatCan-2016 CSD link is not established by this inventory'},
        })
    result = {
        'version': 1,
        'scope': {'assigned_source_members': 376, 'flagged_subjects': 58, 'flag_counts': {'no_normalized_name_match': 20, 'multiple_normalized_name_matches': 5, 'best_overlap_below_95_pct': 33}, 'subjects_sha256': hashlib.sha256(json.dumps(sorted(r['source_id'] for r in records), separators=(',', ':')).encode()).hexdigest()},
        'source_vintages': {'geoBoundaries_CAN_ADM3': 2016, 'Statistics_Canada_Census_Subdivision': 2021, 'Statistics_Canada_DB_correspondence_current': 2021, 'Statistics_Canada_DB_correspondence_previous': 2016},
        'methods': {'screen_source': 'Pinned #485 exhaustive overlay/name screen in assessment.json. Reused as screening evidence only.', 'transition_source': 'Statistics Canada 2021 correspondence file DB_ID maps DBUID2021 to DBUID2016 and carries DBRELFLAG. Derive candidate CSDUIDs from each 10-digit DBUID first seven digits, aggregate ID-pair counts by target CSDUID and relation flag. Counts are dissemination-block record counts, not area or population weights.', 'normalization': 'Exactly as #485 assessment script; see source file path and pinned baseline. Source spelling is preserved.', 'interpretation': 'A candidate 2021 name/overlay is not a direct source lineage. Official DB correspondence joins statistical 2016/2021 subdivisions and cannot by itself establish geoBoundaries feature identity, political ownership, or legal boundary changes.'},
        'records': records,
        'summary': {'records_assessed': len(records), 'unique_name_candidate_with_geometry_exception': sum(r['assessment']['disposition'].startswith('unique-name') for r in records), 'multiple_name_ambiguous': sum(r['assessment']['disposition'].startswith('ambiguous') for r in records), 'no_name_spatial_only': sum(r['assessment']['disposition'].startswith('no-name') for r in records), 'unresolved_direct_feature_successor_links': sum(r['assessment']['successor_mapping_status'] != 'established' for r in records), 'open_fact': 'Official 2016 CSD geospatial/code reconciliation to each geoBoundaries ADM3 feature has not been established by this packet; no row is labeled a proven legal successor.'},
        'limitations': ['This packet exhaustively accounts for the 58 triage-flagged source IDs. The other 318 of the assigned 376-member cohort remain as screened in #485 and were not re-adjudicated here.', 'The official correspondence file is dissemination-block ID correspondence; prefix derivation uses Statistics Canada identifier structure. DB-pair counts do not measure land area or imply one-to-one administrative succession.', 'The 2016 geoBoundaries identifiers are not Statistics Canada CSDUIDs. Name and overlay candidates cannot certify an identity mapping or infer Indigenous/municipal political ownership.', 'The #485 2021 geometry screen and source snapshots remain immutable in their original packet; no copy or modification is made here.'],
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    features = [{'type':'Feature','id':r['source_id'],'geometry':None,'properties':{'id':r['source_id'],'source_value':r['source_shape_id'],'source_property':'shapeID'}} for r in records]
    REGISTRY.write_text(json.dumps({'type':'FeatureCollection','features':features}, ensure_ascii=False, separators=(',', ':'))+'\n')
    print(json.dumps({'flagged':len(records),'no_name':sum(r['screen_flags']['normalized_name_matches_2021_csd_within_cd']==0 for r in records),'multiple':sum(r['screen_flags']['normalized_name_matches_2021_csd_within_cd']>1 for r in records),'below_95':sum(r['screen_flags']['best_overlay_pct_of_2016_shape']<95 for r in records),'output_sha256':sha(OUT)},indent=2))
if __name__ == '__main__': main()
