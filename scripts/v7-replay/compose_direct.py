#!/usr/bin/env python3
"""Compose an unverified direct research grid without reading prior continent grids."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import compose_full_water_grid as c
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exclusive_outputs import create_binary_exclusive, create_directory_exclusive, write_json_exclusive


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--input-root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--allow-unverified-snapshot', action='store_true')
    ap.add_argument('--allow-draft-snapshot', action='store_true')
    ap.add_argument('--allow-research-shore', action='store_true', help='research only: allow the unapproved WGS84 coastal land-cell-center method')
    a = ap.parse_args()
    if not a.allow_unverified_snapshot:
        raise ValueError('snapshot authentication is not implemented; research opt-in required')
    root, plan_path, out = a.input_root.resolve(), a.plan.resolve(), a.out.resolve()
    if not root.is_dir() or out.is_relative_to(root) or root.is_relative_to(out) or plan_path.is_relative_to(out):
        raise ValueError('output must be outside the input tree and must not contain the plan')
    raw_plan = plan_path.read_bytes(); plan = json.loads(raw_plan)
    if plan.get('schema') != 'worldatlas-direct-final-plan-v1' or plan.get('grid') != {'width': c.W, 'height': c.H}:
        raise ValueError('wrong plan schema or grid')
    digest=plan.get('decision_snapshot_sha256')
    if (not isinstance(digest,str) or len(digest)!=64 or any(ch not in '0123456789abcdef' for ch in digest)
            or any(not isinstance(plan.get(k),str) or not plan[k].strip() for k in ('decision_revision','entity_revision'))):
        raise ValueError('valid decision digest and revision IDs required')
    if plan.get('decision_revision_status') not in ('accepted', 'draft'):
        raise ValueError('decision revision status required')
    if plan['decision_revision_status'] == 'draft' and not a.allow_draft_snapshot:
        raise ValueError('draft plan requires explicit research opt-in')
    spec = plan['prefill']
    def pinned(key):
        path = c.resolve_input(spec[key + '_path'], plan_path.parent, root)
        if c.sha256(path) != spec[key + '_sha256']:
            raise ValueError(f'prefill {key} hash mismatch')
        return path
    rows_path, runs_path, audit_path, prefill_plan_path = (pinned(k) for k in ('rows', 'runs', 'audit', 'plan'))
    audit = json.loads(audit_path.read_text())
    if (audit.get('schema') != 'worldatlas-v7-prefill-class-rle-audit-v1'
            or audit.get('status') != 'staged-not-published'
            or audit.get('land_input_kind') != 'direct-research'
            or audit.get('source_plan_sha256') != spec['plan_sha256']
            or audit.get('decision_snapshot_sha256') != plan.get('decision_snapshot_sha256')
            or audit.get('decision_revision') != plan.get('decision_revision')
            or audit.get('entity_revision') != plan.get('entity_revision')
            or audit.get('output', {}).get('rows_sha256') != spec['rows_sha256']
            or audit.get('output', {}).get('runs_sha256') != spec['runs_sha256']):
        raise ValueError('prefill audit does not match direct plan')
    prefill_plan = json.loads(prefill_plan_path.read_text())
    if (prefill_plan.get('land_input_kind') != 'direct-research'
            or prefill_plan.get('decision_revision_status') != plan['decision_revision_status']
            or prefill_plan.get('decision_snapshot_sha256') != plan.get('decision_snapshot_sha256')
            or prefill_plan.get('decision_revision') != plan.get('decision_revision')
            or prefill_plan.get('entity_revision') != plan.get('entity_revision')
            or prefill_plan.get('research_shore_method') != audit.get('research_shore_method')):
        raise ValueError('prefill plan decision binding mismatch')
    method=prefill_plan.get('research_shore_method')
    if method is not None and (method!='wgs84-coastal-4neighbor-center-v2' or not a.allow_research_shore):
        raise ValueError('WGS84 research shore method requires explicit opt-in; retired or unknown methods are rejected')
    def validate_shore_manifest(manifest):
        source=manifest.get('source') or {};nearest=manifest.get('nearest_assignment_audit')
        if source.get('assignment_method')=='shared_nearest_assigned_shore' or nearest is not None:
            if (source.get('assignment_method')!='shared_nearest_assigned_shore'
                    or method!='wgs84-coastal-4neighbor-center-v2'
                    or not a.allow_research_shore
                    or not isinstance(nearest,dict)
                    or nearest.get('shore_method')!='wgs84-coastal-4neighbor-center-v2 (research, not an approved decision)'
                    or any(key in nearest for key in ('execution_method','interval_nearest_sha256','interval_certified_cells'))):
                raise ValueError('shared-shore manifest does not bind the WGS84 research method')
    for entry in prefill_plan.get('water_layers',[]):
        _, prefill_manifest=c.read_pinned_manifest(entry,prefill_plan_path,root)
        validate_shore_manifest(prefill_manifest)
    rows, runs = c.open_validated_rle(rows_path, runs_path, 'prefill')
    layers = []
    ids = set()
    for entry in plan.get('water_layers', []):
        ident = entry.get('layer_id'); allowed = entry.get('allowed_codes')
        if (not isinstance(ident, str) or not ident or ident in ids or type(entry.get('priority')) is not int
                or not isinstance(entry.get('overrides'), list) or not isinstance(allowed, list)
                or not allowed or len(set(allowed)) != len(allowed)
                or any(type(x) is not int or x not in range(1, 11) for x in allowed)):
            raise ValueError('invalid water layer descriptor')
        ids.add(ident)
        _, manifest = c.read_pinned_manifest(entry, plan_path, root)
        source = manifest.get('source', {})
        validate_shore_manifest(manifest)
        if (manifest.get('coverage', {}).get('complete') is not True
                or source.get('prefill_rows_sha256') != spec['rows_sha256']
                or source.get('prefill_runs_sha256') != spec['runs_sha256']
                or source.get('decision_snapshot_sha256') != plan.get('decision_snapshot_sha256')
                or source.get('decision_revision') != plan.get('decision_revision')
                or source.get('entity_revision') != plan.get('entity_revision')):
            raise ValueError(f'water layer not bound to direct prefill: {ident}')
        manifest['_tiles'] = manifest['tiles']
        layers.append((entry, c.RowCursor(manifest, 0, c.H, 'water')))
    for entry, _ in layers:
        if any(x not in ids or x == entry['layer_id'] for x in entry['overrides']):
            raise ValueError('unknown or self-referential override')
    create_directory_exclusive(out)
    counts = {str(i): 0 for i in list(range(1, 11)) + list(range(17, 23))}
    nrun = 0
    with create_binary_exclusive(out/'rows.u32le') as yf, create_binary_exclusive(out/'runs.u32le') as rf:
        yf.write(np.asarray([0], dtype='<u4').tobytes())
        for y in range(c.H):
            ends, values = c.rle_row(rows, runs, y)
            if (not len(ends) or int(ends[0]) == 0 or int(ends[-1]) != c.W
                    or np.any(ends[1:] <= ends[:-1])
                    or np.any(~np.isin(values, [0,1,2,3,4,5,6,17,18,19,20,21,22]))):
                raise ValueError(f'invalid direct prefill row {y}')
            physical = np.where(values >= 17, 17, 1)
            spans = []
            for entry, cursor in layers:
                items = cursor.take(y)
                if any(item[3] not in entry['allowed_codes'] for item in items):
                    raise ValueError(f"water layer code outside allowed set: {entry['layer_id']}")
                spans.extend(c.add_layer_identity(items, entry['priority'], entry['layer_id'], set(entry['overrides'])))
            assignments, _ = c.choose_assignments(spans, y, ends, physical)
            cuts = {0, c.W}; cuts.update(map(int, ends))
            for x0,x1,_,_,_ in assignments: cuts.update((x0,x1))
            cuts = np.array(sorted(cuts), dtype=np.uint32); starts, stops = cuts[:-1], cuts[1:]
            prior = c.row_code_at(ends, values, starts); output = np.empty(len(starts), dtype=np.uint8); i = 0
            for j, x in enumerate(starts.tolist()):
                while i < len(assignments) and assignments[i][1] <= x: i += 1
                assigned = assignments[i] if i < len(assignments) and assignments[i][0] <= x < assignments[i][1] else None
                if assigned is not None and prior[j] != 0:
                    raise ValueError(f'water layer overlaps an already assigned prefill cell at {y}:{x}')
                if prior[j] == 0 and assigned is None:
                    raise ValueError(f'unassigned water at {y}:{x}')
                output[j] = assigned[2] if assigned is not None else prior[j]
            lengths = (stops-starts).astype(np.uint64)
            for value in np.unique(output): counts[str(int(value))] += int(lengths[output == value].sum())
            groups = np.flatnonzero(np.r_[True, output[1:] != output[:-1]])
            next_groups = np.r_[groups[1:], len(output)]
            pairs = np.column_stack((stops[next_groups-1], output[groups])).astype('<u4')
            pairs.tofile(rf); nrun += len(pairs)
            if nrun > np.iinfo(np.uint32).max: raise ValueError('too many output runs')
            yf.write(np.asarray([nrun], dtype='<u4').tobytes())
    for k in ('rows','runs','audit','plan'): pinned(k)
    if plan_path.read_bytes() != raw_plan: raise ValueError('final plan changed during composition')
    for entry, _ in layers: c.read_pinned_manifest(entry, plan_path, root)
    report = {'schema':'worldatlas-direct-final-audit-v1', 'status':'unverified-research-not-published',
              'decision_snapshot_sha256':plan.get('decision_snapshot_sha256'), 'decision_revision':plan.get('decision_revision'),
              'decision_revision_status':plan['decision_revision_status'], 'entity_revision':plan.get('entity_revision'),
              'final_plan_sha256':c.sha256(plan_path), 'prefill_audit_sha256':spec['audit_sha256'],
              'counts':counts, 'run_count':nrun,
              'output':{'rows_sha256':c.sha256(out/'rows.u32le'), 'runs_sha256':c.sha256(out/'runs.u32le')},
              'limitations':'Research composition only; source coverage, geographic decisions and snapshot authority require independent verification.'}
    write_json_exclusive(out/'report.json', report, indent=2)
    print(json.dumps(report, indent=2))

if __name__ == '__main__': main()

