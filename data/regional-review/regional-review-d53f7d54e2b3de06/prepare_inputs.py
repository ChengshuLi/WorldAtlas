#!/usr/bin/env python3
"""Pin issue #476's scope to the published source inventory without editing it."""
from __future__ import annotations
import csv, hashlib, io, json, pathlib, re, subprocess

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[2]
ISSUE_JSON = ROOT / 'claim-context-20261004.json'
BASE = '2f6a964d81bed6acd438399689bbb84b4e3abe80'
ANCESTOR = '678d7e8f8686f575e024b593ce4e744a8bb4d79a'
AREA_TABLE = 'data/regional-review/regional-review-91fc801eb40ba6f9/area-partition-inventory.csv'
SIBLING_SCOPE = 'data/regional-review/regional-review-91fc801eb40ba6f9/scope.json'
SIBLING_MEMBERS = 'data/regional-review/regional-review-91fc801eb40ba6f9/baseline-members.json'
SIBLING_PARTITION = 'data/regional-review/regional-review-91fc801eb40ba6f9/sibling-area-partition.json'


def git_show(rev: str, path: str) -> bytes:
    return subprocess.check_output(['git', 'show', f'{rev}:{path}'], cwd=REPO)


def main() -> None:
    issue = json.loads(ISSUE_JSON.read_text())
    body = issue['body']
    matches = re.findall(r'```json\s*([\s\S]*?)\s*```', body)
    issue_scope = next(json.loads(text) for text in matches if 'member_location_ids' in text)
    exact_scope_bytes = next(text.encode() for text in matches if 'member_location_ids' in text)
    # Preserve the exact live GitHub machine scope in both the original and current pins.
    (ROOT / 'issue-scope-original.json').write_bytes(exact_scope_bytes)
    (ROOT / 'issue-scope-pinned.json').write_bytes(exact_scope_bytes)
    (ROOT / 'issue-scope.json').write_text(json.dumps(issue_scope, ensure_ascii=False, indent=2) + '\n')

    prior_scope = json.loads(git_show(BASE, SIBLING_SCOPE))
    issue_scope.update({
        'issue_number': 476,
        'issue_url': issue['html_url'],
        'published_region_baseline': prior_scope['published_region_baseline'],
        'issue_scope_sha256': hashlib.sha256(exact_scope_bytes).hexdigest(),
        'issue_scope_source_json_sha256': hashlib.sha256(exact_scope_bytes).hexdigest(),
        'partition_reference_commit': BASE,
        'sibling_partition_reference': {'path': SIBLING_PARTITION, 'commit': BASE,
                                        'sha256': hashlib.sha256(git_show(BASE, SIBLING_PARTITION)).hexdigest()},
    })
    assert issue_scope['published_region_baseline']['baseline_git_commit'] == ANCESTOR
    (ROOT / 'scope.json').write_text(json.dumps(issue_scope, ensure_ascii=False, indent=2) + '\n')

    table_bytes = git_show(BASE, AREA_TABLE)
    table_hash = hashlib.sha256(table_bytes).hexdigest()
    issue_scope['assignment_inventory_reference'] = {'path': AREA_TABLE, 'commit': BASE, 'sha256': table_hash}
    (ROOT / 'scope.json').write_text(json.dumps(issue_scope, ensure_ascii=False, indent=2) + '\n')
    rows = list(csv.DictReader(io.StringIO(table_bytes.decode('utf-8'))))
    assigned = [row for row in rows if row['review_issue'] == '476']
    wanted = issue_scope['member_location_ids']
    assert len(rows) == 774 and len(assigned) == len(wanted) == 227
    assert len({row['location_id'] for row in assigned}) == 227
    assert {row['location_id'] for row in assigned} == set(wanted)
    province_counts = {}
    for row in assigned:
        province_counts[row['baseline_province_id']] = province_counts.get(row['baseline_province_id'], 0) + 1
    declared = {p['id']: p for p in issue_scope['province_scopes']}
    assert set(province_counts) == set(declared)
    for pid, count in province_counts.items():
        assert count == declared[pid]['full_province_locations']

    prior_members_bytes = git_show(BASE, SIBLING_MEMBERS)
    prior_members = json.loads(prior_members_bytes)
    sample = next(m for m in prior_members if m['region_id'] == issue_scope['region_id'])
    upper_chain = sample['parent_chain'][1:]
    assert upper_chain[0] == issue_scope['area_scopes'][0]['id']
    assert upper_chain[1] == issue_scope['region_id']
    members = []
    by_id = {row['location_id']: row for row in assigned}
    for sid in wanted:
        row = by_id[sid]
        members.append({
            'id': sid,
            'name': row['baseline_name'],
            'parent_id': row['baseline_province_id'],
            'parent_chain': [row['baseline_province_id'], *upper_chain],
            'owner': 'Nigeria',
            'continent': 'Africa',
            'region_id': issue_scope['region_id'],
            'source_id': 'gb:NGA:ADM2',
            'source_year': '2022',
            'status': 'open',
            'semantic_status': 'open',
        })
    assert [m['id'] for m in members] == wanted
    (ROOT / 'baseline-members.json').write_text(json.dumps(members, ensure_ascii=False, indent=2) + '\n')
    ref = {
        'baseline_commit': BASE,
        'published_region_scope_baseline_commit': ANCESTOR,
        'assignment_inventory': {'path': AREA_TABLE, 'commit': BASE, 'sha256': table_hash, 'rows': len(rows)},
        'upper_chain_reference': {'path': SIBLING_MEMBERS, 'commit': BASE, 'sha256': hashlib.sha256(prior_members_bytes).hexdigest(), 'source_issue': 477},
        'published_hierarchy_sha256': issue_scope['release']['hierarchy_sha256'],
        'issue_scope': {'number': 476, 'created_at': issue['created_at'], 'retrieved_at': '2026-10-04',
                        'path': 'issue-scope-original.json', 'sha256': hashlib.sha256(exact_scope_bytes).hexdigest()},
        'members': 227,
        'province_scope_counts': [{'id': pid, 'name': declared[pid]['name'], 'locations': province_counts[pid]}
                                  for pid in sorted(province_counts)],
        'interpretation': 'The assignment inventory and upper-chain reference are prior evidence available at the fresh PR base; the exact member inventory was derived in the accepted adjacent Nigeria packet from the declared ancestor snapshots. The release pins remain the geographic baseline. These records do not independently establish administrative tier purpose, settlement completeness, physical land completeness or regional approval.'
    }
    (ROOT / 'baseline-source-reference.json').write_text(json.dumps(ref, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'subjects': len(members), 'province_scopes': len(province_counts),
                      'scope_assignment_match': True, 'baseline_commit': BASE,
                      'ancestor_release_snapshot': ANCESTOR, 'area_partition_sha256': table_hash}, indent=2))

if __name__ == '__main__':
    main()
