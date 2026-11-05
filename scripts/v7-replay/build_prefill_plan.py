#!/usr/bin/env python3
"""Assemble a pinned prefill plan from the selected basin policies and fresh inputs."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exclusive_outputs import write_json_exclusive
from decision_snapshot import read_snapshot, validate_revision, participant_water_codes, find_source
import compose_full_water_grid as c


def input_path(value, config_path, root):
    path = Path(value)
    if not path.is_absolute():
        path = config_path.parent / path
    path = path.resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f'input missing or outside input root: {path}')
    return path


def require_selected_policy(policy, record):
    if policy.get('decision_revision', {}).get('status') == 'draft':
        evidence = record.get('evidence')
        if not isinstance(evidence, dict) or evidence.get('execution_status') != 'selected_for_research':
            raise ValueError('draft policy requires explicit research selection')


def layer_precedence(policy, layer_ids):
    records = [p for p in policy.get('policies', []) if p.get('kind') == 'layer_precedence']
    if len(records) != 1 or not isinstance(records[0].get('definition'), dict):
        raise ValueError('exactly one layer precedence decision is required')
    require_selected_policy(policy, records[0])
    definition = records[0]['definition']; priorities = definition.get('priorities'); overrides = definition.get('allowed_overrides')
    if (not isinstance(priorities, dict) or set(priorities) != set(layer_ids)
            or any(type(p) is not int for p in priorities.values())):
        raise ValueError('precedence priorities must exactly cover the selected layers')
    if not isinstance(overrides, list):
        raise ValueError('explicit allowed overrides are required')
    result = {layer: [] for layer in layer_ids}; seen = set()
    for rule in overrides:
        if not isinstance(rule, dict) or set(rule) != {'winner', 'loser'}:
            raise ValueError('invalid allowed override')
        winner, loser = rule['winner'], rule['loser']
        if (not isinstance(winner, str) or not isinstance(loser, str) or winner not in priorities
                or loser not in priorities or priorities[winner] <= priorities[loser] or (winner, loser) in seen):
            raise ValueError('invalid allowed override')
        seen.add((winner, loser)); result[winner].append(loser)
    return priorities, result


def coastline_policy(policy):
    records = [p for p in policy.get('policies', []) if p.get('kind') == 'coastline_assignment']
    if len(records) != 1 or not isinstance(records[0].get('id'), str) or not records[0]['id'].strip():
        raise ValueError('exactly one identified coastline assignment decision is required')
    require_selected_policy(policy, records[0])
    definition = records[0].get('definition')
    if isinstance(definition, dict) and definition.get('method') == 'nearest_final_shore_band_v2':
        if policy.get('decision_revision',{}).get('status') != 'draft':
            raise ValueError('derived coastline method is draft research only')
        import coastal_core
        coastal_core.policy(policy, allow_selected_research=True)
        return records[0], None
    if (not isinstance(definition, dict) or not isinstance(definition.get('source_id'), str)
            or not definition['source_id'] or not isinstance(definition.get('source_version'), str)
            or not definition['source_version'] or not isinstance(definition.get('method'), str)
            or not definition['method'] or not isinstance(definition.get('parameters'), dict)):
        raise ValueError('invalid coastline assignment decision')
    return records[0], find_source(policy, definition)


def canonical_physical_grid():
    return {'width':c.W, 'height':c.H, 'step':360.0/c.W, 'west':-180, 'north':90}


def validate_physical_report(report, physical):
    output=report.get('physical_output_sha256',report.get('output_sha256',{}))
    if (report.get('status') != 'candidate-only' or report.get('grid') != canonical_physical_grid()
            or output.get('rows.u32le') != physical['rows_sha256'] or output.get('runs.u32le') != physical['runs_sha256']
            or (physical.get('physical_mask_sha256') and output.get('physical-dry.tif') != physical['physical_mask_sha256'])):
        raise ValueError('physical report does not bind the canonical grid and streams')


def validate_land_report(report, report_path, physical, land, snapshot_hash, revision, input_root=None):
    """Bind research land output to its physical grid and snapshot.

    The same-run manifest path is a research lineage assertion, not independent
    connectivity verification or authentication of source provenance.
    """
    if report.get('schema') == 'single-generation-nearest-report-v1':
        raise ValueError('retired spherical nearest-land reports cannot drive new builds')
    digest = lambda value: isinstance(value, str) and len(value) == 64 and all(ch in '0123456789abcdef' for ch in value)
    stream = report.get('schema') == 'single-generation-direct-land-report-v1'
    if stream:
        if input_root is None: raise ValueError('input root required for streaming land lineage')
        root = Path(input_root).resolve(); base = report_path.parent.resolve()
        nested_path = (base/'assignment/report.json').resolve(); manifest_path = (base/'manifests/components.json').resolve()
        request_path = (base/'request.json').resolve()
        if any(not path.is_relative_to(root) for path in (nested_path,manifest_path,request_path)):
            raise ValueError('streaming land lineage escapes input root')
        code_hashes=report.get('code_sha256',{})
        if (not isinstance(code_hashes,dict) or set(code_hashes) != {'runner','compiler','stream_backend','shared_backend'} or not all(digest(x) for x in code_hashes.values())
                or report.get('status') != 'unverified-research-not-published' or report.get('component_generations') != 1
                or report.get('snapshot_sha256') != snapshot_hash
                or report.get('output_rows_sha256') != land['rows_sha256'] or report.get('output_runs_sha256') != land['runs_sha256']
                or c.sha256(nested_path) != report.get('land_report_sha256')
                or c.sha256(manifest_path) != report.get('component_manifest_sha256')
                or c.sha256(request_path) != report.get('request_sha256')):
            raise ValueError('streaming land orchestration report mismatch')
        nested=json.loads(nested_path.read_text());manifest=json.loads(manifest_path.read_text());request=json.loads(request_path.read_text())
        gen=nested.get('component_generation',{});mpins=manifest.get('pins',{});physical_report=manifest.get('physical_report',{})
        physical_report_path=Path(physical_report.get('path','')).resolve()
        if not physical_report_path.is_relative_to(root) or not physical_report_path.is_file():
            raise ValueError('streaming physical report escapes input root or is missing')
        if (not digest(physical_report.get('sha256')) or c.sha256(physical_report_path) != physical_report['sha256']
                or physical_report != request.get('physical_report')
                or physical_report['sha256'] != report.get('physical_report_sha256')
                or physical_report['sha256'] != gen.get('physical_report_sha256')):
            raise ValueError('streaming physical report pin mismatch')
        for entry in (mpins.get('component_rows',{}),mpins.get('component_runs',{}),manifest.get('builder_binary',{})):
            artifact=Path(entry.get('path','')).resolve()
            if (not artifact.is_relative_to(root) or not artifact.is_file() or not digest(entry.get('sha256'))
                    or c.sha256(artifact) != entry['sha256']):
                raise ValueError('streaming component artifact missing, outside input root or hash mismatch')
        physical_doc=json.loads(physical_report_path.read_text()); output=physical_doc.get('physical_output_sha256',physical_doc.get('output_sha256',{}))
        kind='raw-pipeline-report' if all(k in physical_doc for k in ('physical_output_sha256','source_manifest','land_config','water_config','stage_reports')) else 'compose-report'
        if (physical_doc.get('status') != 'candidate-only' or physical_doc.get('grid') != manifest.get('grid')
                or manifest.get('grid') != canonical_physical_grid()
                or output.get('rows.u32le') != physical['rows_sha256'] or output.get('runs.u32le') != physical['runs_sha256']
                or report.get('physical_report_kind') != kind or gen.get('physical_report_kind') != kind or manifest.get('physical_report_kind') != kind
                or manifest.get('schema') != 'single-generation-component-manifest-v1' or manifest.get('status') != 'complete-research'
                or gen.get('method') != 'single-generation-manifest' or gen.get('manifest_sha256') != report.get('component_manifest_sha256')
                or gen.get('builder_source_sha256') != manifest.get('component_source_sha256')
                or gen.get('builder_binary_sha256') != manifest.get('builder_binary_sha256')
                or manifest.get('builder_binary',{}).get('sha256') != manifest.get('builder_binary_sha256')
                or code_hashes.get('compiler') != nested.get('program_sha256')
                or code_hashes.get('stream_backend') != nested.get('compiler_report',{}).get('program_sha256')
                or gen.get('compiler_version') != manifest.get('compiler_version') or gen.get('builder_output') != manifest.get('builder_output')
                or request.get('snapshot',{}).get('sha256') != snapshot_hash or request.get('grid') != manifest.get('grid')
                or request.get('component_source_sha256') != gen.get('builder_source_sha256')
                or gen.get('rows_sha256') != mpins.get('component_rows',{}).get('sha256')
                or gen.get('runs_sha256') != mpins.get('component_runs',{}).get('sha256')
                or any(request.get(k,{}).get('sha256') != physical[k.replace('physical_','')+'_sha256'] for k in ('physical_rows','physical_runs'))
                or any(mpins.get(k,{}).get('sha256') != physical[k.replace('physical_','')+'_sha256'] for k in ('physical_rows','physical_runs'))
                or (physical.get('physical_mask_sha256') and output.get('physical-dry.tif') != physical['physical_mask_sha256'])):
            raise ValueError('streaming land manifest does not bind physical grid and snapshot')
        verified=gen; report=nested; expected_schema='direct-neon-land-stream-build-report-v1'; compiler_schema='land-streaming-research-report-v1'
        expected_rows=(base/'assignment/land/rows.u32le').resolve();expected_runs=(base/'assignment/land/runs.u32le').resolve()
    else:
        config_path=(report_path.parent/'config.json').resolve()
        if input_root is None or not config_path.is_relative_to(Path(input_root).resolve()) or not config_path.is_file():
            raise ValueError('direct land configuration missing or outside input root')
        if c.sha256(config_path) != report.get('config_sha256'):
            raise ValueError('direct land configuration hash mismatch')
        config=json.loads(config_path.read_text())
        verified=report.get('component_verification',{})
        for name,key in (('component-builder','builder_binary_sha256'),('verified-component-rows.u32le','rows_sha256'),('verified-component-runs.u32le','runs_sha256')):
            artifact=(report_path.parent/name).resolve()
            if (not artifact.is_relative_to(Path(input_root).resolve()) or not artifact.is_file()
                    or not digest(verified.get(key)) or c.sha256(artifact) != verified[key]):
                raise ValueError('independent component artifact missing, outside input root or hash mismatch')
        if (config.get('grid') != canonical_physical_grid() or config.get('snapshot',{}).get('sha256') != snapshot_hash
                or config.get('physical_rows',{}).get('sha256') != physical['rows_sha256']
                or config.get('physical_runs',{}).get('sha256') != physical['runs_sha256']):
            raise ValueError('direct land configuration grid or input mismatch')
        verified=report.get('component_verification',{});expected_schema='direct-neon-land-build-report-v1';compiler_schema='land-decision-compiler-prototype-report-v1'
        expected_rows=(report_path.parent/'land/rows.u32le').resolve();expected_runs=(report_path.parent/'land/runs.u32le').resolve()
    comp = report.get('compiler_report', {}); pins = comp.get('input_sha256', {})
    if (not all(digest(verified.get(k)) for k in ('builder_source_sha256', 'builder_binary_sha256', 'rows_sha256', 'runs_sha256'))
            or not verified.get('compiler_version') or not verified.get('builder_output')
            or verified.get('rows_sha256') != pins.get('component_rows') or verified.get('runs_sha256') != pins.get('component_runs')
            or report.get('schema') != expected_schema or report.get('status') != 'unverified-research-not-published'
            or report.get('snapshot_sha256') != snapshot_hash or report.get('decision_revision') != revision.get('id')
            or report.get('decision_revision_asserted_status') != revision.get('status') or report.get('entity_revision') != revision.get('entity_revision')
            or comp.get('schema') != compiler_schema or pins.get('physical_rows') != physical['rows_sha256']
            or pins.get('physical_runs') != physical['runs_sha256'] or comp.get('output_rows_sha256') != land['rows_sha256']
            or comp.get('output_runs_sha256') != land['runs_sha256']):
        raise ValueError('direct land report does not bind this snapshot and physical grid')
    if land['resolved_rows'] != expected_rows or land['resolved_runs'] != expected_runs:
        raise ValueError('direct land outputs do not match report location')


def assemble(config, config_path, root, policy, policy_path, out, allow_draft=False, allow_research_shore=False, allow_historical_v6=False):
    revision = validate_revision(policy, allow_draft=allow_draft)
    selected = policy.get('basins', [])
    methods = {row.get('assignment_method') for row in selected}
    if methods - {'single_continent_named_basin', 'shared_nearest_assigned_shore'}:
        raise ValueError('unsupported basin assignment method or tie rules')
    shared = 'shared_nearest_assigned_shore' in methods
    if shared and (not allow_research_shore or revision['status'] != 'draft'):
        raise ValueError('shared shoreline metric requires explicit draft research opt-in')
    by_id = {str(row['id']): row for row in selected}
    expected = set(by_id)
    if not expected or len(expected) != len(selected):
        raise ValueError('invalid selected basin set')
    incoming = config.get('basins', [])
    provided = [str(row['decision_id']) for row in incoming]
    if len(provided) != len(set(provided)) or set(provided) != expected:
        raise ValueError('basin input IDs must exactly match selected decisions')
    def rel(path):
        return os.path.relpath(path, out.parent)
    rles = {}
    land_key = 'land' if 'land' in config['rle_inputs'] else 'v6'
    if set(config['rle_inputs']) != {'physical', land_key}:
        raise ValueError('exactly one direct land or historical v6 grid is required')
    if land_key == 'v6' and not allow_historical_v6:
        raise ValueError('historical V6 replay requires explicit opt-in')
    for key in ('physical', land_key):
        source = config['rle_inputs'][key]
        rows = input_path(source['rows_path'], config_path, root)
        runs = input_path(source['runs_path'], config_path, root)
        if c.sha256(rows) != source['rows_sha256'] or c.sha256(runs) != source['runs_sha256']:
            raise ValueError(f'{key} grid hash mismatch')
        rles[key] = {'rows_path':rel(rows), 'runs_path':rel(runs), 'rows_sha256':source['rows_sha256'], 'runs_sha256':source['runs_sha256']}
        if source.get('physical_mask_sha256'):
            rles[key]['physical_mask_sha256'] = source['physical_mask_sha256']
    if shared and land_key != 'land':
        raise ValueError('shared basins require direct decision-derived land')
    if land_key == 'land':
        source = config['rle_inputs']['land']
        report_path = input_path(source['report_path'], config_path, root)
        if c.sha256(report_path) != source['report_sha256']:
            raise ValueError('direct land report hash mismatch')
        land = {**rles['land'], 'resolved_rows':input_path(source['rows_path'], config_path, root),
                'resolved_runs':input_path(source['runs_path'], config_path, root)}
        validate_land_report(json.loads(report_path.read_text()), report_path, rles['physical'],
                             land, c.sha256(policy_path), revision, root)
        rles['land']['report_path'] = rel(report_path)
        rles['land']['report_sha256'] = source['report_sha256']
    def validate_manifest(rec):
        path = input_path(rec['manifest_path'], config_path, root)
        if c.sha256(path) != rec['manifest_sha256']:
            raise ValueError(f'manifest hash mismatch: {path}')
        manifest = c.read_manifest(path, root)
        if manifest.get('coverage', {}).get('complete') is not True:
            raise ValueError(f'manifest does not declare complete coverage: {path}')
        return path, manifest
    coast = config['coastal_band']
    coast_path, coast_manifest = validate_manifest(coast)
    coast_source = coast_manifest.get('source', {}); physical = rles['physical']
    coast_decision, coast_catalog = coastline_policy(policy); coast_definition = coast_decision['definition']
    if coast_catalog is None:
        if land_key != 'land': raise ValueError('derived coastline requires direct land')
        physical_source=config['rle_inputs']['physical']
        physical_report_path=input_path(physical_source['report_path'],config_path,root)
        if c.sha256(physical_report_path)!=physical_source['report_sha256']:
            raise ValueError('physical report hash mismatch')
        validate_physical_report(json.loads(physical_report_path.read_text()),physical)
        physical['report_path']=rel(physical_report_path);physical['report_sha256']=physical_source['report_sha256']
        if (coast_source.get('decision_id') != coast_decision['id'] or coast_source.get('policy_definition') != coast_definition
                or coast_source.get('physical_report_sha256') != physical['report_sha256']
                or coast_source.get('land_rows_sha256') != rles['land']['rows_sha256']
                or coast_source.get('land_runs_sha256') != rles['land']['runs_sha256']
                or coast_source.get('land_report_sha256') != rles['land']['report_sha256']):
            raise ValueError('derived coastal manifest policy or land/physical lineage mismatch')
    elif (coast_source.get('decision_id') != coast_decision['id']
            or coast_source.get('source_id') != coast_definition['source_id']
            or coast_source.get('source_version') != coast_definition['source_version']
            or coast_source.get('source_file_sha256') != coast_catalog['sha256']
            or coast_source.get('assignment_method') != coast_definition['method']
            or coast_source.get('parameters') != coast_definition['parameters']):
        raise ValueError('coastal manifest source or assignment decision mismatch')
    if (coast_source.get('decision_revision') != revision['id']
            or coast_source.get('entity_revision') != revision['entity_revision']
            or coast_source.get('policy_sha256') != c.sha256(policy_path)
            or coast_source.get('physical_rows_sha256') != physical['rows_sha256']
            or coast_source.get('physical_runs_sha256') != physical['runs_sha256']):
        raise ValueError('coastal manifest decision or physical grid mismatch')
    layer_ids = ['coastal-band'] + [f'named-{sid}' for sid in sorted(expected)]
    priorities, overrides = layer_precedence(policy, layer_ids)
    layers = [{'layer_id':'coastal-band','manifest_path':rel(coast_path),'manifest_sha256':coast['manifest_sha256'],'priority':priorities['coastal-band'],'overrides':overrides['coastal-band']}]
    for entry in sorted(incoming, key=lambda x: str(x['decision_id'])):
        sid = str(entry['decision_id']); path, manifest = validate_manifest(entry)
        basin = by_id[sid]; source = manifest.get('source', {}); physical = rles['physical']
        expected_source = find_source(policy, basin)
        if (source.get('decision_id') != sid or not basin.get('assignment_method')
                or source.get('assignment_method') != basin['assignment_method']
                or source.get('source_id') != basin.get('source_id')
                or source.get('source_version') != basin.get('source_version')
                or str(source.get('source_feature_id')) != str(basin.get('source_feature_id'))
                or source.get('source_file_sha256') != expected_source['sha256']):
            raise ValueError(f'manifest source does not match selected decision: {sid}')
        if not basin.get('geometry_sha256') or source.get('canonical_geometry_sha256') != basin['geometry_sha256']:
            raise ValueError(f'manifest source geometry is not pinned by decision: {sid}')
        if (source.get('policy_sha256') != c.sha256(policy_path) or source.get('decision_revision') != revision['id']
                or source.get('entity_revision') != revision['entity_revision']):
            raise ValueError(f'manifest decision snapshot mismatch: {sid}')
        if source.get('physical_rows_sha256') != physical['rows_sha256'] or source.get('physical_runs_sha256') != physical['runs_sha256']:
            raise ValueError(f'manifest physical grid mismatch: {sid}')
        allowed = participant_water_codes(policy, basin)
        if basin['assignment_method'] == 'shared_nearest_assigned_shore':
            from shared_nearest import selected_rules
            selected_rules(policy, basin)  # Validate participant bindings and exact tie policy.
            audit = manifest.get('nearest_assignment_audit') or {}
            count = manifest.get('physical_water_cells')
            certified, exact = audit.get('certified_bound_cells'), audit.get('exact_distance_cells')
            hashes = (manifest.get('algorithm_sha256'), audit.get('shared_nearest_sha256'), audit.get('shore_geometry_sha256'))
            valid_hash = lambda value: isinstance(value, str) and len(value) == 64 and all(ch in '0123456789abcdef' for ch in value)
            if (source.get('land_rows_sha256') != rles['land']['rows_sha256']
                    or source.get('land_runs_sha256') != rles['land']['runs_sha256']
                    or source.get('decision_status') != revision['status']
                    or source.get('tie_rules') != basin.get('tie_rules')
                    or audit.get('shore_method') != 'wgs84-coastal-4neighbor-center-v2 (research, not an approved decision)'
                    or type(count) is not int or count < 0 or type(certified) is not int or certified < 0
                    or type(exact) is not int or exact < 0 or certified + exact != count
                    or not all(valid_hash(x) for x in hashes)):
                raise ValueError(f'shared basin research method or land binding mismatch: {sid}')
        layer_id = f'named-{sid}'
        layers.append({'layer_id':layer_id,'manifest_path':rel(path),'manifest_sha256':entry['manifest_sha256'],
                       'priority':priorities[layer_id],'overrides':overrides[layer_id],'allowed_codes':allowed})
    return {'schema':'worldatlas-v7-full-grid-composition-plan-v1', 'status':'fresh-prefill-unverified-test-candidate',
            'purpose':'Fresh selected named basins and coast, with residual marine water code 0.',
            'land_input_kind':'direct-research' if land_key == 'land' else 'historical-v6-replay',
            'research_shore_method': 'wgs84-coastal-4neighbor-center-v2' if shared else None,
            'grid':{'width':c.W,'height':c.H}, 'rle_inputs':rles, 'water_layers':layers,
            'decision_snapshot_sha256':c.sha256(policy_path), 'decision_revision':revision['id'], 'decision_revision_status':revision['status'], 'entity_revision':revision['entity_revision'],
            'precedence':'As specified by the revisioned layer-precedence decision; undeclared overlaps fail.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input-root', type=Path, required=True); ap.add_argument('--inputs', type=Path, required=True)
    ap.add_argument('--policy', type=Path, required=True); ap.add_argument('--policy-sha256', required=True)
    ap.add_argument('--allow-unverified-snapshot', action='store_true', help='test only: Neon acceptance cannot yet be authenticated by this tool')
    ap.add_argument('--allow-draft-snapshot', action='store_true', help='research only: allow explicitly draft Neon evidence')
    ap.add_argument('--allow-research-shore', action='store_true', help='research only: allow the unapproved WGS84 coastal land-cell-center method')
    ap.add_argument('--allow-historical-v6', action='store_true', help='historical replay only: permit the V6 land grid')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if not args.allow_unverified_snapshot:
        raise ValueError('authenticated Neon revision verification is not implemented; explicit test-only flag required')
    root=args.input_root.resolve(); config_path=args.inputs.resolve(); policy_path=args.policy.resolve(); out=args.out.resolve()
    if not root.is_dir() or not config_path.is_relative_to(root):
        raise ValueError('input configuration must be inside the input root')
    if out.is_relative_to(root) or root.is_relative_to(out):
        raise ValueError('plan must be outside the input root')
    policy=read_snapshot(policy_path,args.policy_sha256,allow_draft=args.allow_draft_snapshot)
    config=json.loads(config_path.read_text())
    plan=assemble(config,config_path,root,policy,policy_path,out,allow_draft=args.allow_draft_snapshot,allow_research_shore=args.allow_research_shore,allow_historical_v6=args.allow_historical_v6)
    write_json_exclusive(out,plan,indent=2)
    print(json.dumps({'plan':str(out),'sha256':c.sha256(out),'layers':len(plan['water_layers'])}))


if __name__ == '__main__':
    main()
