#!/usr/bin/env python3
"""Compose a research grid from a previous full grid and a fresh split-ocean run.

The previous enclosed-water layer is reused only if all unseeded component
cells, grouping and source-cut contacts remain identical. Every changed ocean
cell is checked against the original full grid. Nothing is published.
"""
import argparse, collections, gzip, hashlib, json, os, struct, time
from pathlib import Path
import numpy as np
import ocean_fill_runner as ocean
import exclusive_outputs as xo
import split_lineage_ocean as split
from exclusive_outputs import create_directory_exclusive, create_binary_exclusive, create_text_exclusive, write_json_exclusive

KEYS = ('baseline_report','baseline_rows','baseline_runs','baseline_plan','closed_manifest',
        'old_partition','old_layer_manifest','old_summary','old_ocean_rows','old_ocean_spans','old_unseeded_rows','old_unseeded_spans','old_barrier',
        'new_partition','new_layer_manifest','new_summary','new_ocean_rows','new_ocean_spans','new_unseeded_rows','new_unseeded_spans','new_barrier',
        'prefill_snapshot','ocean_snapshot','prefill_plan','prefill_audit','ocean_candidate_build')

def read_pins(config):
    if config.get('schema') != 'worldatlas-split-ocean-final-config-v1' or set(config.get('inputs', {})) != set(KEYS):
        raise ValueError('invalid split final configuration')
    paths={}; hashes={}
    for key in KEYS:
        pin=config['inputs'][key]
        if set(pin) != {'path','sha256'} or not ocean.HEX.fullmatch(str(pin['sha256'])):
            raise ValueError('invalid input pin: '+key)
        path=Path(pin['path']).resolve()
        if not path.is_file() or ocean.sha(path)!=pin['sha256']:
            raise ValueError('input hash mismatch: '+key)
        paths[key]=path;hashes[key]=pin['sha256']
    return paths,hashes



def conservative_cut_contacts(rows_path, spans_path, barrier_path, width, height):
    """Count every cut incident to a component, including internal cuts."""
    offsets=np.memmap(rows_path,dtype='<u8',mode='r')
    size=Path(spans_path).stat().st_size
    spans=(np.memmap(spans_path,dtype='<u4',mode='r').reshape(-1,3)
           if size else np.empty((0,3),dtype=np.uint32))
    def owner(y,x):
        r=spans[int(offsets[y]):int(offsets[y+1])]
        if not len(r):return None
        i=int(np.searchsorted(r[:,0],x,side='right'))-1
        return int(r[i,2]) if i>=0 and x<int(r[i,1]) else None
    counts=collections.Counter();prev=None
    with Path(barrier_path).open('rb') as f:
        while True:
            raw=f.read(12)
            if not raw:break
            if len(raw)!=12:raise ValueError('truncated barrier edge')
            k,y,x=record=struct.unpack('<III',raw)
            if prev is not None and record<=prev:raise ValueError('barrier edges not unique and sorted')
            prev=record
            if k==0 and y<height and x<width-1:pts=((y,x),(y,x+1))
            elif k==1 and y<height-1 and x<width:pts=((y,x),(y+1,x))
            elif k==2 and y<height and x==0:pts=((y,width-1),(y,0))
            else:raise ValueError('barrier edge outside grid')
            for root in {owner(*pt) for pt in pts}-{None}:counts[root]+=1
    return counts


def _safe_bindings(snapshot):
    return split._bindings(snapshot)


def validate_lineage(paths, hashes):
    def document(key):
        raw=paths[key].read_bytes()
        if hashlib.sha256(raw).hexdigest()!=hashes[key]:raise ValueError('JSON input changed while being read: '+key)
        return json.loads(raw)
    report=document('baseline_report');plan=document('baseline_plan');closed=document('closed_manifest')
    old=document('old_partition');new=document('new_partition');prefill=document('prefill_snapshot');snap=document('ocean_snapshot')
    prefill_plan=document('prefill_plan');audit=document('prefill_audit');candidate=document('ocean_candidate_build')
    base=prefill.get('decision_revision',{});rev=snap.get('decision_revision',{});entity=rev.get('entity_revision')
    if (report.get('schema')!='worldatlas-direct-final-audit-v1' or report.get('status')!='unverified-research-not-published'
            or report.get('publishable') is not False or report.get('output',{}).get('rows_sha256')!=hashes['baseline_rows']
            or report.get('output',{}).get('runs_sha256')!=hashes['baseline_runs'] or report.get('final_plan_sha256')!=hashes['baseline_plan']
            or report.get('decision_snapshot_sha256')!=hashes['prefill_snapshot'] or report.get('decision_revision')!=base.get('id')
            or report.get('entity_revision')!=base.get('entity_revision')):
        raise ValueError('baseline report or decision binding mismatch')
    if (plan.get('decision_snapshot_sha256')!=hashes['prefill_snapshot'] or plan.get('decision_revision')!=base.get('id')
            or plan.get('research_provenance',{}).get('partition_manifest_sha256')!=hashes['old_partition']
            or plan.get('prefill',{}).get('plan_sha256')!=hashes['prefill_plan']
            or plan.get('prefill',{}).get('audit_sha256')!=hashes['prefill_audit']
            or not any(x.get('layer_id')=='ocean' and x.get('manifest_sha256')==hashes['old_layer_manifest'] for x in plan.get('water_layers',[]))
            or not any(x.get('layer_id')=='enclosed-water' and x.get('manifest_sha256')==hashes['closed_manifest'] for x in plan.get('water_layers',[]))):
        raise ValueError('baseline plan does not bind the old partition and closed layer')
    for prefix in ('old','new'):
        summary=document(prefix+'_summary')
        if (summary.get('status')!='unverified-candidate-not-published'
                or summary.get('barrier_sha256')!=hashes[prefix+'_barrier']
                or summary.get('layer_manifest_sha256')!=hashes[prefix+'_layer_manifest']
                or summary.get('snapshot_sha256')!=hashes['prefill_snapshot' if prefix=='old' else 'ocean_snapshot']):
            raise ValueError('ocean summary binding mismatch')
    if (closed.get('pending_cells')!=0 or closed.get('coverage',{}).get('complete') is not True
            or closed.get('source',{}).get('partition_manifest_sha256')!=hashes['old_partition']
            or closed.get('source',{}).get('barrier_edges_sha256')!=hashes['old_barrier']):
        raise ValueError('closed layer does not bind the old partition')
    oi=old.get('inputs',{});ni=new.get('inputs',{}); common=('physical_rows_sha256','physical_runs_sha256','physical_mask_sha256','prefill_rows_sha256','prefill_runs_sha256','prefill_audit_sha256','entity_revision')
    split_code=ni.get('split_execution_code_sha256',{});run_code=ni.get('candidate_code_sha256',{})
    required_code={'adapter','ocean_runner','partition_core','rle_inputs','exclusive_outputs'}
    if (snap.get('source')!='neon-export' or snap.get('schema')!='worldatlas-geography-decision-draft-evidence-v1'
            or rev.get('status')!='draft' or snap.get('entity_revision',{}).get('id')!=entity
            or snap.get('entity_revision',{}).get('status')!='draft'
            or prefill.get('entity_revision',{}).get('id')!=entity
            or _safe_bindings(prefill)!=_safe_bindings(snap)
            or ni.get('lineage_mode')!='separately-pinned-prefill-and-ocean-research-decisions'
            or ni.get('prefill_plan_sha256')!=hashes['prefill_plan'] or ni.get('prefill_audit_sha256')!=hashes['prefill_audit']
            or ni.get('candidate_build_sha256')!=hashes['ocean_candidate_build']
            or set(split_code)!=required_code or any(not ocean.HEX.fullmatch(str(x)) for x in split_code.values())
            or any(run_code.get(name+'.py')!=split_code[key] for name,key in [('ocean_fill_runner','ocean_runner'),('partition_core','partition_core'),('rle_inputs','rle_inputs'),('exclusive_outputs','exclusive_outputs')])):
        raise ValueError('new split execution lineage mismatch')
    if (candidate.get('schema')!='worldatlas-direct-candidate-build-v1' or candidate.get('status')!='unverified-research-not-published'
            or candidate.get('decision_snapshot_sha256')!=hashes['ocean_snapshot'] or candidate.get('decision_revision')!=rev.get('id')
            or candidate.get('entity_revision')!=entity or candidate.get('physical_rows_sha256')!=ni.get('physical_rows_sha256')
            or candidate.get('physical_runs_sha256')!=ni.get('physical_runs_sha256') or candidate.get('physical_mask_sha256')!=ni.get('physical_mask_sha256')
            or audit.get('schema')!='worldatlas-v7-prefill-class-rle-audit-v1' or audit.get('status')!='staged-not-published'
            or audit.get('prior_ocean_water_labels_read')!='none' or audit.get('source_plan_sha256')!=hashes['prefill_plan']
            or audit.get('decision_snapshot_sha256')!=hashes['prefill_snapshot'] or audit.get('decision_revision')!=base.get('id')
            or audit.get('entity_revision')!=entity or audit.get('physical_mask_sha256')!=ni.get('physical_mask_sha256')
            or audit.get('output',{}).get('rows_sha256')!=ni.get('prefill_rows_sha256')
            or audit.get('output',{}).get('runs_sha256')!=ni.get('prefill_runs_sha256')
            or prefill_plan.get('decision_snapshot_sha256')!=hashes['prefill_snapshot']
            or prefill_plan.get('decision_revision')!=base.get('id') or prefill_plan.get('entity_revision')!=entity
            or prefill_plan.get('rle_inputs',{}).get('physical',{}).get('rows_sha256')!=ni.get('physical_rows_sha256')
            or prefill_plan.get('rle_inputs',{}).get('physical',{}).get('runs_sha256')!=ni.get('physical_runs_sha256')
            or prefill_plan.get('rle_inputs',{}).get('physical',{}).get('physical_mask_sha256')!=ni.get('physical_mask_sha256')
            or prefill_plan.get('rle_inputs',{}).get('physical',{}).get('report_sha256')!=candidate.get('physical_report_sha256')
            or candidate.get('grid',{}).get('width')!=old.get('grid',{}).get('W')
            or candidate.get('grid',{}).get('height')!=old.get('grid',{}).get('H')
            or prefill_plan.get('grid',{}).get('width')!=old.get('grid',{}).get('W')
            or prefill_plan.get('grid',{}).get('height')!=old.get('grid',{}).get('H')):
        raise ValueError('candidate build or prefill audit lineage mismatch')
    if (old.get('schema')!='fresh-ocean-run-partition-v1' or new.get('schema')!='fresh-ocean-run-partition-v1'
            or old.get('grid')!=new.get('grid') or any(oi.get(k)!=ni.get(k) or not oi.get(k) for k in common)
            or oi.get('decision_snapshot_sha256')!=hashes['prefill_snapshot']
            or oi.get('legacy_ocean_label_inheritance') is not False or ni.get('legacy_ocean_label_inheritance') is not False
            or report.get('prefill_audit_sha256')!=oi.get('prefill_audit_sha256')
            or ni.get('decision_snapshot_sha256')!=hashes['ocean_snapshot']
            or ni.get('prefill_decision_snapshot_sha256')!=hashes['prefill_snapshot']
            or oi.get('source_cut_edges_sha256')!=hashes['old_barrier'] or ni.get('source_cut_edges_sha256')!=hashes['new_barrier']
            or rev.get('evidence',{}).get('base_local_snapshot_sha256')!=hashes['prefill_snapshot']
            or rev.get('id')!=ni.get('decision_revision') or entity!=ni.get('entity_revision')
            or base.get('entity_revision')!=entity):
        raise ValueError('split ocean partition lineage mismatch')
    for prefix,part in (('old',old),('new',new)):
        layer=document(prefix+'_layer_manifest'); src=layer.get('source',{}); inp=part.get('inputs',{})
        if src!=inp:raise ValueError('ocean layer source binding mismatch')
    if (closed.get('source',{}).get('decision_snapshot_sha256')!=hashes['prefill_snapshot']
            or closed.get('source',{}).get('decision_revision')!=base.get('id')
            or closed.get('source',{}).get('entity_revision')!=entity
            or closed.get('source',{}).get('legacy_ocean_label_inheritance') is not False
            or closed.get('source',{}).get('physical_rows_sha256')!=oi['physical_rows_sha256']
            or closed.get('source',{}).get('physical_runs_sha256')!=oi['physical_runs_sha256']
            or closed.get('source',{}).get('prefill_audit_sha256')!=oi['prefill_audit_sha256']
            or closed.get('source',{}).get('prefill_rows_sha256')!=oi['prefill_rows_sha256']
            or closed.get('source',{}).get('prefill_runs_sha256')!=oi['prefill_runs_sha256']
            or closed.get('source',{}).get('component_rows_sha256')!=hashes['old_unseeded_rows']
            or closed.get('source',{}).get('component_spans_sha256')!=hashes['old_unseeded_spans']):
        raise ValueError('closed layer inputs mismatch')
    for prefix, part in (('old',old),('new',new)):
        parent=paths[prefix+'_partition'].parent
        for key, filename in (('ocean_rows','ocean_rows.u64le'),('ocean_spans','ocean_assignment_spans.u32le'),
                              ('unseeded_rows','unseeded_rows.u64le'),('unseeded_spans','unseeded_component_spans.u32le')):
            if paths[prefix+'_'+key]!=(parent/filename).resolve():
                raise ValueError('partition data path mismatch')
    if (old.get('eligible_water_cells')!=new.get('eligible_water_cells') or old.get('unseeded_cell_count')!=new.get('unseeded_cell_count')
            or old.get('seed_cells')!=new.get('seed_cells') or hashes['old_unseeded_rows']!=hashes['new_unseeded_rows']):
        raise ValueError('ocean eligibility, seeds, or unseeded rows changed')
    grid=old['grid']; w=grid.get('W'); h=grid.get('H')
    if type(w) is not int or type(h) is not int or w<=0 or h<=0:raise ValueError('invalid partition grid')
    unseeded_offsets=np.memmap(paths['old_unseeded_rows'],dtype='<u8',mode='r')
    span_count=paths['old_unseeded_spans'].stat().st_size//12
    if (paths['old_unseeded_spans'].stat().st_size%12 or len(unseeded_offsets)!=h+1 or int(unseeded_offsets[0])!=0
            or int(unseeded_offsets[-1])!=span_count or np.any(unseeded_offsets[1:]<unseeded_offsets[:-1])):
        raise ValueError('invalid unseeded row offsets')
    mapping={};reverse={}; component_cells=collections.Counter(); count=0; ordinal=0; row=0; previous_end=0
    with paths['old_unseeded_spans'].open('rb') as a, paths['new_unseeded_spans'].open('rb') as b:
        while True:
            x=a.read(12);y=b.read(12)
            if not x and not y: break
            if len(x)!=12 or len(y)!=12:raise ValueError('unseeded span length mismatch')
            x=struct.unpack('<III',x);y=struct.unpack('<III',y)
            while row<h and ordinal>=int(unseeded_offsets[row+1]):row+=1;previous_end=0
            if row>=h or x[0]>=x[1] or x[1]>w or x[0]<previous_end:raise ValueError('invalid unseeded span')
            previous_end=x[1];ordinal+=1
            if x[:2]!=y[:2] or mapping.setdefault(x[2],y[2])!=y[2] or reverse.setdefault(y[2],x[2])!=x[2]:
                raise ValueError('unseeded footprint or component grouping changed')
            component_cells[x[2]]+=x[1]-x[0];count+=x[1]-x[0]
    old_components=old['components'];new_components=new['components']
    oc={x['component_root']:x for x in old_components};nc={x['component_root']:x for x in new_components}
    if (len(oc)!=len(old_components) or len(nc)!=len(new_components)
            or set(mapping)!={i for i,c in oc.items() if c.get('ocean_code') is None}
            or set(reverse)!={i for i,c in nc.items() if c.get('ocean_code') is None}
            or any(oc[i].get('cell_count')!=component_cells[i] or nc[j].get('cell_count')!=component_cells[i]
                   for i,j in mapping.items())):
        raise ValueError('unseeded component metadata mismatch')
    if (count!=old['unseeded_cell_count'] or any(i not in oc or j not in nc or
            (oc[i]['source_barrier_contact_edge_count']!=0 or nc[j]['source_barrier_contact_edge_count']!=0) for i,j in mapping.items())):
        raise ValueError('unseeded source-cut contacts changed')
    old_contacts=conservative_cut_contacts(paths['old_unseeded_rows'],paths['old_unseeded_spans'],paths['old_barrier'],w,h)
    new_contacts=conservative_cut_contacts(paths['new_unseeded_rows'],paths['new_unseeded_spans'],paths['new_barrier'],w,h)
    if old_contacts or new_contacts:
        raise ValueError('conservative unseeded source-cut contacts prevent reuse')
    return report,old,new,w,h,len(mapping)


def layer_rows(path, expected_height, expected_hash):
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_hash:raise ValueError('ocean manifest changed while being read')
    manifest=json.loads(raw)
    if manifest.get('schema')!='worldatlas-full-water-assignment-tiles-v1' or manifest.get('coverage',{}).get('complete') is not True:
        raise ValueError('invalid ocean layer manifest')
    tiles=manifest.get('tiles',[]); expected=0; pinned=[]
    for tile in tiles:
        first,last=tile.get('core_rows',[None,None]);spec=tile.get('span_file',{})
        if first!=expected or type(last) is not int or not first<last<=expected_height or not ocean.HEX.fullmatch(str(spec.get('sha256',''))):
            raise ValueError('invalid ocean tile coverage')
        p=(path.parent/spec.get('path','')).resolve()
        if not p.is_relative_to(path.parent.resolve()) or ocean.sha(p)!=spec['sha256']:
            raise ValueError('ocean tile hash or path mismatch')
        pinned.append((p,spec['sha256']))
        with p.open(encoding='utf8') as f:
            for line in f:
                row=json.loads(line)
                if expected>=last or row.get('row')!=expected:raise ValueError('ocean tile row order mismatch')
                yield expected,[(x['start'],x['end'],x['code']) for x in row.get('spans',[])]
                expected+=1
        if expected!=last:raise ValueError('incomplete ocean tile')
    if expected!=expected_height or any(ocean.sha(p)!=h for p,h in pinned):
        raise ValueError('ocean tiles incomplete or changed')

def compose(config_path, output):
    processing_started=time.perf_counter()
    config_path=Path(config_path).resolve();raw=config_path.read_bytes();config=json.loads(raw);paths,hashes=read_pins(config)
    code_paths={'split_compose':Path(__file__).resolve(),'ocean_runner':Path(ocean.__file__).resolve(),'exclusive_outputs':Path(xo.__file__).resolve(),'split_ocean':Path(split.__file__).resolve()}
    code_hashes={k:ocean.sha(v) for k,v in code_paths.items()}
    out=Path(os.path.abspath(output))
    # Plans and candidate documents may be siblings of the fresh final output.
    # Layer roots, unlike individual documents, also own relative tile files.
    layer_roots=[paths[key].parent for key in ('old_layer_manifest','new_layer_manifest','closed_manifest')]
    if (out!=out.resolve() or any(out==p or p.is_relative_to(out) or out.is_relative_to(p)
            for p in [config_path,*paths.values()])
            or any(out.is_relative_to(root) for root in layer_roots)):
        raise ValueError('output must be separate from inputs')
    report,old,new,w,h,component_count=validate_lineage(paths,hashes)
    br=np.memmap(paths['baseline_rows'],dtype='<u4',mode='r');bu=np.memmap(paths['baseline_runs'],dtype='<u4',mode='r').reshape(-1,2)
    def ocean_grid(prefix):
        rows=np.memmap(paths[prefix+'_ocean_rows'],dtype='<u8',mode='r');spans=np.memmap(paths[prefix+'_ocean_spans'],dtype='<u4',mode='r').reshape(-1,3)
        if len(rows)!=h+1 or int(rows[0])!=0 or int(rows[-1])!=len(spans) or np.any(rows[1:]<rows[:-1]):raise ValueError('invalid ocean row offsets')
        return rows,spans
    ar,au=ocean_grid('old');nr,nu=ocean_grid('new')
    if len(br)!=h+1 or int(br[0])!=0 or int(br[-1])!=len(bu) or np.any(br[1:]<br[:-1]):raise ValueError('invalid baseline row offsets')
    old_layer=iter(layer_rows(paths['old_layer_manifest'],h,hashes['old_layer_manifest']));new_layer=iter(layer_rows(paths['new_layer_manifest'],h,hashes['new_layer_manifest']))
    create_directory_exclusive(out);offsets=[0];nrun=0;changes=collections.Counter();spans_count=0
    with create_binary_exclusive(out/'runs.u32le') as stream, gzip.open(out/'difference-spans.jsonl.gz','xt',encoding='utf8') as delta:
      for y in range(h):
        x=au[int(ar[y]):int(ar[y+1])];z=nu[int(nr[y]):int(nr[y+1])];base=bu[int(br[y]):int(br[y+1])]
        for layer,v in ((old_layer,x),(new_layer,z)):
            row,listed=next(layer)
            if row!=y or listed!=[tuple(map(int,t)) for t in v]:raise ValueError('partition spans differ from pinned ocean layer')
        if (not len(base) or int(base[0,0])<=0 or int(base[-1,0])!=w or np.any(base[1:,0]<=base[:-1,0])
                or np.any(~np.isin(base[:,1],[1,2,3,4,5,6,7,8,9,10,17,18,19,20,21,22]))):raise ValueError('invalid baseline row')
        for v in (x,z):
            if len(v) and (np.any(v[:,0]>=v[:,1]) or np.any(v[:,1]>w) or np.any(v[1:,0]<v[:-1,1]) or np.any(~np.isin(v[:,2],[7,8,9,10]))):raise ValueError('invalid ocean spans')
        ends=np.unique(np.r_[x[:,0],x[:,1],z[:,0],z[:,1]]);starts=ends[:-1];stops=ends[1:]
        def labels(v):
            ix=np.searchsorted(v[:,0],starts,side='right')-1;ok=ix>=0;out=np.zeros(len(starts),dtype=np.uint32)
            if len(v):ok &= starts<v[np.maximum(ix,0),1];out[ok]=v[ix[ok],2]
            return out
        before,after=labels(x),labels(z);changed=np.flatnonzero(before!=after)
        if len(changed)==0:
            stream.write(base.tobytes());nrun+=len(base);offsets.append(nrun);continue
        if np.any(before[changed]==0) or np.any(after[changed]==0):raise ValueError('ocean assigned footprint changed')
        d=np.column_stack((starts[changed],stops[changed],before[changed],after[changed])).astype(np.int64)
        cuts=np.unique(np.r_[0,base[:,0],d[:,0],d[:,1]]);left=cuts[:-1];right=cuts[1:];orig=base[np.searchsorted(base[:,0],left,side='right'),1].astype(np.int64);values=orig.copy()
        ix=np.searchsorted(d[:,0],left,side='right')-1;hit=ix>=0;hit &= left<d[np.maximum(ix,0),1]
        if np.any(orig[hit]!=d[ix[hit],2]):raise ValueError('baseline disagrees with previous ocean labels')
        values[hit]=d[ix[hit],3]
        for i in np.flatnonzero(hit):changes[f'{orig[i]}->{values[i]}']+=int(right[i]-left[i])
        keep=np.r_[values[:-1]!=values[1:],True];packed=np.column_stack((right[keep],values[keep])).astype('<u4');stream.write(packed.tobytes());nrun+=len(packed);offsets.append(nrun)
        delta.write(json.dumps({'row':y,'spans':d.tolist()},separators=(',',':'))+'\n');spans_count+=len(d)
    if next(old_layer,None) is not None or next(new_layer,None) is not None:raise ValueError('extra ocean layer rows')
    if nrun>=2**32:raise ValueError('output exceeds u32 row offsets')
    with create_binary_exclusive(out/'rows.u32le') as f:f.write(np.asarray(offsets,dtype='<u4').tobytes())
    if (config_path.read_bytes()!=raw or any(ocean.sha(p)!=hashes[k] for k,p in paths.items())
            or any(ocean.sha(p)!=code_hashes[k] for k,p in code_paths.items())):raise ValueError('input or code changed during composition')
    counts={str(k):int(v) for k,v in report['counts'].items()}
    for pair,n in changes.items():a,b=pair.split('->');counts[a]-=n;counts[b]+=n
    if sum(counts.values())!=w*h or any(x<0 for x in counts.values()):raise ValueError('output cell accounting mismatch')
    result={'schema':'worldatlas-split-ocean-final-audit-v1','status':'unverified-research-not-published','publishable':False,
      'grid':{'width':w,'height':h},'counts':counts,'run_count':nrun,'changed_cells':sum(changes.values()),'pair_counts':dict(changes),'difference_span_count':spans_count,
      'inputs':hashes,'code_sha256':code_hashes,'reused_unseeded_components':component_count,'output':{'rows_sha256':ocean.sha(out/'rows.u32le'),'runs_sha256':ocean.sha(out/'runs.u32le'),'difference_spans_sha256':ocean.sha(out/'difference-spans.jsonl.gz')},
      'limitations':['Research-only split lineage; snapshot authentication and geographic authority are not established.','Unseeded cells, component grouping and conservatively scanned cut-contact counts are unchanged; prior closed-water classifications are reused, not revalidated.']}
    result['processing_elapsed_seconds']=time.perf_counter()-processing_started
    write_json_exclusive(out/'report.json',result,indent=2);return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--out',required=True);p.add_argument('--allow-unverified',action='store_true');a=p.parse_args()
    if not a.allow_unverified:raise ValueError('explicit unverified research opt-in required')
    print(json.dumps(compose(a.config,a.out),indent=2))
