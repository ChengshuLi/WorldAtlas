#!/usr/bin/env python3
"""Plan source-hint repairs without changing retained evidence or contacting GitHub."""
import argparse
import copy
import gzip
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.immutable import Baseline, VERSION, canonical_json, descriptor, sha256

OLD_PATH = 'data/macro-foundation/new-location-source-profiles-v4.json.gz'
PROFILE_PATH = 'data/reference-migrations/macro-improvements-v4/queue-checkpoint/new-location-source-profiles-v4.json.gz'
COMPRESSED_SHA256 = 'f13cb0b2a023c5bce5abdb3223f99148685961d4608b4acb81c3c2ea800d680e'
UNCOMPRESSED_SHA256 = 'b1f86acef46ac0c4fd04c275774294809b89eef2ae1d656a78c2e0ba4980167b'
SUPPLEMENT_NUMBERS = tuple(range(520, 528))
HASH_SCOPE = 'canonical-entry-utf8-json-without-trailing-newline'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def entry_hash(record):
    # Original issue hashes use Python sorted compact UTF-8 JSON WITHOUT a newline.
    # The shared new-output helper includes one; remove it only for this legacy contract.
    return sha256(canonical_json(record)[:-1])


def profile_index(records):
    require(isinstance(records, list), 'Expected the retained source-profile array')
    result = {}
    for record in records:
        identity = record.get('location_id')
        require(isinstance(identity, str) and identity and identity not in result,
                'Missing or duplicate retained profile identity')
        result[identity] = record
    return result


def source_artifact(compressed, uncompressed):
    require(sha256(compressed) == COMPRESSED_SHA256, 'Compressed source file pin changed')
    require(sha256(uncompressed) == UNCOMPRESSED_SHA256, 'Uncompressed source file pin changed')
    return {'path': PROFILE_PATH,
            'compressed_file': {'sha256': sha256(compressed), 'bytes': len(compressed)},
            'uncompressed_file': {'sha256': sha256(uncompressed), 'bytes': len(uncompressed)},
            'entry_hash': {'algorithm': 'sha256', 'scope': HASH_SCOPE,
                           'serialization': 'Python json.dumps(sort_keys=True, separators=(\",\",\":\"), ensure_ascii=False, allow_nan=False)',
                           'identity_field': 'location_id'}}


def repair_issue(issue, profiles, artifact):
    body = issue['body']
    candidates = []
    for match in re.finditer(r'```json[^\S\n]*\n(.*?)\n```', body, re.S):
        value = json.loads(match[1])
        if isinstance(value, dict) and 'source_profile_hints' in value:
            candidates.append((match, value))
    require(len(candidates) == 1, 'Expected exactly one supplemental source-hint scope')
    match, before = candidates[0]
    hints = before['source_profile_hints']
    require(isinstance(hints, list) and hints, 'Missing source hints')
    identities = [hint['location_id'] for hint in hints]
    require(len(set(identities)) == len(identities) and
            sorted(identities) == sorted(before['member_location_ids']),
            'Source hints must exhaust the exact disjoint owned subjects')
    after = copy.deepcopy(before)
    require('source_profile_artifact' not in before or before['source_profile_artifact'] == artifact,
            'An existing source artifact declaration disagrees with retained bytes')
    after['source_profile_artifact'] = artifact
    verified = []
    for original, hint in zip(hints, after['source_profile_hints']):
        identity = original['location_id']
        require(identity in profiles, 'Advertised subject has no retained profile: ' + identity)
        digest = entry_hash(profiles[identity])
        require(original['full_source_profile_canonical_sha256'] == digest,
                'Advertised canonical entry hash mismatch: ' + identity)
        require(original['durable_full_source_profile_path'] in (OLD_PATH, PROFILE_PATH),
                'Unexpected advertised profile path: ' + identity)
        require(original.get('full_source_profile_hash_scope', HASH_SCOPE) == HASH_SCOPE,
                'Existing entry hash scope disagrees with the original contract')
        hint['durable_full_source_profile_path'] = PROFILE_PATH
        hint['full_source_profile_hash_scope'] = HASH_SCOPE
        verified.append({'location_id': identity, 'canonical_entry_sha256': digest})
    # Prove every non-hint field, subject, release pin and ownership declaration survives.
    before_rest = copy.deepcopy(before)
    after_rest = copy.deepcopy(after)
    for value in (before_rest, after_rest):
        value.pop('source_profile_artifact', None)
        for hint in value['source_profile_hints']:
            hint['durable_full_source_profile_path'] = OLD_PATH
            hint.pop('full_source_profile_hash_scope', None)
    require(before_rest == after_rest, 'Instruction repair changed unrelated scope')
    replacement = json.dumps(after, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    patched = body[:match.start(1)] + replacement + body[match.end(1):]
    require(OLD_PATH not in patched, 'An obsolete source pointer remains outside the scoped hints')
    return {'number': issue['number'], 'state': issue['state'],
            'before_updated_at': issue.get('updated_at'),
            'before_body_sha256': sha256(body.encode()), 'after_body_sha256': sha256(patched.encode()),
            'body': patched, 'verified_entries': verified,
            'unrelated_scope_preserved': True, 'changed': body != patched}


def build_plan(baseline, snapshots):
    compressed = baseline.read(PROFILE_PATH)
    # Inputs are bounded by the shared baseline helper; cap gzip expansion as well.
    import io
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        uncompressed = stream.read(32 * 1024 * 1024 + 1)
    require(len(uncompressed) <= 32 * 1024 * 1024, 'Uncompressed source file exceeds byte budget')
    artifact = source_artifact(compressed, uncompressed)
    profiles = profile_index(json.loads(uncompressed))
    require(sorted(issue['number'] for issue in snapshots) == list(SUPPLEMENT_NUMBERS),
            'Use exactly the eight original supplemental issues')
    rows = [repair_issue(issue, profiles, artifact) for issue in sorted(snapshots, key=lambda row: row['number'])]
    ids = [entry['location_id'] for row in rows for entry in row['verified_entries']]
    require(len(ids) == len(set(ids)) and set(ids) == set(profiles),
            'Supplemental issue inventory does not exhaust retained source profiles once')
    return {'version': 1, 'issue': 554, 'helper_version': VERSION,
            'baseline_commit': baseline.commit, 'source_artifact': artifact,
            'repairs': rows, 'subject_ids': sorted(ids),
            'limits': ['Instruction/hash repair only; no new source inspection, geographic approval or content permission.',
                       'Apply requires fresh canonical reservations, active-PR and body-hash checks; this planner is offline.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', required=True, help='Reviewed exact immutable commit')
    parser.add_argument('--issues', type=Path, required=True, help='Directory containing issue-N.json snapshots')
    parser.add_argument('--out', type=Path, required=True, help='New owned plan file; never overwrites')
    args = parser.parse_args()
    compressed = (ROOT / PROFILE_PATH).read_bytes()
    require(sha256(compressed) == COMPRESSED_SHA256, 'Checkout source evidence does not match the reviewed pin')
    baseline = Baseline(ROOT, args.baseline, [descriptor(PROFILE_PATH, compressed)])
    snapshots = [json.loads((args.issues / f'issue-{number}.json').read_bytes()) for number in SUPPLEMENT_NUMBERS]
    plan = build_plan(baseline, snapshots)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('xb') as output:
        output.write(canonical_json(plan))
    print(json.dumps({'plan': str(args.out), 'source_bytes_verified': True,
                      'issue_numbers': list(SUPPLEMENT_NUMBERS), 'subjects': len(plan['subject_ids']),
                      'github_mutations': False}))


if __name__ == '__main__':
    main()
