"""Apply selected structured geographic records to current land components."""
from worldatlas.map_build.inputs.selection import geographic_domain, selection_domains


import json
from pathlib import Path
import time

from worldatlas.map_build.land.geographic_assignments import resolve_assignments
from worldatlas.map_build.land.components import ComponentGrid
from worldatlas.map_build.land.composition import compose_land
from worldatlas.map_build.land.regions import assemble_regions
from worldatlas.map_build.land.partitions import build_partitions, resolve_component_partitions
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
        if selection.get('regional_partitions') or selection.get('regional_partition'):
            raise ValueError('historical regional rules require the release archive\'s captured code')
        inferred = resolve_component_partitions(
            domain.get('partitions', []), domain['features'], components,
            domain['category_bindings'], protected=protected,
        )
        for root, entity in inferred['component_entities'].items():
            if root in entities and entities[root] != entity:
                raise ValueError('geographic partition conflicts with an explicit assignment')
            entities[root] = entity
        mainland = (geographic_domain(selection, 'mainland')
                    if 'mainland' in selection_domains(selection) else None)
        geographic = []
        if mainland is not None and any(p['method'] == 'land_cells'
                                        for p in mainland.get('partitions', [])):
            regions, _ = assemble_regions(mainland, components)
            geographic = build_partitions(mainland, regions)
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
        'partitions': inferred['claims'],
        'processing_seconds': time.monotonic() - started,
        'download_seconds': 0.0,
    }
    (directory / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
