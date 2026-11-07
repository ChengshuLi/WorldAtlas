"""Validate a provisional Neon geography-decision export for test builds.

A local JSON document is a transport snapshot, not proof of Neon acceptance.
Authenticated export and revision verification remain to be implemented.
"""
import hashlib
import json


def validate_revision(data, allow_draft=False):
    revision = data.get('decision_revision', {})
    entity = data.get('entity_revision', {})
    valid_ids = (isinstance(revision.get('id'), str) and revision['id'].strip()
                 and isinstance(revision.get('entity_revision'), str) and revision['entity_revision'].strip())
    accepted = (data.get('schema') == 'worldatlas-geography-decision-export-v1'
                and revision.get('status') == 'accepted' and entity.get('status') == 'accepted'
                and entity.get('id') == revision.get('entity_revision'))
    draft = (allow_draft and data.get('schema') == 'worldatlas-geography-decision-draft-evidence-v1'
             and revision.get('status') == 'draft' and entity.get('status') == 'draft'
             and entity.get('id') == revision.get('entity_revision'))
    local = (allow_draft and data.get('source') == 'local-user-directed-overlay-not-neon' and data.get('_local_overlay_verified') is True and data.get('schema') == 'worldatlas-local-water-effective-snapshot-v1' and revision.get('status') == 'draft' and entity.get('status') == 'draft' and entity.get('id') == revision.get('entity_revision'))
    if (data.get('source') != 'neon-export' and not local) or not valid_ids or not (accepted or draft or local):
        raise ValueError('an accepted or explicitly opted-in draft revisioned Neon decision export is required')
    return revision


def read_snapshot(path, expected_sha256, allow_draft=False):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('decision snapshot hash mismatch')
    data = json.loads(raw)
    if data.get('source') == 'local-user-directed-overlay-not-neon':
        import local_water_overlay
        local_water_overlay.verify(data)
        data['_local_overlay_verified'] = True
    validate_revision(data, allow_draft=allow_draft)
    return data


def find_basin(snapshot, decision_id):
    matches = [x for x in snapshot.get('basins', []) if x.get('id') == decision_id]
    if len(matches) != 1:
        raise ValueError('basin decision ID must identify exactly one selected decision')
    return matches[0]


def find_source(snapshot, basin):
    matches = [x for x in snapshot.get('sources', []) if x.get('source_id') == basin.get('source_id') and x.get('version') == basin.get('source_version')]
    if len(matches) != 1:
        raise ValueError('decision must bind to one pinned source version')
    digest = matches[0].get('sha256')
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('source SHA-256 must be a lowercase hexadecimal digest')
    return matches[0]


def participant_water_codes(snapshot, basin):
    """Adapt stable participant IDs through matching V7 registry bindings."""
    entities = basin.get('participant_entity_ids'); bindings = snapshot.get('category_bindings')
    if not isinstance(entities, list) or not entities or len(set(entities)) != len(entities) or not isinstance(bindings, list):
        raise ValueError('invalid basin participants or registry bindings')
    codes = []
    for entity in entities:
        matches = [b for b in bindings if b.get('entity_id') == entity and b.get('physical_class') == 'water']
        if len(matches) != 1 or type(matches[0].get('code')) is not int or matches[0]['code'] not in range(1, 7):
            raise ValueError(f'participant has no unique V7 water binding: {entity}')
        codes.append(matches[0]['code'])
    if len(set(codes)) != len(codes):
        raise ValueError('basin participant water codes are not unique')
    return sorted(codes)
