"""Compose a source-derived sparse split into a seed with that root omitted.

Research-only row primitive. It never consults a prior label grid. Caller must
independently pin and validate streams, identify the selected physical root,
and apply resource guards around whole-grid I/O.
"""

def _coverage(spans, width, triples):
    merged = []
    last = 0
    for item in spans:
        if len(item) != (3 if triples else 2):
            raise ValueError('invalid interval fields')
        a, b = item[:2]
        if type(a) is not int or type(b) is not int or not 0 <= a < b <= width or a < last:
            raise ValueError('invalid or overlapping intervals')
        if triples and (type(item[2]) is not int or not 17 <= item[2] <= 22):
            raise ValueError('invalid split code')
        if merged and merged[-1][1] == a:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
        last = b
    return merged


def compose_row(seed_runs, split_spans, selected_intervals, width):
    """Return coalesced (exclusive end, code) runs, failing on gaps/conflicts.

    The seed uses end-coded full-width runs (0 means no seed). Split spans are
    half-open (start, end, code). Selected intervals are the current physical
    root's half-open ranges on this row, independently supplied by the caller.
    """
    if type(width) is not int or width <= 0 or not seed_runs:
        raise ValueError('invalid row width or seed')
    last = 0
    for end, code in seed_runs:
        if type(end) is not int or not last < end <= width or type(code) is not int or code not in (0, 17, 18, 19, 20, 21, 22):
            raise ValueError('invalid seed runs')
        last = end
    if last != width:
        raise ValueError('seed row does not cover width')
    if _coverage(split_spans, width, True) != _coverage(selected_intervals, width, False):
        raise ValueError('split does not exactly cover selected root')

    x = i = j = 0
    out = []
    while x < width:
        base_end, base_code = seed_runs[i]
        while j < len(split_spans) and split_spans[j][1] <= x:
            j += 1
        covered = j < len(split_spans) and split_spans[j][0] <= x
        if covered:
            _, end, code = split_spans[j]
            if base_code != 0:
                raise ValueError('split overlaps another seed')
            end = min(end, base_end)
        else:
            code = base_code
            end = min(base_end, split_spans[j][0]) if j < len(split_spans) else base_end
        if end <= x:
            raise ValueError('composition made no progress')
        if out and out[-1][1] == code:
            out[-1] = (end, code)
        else:
            out.append((end, code))
        x = end
        if x == base_end:
            i += 1
    return out
