"""Apply selected structured geographic records to current land components."""
from worldatlas.map_build.inputs.selection import geographic_domain, selection_domains


import json
from pathlib import Path
import time

from worldatlas.map_build.land.geographic_assignments import resolve_assignments
from worldatlas.map_build.land.components import ComponentGrid
from worldatlas.map_build.land.composition import compose_land
from worldatlas.map_build.land.islands import resolve_islands
from worldatlas.map_build.land.partitions import build_partitions
from worldatlas.map_build.inputs.selection import validate_bindings


def build_regional(
    selection,
    grid,
    physical_directory,
    component_directory,
    mainland_directory,
    directory,
    *,
    protected=(),
    partitions=(),
    component_defaults=None,
):
    """Resolve working geographic rules and return final land paths and counts."""
    started = time.monotonic()
    validate_bindings(selection_domains(selection))
    domain = geographic_domain(selection, 'regional')
    rules = domain['assignments'] if 'assignments' in domain else domain['affiliations']
    directory = Path(directory)
    directory.mkdir()
    with ComponentGrid(physical_directory, component_directory, grid) as components:
        resolved = resolve_assignments(
            rules, domain['features'], components, domain['category_bindings'], protected=protected
        )
        entities = dict(resolved['component_entities'])
        islands = []
        policies = selection.get('regional_partitions', [])
        # Read earlier frozen selections without changing their stored bytes.
        if 'regional_partition' in selection:
            policies = [selection['regional_partition']]
        features = {f['feature_id']: f for f in domain['features']}
        for selected in policies:
            # Earlier archives carry their line inline; new selections reference the shared feature.
            line = selected['line'] if 'line' in selected else features[selected['feature_id']]
            result = resolve_islands(
                selected['policy'],
                line,
                domain['features'],
                selection['raw_sources'],
                components,
                resolved['component_entities'],
                domain['category_bindings'],
                protected=protected,
            )
            conflicts = {
                root: reason
                for root, reason in result['review'].items()
                if reason
                in {
                    'conflicting_regional_group_conventions',
                    'conflicting_group_and_anchor',
                    'conflicting_nearest_land_targets',
                }
            }
            if conflicts:
                raise ValueError(
                    f"conflicting regional assignments for {selected.get('rule_set_id', 'regional rule')}: {conflicts}"
                )
            for root, entity in result['component_entities'].items():
                if root in entities and entities[root] != entity:
                    raise ValueError('regional line rules conflict with a selected affiliation')
                entities[root] = entity
            islands.append(result)
        geographic = (
            build_partitions(geographic_domain(selection, 'mainland'))
            if 'mainland' in selection_domains(selection)
            else []
        )
        result = compose_land(
            components,
            mainland_directory,
            entities,
            domain['category_bindings'],
            directory / 'land',
            partitions=[*geographic, *partitions],
            component_defaults=component_defaults,
        )
    report = {
        'land': str(directory / 'land'),
        'claims': resolved['claims'],
        'counts': result['counts'],
        'islands': islands,
        'processing_seconds': time.monotonic() - started,
        'download_seconds': 0.0,
    }
    (directory / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
