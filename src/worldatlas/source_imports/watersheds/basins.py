"""Use basin maps to tell where streams and terrain cells drain.

An outlet is where the mapped stream or calculated flow stops. The
basin covering that point can identify the water's destination.
"""

from collections import defaultdict
from collections.abc import Collection, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from osgeo import gdal
from pyproj import CRS, Transformer
from shapely import from_wkb, get_coordinates, points
from shapely import transform as transform_geometry
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

from worldatlas.source_imports.watersheds.drainage import index_incoming_flow
from worldatlas.source_imports.watersheds.terrain import Grid


class Basins:
    """Look up the drainage group of a point using basin outlines."""

    def __init__(
        self,
        paths: Iterable[Path | str],
        attribute: str,
        groups: Mapping[str, Collection[str | int]]
        | Mapping[int, Collection[str | int]],
        bounds: Sequence[float],
    ) -> None:
        """Load the basin outlines we might need for this boundary.

        Args:
            paths: GDAL vector dataset paths, including Shapefiles inside ZIP archives.
            attribute: Field in the source file, such as ``MAIN_BAS``, that
                identifies which larger basin each polygon drains into.
            groups: Source IDs grouped by destination. For example,
                ``{"3": [41, 42], "7": [99]}`` puts 41 and 42 in group 3.
            bounds: WGS84 west, south, east, and north bounds in degrees.

        Raises:
            ValueError: The groups overlap, or a source lacks one georeferenced layer.
        """
        self.polygons, self.values = [], []
        self.groups = {int(group): set(values) for group, values in groups.items()}
        if len(self.groups) != len(groups):
            raise ValueError('equivalent numeric drainage group IDs are repeated')
        if not self.groups or any(
            group < 0 or not values for group, values in self.groups.items()
        ):
            raise ValueError('known group IDs and source basin values are required')
        # If 42 appears under both 3 and 7, a lookup for 42 has two answers.
        if any(
            a & b
            for i, a in enumerate(self.groups.values())
            for b in list(self.groups.values())[i + 1 :]
        ):
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
                source_bounds = Transformer.from_crs(
                    wgs84, source_crs, always_xy=True
                ).transform_bounds(*bounds, densify_pts=21, errcheck=True)
                # GDAL searches in the file's units, which may be metres.
                # Convert the search box first, then load and convert just those shapes.
                layer.SetSpatialFilterRect(*source_bounds)
                project = not source_crs.equals(wgs84, ignore_axis_order=True)
                for feature in layer:
                    polygon = from_wkb(bytes(feature.GetGeometryRef().ExportToWkb()))
                    if project:
                        # Shapely passes two coordinate arrays with interleaved=False.
                        polygon = transform_geometry(  # pyright: ignore[reportCallIssue]
                            polygon,
                            to_geo.transform,  # pyright: ignore[reportArgumentType]
                            interleaved=False,
                        )
                    self.polygons.append(polygon)
                    self.values.append(feature[attribute])
        # The search tree returns positions in the list of outlines. Use
        # those same positions in self.values to get the source IDs.
        self.tree = STRtree(self.polygons)
        self.mapped = set().union(*self.groups.values())

    def group_at_point(self, point: Sequence[float]) -> int:
        """Identify the drainage group at a point.

        Args:
            point: Longitude and latitude in WGS84 degrees.

        Returns:
            The local group ID, or -1 if coverage cannot establish one group.
        """
        return self.group_for_basin_ids(self.basin_ids_at_point(point))

    def basin_ids_at_point(self, point: Sequence[float]) -> set[str | int]:
        """Find the source basin IDs at a point.

        Args:
            point: Longitude and latitude in WGS84 degrees.

        Returns:
            The source IDs of all outlines covering the point. A point
            on the line between two basins can return both IDs.
        """
        return {
            self.values[i]
            for i in self.tree.query(Point(*point), predicate='covered_by')
        }

    def group_for_basin_ids(self, basin_ids: set[str | int]) -> int:
        """Give a point one group when all its source basin IDs agree.

        Args:
            basin_ids: Set of source basin IDs found at the location.

        Returns:
            The common group, or -1 when unknown. If 41 and 42 both map
            to group 3, then ``{41, 42}`` gives 3.
        """
        matches = {
            group
            for group, group_basin_ids in self.groups.items()
            if basin_ids & group_basin_ids
        }
        return (
            next(iter(matches))
            if len(matches) == 1 and basin_ids <= self.mapped
            else -1
        )

    def river_exit_group_and_point(
        self, line: LineString
    ) -> tuple[int, tuple[float, ...] | None]:
        """Find the last mapped basin a river passes through.

        Say the river flows A → B → C. Its mapped basin ends at B, but the
        river line ends farther out at C. Look at B when C has no covering
        basin. If C has a basin whose group is unknown, use that answer.

        Args:
            line: The last stretch of the river, with WGS84 points in flow order.

        Returns:
            ``(group, point)``. The group is -1 when unknown. The point is B
            in the example above. It is None when the river ends inside a
            basin or the whole stretch lies outside the basin map.
        """
        endpoint = Point(line.coords[-1])
        values = {
            self.values[int(i)]
            for i in self.tree.query(endpoint, predicate='intersects')
        }
        if values:
            return self.group_for_basin_ids(values), None
        exits = []
        for index in self.tree.query(line, predicate='intersects'):
            index = int(index)
            for coordinate in get_coordinates(line.intersection(self.polygons[index])):
                point = tuple(map(float, coordinate))
                exits.append((line.project(Point(point)), self.values[index], point))
        if not exits:
            return -1, None
        # Choose the point farthest along the river, even if it winds back.
        last_distance = max(item[0] for item in exits)
        last = [item for item in exits if item[0] == last_distance]
        return self.group_for_basin_ids({item[1] for item in last}), min(
            item[2] for item in last
        )

    def _groups_at_cell_centers(
        self, grid: Grid, rows: np.ndarray, columns: np.ndarray
    ) -> np.ndarray:
        """Look up drainage groups at terrain cell centres in one spatial query.

        Args:
            grid: Elevation grid and the coordinate system for its cells.
            rows: One-dimensional array of row indices.
            columns: Matching column indices.

        Returns:
            Int64 array with the group ID for each cell, or -1 when its
            destination is unknown or ambiguous.
        """
        to_geo = Transformer.from_crs(grid.crs, 4326, always_xy=True)
        lon, lat = to_geo.transform(
            *grid.cell_coordinates(rows, columns), errcheck=True
        )
        cell_indices, polygon_indices = self.tree.query(
            points(lon, lat), predicate='covered_by'
        )
        # A point on a shared edge can be covered by more than one basin.
        basin_ids = defaultdict(set)
        for location, polygon in zip(cell_indices, polygon_indices, strict=True):
            basin_ids[location].add(self.values[polygon])
        groups = np.full(len(rows), -1, dtype='int64')
        for location, values in basin_ids.items():
            groups[location] = self.group_for_basin_ids(values)
        return groups

    def classify_crop_exits(self, grid: Grid, flow: np.ndarray) -> np.ndarray:
        """Find the basin groups of cells where flow stops at the crop edge.

        Args:
            grid: Terrain grid with its native coordinates and CRS.
            flow: Downstream indices, with -1 for terminals.

        Returns:
            An array of drainage group IDs, with -1 for unclassified cells.
        """
        result = np.full(flow.shape, -1, dtype='int64')
        height, width = flow.shape
        rows, columns = np.nonzero(flow == -1)
        # A pit in the middle can also have no next cell. Only edge cells
        # can count as places where water leaves this crop.
        edge = (
            (rows == 0) | (rows == height - 1) | (columns == 0) | (columns == width - 1)
        )
        rows, columns = rows[edge], columns[edge]
        result[rows, columns] = self._groups_at_cell_centers(grid, rows, columns)
        return result

    def classify_coastal_outlets(
        self, grid: Grid, ocean: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Mark the ocean and the land cells touching it as places flow stops.

        Args:
            grid: Terrain grid with its native coordinates and CRS.
            ocean: Ocean cells identified by the provider's water mask.

        Returns:
            The combined ocean and shore mask, and drainage group labels for
            the shore cells. Unclassified cells have label -1.

        Raises:
            ValueError: The ocean mask and elevation grid have different shapes.
        """
        ocean = np.asarray(ocean, dtype=bool)
        if ocean.shape != grid.elevation.shape:
            raise ValueError('ocean mask and terrain grid must match')
        height, width = ocean.shape
        shore = np.zeros(ocean.shape, dtype=bool)
        # A land cell counts as shore even if it touches ocean at a corner.
        # Stop at the crop edges so the left edge never sees the right edge.
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if not (dr or dc):
                    continue
                first = (
                    slice(max(0, -dr), min(height, height - dr)),
                    slice(max(0, -dc), min(width, width - dc)),
                )
                second = (
                    slice(max(0, dr), min(height, height + dr)),
                    slice(max(0, dc), min(width, width + dc)),
                )
                shore[first] |= ocean[second]
        shore &= ~ocean
        labels = np.full(ocean.shape, -1, dtype='int64')
        rows, columns = np.nonzero(shore)
        labels[rows, columns] = self._groups_at_cell_centers(grid, rows, columns)
        return ocean | shore, labels

    def classify_uncovered_outlets(
        self,
        grid: Grid,
        flow: np.ndarray,
        exits: np.ndarray,
        labels: np.ndarray,
        seeds: dict[int, np.ndarray],
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Look upstream for evidence when an outlet's group is unknown.

        If the basin map ends before the shore, start at the unlabeled shore
        cell and follow the cells that drain into it. Stop each branch at the
        first mapped river or basin. If branches find groups 3 and 7, the
        outlet stays unknown.

        Args:
            grid: Terrain grid with its native coordinates and CRS.
            flow: Downstream indices, with -1 for terminals.
            exits: Boolean mask selecting outlet cells to check.
            labels: Existing outlet group labels, with -1 for unknowns.
            seeds: Mapping from drainage group IDs to mapped river masks.

        Returns:
            A copy of the labels with resolved outlets filled, and a report
            of resolved, conflicting, and unreferenced outlets.

        Raises:
            ValueError: Inputs use different grid shapes or select nonterminal exits.
        """
        if any(
            np.asarray(a).shape != flow.shape for a in (exits, labels, *seeds.values())
        ):
            raise ValueError('outlets, labels and terrain flow must share one grid')
        if np.any(np.asarray(exits) & (flow != -1)):
            raise ValueError('selected exits must be flow terminals')
        result = labels.copy()
        unresolved = np.flatnonzero(np.asarray(exits).ravel() & (result.ravel() < 0))
        report = {'resolved': [], 'conflicting': [], 'unreferenced': 0}
        if not unresolved.size:
            return result, report
        heads, following = index_incoming_flow(flow)
        width = flow.shape[1]
        to_geo = Transformer.from_crs(grid.crs, 4326, always_xy=True)

        def point(index: int | np.integer) -> tuple[float, ...]:
            """Find the WGS84 centre of a cell using its flat index.

            Args:
                index: Row-major cell number in the crop.

            Returns:
                (longitude, latitude) in degrees.
            """
            row, column = divmod(int(index), width)
            return tuple(
                map(
                    float,
                    to_geo.transform(
                        *grid.cell_coordinates(row, column), errcheck=True
                    ),
                )
            )

        for terminal in unresolved:
            todo = [int(terminal)]
            groups, basin_values, references = set(), set(), {}
            while todo:
                index = todo.pop()
                seed_groups = {
                    group for group, cells in seeds.items() if cells.ravel()[index]
                }
                group = next(iter(seed_groups)) if len(seed_groups) == 1 else -1
                location = point(index)
                values = set() if seed_groups else self.basin_ids_at_point(location)
                if seed_groups or values:
                    group = group if group >= 0 else self.group_for_basin_ids(values)
                    groups.update(seed_groups or {group})
                    basin_values.update(values)
                    references.setdefault(group, location)
                    # Even a basin with an unknown group is the first basin
                    # on this branch. Looking farther back could pick the wrong one.
                    continue
                child = heads[index]
                while child >= 0:
                    todo.append(int(child))
                    child = following[child]
            if len(groups) == 1 and min(groups) >= 0:
                (group,) = groups
                result.ravel()[terminal] = group
                report['resolved'].append(
                    {
                        'outlet': point(terminal),
                        'group': group,
                        'basin_values': sorted(basin_values),
                        'upstream_reference': references[group],
                    }
                )
            elif groups:
                report['conflicting'].append(
                    {
                        'outlet': point(terminal),
                        'groups': sorted(groups),
                        'basin_values': sorted(basin_values),
                    }
                )
            else:
                report['unreferenced'] += 1
        return result, report
