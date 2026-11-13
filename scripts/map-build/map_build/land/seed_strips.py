"""Vectorized seed-run composition for arbitrary region IDs and entity codes."""
import numpy as np


class SeedRules:
    def __init__(self, rules):
        if any(type(r[k]) is not int for r in rules for k in ('component_id', 'inside_code', 'outside_code')):
            raise ValueError('seed roots and category codes must be integers')
        self.regions = [rule['region_id'] for rule in rules]
        self.region_keys = list(dict.fromkeys(self.regions))
        self.region_index = np.array([self.region_keys.index(region) for region in self.regions])
        self.table = np.array([[r['component_id'], r['inside_code'], r['outside_code']]
                               for r in rules], dtype=np.int64)
        if (not len(rules) or np.any(self.table[:, 0] < 0) or np.any(self.table[:, 0] >= 2**32-1)
                or np.any(self.table[:, 1:] <= 0) or np.any(self.table[:, 1:] >= 2**32)):
            raise ValueError('seed rules need current roots and nonzero uint32 codes')
        if any(region is None and a != b for region, (_, a, b) in zip(self.regions, self.table)):
            raise ValueError('whole-component seed rule has conflicting targets')
        self.order = np.argsort(self.table[:, 0], kind='stable')
        self.roots = self.table[self.order, 0]
        if np.any(self.roots[1:] == self.roots[:-1]):
            raise ValueError('duplicate seed component')
        self.codes = np.unique(self.table[:, 1:])

    def selection(self, records):
        positions = np.searchsorted(self.roots, records[:, 2])
        safe = np.minimum(positions, len(self.roots)-1)
        selected = (positions < len(self.roots)) & (self.roots[safe] == records[:, 2])
        return selected, self.order[positions[selected]]

    def required_regions(self, records):
        _, owners = self.selection(records)
        return {self.region_keys[int(index)] for index in np.unique(self.region_index[owners])} - {None}

    def strip(self, masks, offsets, records, width, height):
        """Split only selected intervals at their own polygon's transitions."""
        if (len(offsets) != height+1 or offsets[0] != 0 or offsets[-1] != len(records)
                or np.any(offsets[1:] < offsets[:-1])):
            raise ValueError('invalid seed component strip offsets')
        rows = np.searchsorted(offsets, np.arange(len(records)), side='right')-1
        if len(records) and (np.any(records[:, 0] >= records[:, 1]) or np.any(records[:, 1] > width)
                or np.any((rows[1:] == rows[:-1]) & (records[1:, 0] < records[:-1, 1]))):
            raise ValueError('invalid seed component intervals')
        selected, owners = self.selection(records)
        starts = rows[selected].astype(np.int64)*width + records[selected, 0].astype(np.int64)
        ends = rows[selected].astype(np.int64)*width + records[selected, 1].astype(np.int64)
        parts = []
        for index, region in enumerate(self.region_keys):
            chosen = np.flatnonzero(self.region_index[owners] == index)
            if not len(chosen):
                continue
            a, b, group = starts[chosen], ends[chosen], owners[chosen]
            if region is None:
                parts.append((a, b, group, np.ones(len(a), dtype=bool)))
                continue
            mask = np.asarray(masks[region])
            if mask.shape != (height, width):
                raise ValueError('seed mask differs from the component strip')
            inside = mask.reshape(-1) != 0
            changes = np.flatnonzero(inside[1:] != inside[:-1])+1
            lo, hi = np.searchsorted(changes, a, side='right'), np.searchsorted(changes, b, side='left')
            count = hi-lo
            repeat = count+1
            parent = np.repeat(np.arange(len(a)), repeat)
            within = np.arange(int(repeat.sum()))-np.repeat(np.cumsum(repeat)-repeat, repeat)
            stop = np.repeat(b, repeat).copy()
            middle = within < np.repeat(count, repeat)
            stop[middle] = changes[(np.repeat(lo, repeat)+within)[middle]]
            begin = np.r_[0, stop[:-1]]
            first = within == 0
            begin[first] = a[parent[first]]
            parts.append((begin, stop, group[parent], inside[begin]))
        inside_counts = np.zeros(len(self.table), dtype=np.uint64)
        outside_counts = inside_counts.copy()
        categories = np.zeros(len(self.codes), dtype=np.uint64)
        if parts:
            a, b, owner, inside = [np.concatenate([part[i] for part in parts]) for i in range(4)]
            labels = np.where(inside, self.table[owner, 1], self.table[owner, 2])
            lengths = (b-a).astype(np.uint64)
            np.add.at(inside_counts, owner[inside], lengths[inside])
            np.add.at(outside_counts, owner[~inside], lengths[~inside])
            np.add.at(categories, np.searchsorted(self.codes, labels), lengths)
            order = np.argsort(a, kind='stable')
            a, b, labels = a[order], b[order], labels[order]
            finish = np.empty(2*len(a)+1, dtype=np.int64)
            values = np.zeros(len(finish), dtype=np.uint32)
            finish[:-1:2], finish[1:-1:2], finish[-1] = a, b, width*height
            values[1:-1:2] = labels
            positive = finish > np.r_[0, finish[:-1]]
            finish, values = finish[positive], values[positive]
        else:
            finish, values = np.array([width*height]), np.array([0], dtype=np.uint32)
        boundaries = np.union1d(finish, np.arange(width, width*height+1, width))
        codes = values[np.searchsorted(finish, boundaries, side='left')]
        keep = np.r_[(codes[:-1] != codes[1:]) | (boundaries[:-1] % width == 0), True]
        boundaries, codes = boundaries[keep], codes[keep]
        pairs = np.column_stack(((boundaries-1) % width+1, codes)).astype('<u4')
        counts = np.bincount((boundaries-1)//width, minlength=height)
        return pairs, counts, inside_counts, outside_counts, categories
