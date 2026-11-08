"""Resolve validated water spans as numeric columns without repeating metadata.

Any number of declared priority levels is supported. Internally overlapping
priority bands retain the original resolver, including all ambiguity and
override diagnostics. No layer names, geography, span counts or map decisions
select the algorithm.
"""
from dataclasses import dataclass

import numpy as np

import compose_full_water_grid as reference


@dataclass(frozen=True)
class ResolvedRow:
    columns: tuple
    overlap_cells: int
    used_reference: bool = False


def empty_columns():
    return (np.empty(0, dtype=np.uint32), np.empty(0, dtype=np.uint32),
            np.empty(0, dtype=np.uint8))


class LayerPolicy:
    """Immutable layer metadata, factored once rather than copied per span."""
    def __init__(self, entries):
        self.labels = tuple(str(entry.get('layer_id', entry['manifest_path'])) for entry in entries)
        self.priorities = tuple(int(entry['priority']) for entry in entries)
        self.overrides = tuple(frozenset(entry.get('overrides', [])) for entry in entries)
        levels = {value: index for index, value in enumerate(sorted(set(self.priorities)))}
        self.levels = np.asarray([levels[value] for value in self.priorities], dtype=np.intp)
        self.allowed = np.asarray([
            [code in entry['allowed_codes'] if 'allowed_codes' in entry else True for code in range(1, 7)]
            for entry in entries], dtype=bool).reshape(len(entries), 6)
        self.levels.flags.writeable = False
        self.allowed.flags.writeable = False

    def reference_row(self, chunks, row, physical_ends, physical_values):
        spans = []
        for layer, records in chunks:
            if hasattr(records, 'reference_records'):
                records = records.reference_records(row)
            for record in records:
                code = record[3]
                if code > 6:
                    raise ValueError(f'prefill layers may only assign water code 1–6, got {code} on row {row}')
                if not 1 <= code <= 6 or not self.allowed[layer, code - 1]:
                    raise ValueError(f'assignment code not allowed by selected basin policy on row {row}: {code}')
            spans.extend(reference.add_layer_identity(records, self.priorities[layer], self.labels[layer],
                                                       self.overrides[layer]))
        assignments, conflicts = reference.choose_assignments(spans, row, physical_ends, physical_values)
        cells = sum(end - start for start, end in {(a, b) for a, b, _, _ in conflicts})
        return ResolvedRow(reference.assignment_arrays(assignments), cells, True)

    def resolve(self, chunks, row, physical_ends, physical_values):
        """Consume already validated row records and retain every breakpoint."""
        chunks = [(layer, records) for layer, records in chunks if records]
        if not chunks:
            return ResolvedRow(empty_columns(), 0)
        # Non-string legacy identities can affect sorting/hash diagnostics.
        # Arrow's validated string columns avoid this Python metadata scan.
        if any(not (records.metadata_strings_only if hasattr(records, 'metadata_strings_only') else
                    all(isinstance(span[4], str) and isinstance(span[5], str) for span in records))
               for _, records in chunks):
            return self.reference_row(chunks, row, physical_ends, physical_values)
        def column(records, index, dtype):
            if hasattr(records, 'columns'):
                return records.columns[index - 1]
            return np.fromiter((s[index] for s in records), dtype=dtype, count=len(records))
        starts = np.concatenate([column(records, 1, np.uint32) for _, records in chunks])
        stops = np.concatenate([column(records, 2, np.uint32) for _, records in chunks])
        codes = np.concatenate([column(records, 3, np.int64) for _, records in chunks])
        layers = np.concatenate([np.full(len(records), layer, dtype=np.intp) for layer, records in chunks])
        invalid = (codes < 1) | (codes > 6)
        if np.any(invalid) or np.any(~self.allowed[layers, codes - 1]):
            return self.reference_row(chunks, row, physical_ends, physical_values)
        bands = []
        for level in np.unique(self.levels[layers]):
            ids = np.flatnonzero(self.levels[layers] == level)
            ids = ids[np.argsort(starts[ids], kind='stable')]
            if np.any(starts[ids][1:] < stops[ids][:-1]):
                return self.reference_row(chunks, row, physical_ends, physical_values)
            bands.append(ids)
        cuts = np.unique(np.concatenate((starts, stops)))
        left, right = cuts[:-1], cuts[1:]
        winner = np.full(len(left), -1, dtype=np.intp)
        active_count = np.zeros(len(left), dtype=np.intp)

        def owners(ids):
            position = np.searchsorted(starts[ids], left, side='right') - 1
            safe = np.maximum(position, 0)
            return np.where((position >= 0) & (left < stops[ids[safe]]), ids[safe], -1)

        # Determine the final winner before checking permissions: a still
        # higher layer may lawfully cover an otherwise forbidden lower overlap.
        for ids in bands:
            owner = owners(ids)
            present = owner >= 0
            winner[present] = owner[present]
            active_count += present
        for ids in bands:
            owner = owners(ids)
            lost = (owner >= 0) & (winner != owner)
            if np.any(lost):
                pairs = np.unique(np.column_stack((layers[winner[lost]], layers[owner[lost]])), axis=0)
                if any(self.labels[int(lower)] not in self.overrides[int(higher)] for higher, lower in pairs):
                    return self.reference_row(chunks, row, physical_ends, physical_values)
        active = winner >= 0
        if np.any(reference.row_code_at(physical_ends, physical_values, left[active]) != 1):
            return self.reference_row(chunks, row, physical_ends, physical_values)
        overlap = int((right[active_count > 1] - left[active_count > 1]).astype(np.uint64).sum())
        columns = (left[active], right[active], codes[winner[active]].astype(np.uint8))
        return ResolvedRow(columns, overlap)
