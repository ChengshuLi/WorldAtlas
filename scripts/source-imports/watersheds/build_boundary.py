"""Regenerate an editable mainland boundary from a Neon construction record."""
import argparse
from contextlib import closing
import hashlib
from importlib.metadata import version
import json
import logging
import os
from pathlib import Path
import platform
import time

from shapely.geometry import LineString

from source_io import assemble_parts, catalog_source, download_source, read_recipe, save_boundary
from watersheds.boundary import Divide, assemble, cell_at, distance, flow_to_point, geodesic, intersection
from watersheds.drainage import compute_flow, destinations
from watersheds.sources import Sources
from watersheds.terrain import prepare
from watersheds.waterways import Basins, seed_grid

LOGGER = logging.getLogger(__name__)


def runtime_versions():
    from osgeo import gdal, osr
    import pyproj
    import shapely

    database = Path(pyproj.datadir.get_data_dir()) / 'proj.db'
    return {'python': platform.python_version(),
            'packages': {name: version(name) for name in (
                'numpy', 'pyproj', 'shapely', 'numba', 'llvmlite', 'pyshp', 'osmium', 'boto3', 'psycopg')},
            'gdal': gdal.VersionInfo('RELEASE_NAME'), 'pyproj_proj': pyproj.proj_version_str,
            'gdal_proj': '.'.join(map(str, (osr.GetPROJVersionMajor(), osr.GetPROJVersionMinor(),
                                          osr.GetPROJVersionMicro()))),
            'shapely_geos': shapely.geos_version_string,
            'proj_database_sha256': hashlib.sha256(database.read_bytes()).hexdigest()}


def resolve_sources(database, recipe):
    """Resolve exact catalog versions, including the parts of large provider files."""
    resolved = {}
    for alias, selection in recipe['sources'].items():
        if 'parts' in selection:
            resolved[alias] = dict(selection, parts=[
                catalog_source(database, part['source_id'], part['version'])
                for part in selection['parts']])
        else:
            resolved[alias] = catalog_source(database, selection['source_id'], selection['version'])
    return resolved


def stage_sources(client, selections, work_dir):
    files, references = {}, []
    for alias, source in selections.items():
        if 'parts' in source:
            files[alias] = assemble_parts(client, source['parts'], source['sha256'],
                                          source['size_bytes'], source['filename'], work_dir)
            references.extend(source['parts'])
        else:
            files[alias] = download_source(client, source, work_dir)
            references.append(source)
    return files, references


def construct(recipe, files):
    """Calculate independent sections, choose their shared joins, then assemble once.

    Source IDs, drainage identities, domains and geographic route choices are
    construction data. Algorithms do not depend on the boundary's name.
    """
    started = time.monotonic()
    report = {'terrain': {}, 'connections': {}}
    with Sources(files) as sources:
        lines = {name: sources.line(parts) for name, parts in recipe['lines'].items()}
        report['source_geometry_seconds'] = time.monotonic() - started
        divides, connections = {}, {}
        for name, settings in recipe.get('terrains', {}).items():
            phase = time.monotonic()
            domains = settings['domains']
            if not domains:
                raise ValueError('terrain requires at least one analysis domain')
            paths = lambda selected: [sources.path({'source': item} if isinstance(item, str) else item)
                                      for item in selected]
            bounds = [min(b[0] for b in domains), min(b[1] for b in domains),
                      max(b[2] for b in domains), max(b[3] for b in domains)]
            network = sources.network(settings.get('waterways', []), natural_only=True)
            if network.nodes:
                # Complete ways can end outside the terrain crop. Include those
                # destinations when looking up source basin identities.
                bounds = [min(bounds[0], min(p[0] for p in network.nodes.values())),
                          min(bounds[1], min(p[1] for p in network.nodes.values())),
                          max(bounds[2], max(p[0] for p in network.nodes.values())),
                          max(bounds[3], max(p[1] for p in network.nodes.values()))]
            basins = Basins(paths(settings['basins']), settings['basin_attribute'],
                            settings['groups'], bounds)
            assigned, network_report = (network.groups(settings['waterway_groups'])
                                        if 'waterway_groups' in settings else network.basin_groups(basins))
            network_seconds = time.monotonic() - phase
            required = [(i, section['flow']) for i, section in enumerate(recipe['sections'])
                        if 'flow' in section and section['flow']['terrain'] == name]
            if required and len(domains) != 1:
                raise ValueError('a stream-head connection requires one continuous terrain domain')
            graph, domain_reports = Divide(), []
            for domain in domains:
                tick = time.monotonic()
                grid = prepare(paths(settings['primary']), domain,
                               paths(settings.get('secondary', [])),
                               sources.path({'source': settings['height_offset']})
                               if 'height_offset' in settings else None)
                terrain_seconds = time.monotonic() - tick
                step = time.monotonic()
                seeds, seed_report = seed_grid(network, assigned, grid)
                for _, flow_settings in required:
                    point = sources.point(flow_settings['point'], lines)
                    row, column = cell_at(grid, point)
                    group = int(flow_settings['inside_group'])
                    if seeds[row, column] not in (-1, group):
                        raise ValueError('source stream head conflicts with a mapped drainage group')
                    seeds[row, column] = group
                closed = []
                for sink in settings.get('closed_sinks', []):
                    row, column = cell_at(grid, sources.point(sink['point'], lines))
                    group = int(sink['group'])
                    if group < 0 or seeds[row, column] not in (-1, group):
                        raise ValueError('closed drainage destination conflicts with a mapped group')
                    seeds[row, column] = group
                    closed.append((row, column))
                seed_seconds = time.monotonic() - step
                step = time.monotonic()
                working, flow = compute_flow(grid, closed)
                labels = destinations(flow, seeds, basins.terminals(grid, flow))
                drainage_seconds = time.monotonic() - step
                step = time.monotonic()
                graph.add_grid(grid, labels, settings['interfaces'])
                for index, flow_settings in required:
                    curve, receipt = flow_to_point(
                        grid, flow, labels, sources.point(flow_settings['point'], lines),
                        int(flow_settings['inside_group']), flow_settings['outside_groups'],
                        flow_settings['max_step_m'])
                    connections[index] = curve
                    report['connections'][str(index)] = receipt
                domain_reports.append({
                    'bounds': domain, 'shape': list(labels.shape),
                    'secondary_cells': grid.secondary_cells,
                    'unknown_cells': int((labels < 0).sum()),
                    'raised_cells': int((working > grid.elevation).sum()),
                    'max_raise_m': float((working - grid.elevation).max()),
                    'seeds': seed_report, 'terrain_seconds': terrain_seconds,
                    'seed_seconds': seed_seconds, 'drainage_seconds': drainage_seconds,
                    'divide_seconds': time.monotonic() - step,
                    'seconds': time.monotonic() - tick,
                })
                LOGGER.info('%s: %s cells, %.2f seconds', name, labels.shape,
                            domain_reports[-1]['seconds'])
            divides[name] = graph
            report['terrain'][name] = {'domains': domain_reports, 'network': network_report,
                                       'network_seconds': network_seconds,
                                       'seconds': time.monotonic() - phase}
        phase = time.monotonic()
        def selected_point(specification):
            if 'nearest_divide' in specification:
                target = sources.point(specification['near'], lines)
                return divides[specification['nearest_divide']].nearest_vertex(target).point
            return sources.point(specification, lines)

        sections = []
        for index, section in enumerate(recipe['sections']):
            if 'line' in section:
                sections.append(lines[section['line']])
            elif 'divide' in section:
                sections.append(divides[section['divide']])
            elif 'flow' in section:
                sections.append(connections[index])
            elif 'geodesic' in section:
                choice = section['geodesic']
                first, last = selected_point(choice['start']), selected_point(choice['end'])
                sections.append(LineString(geodesic(first, last, choice['max_step_m'])))
                report.setdefault('connectors', {})[str(index)] = {
                    'start': list(first), 'end': list(last), 'length_m': distance(first, last)}
            else:
                raise ValueError('unknown boundary section type')
        if len(recipe['joins']) != len(sections) - 1:
            raise ValueError('one geographic join selection is required between adjacent sections')
        joins = [intersection(a, b, choice['near'])
                 for a, b, choice in zip(sections, sections[1:], recipe['joins'])]
        geometry = assemble(sections, joins, selected_point(recipe['start']), selected_point(recipe['end']))
        report['joins'] = [list(join.point) for join in joins]
        report['assembly_seconds'] = time.monotonic() - phase
    report['construction_seconds'] = time.monotonic() - started
    return geometry, report


def build_boundary(database, client, recipe_id, recipe_version, revision, work_dir):
    """Read immutable inputs, calculate, then save the final result atomically."""
    with database.transaction():
        if database.execute('SELECT 1 FROM atlas.decision_revisions WHERE revision=%s',
                            (revision,)).fetchone() is None:
            raise ValueError('destination decision revision does not exist')
        recipe = read_recipe(database, recipe_id, recipe_version)
        if recipe.get('method') != 'watershed_boundary' or not recipe.get('basis') or not recipe.get('boundary_id'):
            raise ValueError('invalid watershed construction record')
        selections = resolve_sources(database, recipe)
        evidence = [dict(catalog_source(database, item['source_id'], item['version']),
                         relationship='supporting_evidence')
                    for item in recipe.get('evidence_sources', [])]
    started = time.monotonic()
    files, references = stage_sources(client, selections, work_dir)
    download_seconds = time.monotonic() - started
    geometry, report = construct(recipe, files)
    runtime = runtime_versions()
    provenance = {'basis': recipe['basis'], 'lineage_status': 'complete', 'construction': {
        'processor': 'watersheds.build_boundary', 'recipe_id': recipe_id,
        'recipe_version': recipe_version, 'sources': [
            {'source_id': source['source_id'], 'version': source['version'], 'sha256': source['sha256']}
            for source in references],
    }}
    started = time.monotonic()
    digest = save_boundary(database, revision, recipe['boundary_id'], geometry, provenance,
                           [*references, *evidence])
    report.update(revision=revision, boundary_id=recipe['boundary_id'], sha256=digest,
                  vertices=len(geometry['coordinates']), download_verify_seconds=download_seconds,
                  save_seconds=time.monotonic() - started)
    report['runtime'] = runtime
    return report


def main():
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', nargs=2, required=True, metavar=('ID', 'VERSION'))
    parser.add_argument('--revision', required=True)
    parser.add_argument('--r2-endpoint', required=True)
    parser.add_argument('--work-dir', type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get('NEON_DATABASE_URL'):
        parser.error('set NEON_DATABASE_URL to the working database')
    import boto3
    import psycopg

    with psycopg.connect(os.environ['NEON_DATABASE_URL']) as database, closing(
            boto3.client('s3', endpoint_url=args.r2_endpoint, region_name='auto')) as client:
        result = build_boundary(database, client, *args.recipe, args.revision, args.work_dir)
    destination = args.work_dir / 'receipts' / f'{args.recipe[0]}-{args.recipe[1]}.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
