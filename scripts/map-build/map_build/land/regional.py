"""Apply selected structured geographic records to current land components."""
import json
from pathlib import Path
import time

from map_build.land.affiliations import resolve_affiliations
from map_build.land.components import ComponentGrid
from map_build.land.composition import compose_land


def build_regional(selection, grid, physical_directory, component_directory,
                   mainland_directory, directory, *, protected=(), partitions=()):
    """Resolve working geographic rules and return final land paths and counts."""
    started = time.monotonic()
    domain = selection['domains']['regional']
    rules = domain['affiliations']
    if any(rule['method'] != 'component_selection' for rule in rules):
        raise ValueError('regional rules must use source-neutral component selections')
    directory = Path(directory)
    directory.mkdir()
    with ComponentGrid(physical_directory, component_directory, grid) as components:
        resolved = resolve_affiliations(rules, domain['features'], components,
                                        domain['category_bindings'], protected=protected)
        result = compose_land(components, mainland_directory, resolved['component_entities'],
                              domain['category_bindings'], directory / 'land', partitions=partitions)
    report = {'land': str(directory / 'land'), 'claims': resolved['claims'], 'counts': result['counts'],
              'processing_seconds': time.monotonic() - started, 'download_seconds': 0.}
    (directory / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
