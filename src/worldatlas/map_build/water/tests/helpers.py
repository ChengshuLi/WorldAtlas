import numpy as np
from scipy.spatial import cKDTree


def rle(array):
    rows = [0]
    runs = []
    for row in array:
        for i, x in enumerate(row):
            if i == len(row) - 1 or row[i + 1] != x:
                runs.extend((i + 1, int(x)))
        rows.append(len(runs) // 2)
    return np.array(rows, dtype='<u4'), np.array(runs, dtype='<u4')


def index_present(centers, pairs):
    indices = {}
    if not len(centers['mids']):
        return indices
    for _, lc, _ in pairs:
        m = centers['category'] == lc
        if np.any(m):
            part = {k: centers[k][m] for k in ('mids', 'lat', 'lon', 'category')}
            indices[lc] = (part, cKDTree(part['mids']))
    return indices
