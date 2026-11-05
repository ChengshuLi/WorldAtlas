"""Check a pinned exported revision's selected Caucasus source binding.

Read-only: this checks an existing export and real raw sources, but does not
write Neon, select a recipe, run the outer pipeline, or establish watershed
correctness. The caller must authenticate the export and all code pins.
"""
import argparse
import json
from caucasus_effective_snapshot import derive_verified
from caucasus_seed_gate import BOUNDARY


def preflight(request, request_sha256, recipe, recipe_sha256, hydro, author):
    effective, trace = derive_verified(request, request_sha256, recipe, recipe_sha256, hydro, author)
    selected = [x for x in effective['mainland_boundaries'] if x.get('boundary_id') == BOUNDARY]
    if len(selected) != 1:
        raise ValueError('expected one Caucasus boundary')
    gate = trace['source_gate']
    view = trace['effective_snapshot']
    return {'schema': 'caucasus-selected-revision-preflight-v1',
            'request_sha256': trace['request_sha256'],
            'snapshot_sha256': view['original_snapshot_sha256'],
            'recipe_sha256': gate['recipe_sha256'],
            'selected_geometry_sha256': view['selected_geometry_sha256'],
            'derived_geometry_sha256': view['derived_geometry_sha256'],
            'source_sha256': gate['source_sha256'],
            'possible_changed_centers': gate['assembly']['comparison']['possible_changed_centers'],
            'regions': view['regions'],
            'limitations': 'Source replay against pinned export; not a watershed or outer-pipeline validation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('request', 'request-sha256', 'recipe', 'recipe-sha256', 'hydro', 'author'):
        parser.add_argument('--' + name, required=True)
    a = parser.parse_args()
    result = preflight(a.request, a.request_sha256, a.recipe, a.recipe_sha256, a.hydro, a.author)
    print(json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False))


if __name__ == '__main__':
    main()
