"""Build and save a boundary from the files and choices named in a recipe."""

import hashlib
import logging
import platform
import time
from collections.abc import Mapping, Sequence
from importlib.metadata import version
from itertools import pairwise
from pathlib import Path
from typing import Any, NotRequired, cast

import numpy as np
import pyproj
import shapely
from osgeo import gdal, osr
from pyproj import Transformer, datadir
from shapely.geometry import LineString
from typing_extensions import TypedDict

from worldatlas.geodesy.geojson import Position
from worldatlas.geodesy.wgs84 import geodesic, geodesic_distance
from worldatlas.source_imports.shared.recipe_types import NonEmptyText, SourceId
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.sources import acquire_sources
from worldatlas.source_imports.shared.storage import save_features
from worldatlas.source_imports.watersheds.basins import Basins
from worldatlas.source_imports.watersheds.boundary import (
    Divide,
    Join,
    assemble_boundary_line,
    cell_containing_point,
    choose_intersection_join,
    connect_divide_to_stream_head,
)
from worldatlas.source_imports.watersheds.drainage import (
    compute_cell_flow,
    trace_destination_masks,
    unique_destination_labels,
)
from worldatlas.source_imports.watersheds.sources import (
    FileSelection,
    SourceLine,
    SourcePoint,
    Sources,
)
from worldatlas.source_imports.watersheds.terrain import (
    align_raster_to_grid,
    prepare_elevation_grid,
)
from worldatlas.source_imports.watersheds.waterways import (
    rasterize_waterway_destinations,
)

LOGGER = logging.getLogger(__name__)

Bounds = tuple[float, float, float, float]


class DivideCorner(TypedDict, closed=True):
    """Select the divide corner closest to a reviewed source point."""

    nearest_divide: NonEmptyText
    near: SourcePoint


type BoundaryPoint = SourcePoint | DivideCorner


class SourceSection(TypedDict, closed=True):
    """Use a named line that was read from a source file."""

    line: NonEmptyText


class DivideSection(TypedDict, closed=True):
    """Use a terrain divide as calculated."""

    divide: NonEmptyText


class DivideViaPoints(TypedDict, closed=True):
    """Follow the terrain divide through reviewed source points."""

    divide: NonEmptyText
    via: list[SourcePoint]
    max_step_m: float


class FlowConnection(TypedDict, closed=True):
    """Follow drainage from a divide to the mapped head of a stream."""

    terrain: NonEmptyText
    point: SourcePoint
    inside_group: int | NonEmptyText
    outside_groups: list[int]
    max_step_m: float


class FlowSection(TypedDict, closed=True):
    """Use a calculated route to a mapped stream head."""

    flow: FlowConnection


class GeodesicConnector(TypedDict, closed=True):
    """Connect two reviewed points using short WGS84 geodesic segments."""

    start: BoundaryPoint
    end: BoundaryPoint
    max_step_m: float


class GeodesicSection(TypedDict, closed=True):
    """Use a geodesic connector between two boundary sections."""

    geodesic: GeodesicConnector


type BoundarySection = (
    SourceSection | DivideSection | DivideViaPoints | FlowSection | GeodesicSection
)


class JoinSelection(TypedDict, closed=True):
    """Choose the intersection of adjacent sections nearest this coordinate."""

    near: Position


class ClosedSink(TypedDict, closed=True):
    """Stop flow at a reviewed inland location and label its destination."""

    point: SourcePoint
    group: int | NonEmptyText


class OceanMask(TypedDict, closed=True):
    """Choose categorical rasters and the values that mean ocean."""

    sources: list[NonEmptyText | FileSelection]
    values: list[int]


class TerrainDomain(TypedDict):
    """Choose how much terrain to read and which part can supply the divide.

    Two crops can overlap so both have room to trace streams near their
    edges. Give each crop a smaller ``output_bounds`` to choose where it
    contributes boundary edges. Both boxes use the same coordinate system.
    """

    bounds: Bounds
    crs: NotRequired[NonEmptyText | int]
    output_bounds: NotRequired[Bounds | None]


class DrainageSettings(TypedDict):
    """Identify the basin and stream data used to label drainage destinations.

    For example, if ``basin_attribute`` is ``MAIN_BAS``, read each polygon's
    basin ID from that field. Groups ``{"3": [41, 42], "7": [99]}`` label
    water reaching basins 41 or 42 as group 3 and basin 99 as group 7.
    """

    basins: list[NonEmptyText | FileSelection]
    basin_attribute: NonEmptyText
    groups: dict[NonEmptyText, list[NonEmptyText | int]]
    waterways: NotRequired[list[NonEmptyText | FileSelection]]
    reverse_waterways: NotRequired[list[NonEmptyText | int]]
    waterway_groups: NotRequired[dict[NonEmptyText, list[NonEmptyText | int]]]


class TerrainSettings(TypedDict):
    """Select elevation inputs, calculation windows, and divides to extract.

    ``drainage`` names the settings for classifying where water goes.
    ``interfaces`` selects which divides to build from those groups. For
    example, ``[[3, 7]]`` selects the divide between groups 3 and 7.
    """

    domains: list[TerrainDomain]
    primary: list[NonEmptyText | FileSelection]
    drainage: NonEmptyText
    interfaces: list[tuple[int | NonEmptyText, int | NonEmptyText]]
    secondary: NotRequired[list[NonEmptyText | FileSelection]]
    height_offset: NotRequired[NonEmptyText]
    closed_sinks: NotRequired[list[ClosedSink]]
    ocean_mask: NotRequired[OceanMask]


def runtime_versions() -> dict[str, Any]:
    """Record which software and coordinate data produced this boundary.

    Returns:
        Versions of the Python and native libraries and the PROJ database checksum.
    """
    database = Path(datadir.get_data_dir()) / 'proj.db'
    with database.open('rb') as stream:
        database_sha256 = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {
        'python': platform.python_version(),
        'packages': {
            name: version(name)
            for name in (
                'numpy',
                'pyproj',
                'shapely',
                'scipy',
                'numba',
                'llvmlite',
                'osmium',
                'boto3',
                'psycopg',
            )
        },
        'gdal': gdal.VersionInfo('RELEASE_NAME'),
        'pyproj_proj': pyproj.proj_version_str,
        'gdal_proj': '.'.join(
            map(
                str,
                (
                    osr.GetPROJVersionMajor(),
                    osr.GetPROJVersionMinor(),
                    osr.GetPROJVersionMicro(),
                ),
            )
        ),
        'shapely_geos': shapely.geos_version_string,
        'proj_database_sha256': database_sha256,
    }


def construct_boundary(
    files: Mapping[str, Path],
    *,
    line_selections: Mapping[str, SourceLine],
    sections: Sequence[BoundarySection],
    joins: Sequence[JoinSelection],
    start: BoundaryPoint,
    end: BoundaryPoint,
    terrains: Mapping[str, TerrainSettings] | None = None,
    drainage: Mapping[str, DrainageSettings] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Trace drainage, find the divide, and join the boundary sections.

    For a recipe with a coastline, a calculated divide, and a river,
    read the two saved lines, calculate the middle section, then join
    the three at their chosen intersections.

    Args:
        files: Verified local paths keyed by the recipe's source aliases.
        line_selections: Provider feature selections keyed by line name.
        sections: Ordered source lines, divides, flow paths, or connectors.
        joins: Coordinates near the intended meeting point of each pair
            of neighboring sections.
        start: Selection for the first point of the boundary.
        end: Selection for the last point of the boundary.
        terrains: Elevation inputs and analysis domains keyed by terrain name.
        drainage: Basin and stream settings keyed by the names used by terrains.

    Returns:
        The final GeoJSON boundary and a report of inputs, checks, and timings.

    Raises:
        ValueError: The evidence or recipe does not produce a valid connected boundary.
    """
    started = time.monotonic()
    report: dict[str, Any] = {'terrain': {}, 'connections': {}}
    sources = Sources(files)
    # A recipe can name one line "river" and reuse that name in a section or join.
    lines = {
        name: sources.read_source_line(selection)
        for name, selection in line_selections.items()
    }
    report['source_geometry_seconds'] = time.monotonic() - started
    divides, connections, networks = {}, {}, {}
    drainage_by_name = drainage or {}
    for name, settings in (terrains or {}).items():
        phase = time.monotonic()
        drainage_name = settings['drainage']
        if drainage_name not in drainage_by_name:
            raise ValueError(
                f'terrain {name!r} refers to unknown drainage settings {drainage_name!r}'
            )
        destination_settings = drainage_by_name[drainage_name]
        domains = settings['domains']
        if not domains:
            raise ValueError('terrain requires at least one analysis domain')
        raster_paths = lambda selected: [
            sources.resolve_raster_path(
                {'source': item} if isinstance(item, str) else item
            )
            for item in selected
        ]
        geographic_bounds = [
            Transformer.from_crs(
                domain.get('crs', 4326), 4326, always_xy=True
            ).transform_bounds(*domain['bounds'], densify_pts=21, errcheck=True)
            for domain in domains
        ]
        bounds = [
            min(b[0] for b in geographic_bounds),
            min(b[1] for b in geographic_bounds),
            max(b[2] for b in geographic_bounds),
            max(b[3] for b in geographic_bounds),
        ]
        reversed_ways = [
            str(ident) for ident in destination_settings.get('reverse_waterways', [])
        ]
        network = sources.read_osm_network(
            destination_settings.get('waterways', []),
            rivers_and_streams_only=True,
            reverse=reversed_ways,
        )
        if network.nodes:
            # A stream can cross our terrain crop and reach its outlet
            # farther away. Read the basin map far enough to find that outlet.
            bounds = [
                min(bounds[0], min(p[0] for p in network.nodes.values())),
                min(bounds[1], min(p[1] for p in network.nodes.values())),
                max(bounds[2], max(p[0] for p in network.nodes.values())),
                max(bounds[3], max(p[1] for p in network.nodes.values())),
            ]
        basins = Basins(
            [
                sources.resolve_vector_path(source)
                for source in destination_settings['basins']
            ],
            destination_settings['basin_attribute'],
            destination_settings['groups'],
            bounds,
        )
        assigned, network_report = (
            network.trace_destinations_from_ways(
                destination_settings['waterway_groups']
            )
            if 'waterway_groups' in destination_settings
            else network.trace_destinations_from_basins(basins)
        )
        network.require_known_drainage_in_bounds(geographic_bounds, network_report)
        shared_forks = networks.setdefault(network, {})
        # A named fork can be a boundary waypoint if its branches drain to
        # the two groups we are separating, for example 3 and 7.
        for section in sections:
            if 'divide' not in section or section['divide'] != name:
                continue
            if 'via' not in section:
                continue
            for waypoint in section['via']:
                if 'node' not in waypoint:
                    continue
                node = str(waypoint['node'])
                destinations = network.drainage_groups_by_outgoing_node(node, assigned)
                groups = set(destinations.values())
                if (
                    len(groups) == 2
                    and any(
                        groups == set(map(int, pair)) for pair in settings['interfaces']
                    )
                    and network.nodes[node]
                    == sources.resolve_recipe_point(waypoint, lines)
                ):
                    shared_forks[node] = destinations
        network_seconds = time.monotonic() - phase
        stream_head_sections = [
            (i, section['flow'])
            for i, section in enumerate(sections)
            if 'flow' in section and section['flow']['terrain'] == name
        ]
        if stream_head_sections and len(domains) != 1:
            raise ValueError(
                'a stream-head connection requires one continuous terrain domain'
            )
        divide, domain_reports, relevant_ways = Divide(), [], set()
        sinks = [
            (sources.resolve_recipe_point(sink['point'], lines), int(sink['group']))
            for sink in settings.get('closed_sinks', [])
        ]
        if any(group < 0 for _, group in sinks):
            raise ValueError('closed drainage destinations require known group IDs')
        covered_sinks = set()
        for domain in domains:
            # Read heights, mark where mapped rivers drain, then trace the
            # other cells downhill to those rivers or to known outlets.
            bounds = domain['bounds']
            output_bounds = domain.get('output_bounds')
            bounds_crs = domain.get('crs', 4326)
            tick = time.monotonic()
            grid = prepare_elevation_grid(
                raster_paths(settings['primary']),
                bounds,
                raster_paths(settings.get('secondary', [])),
                sources.resolve_raster_path({'source': settings['height_offset']})
                if 'height_offset' in settings
                else None,
                bounds_crs=bounds_crs,
            )
            terrain_seconds = time.monotonic() - tick
            step = time.monotonic()
            seeds, seed_report, way_ids = rasterize_waterway_destinations(
                network, assigned, grid
            )
            relevant_ways.update(way_ids)

            def seed_point(row: int, column: int, group: int, message: str) -> None:
                """Mark a cell as draining to the specified group.

                Args:
                    row: Terrain row of the selected point.
                    column: Terrain column of the selected point.
                    group: Known destination ID.
                    message: Error message if a mapped stream disagrees.

                Raises:
                    ValueError: The cell already has a different known destination.
                """
                present = {g for g, cells in seeds.items() if cells[row, column]}
                # If the river at this cell says group 3, an explicit point
                # cannot overwrite it with group 7.
                if present and present != {group}:
                    raise ValueError(message)
                if group not in seeds:
                    seeds[group] = np.zeros(grid.elevation.shape, dtype=bool)
                seeds[group][row, column] = True

            for _, flow_settings in stream_head_sections:
                point = sources.resolve_recipe_point(flow_settings['point'], lines)
                row, column = cast(tuple[int, int], cell_containing_point(grid, point))
                group = int(flow_settings['inside_group'])
                seed_point(
                    row,
                    column,
                    group,
                    'source stream head conflicts with a mapped drainage group',
                )
            closed_cells = []
            for index, (point, group) in enumerate(sinks):
                cell = cell_containing_point(grid, point, required=False)
                if cell is None:
                    continue
                row, column = cell
                seed_point(
                    row,
                    column,
                    group,
                    'closed drainage destination conflicts with a mapped group',
                )
                closed_cells.append((row, column))
                covered_sinks.add(index)
            outlets, coastal_labels, ocean = None, None, None
            coast_report: dict[str, Any] | None = None
            if 'ocean_mask' in settings:
                selection = settings['ocean_mask']
                water = align_raster_to_grid(
                    raster_paths(selection['sources']), grid, resampling='near'
                )
                ocean = np.isin(water, selection['values'])
                outlets, coastal_labels = basins.classify_coastal_outlets(grid, ocean)
                unique_seeds = unique_destination_labels(seeds, grid.elevation.shape)
                conflict = (
                    (unique_seeds >= 0)
                    & (coastal_labels >= 0)
                    & (unique_seeds != coastal_labels)
                )
                # At the shore, a river with a known route can give a
                # better answer than the basin outline. Count disagreements.
                coastal_labels[unique_seeds >= 0] = unique_seeds[unique_seeds >= 0]
                coast_report = {
                    'ocean_cells': int(ocean.sum()),
                    'land_outlet_cells': int((outlets & ~ocean).sum()),
                    'river_basin_conflicts': int(conflict.sum()),
                }
            seed_seconds = time.monotonic() - step
            step = time.monotonic()
            filled_elevation, flow = compute_cell_flow(
                grid, closed_cells, outlets=outlets
            )
            terminals = basins.classify_crop_exits(grid, flow)
            if coastal_labels is not None and coast_report is not None:
                assert outlets is not None and ocean is not None
                coastal_labels, coverage_report = basins.classify_uncovered_outlets(
                    grid, flow, outlets & ~ocean, coastal_labels, seeds
                )
                coast_report['source_coverage'] = coverage_report
                # At ocean and shore stops, use the shoreline results in
                # place of the crop-edge lookup, even if the group is unknown.
                terminals[outlets] = coastal_labels[outlets]
            labels = trace_destination_masks(flow, seeds, terminals)
            drainage_seconds = time.monotonic() - step
            step = time.monotonic()
            divide.add_catchment_edges(
                grid,
                labels,
                settings['interfaces'],
                output_bounds,
                bounds_crs=bounds_crs,
            )
            for index, flow_settings in stream_head_sections:
                curve, receipt = connect_divide_to_stream_head(
                    grid,
                    flow,
                    unique_destination_labels(labels, flow.shape),
                    sources.resolve_recipe_point(flow_settings['point'], lines),
                    int(flow_settings['inside_group']),
                    flow_settings['outside_groups'],
                    flow_settings['max_step_m'],
                )
                connections[index] = curve
                report['connections'][str(index)] = receipt
            destination_count = np.zeros(flow.shape, dtype='int64')
            for cells in labels.values():
                destination_count += cells
            domain_reports.append(
                {
                    'bounds': bounds,
                    'output_bounds': output_bounds,
                    'shape': list(flow.shape),
                    'bounds_crs': bounds_crs,
                    'secondary_cells': grid.secondary_cells,
                    'unknown_cells': int((destination_count == 0).sum()),
                    'shared_drainage_cells': int((destination_count > 1).sum()),
                    'raised_cells': int((filled_elevation > grid.elevation).sum()),
                    'max_raise_m': float((filled_elevation - grid.elevation).max()),
                    'seeds': seed_report,
                    'terrain_seconds': terrain_seconds,
                    'coast': coast_report,
                    'seed_seconds': seed_seconds,
                    'drainage_seconds': drainage_seconds,
                    'divide_seconds': time.monotonic() - step,
                    'seconds': time.monotonic() - tick,
                }
            )
            LOGGER.info(
                '%s: %s cells, %.2f seconds',
                name,
                flow.shape,
                domain_reports[-1]['seconds'],
            )
        if len(covered_sinks) != len(sinks):
            raise ValueError(
                'closed drainage destination is outside every analysis domain'
            )
        divides[name] = divide
        network_report = dict(network_report)
        for category in ('ambiguous', 'unassigned'):
            network_report[category] = [
                way for way in network_report[category] if way in relevant_ways
            ]
        network_report['shared_sections'] = [
            section
            for section in network_report['shared_sections']
            if any(way in relevant_ways for way, _, _ in section['source_segments'])
        ]
        # The check before reading terrain already rejects unknown river
        # routes that affect a crop. Leave those outside it out of this report.
        network_report.pop('unresolved_sections')
        network_report['river_and_stream_ways_in_domains'] = len(relevant_ways)
        network_report['river_and_stream_ways_in_sources'] = len(
            network.river_and_stream_ids
        )
        network_report['reversed_waterways'] = {
            ident: network.ways[ident].version for ident in reversed_ways
        }
        report['terrain'][name] = {
            'domains': domain_reports,
            'network': network_report,
            'network_seconds': network_seconds,
            'seconds': time.monotonic() - phase,
        }
    phase = time.monotonic()

    def resolve_section_point(
        specification: BoundaryPoint, *, retain_join: bool = False
    ) -> Join | tuple[float, float]:
        """Find the point at which to start or end a boundary section.

        Args:
            specification: Source point or a request to find the nearest divide
                corner.
            retain_join: Keep the edge needed to route along the divide.

        Returns:
            (longitude, latitude), or a Join with the supporting divide edge.
        """
        if 'nearest_divide' in specification:
            target = sources.resolve_recipe_point(specification['near'], lines)
            join = divides[specification['nearest_divide']].join_at_nearest_corner(
                target
            )
        else:
            return sources.resolve_recipe_point(specification, lines)
        # A connector needs only the coordinate. Routing along the divide
        # also needs to know which edge contains it.
        return join if retain_join else join.point

    section_lines, waypoints = [], {}
    for index, section in enumerate(sections):
        if 'line' in section:
            section_lines.append(lines[section['line']])
        elif 'divide' in section:
            section_lines.append(divides[section['divide']])
            if 'via' in section and section['via']:
                waypoints[index] = {
                    'points': [
                        sources.resolve_recipe_point(p, lines) for p in section['via']
                    ],
                    'max_step_m': section['max_step_m'],
                }
        elif 'flow' in section:
            section_lines.append(connections[index])
        elif 'geodesic' in section:
            choice = section['geodesic']
            first = cast(tuple[float, float], resolve_section_point(choice['start']))
            last = cast(tuple[float, float], resolve_section_point(choice['end']))
            section_lines.append(
                LineString(geodesic(first, last, choice['max_step_m']))
            )
            report.setdefault('connectors', {})[str(index)] = {
                'start': list(first),
                'end': list(last),
                'length_m': geodesic_distance(first, last),
            }
        else:
            raise ValueError('unknown boundary section type')
    if len(joins) != len(section_lines) - 1:
        raise ValueError(
            'one geographic join selection is required between adjacent sections'
        )
    # Turn each nearby hint into a real intersection before trimming the lines.
    chosen_joins = [
        choose_intersection_join(a, b, choice['near'])
        for (a, b), choice in zip(pairwise(section_lines), joins, strict=True)
    ]
    geometry, followed_sources = assemble_boundary_line(
        section_lines,
        chosen_joins,
        resolve_section_point(start, retain_join=True),
        resolve_section_point(end, retain_join=True),
        waypoints=waypoints,
        connections=report['connections'],
        source_sections={
            index for index, section in enumerate(sections) if 'line' in section
        },
    )
    final_line = LineString(geometry['coordinates'])
    followed_source_line = (
        shapely.union_all(followed_sources) if followed_sources else None
    )
    report['river_checks'] = [
        network.check_boundary_crossings(
            final_line, shared_forks=forks, followed_source_line=followed_source_line
        )
        for network, forks in networks.items()
    ]
    report['joins'] = [list(join.point) for join in chosen_joins]
    report['assembly_seconds'] = time.monotonic() - phase
    report['construction_seconds'] = time.monotonic() - started
    return geometry, report


def watershed_boundary(
    runtime: Runtime,
    *,
    feature_id: NonEmptyText,
    sources: dict[NonEmptyText, SourceId],
    lines: dict[NonEmptyText, SourceLine],
    sections: list[BoundarySection],
    joins: list[JoinSelection],
    start: BoundaryPoint,
    end: BoundaryPoint,
    terrains: dict[NonEmptyText, TerrainSettings] | None = None,
    drainage: dict[NonEmptyText, DrainageSettings] | None = None,
    evidence_sources: list[SourceId] | None = None,
) -> dict[str, Any]:
    """Read the recipe's files, build the boundary, and save it to Neon.

    Args:
        runtime: Import resources and saved recipe snapshot.
        feature_id: Output boundary ID in Neon.
        sources: File names used in the recipe, mapped to catalog source IDs.
        lines: Provider feature selections keyed by line name.
        sections: Ordered source lines, divides, flow paths, or connectors.
        joins: Geographic anchors for intersections between adjacent sections.
        start: Selection for the first point of the boundary.
        end: Selection for the last point of the boundary.
        terrains: Optional elevation inputs and analysis domains.
        drainage: Named basin and stream settings referenced by the terrains.
        evidence_sources: Additional catalog IDs to cite, such as a study
            supporting the location of a stream fork.

    Returns:
        Saved boundary identity, vertex count, and construction report.

    Raises:
        ValueError: Source acquisition, boundary construction, or save validation fails.
    """
    # Neon checks the evidence links when the recipe is saved. Only calculation
    # inputs go through the file cache.
    acquisition = {}
    paths = acquire_sources(
        runtime,
        list(sources.values()),
        timing=acquisition,
    )
    # Turn the downloaded paths back into the file names the recipe uses.
    files = dict(zip(sources, paths, strict=True))
    geometry, report = construct_boundary(
        files,
        line_selections=lines,
        sections=sections,
        joins=joins,
        start=start,
        end=end,
        terrains=terrains,
        drainage=drainage,
    )
    versions = runtime_versions()
    started = time.monotonic()
    # Save only after the complete line passes the drainage and crossing checks.
    save_features(runtime, [{"feature_id": feature_id, "geometry": geometry}])
    staging_seconds = acquisition['source_staging_seconds']
    report.update(
        feature_id=feature_id,
        vertices=len(geometry['coordinates']),
        catalog_seconds=acquisition['catalog_seconds'],
        source_staging_seconds=staging_seconds,
        download_seconds=acquisition.get('download_seconds', 0.0),
        source_processing_seconds=staging_seconds
        - acquisition.get('download_seconds', 0.0),
        save_seconds=time.monotonic() - started,
    )
    report['runtime'] = versions
    return report
