"""Bind the selected Neon water and ocean decisions to this run's land."""
import hashlib
import json
from pathlib import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(doc):
    provenance = doc.get('local_overlay_provenance', {})
    fields = ('base_land_snapshot_path', 'water_neon_snapshot_path', 'ocean_neon_snapshot_path')
    if not all(isinstance(provenance.get(field), str) and provenance[field] for field in fields):
        raise ValueError('materialized water snapshot lacks the selected input paths')
    expected = bind_selected(*(provenance[field] for field in fields))
    if doc != expected:
        raise ValueError('materialized water snapshot differs from the selected inputs')
    return True


def bind_selected(land_path, water_path, ocean_path):
    """Bind editable water and ocean decisions to the land built by this run."""
    paths = {'base_land_snapshot': Path(land_path).resolve(),
             'water_neon_snapshot': Path(water_path).resolve(),
             'ocean_neon_snapshot': Path(ocean_path).resolve()}
    contents = {name: path.read_bytes() for name, path in paths.items()}
    land, water, ocean = map(json.loads, contents.values())
    registry = land['entity_revision']['id']
    for snapshot in (land, water, ocean):
        if (snapshot['source'] != 'neon-export'
                or snapshot['decision_revision']['status'] != 'draft'
                or snapshot['decision_revision']['entity_revision'] != registry
                or snapshot['entity_revision']['id'] != registry
                or snapshot['entity_revision']['status'] != 'draft'
                or snapshot['category_bindings'] != land['category_bindings']):
            raise ValueError('selected land, water and ocean must share one draft registry')
    policy_kinds = {'coastline_assignment', 'closed_water_assignment', 'layer_precedence'}
    policies = water['policies']
    if len(policies) != len(policy_kinds) or {p['kind'] for p in policies} != policy_kinds:
        raise ValueError('selected water revision lacks the three water policies')
    ocean_policy, = (p for p in ocean['policies'] if p['kind'] == 'ocean_fill')
    if any(not selected({}, p) for p in [*policies, ocean_policy]):
        raise ValueError('selected water and ocean policies must be enabled')
    ocean_policy['evidence']['execution_status'] = 'local_user_authorized_overlay'
    provenance = {name + '_path': str(path) for name, path in paths.items()}
    provenance.update({name + '_sha256': sha(raw) for name, raw in contents.items()})
    return {'schema': 'worldatlas-local-water-effective-snapshot-v1',
            'source': 'local-user-directed-overlay-not-neon',
            'local_overlay_provenance': provenance,
            'decision_revision': land['decision_revision'],
            'entity_revision': land['entity_revision'],
            'category_bindings': land['category_bindings'],
            'basins': water['basins'], 'sources': water['sources'], 'features': water['features'],
            'policies': [*policies, ocean_policy], 'endpoints': ocean['endpoints'],
            'routes': ocean['routes'], 'ocean_seeds': ocean['ocean_seeds']}


def selected(snapshot,record):
    e=record.get('evidence',{})
    return (e.get('execution_status')=='selected_for_research' or (snapshot.get('_local_overlay_verified') is True and e.get('execution_status')=='local_user_authorized_overlay'))

def land_snapshot_hash(snapshot,water_sha):
    if snapshot.get('_local_overlay_verified') is True:return snapshot['local_overlay_provenance']['base_land_snapshot_sha256']
    return water_sha
