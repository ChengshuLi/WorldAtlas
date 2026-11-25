"""Find where water goes on an elevation grid.

Each cell can send water to one of its eight neighbors. A mapped river
can carry that water to more than one destination after the river splits.
"""

import heapq
import os
from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from numba import njit
from numpy.typing import ArrayLike
from pyproj import CRS, Transformer

from worldatlas.geodesy.wgs84 import geodesic_distances
from worldatlas.source_imports.watersheds.terrain import TerrainGrid

UNKNOWN = -1


def neighbor_distances_metres(grid: TerrainGrid) -> np.ndarray:
    """Measure distances between all horizontally, vertically, or diagonally adjacent cells.

    Args:
        grid: Terrain grid with its native coordinates and coordinate reference.

    Returns:
        One grid of WGS84 distances in metres for each of four directions:
        east, south, southeast, and southwest. The distance from A to B
        equals the distance from B to A, so four grids cover all eight neighbors.

    Raises:
        ValueError: A transformed coordinate or neighboring-cell distance is invalid.
    """
    height, width = grid.elevation.shape
    to_geo = Transformer.from_crs(CRS.from_user_input(grid.crs), 4326, always_xy=True)
    distances = np.zeros((4, height, width), dtype='float64')

    def calculate_rows(first: int) -> None:
        """Fill one batch of the grid's adjacent-cell distances.

        Args:
            first: First terrain row in the batch.
        """
        last = min(height, first + 128)
        # A block ending at row 127 needs row 128 to measure the distances
        # from the last row to its neighbors below.
        stop = min(height, last + 1)
        columns, rows = np.meshgrid(np.arange(width), np.arange(first, stop))
        lon, lat = to_geo.transform(
            *grid.cell_coordinates(rows, columns), errcheck=True
        )
        if (
            not np.isfinite(lon).all()
            or not np.isfinite(lat).all()
            or np.any(np.abs(lat) > 90)
        ):
            raise ValueError('invalid WGS84 cell coordinates')
        count = last - first
        for plane, dr, dc in ((0, 0, 1), (1, 1, 0), (2, 1, 1), (3, 1, -1)):
            n = min(count, height - first - dr)
            a = slice(max(0, -dc), min(width, width - dc))
            b = slice(max(0, dc), min(width, width + dc))
            if n == 0 or width <= abs(dc):
                continue
            length = geodesic_distances(
                lon[:n, a], lat[:n, a], lon[dr : n + dr, b], lat[dr : n + dr, b]
            )
            if not np.isfinite(length).all() or np.any(length <= 0):
                raise ValueError('invalid neighboring-cell distance')
            distances[plane, first : first + n, a] = length

    with ThreadPoolExecutor(max_workers=os.cpu_count() or 1) as executor:
        # Consume every result so errors in a worker reach the caller.
        list(executor.map(calculate_rows, range(0, height, 128)))
    return distances


@njit(cache=True)
def _fill_depressions(
    elevation: np.ndarray, closed: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Raise pits to their lowest outlet height and remember the way out.

    Start at crop edges and known stopping points and visit cells in order
    of the lowest water level that can reach them. For a 3 m pit whose
    lowest outlet is 5 m, the working height becomes 5 m.

    Args:
        elevation: Two-dimensional grid of original heights in metres.
        closed: Boolean grid marking where water must stop.

    Returns:
        Working heights in metres and a flat array of next-cell indices
        that lead back to a starting cell. Starting cells use -1.
    """
    height, width = elevation.shape
    working = np.full(elevation.shape, np.inf)
    parent = np.full(elevation.size, -2, dtype=np.int64)
    heap = [(0.0, 0)]
    heap.pop()
    # Start the search at the crop edges and places where the recipe says
    # water stops. Work inward, starting with the lowest available cell.
    for row in range(height):
        for column in range(width):
            if (
                row == 0
                or column == 0
                or row == height - 1
                or column == width - 1
                or closed[row, column]
            ):
                index = row * width + column
                working[row, column] = elevation[row, column]
                parent[index] = -1
                heapq.heappush(heap, (float(working[row, column]), index))
    while heap:
        value, index = heapq.heappop(heap)
        row, column = index // width, index % width
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                rr, cc = row + dr, column + dc
                if (dr or dc) and 0 <= rr < height and 0 <= cc < width:
                    other = rr * width + cc
                    if parent[other] == -2:
                        # If a pit is 3 m and its lowest way out is 5 m,
                        # use 5 m here and remember the way out in parent.
                        parent[other] = index
                        working[rr, cc] = max(value, elevation[rr, cc])
                        heapq.heappush(heap, (float(working[rr, cc]), other))
    return working, parent


@njit(cache=True)
def _route_cell_flow(
    working: np.ndarray,
    distances: np.ndarray,
    closed: np.ndarray,
    routes_out: np.ndarray,
) -> np.ndarray:
    """Pick the steepest downhill neighbor, or follow the known way off a flat.

    Args:
        working: Two-dimensional grid of heights after filling pits, in metres.
        distances: Neighbor distances in metres, indexed by direction, row, column.
        closed: Boolean grid marking where water must stop.
        routes_out: Flat next-cell indices from the pit-filling search,
            updated in place wherever a neighbor has a steeper downhill route.

    Returns:
        A two-dimensional array of flat next-cell indices, with -1 at stops.
    """
    height, width = working.shape
    flow = routes_out.reshape(working.shape)
    # On flat ground, use the way out found above. If a neighbor is lower,
    # choose the steepest drop per metre. Edge cells can drain back inward.
    for row in range(height):
        for column in range(width):
            if closed[row, column]:
                continue
            best = 0.0
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    rr, cc = row + dr, column + dc
                    if (dr or dc) and 0 <= rr < height and 0 <= cc < width:
                        if dr == 0:
                            distance = distances[
                                0, row, column if dc > 0 else column - 1
                            ]
                        elif dc == 0:
                            distance = distances[1, row if dr > 0 else row - 1, column]
                        elif dr == dc:
                            distance = distances[
                                2,
                                row if dr > 0 else row - 1,
                                column if dc > 0 else column - 1,
                            ]
                        else:
                            distance = distances[
                                3,
                                row if dr > 0 else row - 1,
                                column if dr > 0 else column + 1,
                            ]
                        slope = (working[row, column] - working[rr, cc]) / distance
                        if slope > best:
                            best = slope
                            flow[row, column] = rr * width + cc
    return flow


def compute_cell_flow(
    grid: TerrainGrid,
    closed_sinks: Iterable[tuple[int, int]] = (),
    *,
    outlets: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate terrain flow using the elevation grid and known stopping points.

    Args:
        grid: Terrain grid with a finite elevation at each cell.
        closed_sinks: Row and column pairs where water stops inland.
        outlets: Optional Boolean grid marking other terminals, such as the shore.

    Returns:
        The working heights and the next cell for each position. In a
        four-column grid, row 1 column 2 is cell 6. A value of -1 means
        flow stops there.

    Raises:
        ValueError: The terrain, terminal mask, or selected sink cell is invalid.
    """
    elevation = np.asarray(grid.elevation, dtype='float64')
    if elevation.ndim != 2 or not elevation.size or not np.isfinite(elevation).all():
        raise ValueError('a complete finite two-dimensional elevation grid is required')
    closed = np.zeros(elevation.shape, dtype='bool')
    if outlets is not None:
        if np.asarray(outlets).shape != elevation.shape:
            raise ValueError('outlets and terrain grid must match')
        closed |= np.asarray(outlets, dtype=bool)
    for row, column in closed_sinks:
        if not (0 <= row < elevation.shape[0] and 0 <= column < elevation.shape[1]):
            raise ValueError('closed sink is outside the elevation grid')
        closed[row, column] = True
    distances = neighbor_distances_metres(grid)
    working, routes_out = _fill_depressions(elevation, closed)
    return working, _route_cell_flow(working, distances, closed, routes_out)


@njit(cache=True)
def _trace_cell_group_labels(
    flow: np.ndarray, seeds: np.ndarray, terminals: np.ndarray
) -> np.ndarray:
    """Follow each cell until it reaches a known group or the route ends.

    Args:
        flow: Two-dimensional grid of flattened next-cell indices.
        seeds: Known groups along mapped streams, with -1 elsewhere.
        terminals: Known groups at stopping cells, with -1 elsewhere.

    Returns:
        Grid of destination IDs with the same shape as flow.
    """
    links = flow.ravel()
    labels = seeds.ravel().copy()
    stopped = links == -1
    labels[stopped & (labels < 0)] = terminals.ravel()[stopped & (labels < 0)]
    return _follow_destinations(flow, labels)


@njit(cache=True)
def _follow_destinations(flow: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Propagate labels backwards from the first known destination on each path.

    Args:
        flow: Grid of next-cell indices, with -1 where flow stops.
        labels: Flat array of destination values already known, with -1 elsewhere.
            Updated in place with the resolved labels.

    Returns:
        A view of the completed labels with the same shape as flow.
    """
    links = flow.ravel()
    state = np.zeros(links.size, np.uint8)
    path = np.empty(links.size, np.int64)
    # State 0 means untouched, 1 means on the current walk, and 2 means
    # the result is settled. Finding a 1 again means the flow made a loop.
    for index in range(links.size):
        if labels[index] >= 0 or links[index] == -1:
            state[index] = 2
    for start in range(links.size):
        if state[start] == 2:
            continue
        index, count = start, 0
        while index >= 0 and state[index] == 0:
            state[index] = 1
            path[count] = index
            count += 1
            index = links[index]
        # If A → B → C reaches group 3 at C, give both A and B group 3.
        # A later path can stop as soon as it reaches one of those cells.
        destination = labels[index] if index >= 0 and state[index] == 2 else -1
        for i in range(count):
            labels[path[i]] = destination
            state[path[i]] = 2
    return labels.reshape(flow.shape)


def trace_cell_group_labels(
    flow: ArrayLike, seeds: ArrayLike, terminals: ArrayLike | None = None
) -> np.ndarray:
    """Give each cell the group found by following its flow.

    A river with a known destination gives that answer to cells that reach
    it. If flow stops first, the outlet or sink supplies the answer if
    known. A loop or an unlabeled stopping point gives -1.

    Args:
        flow: Next-cell indices in row order, with -1 for terminal cells.
        seeds: Group IDs already known at some cells, such as mapped rivers.
            Use -1 where the trace should keep going.
        terminals: Group IDs at known exits, with -1 where no destination is known.

    Returns:
        The group ID at each cell, with -1 where flow did not establish one.

    Raises:
        ValueError: The inputs contain invalid indices or labels, or have mismatched shapes.
    """
    flow, seeds = np.asarray(flow), np.asarray(seeds)
    if terminals is None:
        terminals = np.full(flow.shape, UNKNOWN, dtype='int64')
    terminals = np.asarray(terminals)
    if flow.ndim != 2 or seeds.shape != flow.shape or terminals.shape != flow.shape:
        raise ValueError('flow, seed and terminal grids must have matching shapes')
    if any(a.dtype.kind not in 'iu' for a in (flow, seeds, terminals)):
        raise ValueError('flow links and destination IDs must be integers')
    if (
        np.any(flow < -1)
        or np.any(flow >= flow.size)
        or np.any(seeds < -1)
        or np.any(terminals < -1)
    ):
        raise ValueError('invalid flow link or destination ID')
    return _trace_cell_group_labels(
        flow.astype('int64'), seeds.astype('int64'), terminals.astype('int64')
    )


def unique_destination_labels(
    memberships: Mapping[int, np.ndarray], shape: tuple[int, int]
) -> np.ndarray:
    """Return a group only where exactly one destination is known.

    A cell marked for both groups 3 and 7 gets -1 in this single-label grid.
    The original two group grids still hold both destinations.

    Args:
        memberships: Mapping from group IDs to Boolean grids marking their catchments.
        shape: Row and column dimensions of the output grid.

    Returns:
        A grid of group IDs, with -1 for both unknown and shared drainage.
    """
    labels = np.full(shape, UNKNOWN, dtype='int64')
    count = np.zeros(shape, dtype='int64')
    for group, cells in memberships.items():
        labels[cells] = group
        count += cells
    labels[count != 1] = UNKNOWN
    return labels


def trace_destination_masks(
    flow: ArrayLike, seeds: Mapping[int, np.ndarray], terminals: ArrayLike
) -> dict[int, np.ndarray]:
    """Follow all known river destinations, including genuine split flow.

    If a river splits and drains to groups 3 and 7, every cell that reaches
    that river before another known destination is True in both group grids.
    A cell that cannot reach a known destination is False in every grid.

    Args:
        flow: Next-cell indices in row order, with -1 for terminal cells.
        seeds: Mapping from known group IDs to cells touched by their mapped rivers.
        terminals: Grid of known group IDs at outlets, with -1 elsewhere.

    Returns:
        A Boolean catchment grid for each known group.

    Raises:
        ValueError: A flow or destination grid contains invalid values or has the wrong shape.
    """
    flow, terminals = np.asarray(flow), np.asarray(terminals)
    shape = flow.shape
    if (
        flow.ndim != 2
        or terminals.shape != shape
        or flow.dtype.kind not in 'iu'
        or terminals.dtype.kind not in 'iu'
        or np.any(flow < -1)
        or np.any(flow >= flow.size)
        or np.any(terminals < -1)
    ):
        raise ValueError(
            'flow links and terminal IDs require matching valid integer grids'
        )
    if any(
        not isinstance(group, (int, np.integer))
        or group < 0
        or np.asarray(cells).shape != shape
        or np.asarray(cells).dtype != bool
        for group, cells in seeds.items()
    ):
        raise ValueError(
            'destination memberships require known IDs and matching Boolean grids'
        )
    known = np.zeros(shape, dtype=bool)
    for cells in seeds.values():
        known |= cells
    groups = sorted(set(seeds) | {int(g) for g in np.unique(terminals) if g >= 0})
    # Trace to the first known cell once. Its position lets us recover every
    # group there, including a stream that reaches more than one destination.
    stop = (flow == -1) & ~known
    reference = np.full(shape, UNKNOWN, dtype=np.int64)
    positions = np.flatnonzero(known | (stop & (terminals >= 0)))
    reference.ravel()[positions] = positions
    destinations = _follow_destinations(flow, reference.ravel())
    assigned = destinations >= 0
    cells = destinations[assigned]
    result = {}
    for group in groups:
        at_destination = stop & (terminals == group)
        if group in seeds:
            at_destination |= seeds[group]
        mask = np.zeros(shape, dtype=bool)
        mask[assigned] = at_destination.ravel()[cells]
        result[group] = mask
    return result


@njit(cache=True)
def index_incoming_flow(flow: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Record which cells send water directly into each cell.

    Args:
        flow: Grid of next-cell indices, with -1 for terminal cells.

    Returns:
        Two arrays, ``(heads, following)``. If cells 2 and 7 flow into
        cell 4, then ``heads[4] == 7`` and ``following[7] == 2``.
        The value -1 means the list of incoming cells is finished.
    """
    links = flow.ravel()
    heads = np.full(links.size, -1, np.int64)
    following = np.full(links.size, -1, np.int64)
    for index in range(links.size):
        target = links[index]
        if target >= 0:
            following[index] = heads[target]
            heads[target] = index
    return heads, following


@njit(cache=True)
def cells_draining_to(flow: np.ndarray, terminal: int) -> np.ndarray:
    """Start at one cell and work backward through all cells that feed it.

    Args:
        flow: Grid of next-cell indices, with -1 for terminal cells.
        terminal: Row-order index of the cell to start from.

    Returns:
        Cell indices in visit order. For A → B → C, starting at C visits
        C, then B, then A.
    """
    links = flow.ravel()
    heads, following = index_incoming_flow(flow)
    queue = np.empty(links.size, np.int64)
    visited = np.zeros(links.size, np.bool_)
    queue[0], visited[terminal] = terminal, True
    first, count = 0, 1
    while first < count:
        index = heads[queue[first]]
        first += 1
        while index >= 0:
            if not visited[index]:
                visited[index] = True
                queue[count] = index
                count += 1
            index = following[index]
    return queue[:count]
