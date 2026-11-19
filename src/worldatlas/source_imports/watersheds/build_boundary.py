"""Regenerate an editable mainland boundary from a Neon construction record."""
import hashlib
from importlib.metadata import version
import logging
from pathlib import Path
import platform
import time
from typing import Any

import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString

from worldatlas.geodesy.wgs84 import geodesic
from worldatlas.source_imports.shared.contracts import NonEmptyText, SourceId
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.sources import MultipartSource, acquire_sources
from worldatlas.source_imports.shared.storage import save_features
from worldatlas.source_imports.watersheds.basins import Basins
from worldatlas.source_imports.watersheds.boundary import (
    Divide, assemble, cell_at, distance, flow_to_point, intersection,
)
from worldatlas.source_imports.watersheds.drainage import compute_flow, possible_destinations, single_destinations
from worldatlas.source_imports.watersheds.sources import Sources
from worldatlas.source_imports.watersheds.terrain import align, prepare
from worldatlas.source_imports.watersheds.waterways import seed_grid

LOGGER = logging.getLogger(__name__)


def runtime_versions():
    """Record the dependency versions used for a watershed calculation.

    Returns:
        Versions of the Python and native libraries and the PROJ database checksum.
    """
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


def construct(files, *, line_selections, sections, joins, start, end, terrains=None):
    """Calculate watershed sections and assemble one final line.

    Args:
        files: Verified local paths keyed by the recipe's source aliases.
        line_selections: Provider feature selections keyed by line name.
        sections: Ordered source lines, divides, flow paths, or connectors.
        joins: Geographic anchors for intersections between adjacent sections.
        start: Selection for the first point of the boundary.
        end: Selection for the last point of the boundary.
        terrains: Analysis domains and drainage settings keyed by terrain name.

    Returns:
        The final GeoJSON boundary and a report of inputs, checks, and timings.
    """
    started = time.monotonic()
    report = {'terrain': {}, 'connections': {}}
    sources = Sources(files)
    lines = {name: sources.line(parts) for name, parts in line_selections.items()}
    report['source_geometry_seconds'] = time.monotonic() - started
    divides, connections, networks = {}, {}, []
    for name, settings in (terrains or {}).items():
        phase = time.monotonic()
        domains = settings['domains']
        if not domains:
            raise ValueError('terrain requires at least one analysis domain')
        bounds_of = lambda domain: domain['bounds'] if isinstance(domain, dict) else domain
        crs_of = lambda domain: domain.get('crs', 4326) if isinstance(domain, dict) else 4326
        paths = lambda selected: [sources.path({'source': item} if isinstance(item, str) else item)
                                  for item in selected]
        geographic_bounds = [Transformer.from_crs(crs_of(domain), 4326, always_xy=True)
                             .transform_bounds(*bounds_of(domain), densify_pts=21, errcheck=True)
                             for domain in domains]
        bounds = [min(b[0] for b in geographic_bounds), min(b[1] for b in geographic_bounds),
                  max(b[2] for b in geographic_bounds), max(b[3] for b in geographic_bounds)]
        network = sources.network(settings.get('waterways', []), natural_only=True,
                                  reverse=settings.get('reverse_waterways', []))
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
        network.require_destinations(geographic_bounds, network_report)
        if network not in networks:
            networks.append(network)
        network_seconds = time.monotonic() - phase
        required = [(i, section['flow']) for i, section in enumerate(sections)
                    if 'flow' in section and section['flow']['terrain'] == name]
        if required and len(domains) != 1:
            raise ValueError('a stream-head connection requires one continuous terrain domain')
        graph, domain_reports, relevant_ways = Divide(), [], set()
        sinks = [(sources.point(sink['point'], lines), int(sink['group']))
                 for sink in settings.get('closed_sinks', [])]
        if any(group < 0 for _, group in sinks):
            raise ValueError('closed drainage destinations require known group IDs')
        covered_sinks = set()
        for domain in domains:
            bounds = bounds_of(domain)
            output_bounds = domain.get('output_bounds') if isinstance(domain, dict) else None
            tick = time.monotonic()
            grid = prepare(paths(settings['primary']), bounds,
                           paths(settings.get('secondary', [])),
                           sources.path({'source': settings['height_offset']})
                           if 'height_offset' in settings else None,
                           bounds_crs=crs_of(domain))
            terrain_seconds = time.monotonic() - tick
            step = time.monotonic()
            seeds, seed_report = seed_grid(network, assigned, grid)
            relevant_ways.update(network.nearby(grid))
            def seed_point(row, column, group, message):
                present = {g for g, cells in seeds.items() if cells[row, column]}
                if present and present != {group}:
                    raise ValueError(message)
                seeds.setdefault(group, np.zeros(grid.elevation.shape, dtype=bool))[row, column] = True
            for _, flow_settings in required:
                point = sources.point(flow_settings['point'], lines)
                row, column = cell_at(grid, point)
                group = int(flow_settings['inside_group'])
                seed_point(row, column, group, 'source stream head conflicts with a mapped drainage group')
            closed = []
            for index, (point, group) in enumerate(sinks):
                cell = cell_at(grid, point, required=False)
                if cell is None:
                    continue
                row, column = cell
                seed_point(row, column, group, 'closed drainage destination conflicts with a mapped group')
                closed.append((row, column))
                covered_sinks.add(index)
            outlets, coastal_labels, coast_report = None, None, None
            if 'ocean_mask' in settings:
                selection = settings['ocean_mask']
                water = align(paths(selection['sources']), grid, resampling='near')
                ocean = np.isin(water, selection['values'])
                outlets, coastal_labels = basins.coastal_outlets(grid, ocean)
                unique_seeds = single_destinations(seeds, grid.elevation.shape)
                conflict = ((unique_seeds >= 0) & (coastal_labels >= 0) &
                            (unique_seeds != coastal_labels))
                # Traced river destinations take precedence over coarse basin
                # membership at the shore. Keep disagreements in the receipt.
                coastal_labels[unique_seeds >= 0] = unique_seeds[unique_seeds >= 0]
                coast_report = {'ocean_cells': int(ocean.sum()),
                                'land_outlet_cells': int((outlets & ~ocean).sum()),
                                'river_basin_conflicts': int(conflict.sum())}
            seed_seconds = time.monotonic() - step
            step = time.monotonic()
            working, flow = compute_flow(grid, closed, outlets=outlets)
            terminals = basins.terminals(grid, flow)
            if coastal_labels is not None:
                coastal_labels, coverage_report = basins.uncovered_exits(
                    grid, flow, outlets & ~ocean, coastal_labels, seeds)
                coast_report['source_coverage'] = coverage_report
                terminals[outlets] = coastal_labels[outlets]
            labels = possible_destinations(flow, seeds, terminals)
            drainage_seconds = time.monotonic() - step
            step = time.monotonic()
            graph.add_grid(grid, labels, settings['interfaces'], output_bounds,
                           bounds_crs=crs_of(domain))
            for index, flow_settings in required:
                curve, receipt = flow_to_point(
                    grid, flow, single_destinations(labels, flow.shape),
                    sources.point(flow_settings['point'], lines),
                    int(flow_settings['inside_group']), flow_settings['outside_groups'],
                    flow_settings['max_step_m'])
                connections[index] = curve
                report['connections'][str(index)] = receipt
            destination_count = np.zeros(flow.shape, dtype='int64')
            for cells in labels.values():
                destination_count += cells
            domain_reports.append({
                'bounds': bounds, 'output_bounds': output_bounds, 'shape': list(flow.shape),
                'bounds_crs': crs_of(domain),
                'secondary_cells': grid.secondary_cells,
                'unknown_cells': int((destination_count == 0).sum()),
                'shared_drainage_cells': int((destination_count > 1).sum()),
                'raised_cells': int((working > grid.elevation).sum()),
                'max_raise_m': float((working - grid.elevation).max()),
                'seeds': seed_report, 'terrain_seconds': terrain_seconds,
                'coast': coast_report,
                'seed_seconds': seed_seconds, 'drainage_seconds': drainage_seconds,
                'divide_seconds': time.monotonic() - step,
                'seconds': time.monotonic() - tick,
            })
            LOGGER.info('%s: %s cells, %.2f seconds', name, flow.shape,
                        domain_reports[-1]['seconds'])
        if len(covered_sinks) != len(sinks):
            raise ValueError('closed drainage destination is outside every analysis domain')
        divides[name] = graph
        network_report = dict(network_report)
        for category in ('ambiguous', 'unassigned'):
            network_report[category] = [way for way in network_report[category] if way in relevant_ways]
        network_report['shared_sections'] = [
            section for section in network_report['shared_sections']
            if any(way in relevant_ways for way, _, _ in section['source_segments'])]
        # The early check established that all relevant routes are resolved.
        network_report.pop('unresolved_sections')
        network_report['natural_ways_in_domains'] = len(relevant_ways)
        network_report['natural_ways_in_sources'] = len(network.natural)
        network_report['reversed_waterways'] = {
            ident: network.ways[ident].version for ident in settings.get('reverse_waterways', [])}
        report['terrain'][name] = {'domains': domain_reports, 'network': network_report,
                                   'network_seconds': network_seconds,
                                   'seconds': time.monotonic() - phase}
    phase = time.monotonic()
    def selected_point(specification, *, retain_join=False):
        if 'nearest_divide' in specification:
            target = sources.point(specification['near'], lines)
            join = divides[specification['nearest_divide']].nearest_vertex(target)
        else:
            return sources.point(specification, lines)
        return join if retain_join else join.point

    section_lines, waypoints = [], {}
    for index, section in enumerate(sections):
        if 'line' in section:
            section_lines.append(lines[section['line']])
        elif 'divide' in section:
            section_lines.append(divides[section['divide']])
            if section.get('via'):
                waypoints[index] = {'points': [sources.point(p, lines) for p in section['via']],
                                    'max_step_m': section['max_step_m']}
        elif 'flow' in section:
            section_lines.append(connections[index])
        elif 'geodesic' in section:
            choice = section['geodesic']
            first, last = selected_point(choice['start']), selected_point(choice['end'])
            section_lines.append(LineString(geodesic(first, last, choice['max_step_m'])))
            report.setdefault('connectors', {})[str(index)] = {
                'start': list(first), 'end': list(last), 'length_m': distance(first, last)}
        else:
            raise ValueError('unknown boundary section type')
    if len(joins) != len(section_lines) - 1:
        raise ValueError('one geographic join selection is required between adjacent sections')
    chosen_joins = [intersection(a, b, choice['near'])
                    for a, b, choice in zip(section_lines, section_lines[1:], joins)]
    geometry = assemble(section_lines, chosen_joins, selected_point(start, retain_join=True),
                        selected_point(end, retain_join=True),
                        waypoints=waypoints, connections=report['connections'])
    final_line = LineString(geometry['coordinates'])
    report['river_checks'] = [network.check_crossings(final_line) for network in networks]
    report['joins'] = [list(join.point) for join in chosen_joins]
    report['assembly_seconds'] = time.monotonic() - phase
    report['construction_seconds'] = time.monotonic() - started
    return geometry, report


def watershed_boundary(runtime: Runtime, *, feature_id: NonEmptyText, basis: NonEmptyText,
                       sources: dict[NonEmptyText, SourceId | MultipartSource],
                       lines: dict[NonEmptyText, list[dict[str, Any]]],
                       sections: list[dict[str, Any]], joins: list[dict[str, Any]],
                       start: dict[str, Any], end: dict[str, Any],
                       terrains: dict[NonEmptyText, dict[str, Any]] | None = None,
                       evidence_sources: list[SourceId] | None = None,
                       geographic_choices: dict[str, Any] | None = None):
    """Construct and save the final watershed boundary.

    Args:
        runtime: Import resources and saved recipe snapshot.
        feature_id: Output boundary ID in Neon.
        basis: Human-readable explanation retained in the recipe.
        sources: Source aliases mapped to catalog IDs or multipart files.
        lines: Provider feature selections keyed by line name.
        sections: Ordered source lines, divides, flow paths, or connectors.
        joins: Geographic anchors for intersections between adjacent sections.
        start: Selection for the first point of the boundary.
        end: Selection for the last point of the boundary.
        terrains: Optional analysis domains and drainage settings.
        evidence_sources: Additional catalog IDs cited as supporting evidence.
        geographic_choices: Optional geographic rationale retained in the recipe.

    Returns:
        Saved boundary identity, geometry checksum, and construction report.
    """
    acquisition = {}
    paths = acquire_sources(runtime, list(sources.values()), evidence_source_ids=evidence_sources or (),
                            timing=acquisition)
    files = dict(zip(sources, paths, strict=True))
    geometry, report = construct(files, line_selections=lines, sections=sections,
                                 joins=joins, start=start, end=end, terrains=terrains)
    versions = runtime_versions()
    started = time.monotonic()
    hashes = save_features(runtime, [dict(feature_id=feature_id, geometry=geometry)])
    digest = hashes[feature_id]
    staging_seconds = acquisition['source_staging_seconds']
    report.update(feature_id=feature_id, sha256=digest,
                  vertices=len(geometry['coordinates']), catalog_seconds=acquisition['catalog_seconds'],
                  source_staging_seconds=staging_seconds,
                  download_seconds=acquisition.get('download_seconds', 0.),
                  source_processing_seconds=staging_seconds - acquisition.get('download_seconds', 0.),
                  save_seconds=time.monotonic() - started)
    report['runtime'] = versions
    return report
