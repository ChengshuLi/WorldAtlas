#!/usr/bin/env python3
"""Read-only v5 queue producer. No network, subprocess or GitHub write capability."""
import argparse, copy, datetime, gzip, hashlib, json, re
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo
BASE = Path('data/reference-migrations/macro-improvements-v4/queue-checkpoint')
NEW_IDS = {'atlas:macro-coverage:location:df975d92f90219ddd9f6', 'atlas:macro-coverage:location:37c3c7fb6cd6cf260c68'}
load = lambda p: json.loads(gzip.decompress(Path(p).read_bytes()) if str(p).endswith('.gz') else Path(p).read_bytes())
sha = lambda x: hashlib.sha256(x.encode() if isinstance(x, str) else x).hexdigest()
js = lambda x: json.dumps(x, separators=(',', ':'), ensure_ascii=False)
member = lambda ids: sha('\n'.join(sorted(ids)))
envelope = lambda ids: sha(js(sorted(ids)))
def protected(issue):
    labels = [x if isinstance(x, str) else x['name'] for x in issue['labels']]
    return issue['state'].lower() != 'open' or 'status:claimed' in labels or bool((issue.get('canonical_claim') or {}).get('active'))
def produce(args):
    old = load(BASE / 'queue-workload-v4.json.gz'); registry = load(BASE / 'queue-issue-registry-v3.archive.json.gz')
    created_old = load(BASE / 'created-supplements-v4.json.gz'); issues = {x['number']: x for x in load(args.issues)}
    candidate = Path(args.candidate); groups = {x['id']: x for x in load(candidate / 'hierarchy.json')}
    packets = old['batches'] + old['supplemental_batches']; oldids = [i for b in packets for i in b['member_location_ids']]
    assert len(oldids) == len(set(oldids)) == 49623
    chains, members, newfeatures = {}, defaultdict(list), {}
    for part in load(candidate / 'world-index.json')['parts']:
        data = load(candidate / part)
        for feature in data['features']:
            p = feature['properties']; identifier = p['id']; assert identifier not in chains
            chain = []; parent = p['parent_id']
            for tier in ['province', 'area', 'region', 'subcontinent', 'continent']:
                unit = groups[parent]; assert unit['level'] == tier; chain.append(parent); members[parent].append(identifier); parent = unit['parent_id']
            assert parent is None; chains[identifier] = chain
            if identifier in NEW_IDS: newfeatures[identifier] = copy.deepcopy(p)
        del data, feature
    assert set(chains) == set(oldids) | NEW_IDS and not set(oldids) & NEW_IDS
    assert chains['atlas:macro-coverage:location:df975d92f90219ddd9f6'][:3] == ['framework:province:line-islands:ce27f8d7a826', 'framework:area:line-is:637147b6194f', 'framework:region:south-central-pacific:8347faa810e3']
    assert chains['atlas:macro-coverage:location:37c3c7fb6cd6cf260c68'][:3] == ['framework:province:hawaii:88e4dd68a18b', 'framework:area:hawaii:964dab8e8ef8', 'framework:region:north-central-pacific:4e0ad85ab366']
    assert all(chains[i][2] == b['region_id'] for b in packets for i in b['member_location_ids'])
    final = load(args.handoffs) if args.handoffs else None; verified = False
    release = final['release'] if final else {'id': 'REQUIRED_FINAL_V5_RELEASE', 'version': 5, 'hierarchy_sha256': sha((candidate / 'hierarchy.json').read_bytes()), 'footprints_sha256': 'REQUIRED_FINAL_V5_FOOTPRINTS_SHA256'}
    cert = final['macro_certificate_sha256'] if final else 'REQUIRED_FINAL_V5_MACRO_CERTIFICATE'
    envs = {r['region_id']: r['envelope'] for r in final['regions']} if final else {r['region_id']: {'geometry_sha256': 'REQUIRED_FINAL_V5_REGION_GEOMETRY', 'member_location_ids_sha256': envelope(members[r['region_id']])} for r in old['regions']}
    if final:
        assert release['version'] == 5 and release['hierarchy_sha256'] == sha((candidate / 'hierarchy.json').read_bytes()) and final['regional_interiors_approved'] is False
        assert len(envs) == 81 and all(envs[r]['member_location_ids_sha256'] == envelope(members[r]) and envs[r]['locations'] == len(members[r]) for r in envs)
    if args.live_confirmation:
        assert final; live = load(args.live_confirmation)
        assert live['published'] is True and live['verified_by_root'] is True and live['release'] == release and live['macro_certificate_sha256'] == cert
        assert live['live_location_count'] == 49625 and live['historical_location_attribute_imports_enabled'] is False; verified = True
    created = load(args.created_issues) if args.created_issues else {}; additions = []; date = datetime.datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
    for identifier in sorted(NEW_IDS):
        chain = chains[identifier]; region = chain[2]; batch = 'regional-supplement:' + sha(region + '\n' + identifier)[:16]; owned = 'data/regional-review/' + batch.replace(':', '-') + '/'
        scope = {'batch_id': batch, 'region_id': region, 'location_count': 1, 'member_location_ids': [identifier], 'member_location_ids_sha256': member([identifier]), 'owned_evidence_path': owned, 'review_only': True, 'release': release, 'macro_certificate_sha256': cert, 'frozen_region_geometry_sha256': envs[region]['geometry_sha256'], 'frozen_region_member_ids_sha256': envs[region]['member_location_ids_sha256'], 'source_profile_hints': [newfeatures[identifier]]}
        for tier, field in [(0, 'province_scopes'), (1, 'area_scopes')]:
            unit = chain[tier]; scope[field] = [{'id': unit, 'name': groups[unit]['name'], 'member_location_ids': [identifier], 'owned_member_location_count': 1, 'full_current_location_count': len(members[unit]), 'partial': len(members[unit]) != 1, 'combined_parent_decision': 'Regional integration owns original and supplemental subjects; no independent shared-parent edits.'}]
        work = {'max_prs': 1, 'depends_on': [33, 36], 'mode': 'geography', 'owned_paths': [owned], 'scope': 'Source-only geography review of exactly ' + identifier + '; proposals/evidence only, no hierarchy/grid/code/live writes or historical attribute imports.'}
        body = f'Raised/recorded: {date} (America/Los_Angeles).\n\nReview this one sourced whole named territory, all dry-land rings, source date/license, omitted associated islands and its existing archipelago parent roles. Macro membership supplies no political owner or historical facts. Regional integration owns shared parents.\n\nExact scope:\n```json\n' + js(scope) + '\n```\n\n<!-- worldatlas-work:v1\n' + js(work) + '\n-->\n'
        key = 'regional-supplement:' + batch; number = created.get(key); number = number.get('number') if isinstance(number, dict) else number
        body += '\n<!-- worldatlas-queue-item:' + key + ' -->\n'
        additions.append({'key': key, 'number': number, 'scope': scope, 'title': 'Review ' + newfeatures[identifier]['name'] + ': whole named territory', 'labels': ['type:geography', 'kind:work-item', 'status:ready' if verified else 'status:blocked'], 'body': body})
    rolemap = {n: (r['region_id'], role) for r in registry['regions'] for n, role in [(r['umbrella'], 'umbrella'), (r['approval_issue'], 'approval'), *[(n, 'packet') for n in r['review_issues']]]}
    for packet in old['supplemental_batches']:
        value = created_old['regional-supplement:' + packet['batch_id']]; rolemap[value['number'] if isinstance(value, dict) else value] = (packet['region_id'], 'packet')
    assert len(rolemap) == 435 and set(rolemap) <= set(issues)
    updates, holds, archives = [], [], []
    changes = load(args.changed_ids) if args.changed_ids else []
    changed = set(changes.get('changed_ids', []) if isinstance(changes, dict) else changes); assert changed <= set(oldids)
    for number, (region, role) in sorted(rolemap.items()):
        actual = issues[number]; body = actual['body']; labels = [x if isinstance(x, str) else x['name'] for x in actual['labels']]
        archives.append(copy.deepcopy(actual))
        if protected(actual): holds.append({'number': number, 'reason': 'closed or actively claimed; preserve exact issue and worker evidence'}); continue
        def replace_scope(match):
            try: scope = json.loads(match[1])
            except ValueError: return match[0]
            if not isinstance(scope, dict) or not scope.get('batch_id'): return match[0]
            before = copy.deepcopy(scope); scope.update(release=release, macro_certificate_sha256=cert, frozen_region_geometry_sha256=envs[region]['geometry_sha256'], frozen_region_member_ids_sha256=envs[region]['member_location_ids_sha256'], required_revalidation_location_ids=sorted(changed & set(scope['member_location_ids'])))
            for item in scope.get('area_scopes', []) + scope.get('province_scopes', []):
                unit = item['id']; count = len(members[unit]); item['partial'] = len(set(scope['member_location_ids']) & set(members[unit])) != count
                for field in ['full_province_locations', 'full_area_location_count', 'full_current_location_count']:
                    if field in item: item[field] = count
            assert all(scope[k] == before[k] for k in ['batch_id', 'member_location_ids', 'member_location_ids_sha256', 'owned_evidence_path']); return '```json\n' + js(scope) + '\n```'
        body = re.sub(r'```json\s*\n([\s\S]*?)\n```', replace_scope, body)
        for label, value in [('Hierarchy SHA-256', release['hierarchy_sha256']), ('Footprints SHA-256', release['footprints_sha256']), ('Macro certificate SHA-256', cert), ('Frozen region geometry SHA-256', envs[region]['geometry_sha256']), ('Frozen region member IDs SHA-256', envs[region]['member_location_ids_sha256'])]: body = re.sub(r'^' + re.escape(label) + r': `[^`]+`\.', label + ': `' + value + '`.', body, flags=re.M)
        body = re.sub(r'^Release: `[^`]+` \(v4\)\.', 'Release: `' + release['id'] + '` (v5).', body, flags=re.M)
        news = [x for x in additions if x['scope']['region_id'] == region]
        if role == 'approval' and news and all(isinstance(x['number'], int) for x in news):
            def deps(match):
                work = json.loads(match[1]); work['depends_on'] = list(dict.fromkeys(work['depends_on'] + [x['number'] for x in news])); return '<!-- worldatlas-work:v1\n' + js(work) + '\n-->'
            body = re.sub(r'<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->', deps, body)
        body += f'\n\n{date} (America/Los_Angeles): v5 queue scope refresh; original members/owned paths and all claims/comments remain unchanged. Region now has {len(members[region])} locations. New supplemental dependencies: ' + (', '.join('#' + str(x['number']) if x['number'] else x['key'] for x in news) or 'none') + '. Regional interiors and historical location-attribute imports remain unapproved.\n'
        updates.append({'number': number, 'role': role, 'region_id': region, 'before_body_sha256': sha(actual['body']), 'before_updated_at': actual['updated_at'], 'before_labels': labels, 'body': body, 'labels': labels, 'owned_members_changed': False, 'require_fresh_canonical_claim_check': True})
    allids = oldids + sorted(NEW_IDS); assert len(allids) == len(set(allids)) == 49625 and set(allids) == set(chains)
    return {'version': 1, 'read_only': True, 'publication_verified': verified, 'release': release, 'macro_certificate_sha256': cert, 'proof': {'packets': 275, 'locations': 49625, 'new_subjects': sorted(NEW_IDS), 'missing': 0, 'duplicates': 0}, 'issue_creations': additions, 'issue_updates': updates, 'preserved_issues': holds, 'previous_issue_archive': archives, 'publication_gate': {'issue_number_links_resolved': all(isinstance(x['number'], int) for x in additions), 'required_before_execution': ['Matching final handoffs + root-verified live v5 receipt; no historical imports', 'Fresh body hash, updated_at, exact labels and canonical comment claim check before every write; preserve closed/claimed issues and replan late edits', 'Idempotent create supplements, resolve their numeric IDs, replan approval dependencies, then exhaustive issue readback; no state/label/comment mutation']}}
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ['candidate', 'issues', 'output']: p.add_argument('--' + name, required=True)
    for name in ['handoffs', 'live-confirmation', 'created-issues', 'changed-ids']: p.add_argument('--' + name)
    args = p.parse_args(); result = produce(args); Path(args.output).write_bytes(gzip.compress(js(result).encode(), mtime=0)); print(js({'publication_verified': result['publication_verified'], 'updates': len(result['issue_updates']), 'preserved': len(result['preserved_issues']), 'proof': result['proof']}))
