"""Build mainland seeds from imported witnesses and selected geographic regions."""

from collections import deque
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import time

import numpy as np

from worldatlas.map_build.core.geometry import rasterize
from worldatlas.map_build.core.layers import file_hash
from worldatlas.map_build.land.regions import assemble_regions
from worldatlas.map_build.land.seed_strips import SeedRules
from worldatlas.map_build.land.witnesses import resolve_witnesses


def selected_rules(domain, groups):
    """Uniform targets come from witness groups; two-sided choices come from partitions."""
    selected = {}
    for partition in domain.get('partitions', []):
        group = partition.get('mainland_group_id')
        if group is not None:
            if group in selected:
                raise ValueError('mainland group has multiple geographic partitions')
            selected[group] = partition
    codes = {b['entity_id']:b['code'] for b in domain['category_bindings']
             if b['physical_class']=='land'}
    rules, used_regions, used_partitions = [],set(),set()
    for ident,group in sorted(groups.items()):
        if group['role'] != 'mainland':
            continue
        targets = group['target_entity_ids']
        partition = selected.get(ident)
        if len(targets)==1 and partition is None:
            inside=outside=targets[0]
            region=None
            rule_id=ident
        elif partition is not None:
            inside,outside=partition['side_a_entity_id'],partition['side_b_entity_id']
            region=partition['mainland_region_id']
            if region is None or inside==outside or set(targets)!={inside,outside}:
                raise ValueError('mainland partition conflicts with its selected witness group')
            used_regions.add(region)
            used_partitions.add(ident)
            rule_id=partition['id']
        else:
            raise ValueError('mainland group needs a uniform target or geographic partition')
        rules.append(dict(rule_id=rule_id,component_id=group['component_id'],
                          region_id=region,inside_code=codes[inside],outside_code=codes[outside]))
    if (used_regions != set(domain['land_baseline_policy']['region_ids'])
            or used_partitions != set(selected)
            or {r[k] for r in rules for k in ('inside_code','outside_code')} != set(codes.values())):
        raise ValueError('selected mainland rules leave an active group, region or category unused')
    return rules


def build_seeds(domain, components, directory, *, strip_rows=64, workers=None):
    """Return ordinary seed streams and current-generation resolution records."""
    started = time.monotonic()
    grid, directory = components.grid, Path(directory)
    workers = (os.cpu_count() or 1) if workers is None else workers
    if type(strip_rows) is not int or strip_rows <= 0 or type(workers) is not int or workers <= 0:
        raise ValueError('seed rasterization needs positive strip size and worker count')
    resolution = resolve_witnesses(domain, components)
    regions, closures = assemble_regions(domain, components)
    rules = selected_rules(domain, resolution['groups'])
    index = SeedRules(rules)
    components.totals()

    def raster(first):
        last = min(grid.height, first + strip_rows)
        lo, hi = map(int, components.offsets[[first, last]])
        needed = index.required_regions(components.runs[lo:hi])
        # Keep the complete native row width and original transform arithmetic.
        # Each selected root reads its own polygon; there is no fixed bit field
        # or limit on the number of selected regions or category codes.
        return (
            first,
            last,
            {
                ident: rasterize(regions[ident]['geometry'], grid, (0, grid.width, first, last))[1]
                for ident in sorted(needed)
            },
        )

    def strips():
        positions = iter(range(0, grid.height, strip_rows))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            pending = deque()
            for _ in range(workers):
                first = next(positions, None)
                if first is None:
                    break
                pending.append(executor.submit(raster, first))
            while pending:
                yield pending.popleft().result()
                first = next(positions, None)
                if first is not None:
                    pending.append(executor.submit(raster, first))

    directory.mkdir()
    inside = np.zeros(len(rules), dtype=np.uint64)
    outside = inside.copy()
    categories = np.zeros(len(index.codes), dtype=np.uint64)
    total = 0
    with (directory / 'rows.u32le').open('xb') as rowout, (directory / 'runs.u32le').open(
        'xb'
    ) as runout:
        np.array([0], dtype='<u4').tofile(rowout)
        for first, last, masks in strips():
            lo, hi = map(int, components.offsets[[first, last]])
            offsets = components.offsets[first : last + 1].astype(np.int64) - lo
            pairs, counts, a, b, c = index.strip(
                masks, offsets, components.runs[lo:hi], grid.width, last - first
            )
            cumulative = np.cumsum(counts, dtype=np.uint64) + total
            if cumulative[-1] >= 2**32:
                raise ValueError('seed run offsets exceed uint32')
            cumulative.astype('<u4').tofile(rowout)
            pairs.tofile(runout)
            total = int(cumulative[-1])
            inside += a
            outside += b
            categories += c
    if np.any(inside + outside == 0) or np.any(categories == 0):
        raise ValueError('selected seed component or category has no physical land cells')
    for i, rule in enumerate(rules):
        if rule['region_id'] is not None and (inside[i] == 0 or outside[i] == 0):
            raise ValueError('selected mainland partition has an empty side')
    report = dict(
        grid=vars(grid),
        groups=resolution['groups'],
        witnesses=resolution['witnesses'],
        rules=rules,
        region_geometry_sha256={key: value['geometry_sha256'] for key, value in regions.items()},
        closures=closures,
        category_cell_counts={
            str(code): int(count) for code, count in zip(index.codes, categories)
        },
        rule_population={
            r['rule_id']: dict(inside_cells=int(inside[i]), outside_cells=int(outside[i]))
            for i, r in enumerate(rules)
        },
        output_sha256={name: file_hash(directory / name) for name in ('rows.u32le', 'runs.u32le')},
        processing_seconds=time.monotonic() - started,
        download_seconds=0.0,
    )
    (directory / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
