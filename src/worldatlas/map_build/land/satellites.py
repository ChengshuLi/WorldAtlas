"""Indexed WGS84 distances from complete small components to source-backed islands."""

import math
from bisect import bisect_left, bisect_right
from itertools import accumulate
from worldatlas.map_build.land.line_groups import _require
from worldatlas.map_build.core.geodesy import MIN_RADIUS, CUSHION_M as BOUND_GUARD_M

MIN_MERIDIONAL_RADIUS = math.floor(MIN_RADIUS)


def run_lower_bound(y, a, b, yy, c, d, width, north):
    step = 360 / width
    gap = min(max(0, max(c + shift - (b - 1), a - (d - 1 + shift))) for shift in (-width, 0, width))
    p1, p2 = math.radians(north - (y + 0.5) * step), math.radians(north - (yy + 0.5) * step)
    dl, dp = math.radians(gap * step), p2 - p1
    hav = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * math.asin(math.sqrt(min(1.0, max(0.0, hav)))) * MIN_MERIDIONAL_RADIUS


class RunIndex:
    """Row interval index over complete parents, including overlapping runs.

    The spherical metric lower bound gives a conservative query rectangle.
    A path of angular length theta stays within theta latitude of its start;
    integrating cos(latitude)*dlongitude there bounds its longitude excursion.
    Near a pole the query deliberately includes every longitude. Exact pruning
    and WGS84 calls below are unchanged, and retain the original per-parent
    candidate/run order and incumbent. No component is replaced by a centroid.
    """

    def __init__(self, root_runs, components, candidates, width, north, radius, max_dy):
        self.width, self.north, self.step = width, north, 360 / width
        self.theta, self.max_dy = radius / MIN_MERIDIONAL_RADIUS, max_dy
        low = min(root_runs[r][0][0] for r in candidates) - max_dy
        high = max(root_runs[r][-1][0] for r in candidates) + max_dy
        minimum = min(components[r]['total'] for r in candidates)
        rows = {}
        for root, runs in root_runs.items():
            if components[root]['total'] <= minimum:
                continue
            start = bisect_left(runs, (low, 0, 0))
            end = bisect_right(runs, (high, width, width))
            for y, a, b in runs[start:end]:
                rows.setdefault(y, []).append((a, b, root))
        self.rows = {}
        for y, records in rows.items():
            records.sort()
            self.rows[y] = (
                [a for a, _, _ in records],
                list(accumulate((b for _, b, _ in records), max)),
                records,
            )
        self.ys = sorted(self.rows)

    def nearby(self, root, runs, components):
        found = {}
        for i, (y, a, b) in enumerate(runs):
            phi = math.radians(self.north - (y + 0.5) * self.step)
            extreme = abs(phi) + self.theta
            dx = (
                self.width
                if extreme >= math.pi / 2
                else math.ceil(math.degrees(self.theta / math.cos(extreme)) / self.step) + 1
            )
            left, right = a - dx, b + dx
            if right - left >= self.width:
                windows = [(0, self.width)]
            elif left < 0:
                windows = [(0, right), (left + self.width, self.width)]
            elif right > self.width:
                windows = [(left, self.width), (0, right - self.width)]
            else:
                windows = [(left, right)]
            start = bisect_left(self.ys, y - self.max_dy)
            end = bisect_right(self.ys, y + self.max_dy)
            for yy in self.ys[start:end]:
                starts, ends, records = self.rows[yy]
                for lo, hi in windows:
                    first, last = bisect_right(ends, lo), bisect_left(starts, hi)
                    for c, d, parent in records[first:last]:
                        if (
                            parent != root
                            and d > lo
                            and components[parent]['total'] > components[root]['total']
                        ):
                            found.setdefault(parent, {}).setdefault(i, []).append((yy, c, d))
        # Restore exactly the reviewed run order; wrap queries can contribute
        # the same interval twice when a parent spans both query windows.
        return {
            parent: {i: sorted(set(values)) for i, values in pairs.items()}
            for parent, pairs in found.items()
        }


def apply_satellites(
    result,
    components,
    root_runs,
    anchors,
    exact_run_pair,
    *,
    width,
    north,
    max_satellite_cells,
    max_gap_m,
    candidate_roots,
    tie_m=1e-5,
    allow_anchored_over_unknown_nearer
):
    """Apply main-island convention after explicit replay and initial line side.

    root_runs must include *all* components larger than the candidate that
    could lie within the search distance, including unanchored competing land; their complete global
    counts must match components. The caller proves this spatial completeness.
    anchors maps generation-only roots to {code, source_id, source_feature_id},
    each resolved from a source-backed named island and already selected or
    unambiguously line-classified. Distances are exact minimum WGS84 center to
    center over complete runs. A directly anchored island may override a
    line-side default; a conflicting independently classified nearer land
    component instead causes review. A source-group proposal keeps its
    provenance and is held if its closest known competitor has another target.
    Unknown nearer land is diagnostic. Existing selected
    affiliations and protected mainland always win. Split or touching components
    remain in review, but an otherwise complete component beyond an endpoint can
    inherit an independently established source anchor without extending the line.
    The size and gap parameters are operational policy,
    not proof of source membership. No chaining through inferred satellites.
    """
    _require(
        isinstance(result, dict)
        and isinstance(components, dict)
        and isinstance(root_runs, dict)
        and isinstance(anchors, dict)
        and callable(exact_run_pair),
        'invalid satellite inputs',
    )
    _require(
        type(width) is int
        and width >= 2
        and type(north) in (int, float)
        and math.isfinite(north)
        and -90 <= north <= 90
        and type(max_satellite_cells) is int
        and max_satellite_cells > 0
        and type(max_gap_m) in (int, float)
        and math.isfinite(max_gap_m)
        and max_gap_m > 0
        and type(tie_m) in (int, float)
        and math.isfinite(tie_m)
        and tie_m >= 0
        and type(allow_anchored_over_unknown_nearer) is bool,
        'invalid satellite policy',
    )
    for root, runs in root_runs.items():
        _require(root in components and isinstance(runs, list) and runs, 'missing component runs')
        _require(
            all(
                isinstance(run, (tuple, list))
                and len(run) == 3
                and all(type(v) is int for v in run)
                and 0 <= run[0]
                and -90 <= north - (run[0] + 0.5) * 360 / width <= 90
                and 0 <= run[1] < run[2] <= width
                for run in runs
            ),
            'invalid run',
        )
        _require(
            sum(b - a for _, a, b in runs) == components[root]['total']
            and len(set(map(tuple, runs))) == len(runs)
            and all((a[0], a[2]) <= (b[0], b[1]) for a, b in zip(runs, runs[1:])),
            'incomplete or overlapping runs',
        )
    root_runs = {root: [tuple(run) for run in runs] for root, runs in root_runs.items()}
    for root, a in anchors.items():
        _require(
            root in root_runs
            and isinstance(a, dict)
            and type(a.get('code')) is int
            and a['code'] > 0
            and isinstance(a.get('source_id'), str)
            and a['source_id']
            and isinstance(a.get('source_feature_id'), str)
            and a['source_feature_id']
            and isinstance(a.get('source_version'), str)
            and a['source_version']
            and isinstance(a.get('source_sha256'), str)
            and len(a['source_sha256']) == 64
            and all(ch in '0123456789abcdef' for ch in a['source_sha256'])
            and isinstance(a.get('main_island_evidence'), str)
            and a['main_island_evidence'],
            'invalid source-backed main island',
        )
        proposal = result['proposals'].get(root)
        _require(
            proposal is not None
            and proposal['code'] == a['code']
            and proposal.get('basis')
            in (
                'selected_affiliation',
                'whole_component_line_side',
                'inferred_source_extent_group_convention',
            ),
            'anchor target must be independently established, not an inferred satellite',
        )
    out = {
        **result,
        'proposals': {k: dict(v) for k, v in result['proposals'].items()},
        'review': dict(result['review']),
        'satellites': {int(k): dict(v) for k, v in result.get('satellites', {}).items()},
        'nearest_unanchored': {
            int(k): dict(v) for k, v in result.get('nearest_unanchored', {}).items()
        },
        'group_anchor_conflicts': {
            int(k): dict(v) for k, v in result.get('group_anchor_conflicts', {}).items()
        },
    }
    _require(
        isinstance(candidate_roots, (set, frozenset)) and candidate_roots.issubset(root_runs),
        'candidate runs missing',
    )
    step = 360 / width
    # Monotonic rows permit exact latitude-only pruning before expensive run
    # comparisons; one extra row absorbs floating-point rounding.
    max_dy = (
        math.ceil(
            (max_gap_m + tie_m + BOUND_GUARD_M) / MIN_MERIDIONAL_RADIUS * 180 / math.pi / step
        )
        + 1
    )
    candidates = {
        root
        for root in candidate_roots
        if root not in anchors
        and components[root]['total'] <= max_satellite_cells
        and result['proposals'].get(root, {}).get('basis') != 'selected_affiliation'
        and (root not in result['review'] or result['review'][root] == 'outside_line_latitude')
        and components[root]['in_scope'] == components[root]['total']
    }
    if not candidates:
        return out
    index = RunIndex(
        root_runs, components, candidates, width, north, max_gap_m + tie_m + BOUND_GUARD_M, max_dy
    )
    for root in candidate_roots:
        runs = root_runs[root]
        if root in anchors or components[root]['total'] > max_satellite_cells:
            continue
        proposal = out['proposals'].get(root)
        if proposal and proposal['basis'] == 'selected_affiliation':
            continue
        source_group = bool(
            proposal and proposal['basis'] == 'inferred_source_extent_group_convention'
        )
        # Only endpoint holds are eligible for source-anchored inheritance.
        # Unknown or conflict review states fail closed, including conflicts
        # raised by earlier group and satellite passes.
        if root in out['review'] and out['review'][root] != 'outside_line_latitude':
            continue
        # Partial-window components are not regional satellite decisions.
        if components[root]['in_scope'] != components[root]['total']:
            continue
        distances = []
        for parent, pairs in index.nearby(root, runs, components).items():
            best = math.inf
            for i, (y, a, b) in enumerate(runs):
                for yy, c, d in pairs.get(i, ()):
                    lower = abs(y - yy) * step * math.pi / 180 * MIN_MERIDIONAL_RADIUS
                    if lower > min(max_gap_m, best) + tie_m + BOUND_GUARD_M:
                        continue
                    if (
                        run_lower_bound(y, a, b, yy, c, d, width, north)
                        > min(max_gap_m, best) + tie_m + BOUND_GUARD_M
                    ):
                        continue
                    distance, _ = exact_run_pair(
                        y,
                        a,
                        b,
                        yy,
                        c,
                        d,
                        width,
                        north=north,
                        incumbent=min(max_gap_m, best) + tie_m,
                        tol=tie_m,
                    )
                    if distance is not None:
                        _require(
                            math.isfinite(distance) and distance >= 0, 'invalid geodesic result'
                        )
                        best = min(best, distance)
            if best <= max_gap_m + tie_m:
                distances.append((best, parent))
        if not distances:
            continue
        distances.sort()
        minimum = distances[0][0]
        if minimum > max_gap_m:
            continue
        if source_group:
            # Source groups precede proximity. Never silently replace their
            # target or source evidence; contradictory nearest known land is
            # held for review rather than resolved by distance alone.
            known = [
                (
                    d,
                    p,
                    (
                        anchors[p]['code']
                        if p in anchors
                        else result['proposals']
                        .get(p, {})
                        .get('code', result.get('competitor_targets', {}).get(p))
                    ),
                )
                for d, p in distances
            ]
            known = [(d, p, code) for d, p, code in known if code is not None]
            if known:
                first = min(d for d, _, _ in known)
                closest = [(d, p, code) for d, p, code in known if d <= first + tie_m]
                if {code for _, _, code in closest} != {proposal['code']}:
                    out['proposals'].pop(root, None)
                    out['review'][root] = 'conflicting_group_and_anchor'
                    out['group_anchor_conflicts'][root] = {
                        'group_target_code': proposal['code'],
                        'competitors': [
                            {
                                'root_current_generation_only': p,
                                'code': code,
                                'distance_m': d,
                                'anchor': dict(anchors[p]) if p in anchors else None,
                                'proposal': (
                                    dict(result['proposals'][p])
                                    if p in result['proposals']
                                    else None
                                ),
                                'selected_claims': result.get('replayed_claims', {}).get(p, []),
                            }
                            for d, p, code in closest
                        ],
                    }
            continue
        nearest = [p for distance, p in distances if distance <= minimum + tie_m]
        targets = {
            (
                anchors[p]['code']
                if p in anchors
                else result['proposals']
                .get(p, {})
                .get('code', result.get('competitor_targets', {}).get(p))
            )
            for p in nearest
        }
        if any(p not in anchors for p in nearest):
            # Mere proximity to unnamed or unanchored land is not evidence that
            # the approved line-side target is wrong. Preserve it unless a
            # nearest independently classified competitor has another target.
            out['nearest_unanchored'][root] = {
                'roots_current_generation_only': nearest,
                'distance_m': minimum,
            }
            known = targets - {None}
            if proposal and proposal['basis'] == 'whole_component_line_side':
                if not known or known == {proposal['code']}:
                    continue
                out['proposals'].pop(root, None)
                out['review'][root] = 'conflicting_nearest_land_targets'
                continue
            if not allow_anchored_over_unknown_nearer:
                # Beyond the endpoints, the conservative default stays held.
                continue
            # Optional broad geographic convention: an unknown nearer land
            # component is diagnostic, not proof that a nearby named main
            # island is the wrong parent. Find the closest independently
            # anchored main island directly, never through inferred satellites.
            anchored = [(d, p) for d, p in distances if p in anchors and d <= max_gap_m]
            if not anchored:
                continue
            anchored.sort()
            anchor_distance = anchored[0][0]
            anchor_nearest = [p for d, p in anchored if d <= anchor_distance + tie_m]
            anchor_codes = {anchors[p]['code'] for p in anchor_nearest}
            known_near = {
                (
                    anchors[p]['code']
                    if p in anchors
                    else result['proposals']
                    .get(p, {})
                    .get('code', result.get('competitor_targets', {}).get(p))
                )
                for d, p in distances
                if d <= anchor_distance + tie_m
            } - {None}
            if len(anchor_codes) != 1 or known_near - anchor_codes:
                out['proposals'].pop(root, None)
                out['review'][root] = 'conflicting_nearest_land_targets'
                continue
            parent = min(anchor_nearest)
            code = anchors[parent]['code']
            out['proposals'][root] = {'code': code, 'basis': 'source_anchored_nearest_main_island'}
            out['review'].pop(root, None)
            out['satellites'][root] = {
                'parent_root_current_generation_only': parent,
                'distance_m': anchor_distance,
                'source_id': anchors[parent]['source_id'],
                'source_feature_id': anchors[parent]['source_feature_id'],
                'source_version': anchors[parent]['source_version'],
                'source_sha256': anchors[parent]['source_sha256'],
                'main_island_evidence': anchors[parent]['main_island_evidence'],
                'nearer_unanchored_land': True,
            }
            continue
        if len(targets) > 1:
            out['proposals'].pop(root, None)
            out['review'][root] = 'conflicting_nearest_land_targets'
            continue
        parent = min(nearest)
        code = next(iter(targets))
        out['proposals'][root] = {'code': code, 'basis': 'source_anchored_nearest_main_island'}
        out['review'].pop(root, None)
        out['satellites'][root] = {
            'parent_root_current_generation_only': parent,
            'distance_m': minimum,
            'source_id': anchors[parent]['source_id'],
            'source_feature_id': anchors[parent]['source_feature_id'],
            'source_version': anchors[parent]['source_version'],
            'source_sha256': anchors[parent]['source_sha256'],
            'main_island_evidence': anchors[parent]['main_island_evidence'],
        }
    return out
