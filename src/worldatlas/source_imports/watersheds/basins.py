"""Classify watershed outlets using the selected provider basin polygons."""

from collections import defaultdict

import numpy as np
from osgeo import gdal
from pyproj import CRS, Transformer
from shapely import from_wkb, get_coordinates, points, transform as transform_geometry
from shapely.geometry import Point
from shapely.strtree import STRtree

from worldatlas.source_imports.watersheds.drainage import upstream_links


class Basins:
    """Source basin polygons grouped by explicitly selected attribute values."""

    def __init__(self, paths, attribute, groups, bounds):
        """Index provider basin polygons in the area of interest.

        Args:
            paths: GDAL vector dataset paths, including Shapefiles inside ZIP archives.
            attribute: Provider field identifying an individual basin.
            groups: Mapping from drainage group IDs to provider basin IDs.
            bounds: WGS84 west, south, east, and north bounds in degrees.
        """
        self.polygons, self.values = [], []
        self.groups = {int(group): set(values) for group, values in groups.items()}
        if not self.groups or any(group < 0 or not values for group, values in self.groups.items()):
            raise ValueError('known group IDs and source basin values are required')
        if any(a & b for i, a in enumerate(self.groups.values())
               for b in list(self.groups.values())[i + 1:]):
            raise ValueError('a source basin cannot belong to multiple drainage groups')
        wgs84 = CRS.from_epsg(4326)
        for path in paths:
            with gdal.ExceptionMgr(), gdal.OpenEx(str(path), gdal.OF_VECTOR) as source:
                if source.GetLayerCount() != 1:
                    raise ValueError('basin source requires one vector layer')
                layer = source.GetLayer(0)
                reference = layer.GetSpatialRef()
                if reference is None:
                    raise ValueError('basin source requires its coordinate reference')
                source_crs = CRS.from_wkt(reference.ExportToWkt())
                to_geo = Transformer.from_crs(source_crs, wgs84, always_xy=True)
                source_bounds = Transformer.from_crs(wgs84, source_crs, always_xy=True).transform_bounds(
                    *bounds, densify_pts=21, errcheck=True)
                layer.SetSpatialFilterRect(*source_bounds)
                project = not source_crs.equals(wgs84, ignore_axis_order=True)
                for feature in layer:
                    polygon = from_wkb(bytes(feature.GetGeometryRef().ExportToWkb()))
                    if project:
                        polygon = transform_geometry(polygon, to_geo.transform, interleaved=False)
                    self.polygons.append(polygon)
                    self.values.append(feature[attribute])
        self.tree = STRtree(self.polygons)
        self.mapped = set().union(*self.groups.values())

    def at(self, point):
        """Return the group for a WGS84 longitude-latitude point, or -1."""
        return self.group(self.values_at(point))

    def values_at(self, point):
        """Return provider basin IDs covering a WGS84 longitude-latitude point."""
        location = Point(*point)
        return {self.values[int(i)] for i in self.tree.query(location)
                if self.polygons[int(i)].covers(location)}

    def group(self, values):
        """Return the common drainage group for the basin IDs, or -1."""
        matches = {group for group, selected in self.groups.items() if values & selected}
        return next(iter(matches)) if len(matches) == 1 and values <= self.mapped else -1

    def exit_group(self, line):
        """Use the last source basin on a complete downstream river way.

        Basin polygons can stop at the shore while river geometry continues
        into an estuary. A covered but unselected destination stays unknown;
        missing polygon coverage is resolved only by an actual intersection
        of this same terminal way with the basin source.

        Args:
            line: Terminal river way in WGS84, ordered downstream.

        Returns:
            A pair of the group ID (-1 if unknown) and the last covered
            point, with None for the point if the endpoint was used or the
            line had no basin coverage.
        """
        endpoint = Point(line.coords[-1])
        values = {self.values[int(i)] for i in self.tree.query(endpoint, predicate='intersects')}
        if values:
            return self.group(values), None
        exits = []
        for index in self.tree.query(line, predicate='intersects'):
            index = int(index)
            for coordinate in get_coordinates(line.intersection(self.polygons[index])):
                point = tuple(map(float, coordinate))
                exits.append((line.project(Point(point)), self.values[index], point))
        if not exits:
            return -1, None
        station = max(item[0] for item in exits)
        last = [item for item in exits if item[0] == station]
        return self.group({item[1] for item in last}), min(item[2] for item in last)

    def _groups_at_cells(self, grid, rows, columns):
        """Look up cell centers in one spatial query and preserve unknown groups."""
        to_geo = Transformer.from_crs(grid.crs, 4326, always_xy=True)
        lon, lat = to_geo.transform(*grid.coordinates(rows, columns), errcheck=True)
        locations, polygons = self.tree.query(points(lon, lat), predicate='covered_by')
        # A point on a shared edge can be covered by more than one basin.
        basin_ids = defaultdict(set)
        for location, polygon in zip(locations, polygons, strict=True):
            basin_ids[location].add(self.values[polygon])
        groups = np.full(len(rows), -1, dtype='int64')
        for location, values in basin_ids.items():
            groups[location] = self.group(values)
        return groups

    def terminals(self, grid, flow):
        """Classify terminal cells at the boundary of the terrain grid.

        Args:
            grid: Terrain grid with its native coordinates and CRS.
            flow: Downstream indices, with -1 for terminals.

        Returns:
            An array of drainage group IDs, with -1 for unclassified cells.
        """
        result = np.full(flow.shape, -1, dtype='int64')
        height, width = flow.shape
        rows, columns = np.nonzero(flow == -1)
        edge = (rows == 0) | (rows == height - 1) | (columns == 0) | (columns == width - 1)
        rows, columns = rows[edge], columns[edge]
        result[rows, columns] = self._groups_at_cells(grid, rows, columns)
        return result

    def coastal_outlets(self, grid, ocean):
        """Stop at observed ocean cells and classify adjacent land exits.

        Args:
            grid: Terrain grid with its native coordinates and CRS.
            ocean: Ocean cells identified by the provider's water mask.

        Returns:
            The combined ocean and shore mask, and drainage group labels for
            the shore cells. Unclassified cells have label -1.
        """
        ocean = np.asarray(ocean, dtype=bool)
        if ocean.shape != grid.elevation.shape:
            raise ValueError('ocean mask and terrain grid must match')
        height, width = ocean.shape
        shore = np.zeros(ocean.shape, dtype=bool)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if not (dr or dc):
                    continue
                first = (slice(max(0, -dr), min(height, height - dr)),
                         slice(max(0, -dc), min(width, width - dc)))
                second = (slice(max(0, dr), min(height, height + dr)),
                          slice(max(0, dc), min(width, width + dc)))
                shore[first] |= ocean[second]
        shore &= ~ocean
        labels = np.full(ocean.shape, -1, dtype='int64')
        rows, columns = np.nonzero(shore)
        labels[rows, columns] = self._groups_at_cells(grid, rows, columns)
        return ocean | shore, labels

    def uncovered_exits(self, grid, flow, exits, labels, seeds):
        """Classify uncovered outlets through their actual upstream flow paths.

        Basin polygons can end inland of a water mask's shoreline. Walk each
        incoming branch to its first mapped river or covered source-basin cell.
        Agreeing references identify the outlet; conflicting or absent references
        leave it unknown.

        Args:
            grid: Terrain grid with its native coordinates and CRS.
            flow: Downstream indices, with -1 for terminals.
            exits: Boolean mask selecting outlet cells to check.
            labels: Existing outlet group labels, with -1 for unknowns.
            seeds: Mapping from drainage group IDs to mapped river masks.

        Returns:
            A copy of the labels with resolved outlets filled, and a report
            of resolved, conflicting, and unreferenced outlets.
        """
        if any(np.asarray(a).shape != flow.shape for a in (exits, labels, *seeds.values())):
            raise ValueError('outlets, labels and terrain flow must share one grid')
        if np.any(np.asarray(exits) & (flow != -1)):
            raise ValueError('selected exits must be flow terminals')
        result = labels.copy()
        unresolved = np.flatnonzero(np.asarray(exits).ravel() & (result.ravel() < 0))
        report = {'resolved': [], 'conflicting': [], 'unreferenced': 0}
        if not unresolved.size:
            return result, report
        heads, following = upstream_links(flow)
        width = flow.shape[1]
        to_geo = Transformer.from_crs(grid.crs, 4326, always_xy=True)

        def point(index):
            row, column = divmod(int(index), width)
            return tuple(map(float, to_geo.transform(*grid.coordinates(row, column), errcheck=True)))

        for terminal in unresolved:
            todo = [int(terminal)]
            groups, basin_values, references = set(), set(), {}
            while todo:
                index = todo.pop()
                seed_groups = {group for group, cells in seeds.items() if cells.ravel()[index]}
                group = next(iter(seed_groups)) if len(seed_groups) == 1 else -1
                location = point(index)
                values = set() if seed_groups else self.values_at(location)
                if seed_groups or values:
                    group = group if group >= 0 else self.group(values)
                    groups.update(seed_groups or {group})
                    basin_values.update(values)
                    references.setdefault(group, location)
                    continue
                child = heads[index]
                while child >= 0:
                    todo.append(int(child))
                    child = following[child]
            if len(groups) == 1 and min(groups) >= 0:
                group, = groups
                result.ravel()[terminal] = group
                report['resolved'].append({'outlet': point(terminal), 'group': group,
                                           'basin_values': sorted(basin_values),
                                           'upstream_reference': references[group]})
            elif groups:
                report['conflicting'].append({'outlet': point(terminal), 'groups': sorted(groups),
                                              'basin_values': sorted(basin_values)})
            else:
                report['unreferenced'] += 1
        return result, report
