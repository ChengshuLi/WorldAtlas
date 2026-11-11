"""One WGS84-distance D8 implementation for geographic and projected grids.

Depression filling changes only a working copy. Exact flats follow the
priority-flood parent toward a spill or outlet; strictly downhill flow takes
precedence. Source-backed closed sinks can be supplied as terminal cells.
"""
import heapq

import numpy as np
from numba import njit
from pyproj import CRS, Geod, Transformer

GEOD = Geod(ellps='WGS84')
UNKNOWN = -1


def neighbor_distances(grid):
    """Measure each undirected E/S/SE/SW edge once, in metres on WGS84."""
    height, width = grid.elevation.shape
    to_geo = Transformer.from_crs(CRS.from_user_input(grid.crs), 4326, always_xy=True)
    distances = np.zeros((4, height, width), dtype='float64')
    for first in range(0, height, 128):
        last = min(height, first + 128)
        stop = min(height, last + 1)
        columns, rows = np.meshgrid(np.arange(width), np.arange(first, stop))
        lon, lat = to_geo.transform(*grid.coordinates(rows, columns), errcheck=True)
        if not np.isfinite(lon).all() or not np.isfinite(lat).all() or np.any(np.abs(lat) > 90):
            raise ValueError('invalid WGS84 cell coordinates')
        count = last - first
        for plane, dr, dc in ((0, 0, 1), (1, 1, 0), (2, 1, 1), (3, 1, -1)):
            n = min(count, height - first - dr)
            a = slice(max(0, -dc), min(width, width - dc))
            b = slice(max(0, dc), min(width, width + dc))
            if n == 0 or width <= abs(dc):
                continue
            length = GEOD.inv(lon[:n, a], lat[:n, a],
                              lon[dr:n + dr, b], lat[dr:n + dr, b])[2]
            if not np.isfinite(length).all() or np.any(length <= 0):
                raise ValueError('invalid neighboring-cell distance')
            distances[plane, first:first + n, a] = length
    return distances


@njit(cache=True)
def _flow(elevation, distances, closed):
    height, width = elevation.shape
    working = np.full(elevation.shape, np.inf)
    parent = np.full(elevation.size, -2, dtype=np.int64)
    heap = [(0., 0)]
    heap.pop()
    for row in range(height):
        for column in range(width):
            if row == 0 or column == 0 or row == height - 1 or column == width - 1 or closed[row, column]:
                index = row * width + column
                working[row, column] = elevation[row, column]
                parent[index] = -1
                heapq.heappush(heap, (working[row, column], index))
    while heap:
        value, index = heapq.heappop(heap)
        row, column = index // width, index % width
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                rr, cc = row + dr, column + dc
                if (dr or dc) and 0 <= rr < height and 0 <= cc < width:
                    other = rr * width + cc
                    if parent[other] == -2:
                        parent[other] = index
                        working[rr, cc] = max(value, elevation[rr, cc])
                        heapq.heappush(heap, (working[rr, cc], other))
    flow = parent.copy().reshape(elevation.shape)
    for row in range(height):
        for column in range(width):
            if closed[row, column]:
                continue
            best = 0.
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    rr, cc = row + dr, column + dc
                    if (dr or dc) and 0 <= rr < height and 0 <= cc < width:
                        if dr == 0:
                            distance = distances[0, row, column if dc > 0 else column - 1]
                        elif dc == 0:
                            distance = distances[1, row if dr > 0 else row - 1, column]
                        elif dr == dc:
                            distance = distances[2, row if dr > 0 else row - 1, column if dc > 0 else column - 1]
                        else:
                            distance = distances[3, row if dr > 0 else row - 1, column if dr > 0 else column + 1]
                        slope = (working[row, column] - working[rr, cc]) / distance
                        if slope > best:
                            best = slope
                            flow[row, column] = rr * width + cc
    return working, flow


def compute_flow(grid, closed_sinks=(), *, outlets=None):
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
    return _flow(elevation, neighbor_distances(grid), closed)


@njit(cache=True)
def _destinations(flow, seeds, terminals):
    links = flow.ravel()
    labels = seeds.ravel().copy()
    state = np.zeros(links.size, np.uint8)
    path = np.empty(links.size, np.int64)
    for index in range(links.size):
        if labels[index] >= 0:
            state[index] = 2
        elif links[index] == -1:
            labels[index] = terminals.ravel()[index]
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
        destination = labels[index] if index >= 0 and state[index] == 2 else -1
        for i in range(count):
            labels[path[i]] = destination
            state[path[i]] = 2
    return labels.reshape(flow.shape)


def destinations(flow, seeds, terminals=None):
    """Follow flow to any supplied group ID; -1 means an unknown destination.

    River seeds take precedence. Source-backed domain exits or closed sinks can
    supply terminal groups. An unclassified pit, exit or cycle stays unknown.
    """
    flow, seeds = np.asarray(flow), np.asarray(seeds)
    if terminals is None:
        terminals = np.full(flow.shape, UNKNOWN, dtype='int64')
    terminals = np.asarray(terminals)
    if flow.ndim != 2 or seeds.shape != flow.shape or terminals.shape != flow.shape:
        raise ValueError('flow, seed and terminal grids must have matching shapes')
    if any(a.dtype.kind not in 'iu' for a in (flow, seeds, terminals)):
        raise ValueError('flow links and destination IDs must be integers')
    if np.any(flow < -1) or np.any(flow >= flow.size) or np.any(seeds < -1) or np.any(terminals < -1):
        raise ValueError('invalid flow link or destination ID')
    return _destinations(flow.astype('int64'), seeds.astype('int64'), terminals.astype('int64'))


@njit(cache=True)
def upstream_links(flow):
    """Index the actual incoming flow edges once for upstream tracing."""
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
def upstream_order(flow, terminal):
    """Visit every cell whose flow reaches terminal, starting at that terminal."""
    links = flow.ravel()
    heads, following = upstream_links(flow)
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
