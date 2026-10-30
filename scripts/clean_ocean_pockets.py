"""Remove enclosed ocean-code artifacts without changing open-ocean boundaries."""
import numpy as np
from scipy.ndimage import label, find_objects, binary_dilation, distance_transform_edt

def clean_ocean_pockets(grid):
    labels, n = label(grid >= 7)
    sizes = np.bincount(labels.ravel())
    main = int(sizes[1:].argmax() + 1)
    parent = np.arange(n + 1)
    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in zip(labels[:, 0], labels[:, -1]):
        if a and b: parent[root(int(a))] = root(int(b))
    main_root = root(main)
    audit = []
    for i, bounds in enumerate(find_objects(labels), 1):
        if bounds is None or root(i) == main_root: continue
        ys, xs = bounds
        if ys.start == 0 or ys.stop == grid.shape[0]: continue
        y0, y1 = max(0, ys.start - 1), min(grid.shape[0], ys.stop + 1)
        x0, x1 = max(0, xs.start - 1), min(grid.shape[1], xs.stop + 1)
        region = grid[y0:y1, x0:x1]
        mask = labels[y0:y1, x0:x1] == i
        rim = binary_dilation(mask) & ~mask
        groups = sorted(int(v) for v in np.unique(region[rim]) if 1 <= v <= 6)
        record = {'parent_cells': int(sizes[i]), 'parent_bounds': [xs.start, ys.start, xs.stop, ys.stop], 'neighbor_groups': groups}
        if len(groups) == 1:
            region[mask] = groups[0]
            record['method'] = 'single_surrounding_continent'
        elif len(groups) > 1 and sizes[i] <= 64:
            # Tiny seam artifacts: nearest existing continent cell, lower ID ties.
            best = np.full(region.shape, np.inf)
            assigned = np.zeros(region.shape, dtype='uint8')
            for group in groups:
                distance = distance_transform_edt(region != group)
                take = distance < best
                assigned[take] = group
                best[take] = distance[take]
            region[mask] = assigned[mask]
            record['method'] = 'nearest_continent_at_small_shared_seam'
        else:
            record['method'] = 'unresolved_review_required'
        audit.append(record)
    return audit
