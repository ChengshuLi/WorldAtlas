#!/usr/bin/env python3
"""Measure reviewed candidate against an immutable initial cluster comparison.

A zero numerical delta is an acceptance check, never evidence for a selector.
The attribution file is explicitly curated and is not inferred from cell labels.
"""
import argparse
import hashlib
import json
import sqlite3
import shutil
import sys
from pathlib import Path

import numpy as np
import cluster
from cluster import digest, grid, pin, row


def reconcile(cluster_directory, original_config, post_config, output):
    cluster_directory, original_config, post_config, output = map(lambda p: Path(p).resolve(), (cluster_directory, original_config, post_config, output))
    manifest_path = cluster_directory / 'report.json'
    code_sha=digest(__file__); cluster_code_sha=digest(cluster.__file__)
    raw_manifest = manifest_path.read_bytes()
    manifest = json.loads(raw_manifest)
    database = cluster_directory / 'clusters.sqlite'
    raw_original = original_config.read_bytes()
    if (manifest.get('schema') != 'list1-land-clusters-report-v1'
        or manifest.get('status') != 'diagnostic-complete-not-an-override'
        or hashlib.sha256(raw_original).hexdigest() != manifest['config_sha256']
        or digest(database) != manifest['database_sha256']):
        raise ValueError('initial comparison integrity failure')
    orig = json.loads(raw_original)
    raw_post = post_config.read_bytes()
    cfg = json.loads(raw_post)
    if set(cfg) != {'schema', 'post_rows', 'post_runs', 'post_report', 'post_snapshot', 'list1_render', 'cluster_links', 'minimum_free_bytes'} or cfg['schema'] != 'list1-land-reconciliation-config-v1':
        raise ValueError('invalid reconciliation config')
    original_names = ('candidate_rows', 'candidate_runs', 'reference_rows', 'reference_runs', 'physical_rows', 'physical_runs')
    paths = {n: pin(orig[n]) for n in original_names}
    post = {n: pin(cfg[n]) for n in ('post_rows', 'post_runs', 'post_report', 'post_snapshot', 'list1_render', 'cluster_links')}
    for spec in orig['provenance'].values(): pin(spec)
    if type(cfg['minimum_free_bytes']) is not int or cfg['minimum_free_bytes'] < 0: raise ValueError('invalid minimum free space')
    report = json.loads(post['post_report'].read_bytes())
    snapshot = json.loads(post['post_snapshot'].read_bytes())
    decision = snapshot.get('decision_revision', {})
    entity_revision = snapshot.get('entity_revision', {})
    compiler = report.get('compiler_report', {})
    if (report.get('schema') not in ('direct-neon-land-build-report-v1','direct-neon-land-stream-build-report-v1')
        or report.get('status') != 'unverified-research-not-published' or report.get('snapshot_sha256') != cfg['post_snapshot']['sha256']
        or report.get('decision_revision') != decision.get('id') or report.get('entity_revision') != entity_revision.get('id')
        or snapshot.get('schema') != 'worldatlas-geography-decision-draft-evidence-v1' or snapshot.get('source') != 'neon-export'
        or not decision.get('id') or report.get('decision_revision_asserted_status') != 'draft' or decision.get('status') != 'draft'
        or entity_revision.get('status') != 'draft' or decision.get('entity_revision') != entity_revision.get('id')
        or compiler.get('output_rows_sha256') != cfg['post_rows']['sha256'] or compiler.get('output_runs_sha256') != cfg['post_runs']['sha256']
        or any(compiler.get('input_sha256', {}).get(n) != orig[n]['sha256'] for n in ('physical_rows','physical_runs'))):
        raise ValueError('post-build report does not bind snapshot, outputs and physical inputs')
    rendered = json.loads(post['list1_render'].read_bytes())
    if (rendered.get('schema') != 'worldatlas-new-list1-draft-v1' or rendered.get('status') != 'research-not-published'
        or rendered.get('snapshot_sha256') != cfg['post_snapshot']['sha256'] or rendered.get('build_report_sha256') != cfg['post_report']['sha256']
        or rendered.get('decision_revision') != decision.get('id') or not isinstance(rendered.get('entries'),list)):
        raise ValueError('List 1 render does not bind post snapshot and build')
    entries = {}
    for entry in rendered['entries']:
        eid=entry.get('entry_id'); decisions=entry.get('decisions')
        if not isinstance(eid,str) or not eid or eid in entries or not isinstance(decisions,list): raise ValueError('invalid rendered entries')
        ids=[d.get('affiliation_id') for d in decisions]
        if any(not isinstance(x,str) or not x for x in ids) or len(set(ids))!=len(ids): raise ValueError('invalid rendered decisions')
        entries[eid]=set(ids)
    summary=report.get('decision_summary')
    if not isinstance(summary,list) or any(not isinstance(x,dict) or 'witness_rule_id' in x or not isinstance(x.get('affiliation_id'),str) for x in summary):
        raise ValueError('unsupported or incomplete post-build trace')
    selected=[x['affiliation_id'] for x in summary]
    if len(set(selected))!=len(selected) or set(selected)!=set().union(*entries.values()): raise ValueError('rendered decisions do not match build trace')
    reference_manifest=json.loads(Path(orig['provenance']['reference_manifest']['path']).read_bytes())
    entities={e['id']:e['name'] for e in snapshot.get('entities',[])}
    bindings={b['code']:(entities.get(b['entity_id']),b['physical_class']) for b in snapshot.get('category_bindings',[])}
    reference_classes={c['id']:(c['name'],c['physical_class']) for c in reference_manifest['categories']}
    if (len(bindings) != len(snapshot.get('category_bindings',[])) or len(entities) != len(snapshot.get('entities',[]))
        or bindings != reference_classes or reference_classes.get(1, (None,None))[1] != 'water'):
        raise ValueError('post-build category mappings differ from V7')
    land={c['id'] for c in reference_manifest['categories'] if c['physical_class']=='land'}
    water={c['id'] for c in reference_manifest['categories'] if c['physical_class']=='water'}
    links = json.loads(post['cluster_links'].read_bytes())
    if links.get('schema') != 'list1-cluster-links-v1' or links.get('comparison_sha256') != manifest['comparison_sha256'] or not isinstance(links.get('links'), list):
        raise ValueError('invalid curated cluster links')
    if output.exists() or any(output == p or p.is_relative_to(output) or output.is_relative_to(p.parent) for p in [original_config, post_config, manifest_path, database, *paths.values(), *post.values()]):
        raise ValueError('output must be new and outside input directories')
    w,h = orig['grid']['width'],orig['grid']['height']
    base = grid(paths['candidate_rows'],paths['candidate_runs'],w,h)
    reference = grid(paths['reference_rows'],paths['reference_runs'],w,h)
    result = grid(post['post_rows'],post['post_runs'],w,h)
    output.mkdir(parents=True, exist_ok=False)
    def check_space():
        if shutil.disk_usage(output).free < cfg['minimum_free_bytes']: raise OSError('free disk space below configured floor')
    check_space()
    source = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    out = sqlite3.connect(output/'reconciliation.sqlite')
    try:
        out.executescript('''CREATE TABLE coverage(root INTEGER PRIMARY KEY, explained INTEGER NOT NULL DEFAULT 0, unresolved INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE links(cluster_id TEXT PRIMARY KEY, entry_ids TEXT NOT NULL, decision_ids TEXT NOT NULL, rationale TEXT NOT NULL);''')
        for item in links['links']:
            if (set(item) != {'cluster_id','entry_ids','decision_ids','rationale'} or not isinstance(item['cluster_id'],str)
                or not isinstance(item['entry_ids'],list) or not isinstance(item['decision_ids'],list)
                or any(not isinstance(x,str) or not x for x in item['entry_ids']+item['decision_ids'])
                or len(set(item['entry_ids'])) != len(item['entry_ids']) or len(set(item['decision_ids'])) != len(item['decision_ids'])
                or bool(item['entry_ids']) != bool(item['decision_ids'])
                or not isinstance(item['rationale'],str) or not item['rationale']):
                raise ValueError('invalid cluster attribution')
            if any(e not in entries for e in item['entry_ids']) or not set(item['decision_ids']) <= set().union(*(entries[e] for e in item['entry_ids'])):
                raise ValueError('attribution contains IDs absent from linked rendered entries')
            if not source.execute('SELECT 1 FROM clusters WHERE cluster_id=?',(item['cluster_id'],)).fetchone():
                raise ValueError('link references unknown cluster')
            out.execute('INSERT INTO links VALUES (?,?,?,?)',(item['cluster_id'],json.dumps(item['entry_ids']),json.dumps(item['decision_ids']),item['rationale']))
        counts = {'initial_mismatches':0,'explained_cells':0,'unresolved_cells':0,'extra_changed_shared_land_cells':0,'post_mismatches':0}
        for y in range(h):
            be,bv=row(base,y,w,land|{0}); re,rv=row(reference,y,w,land|water); pe,pv=row(result,y,w,land|{1})
            ends=np.union1d(np.union1d(be,re),pe); starts=np.r_[np.uint32(0),ends[:-1]]
            b=bv[np.searchsorted(be,starts,side='right')]; r=rv[np.searchsorted(re,starts,side='right')]; p=pv[np.searchsorted(pe,starts,side='right')]
            base_land=np.isin(b,list(land)); reference_land=np.isin(r,list(land)); post_land=np.isin(p,list(land))
            if np.any(base_land!=post_land):
                raise ValueError(f'post-build physical mask changed at row {y}')
            lengths=ends.astype(np.int64)-starts.astype(np.int64); shared=base_land&reference_land; before=shared&(b!=r); after=shared&(p!=r)
            counts['initial_mismatches']+=int(lengths[before].sum())
            counts['post_mismatches']+=int(lengths[after].sum())
            counts['extra_changed_shared_land_cells']+=int(lengths[shared&(b==r)&(p!=r)].sum())
            for a,z,ref,root in source.execute('SELECT start,end,reference,root FROM resolved WHERE row=?',(y,)):
                # Post RLE segments overlapping the exact initial mismatch span.
                first=int(np.searchsorted(pe,a,side='right')); last=int(np.searchsorted(pe,z-1,side='right'))
                pos=a; explained=unresolved=0
                for i in range(first,last+1):
                    end=min(z,int(pe[i])); n=end-pos
                    if int(pv[i])==ref: explained+=n
                    else: unresolved+=n
                    pos=end
                if pos!=z: raise ValueError('post RLE span coverage failure')
                out.execute('''INSERT INTO coverage VALUES (?,?,?) ON CONFLICT(root) DO UPDATE SET
                    explained=explained+excluded.explained, unresolved=unresolved+excluded.unresolved''',(root,explained,unresolved))
                counts['explained_cells']+=explained; counts['unresolved_cells']+=unresolved
            if y%1000==999:
                out.commit(); check_space()
        if (counts['initial_mismatches']!=manifest['counts']['mismatch']
            or counts['explained_cells']+counts['unresolved_cells']!=counts['initial_mismatches']
            or counts['post_mismatches']!=counts['unresolved_cells']+counts['extra_changed_shared_land_cells']):
            raise ValueError('reconciliation accounting failure')
        out.commit()
        unattributed_clusters=unattributed_cells=0
        with (output/'clusters.jsonl').open('x') as f:
            for root,cid,cells in source.execute('SELECT root,cluster_id,cells FROM clusters ORDER BY cluster_id'):
                cov=out.execute('SELECT explained,unresolved FROM coverage WHERE root=?',(root,)).fetchone()
                if cov is None or sum(cov)!=cells: raise ValueError('cluster coverage accounting failure')
                link=out.execute('SELECT entry_ids,decision_ids,rationale FROM links WHERE cluster_id=?',(cid,)).fetchone()
                if not link or not json.loads(link[0]):
                    unattributed_clusters+=1; unattributed_cells+=cells
                f.write(json.dumps({'cluster_id':cid,'cells':cells,'explained_cells':cov[0],'unresolved_cells':cov[1],
                    'entry_ids':json.loads(link[0]) if link else [],'decision_ids':json.loads(link[1]) if link else [],
                    'attribution_note':link[2] if link else 'No attribution supplied; evidence review required.'},sort_keys=True)+'\n')
        out.commit()
        for n in original_names: pin(orig[n])
        for n in post: pin(cfg[n])
        for spec in orig['provenance'].values(): pin(spec)
        if (manifest_path.read_bytes()!=raw_manifest or original_config.read_bytes()!=raw_original or post_config.read_bytes()!=raw_post or digest(database)!=manifest['database_sha256'] or digest(__file__)!=code_sha or digest(cluster.__file__)!=cluster_code_sha):
            raise ValueError('input changed during reconciliation')
        result_report={'schema':'list1-land-reconciliation-report-v1','status':'numerical-reconciliation-only',
            'comparison_sha256':manifest['comparison_sha256'],'initial_report_sha256':hashlib.sha256(raw_manifest).hexdigest(),
            'post_config_sha256':hashlib.sha256(raw_post).hexdigest(),'post_report_sha256':cfg['post_report']['sha256'],
            'cluster_links_sha256':cfg['cluster_links']['sha256'],'list1_render_sha256':cfg['list1_render']['sha256'],'post_snapshot_sha256':cfg['post_snapshot']['sha256'],'counts':counts,'initial_physical_disagreements':{
                'candidate_land_reference_water':manifest['counts']['candidate_land_reference_water'],
                'candidate_water_reference_land':manifest['counts']['candidate_water_reference_land']},
            'unattributed_clusters':unattributed_clusters,'unattributed_initial_cells':unattributed_cells,
            'numerical_acceptance':counts['unresolved_cells']==0 and counts['extra_changed_shared_land_cells']==0,
            'clusters_jsonl_sha256':digest(output/'clusters.jsonl'),'code_sha256':code_sha,'cluster_code_sha256':cluster_code_sha,
            'limitations':['Numerical acceptance does not prove geographic source support or decision attribution.',
                'Explicit curated links must be verified against selected decisions and source evidence; this tool does not infer them.',
                'Decision conflicts and extra changes outside shared land require independent review.']}
        with (output/'report.json').open('x') as f: json.dump(result_report,f,indent=2,sort_keys=True); f.write('\n')
        return result_report
    finally:
        source.close();out.close()


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('cluster_directory');ap.add_argument('original_config');ap.add_argument('post_config');ap.add_argument('output_directory')
    args=ap.parse_args()
    try: print(json.dumps(reconcile(args.cluster_directory,args.original_config,args.post_config,args.output_directory),indent=2))
    except Exception as exc: print('error: '+str(exc),file=sys.stderr); raise SystemExit(1)
