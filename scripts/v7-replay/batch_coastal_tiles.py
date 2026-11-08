#!/usr/bin/env python3
"""WGS84 coastal tiles using a single verified input generation.

Workers share unlinked snapshots opened with read-only file descriptors.
A batch-complete record is written only after every tile and metadata recheck.
Resume copies verified completed tiles into a fresh batch; interrupted tiles
are regenerated, and preserved source directories are never changed.
"""
from __future__ import annotations
import argparse,contextlib,hashlib,json,math,os,stat,uuid
import time
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from pathlib import Path
import numpy as np
import build_coastal_tile as tile
import decision_snapshot,exclusive_outputs,pinned_coastal_metadata,local_water_overlay,direct_lineage,build_prefill_plan,selected_mixed_lineage
from pinned_coastal_metadata import pinned_bytes,pinned_json
from stage_external import check_cancelled
import snapshot_input
import coastal_shore_index_batch
from exclusive_outputs import create_directory_exclusive,create_binary_exclusive,open_checkpoint_readonly

def available_workers():
 """Choose concurrency from the process's available CPUs, never its RAM."""
 return len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else (os.cpu_count() or 1)


def generate_tile(state, index, entry):
 """Generate one tile using read-only grid and shoreline arrays."""
 check_cancelled()
 snapshot,snapshot_sha,physical,land,root,width,height,inputs,chunk,shore_index=state
 return tile.run(snapshot,snapshot_sha,physical,land,root/f'tile-{index:04d}',width,height,
                 entry['core'],entry['latitude_pad_degrees'],inputs,chunk=chunk,
                 allow_selected_research=True,longitude_pad_degrees=entry['longitude_pad_degrees'],
                 shore_index=shore_index)

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def sealed_copy(path,expected):
 """Return a read-only snapshot holding precisely the SHA-pinned input bytes."""
 if not isinstance(expected,str) or len(expected)!=64 or any(x not in '0123456789abcdef' for x in expected):raise ValueError('invalid SHA-256')
 total=0
 def copy(target):
  nonlocal total
  with open(path,'rb',opener=lambda name,flags:os.open(name,flags|os.O_NOFOLLOW|os.O_NONBLOCK)) as source:
   before=os.fstat(source.fileno())
   if not stat.S_ISREG(before.st_mode):raise ValueError('source is not regular')
   digest=hashlib.sha256()
   for block in iter(lambda:source.read(1<<20),b''):
    check_cancelled()
    total+=len(block)
    if total>before.st_size:raise ValueError('source grew during copy')
    digest.update(block)
    target.write(block)
   after=os.fstat(source.fileno())
   if total!=before.st_size or before.st_mtime_ns!=after.st_mtime_ns or digest.hexdigest()!=expected:
    raise ValueError('source changed or SHA-256 mismatch')
 return snapshot_input.open_snapshot(copy),total

def validate_plan(plan,width,height):
 if not isinstance(plan,dict) or set(plan) not in ({'tiles','pad_degrees','chunk'},{'tiles','chunk'}):raise ValueError('invalid batch plan keys')
 entries=plan['tiles'];chunk=plan['chunk'];uniform=plan.get('pad_degrees')
 if not isinstance(entries,list) or not entries or type(chunk)!=int or chunk<1:raise ValueError('invalid batch plan values')
 def positive(v):return not isinstance(v,bool) and isinstance(v,(int,float)) and math.isfinite(v) and v>0
 if uniform is not None and not positive(uniform):raise ValueError('invalid latitude/longitude halo')
 boxes=[]
 for entry in entries:
  if uniform is None:
   if not isinstance(entry,dict) or set(entry)!={'core','latitude_pad_degrees','longitude_pad_degrees'}:raise ValueError('invalid per-tile halo')
   box=entry['core'];ypad=entry['latitude_pad_degrees'];xpad=entry['longitude_pad_degrees']
  else:box=entry;ypad=xpad=uniform
  if not positive(ypad) or not positive(xpad):raise ValueError('invalid latitude/longitude halo')
  if not isinstance(box,list) or len(box)!=4 or any(type(v)!=int for v in box):raise ValueError('invalid tile bounds')
  x0,x1,y0,y1=box
  if not(0<=x0<x1<=width and 0<=y0<y1<=height):raise ValueError('tile outside grid')
  for other in boxes:
   a,c,d,e=other['core']
   if max(x0,a)<min(x1,c) and max(y0,d)<min(y1,e):raise ValueError('overlapping tiles')
  boxes.append({'core':box,'latitude_pad_degrees':ypad,'longitude_pad_degrees':xpad})
 return boxes

def record_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def read_record(path):
    with open_checkpoint_readonly(path) as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('checkpoint is not a regular file')
        return json.load(stream)


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | getattr(os, 'O_NOFOLLOW', 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def publish_record(path, value):
    """Publish a durable immutable record atomically, without replacing anything.

    A killed writer may leave an unreferenced pending file. Only the final name
    is a checkpoint; its hard link appears after the complete bytes are synced.
    """
    pending = path.with_name(path.name + '.' + uuid.uuid4().hex + '.pending')
    with create_binary_exclusive(pending) as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2,
                                 allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    os.link(pending, path, follow_symlinks=False)
    sync_directory(path.parent)


def verified_copy(source, destination, expected):
    """Copy one closed artifact, checking the exact bytes written to new output."""
    digest = hashlib.sha256()
    with open_checkpoint_readonly(source) as src, create_binary_exclusive(destination) as dst:
        if not stat.S_ISREG(os.fstat(src.fileno()).st_mode):
            raise ValueError('tile artifact is not regular')
        for block in iter(lambda: src.read(1 << 20), b''):
            digest.update(block)
            dst.write(block)
        if digest.hexdigest() != expected:
            raise ValueError('resume tile changed while copying')
        dst.flush()
        os.fsync(dst.fileno())


def elapsed_value(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('invalid checkpoint processing time')
    return value


def validate_attempts(attempts):
    if not isinstance(attempts, list):
        raise ValueError('invalid checkpoint attempts')
    ids = set()
    for attempt in attempts:
        if not isinstance(attempt, dict) or set(attempt) != {'attempt_id', 'processing_elapsed_seconds', 'timing_complete'}:
            raise ValueError('invalid checkpoint attempt')
        ident = attempt['attempt_id']
        if (not isinstance(ident, str) or len(ident) != 32 or any(c not in '0123456789abcdef' for c in ident)
                or ident in ids or type(attempt['timing_complete']) is not bool):
            raise ValueError('invalid checkpoint attempt identity')
        ids.add(ident)
        elapsed_value(attempt['processing_elapsed_seconds'])
    return ids


def validate_tile(directory, entry, snapshot, inputs, identity, checkpoint):
    """Authenticate a completed tile against this invocation, not just its name."""
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('invalid checkpoint tile directory')
    manifest_path = directory / 'manifest.json'
    manifest = read_record(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError('invalid resume tile manifest')
    if sha(manifest_path) != checkpoint['manifest_sha256']:
        raise ValueError('resume tile manifest hash mismatch')
    box = entry['core']
    width, height = identity['grid']['width'], identity['grid']['height']
    decision, _, _, _, _ = tile.core.policy(snapshot, allow_selected_research=True)
    expected = {
        'schema': 'worldatlas-coastal-tile-candidate-v1',
        'status': 'partial-unverified-research-not-published',
        'grid': {'width': width, 'height': height, 'angular_step_deg': 360 / width},
        'core_cols': box[:2], 'core_rows': box[2:],
        'shore_crop_bounds': list(tile.coast_crop_bounds(box, width, height, 360 / width,
                                  entry['latitude_pad_degrees'], entry['longitude_pad_degrees'])),
        'policy_id': decision['id'], 'policy_definition': decision['definition'],
        'decision_snapshot_sha256': identity['snapshot_sha256'],
        'decision_revision': snapshot['decision_revision']['id'],
        'entity_revision': snapshot['decision_revision']['entity_revision'], 'inputs': inputs,
        **{key + '_sha256': value for key, value in identity['tile_code_sha256'].items()},
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError('resume tile metadata mismatch')
    span = manifest.get('span_file')
    if not isinstance(span, dict) or span != {'path': 'coastal-assignments.jsonl.gz', 'sha256': checkpoint['span_sha256']}:
        raise ValueError('resume tile span metadata mismatch')
    with open_checkpoint_readonly(directory / span['path']) as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('tile artifact is not regular')
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    if digest.hexdigest() != span['sha256']:
        raise ValueError('resume tile span hash mismatch')
    elapsed_value(manifest.get('processing_elapsed_seconds'))
    return manifest


def load_resume(root, identity, boxes, snapshot, inputs):
    """Read only producer-owned checkpoints; absent tile records mean redo work."""
    lexical = Path(os.path.abspath(root))
    if lexical != lexical.resolve() or not lexical.is_dir():
        raise ValueError('resume root must be a real directory without symlinks')
    start = read_record(lexical / 'batch-start.json')
    if (not isinstance(start, dict) or start.get('schema') != 'worldatlas-coastal-batch-start-v1'
            or start.get('identity') != identity):
        raise ValueError('coastal resume identity mismatch')
    prior = start.get('prior_attempts')
    validate_attempts(prior)
    current = {'attempt_id': start.get('attempt_id'),
               'processing_elapsed_seconds': elapsed_value(start.get('processing_elapsed_seconds')),
               'timing_complete': False}
    validate_attempts(prior + [current])
    completed = {}
    for index, entry in enumerate(boxes):
        directory = lexical / f'tile-{index:04d}'
        path = directory / 'tile-complete.json'
        if directory.is_symlink():
            raise ValueError('invalid checkpoint tile directory')
        if not os.path.lexists(path):
            continue
        checkpoint = read_record(path)
        required = {'schema', 'identity_sha256', 'tile', 'box', 'manifest_sha256', 'span_sha256',
                    'attempt_id', 'attempt_processing_elapsed_seconds'}
        if (not isinstance(checkpoint, dict) or set(checkpoint) != required
                or checkpoint.get('schema') != 'worldatlas-coastal-tile-checkpoint-v1'
                or checkpoint.get('identity_sha256') != record_digest(identity)
                or type(checkpoint.get('tile')) is not int or checkpoint['tile'] != index
                or checkpoint.get('box') != entry['core'] or checkpoint.get('attempt_id') != current['attempt_id']):
            raise ValueError('invalid coastal tile checkpoint')
        elapsed = elapsed_value(checkpoint.get('attempt_processing_elapsed_seconds'))
        if elapsed < current['processing_elapsed_seconds']:
            raise ValueError('nonmonotonic coastal checkpoint time')
        current['processing_elapsed_seconds'] = elapsed
        manifest = validate_tile(directory, entry, snapshot, inputs, identity, checkpoint)
        completed[index] = (directory, checkpoint, manifest)
    complete_path = lexical / 'batch-complete.json'
    if os.path.lexists(complete_path):
        result = read_record(complete_path)
        expected_tiles = [{'tile': i, 'box': boxes[i]['core'], 'manifest_sha256': cp['manifest_sha256']}
                          for i, (_, cp, _) in completed.items()]
        if (not isinstance(result, dict) or result.get('checkpoint_identity_sha256') != record_digest(identity)
                or result.get('tiles') != expected_tiles or len(completed) != len(boxes)
                or result.get('status') != 'complete-research-not-published'
                or result.get('batch_start_sha256') != sha(lexical / 'batch-start.json')):
            raise ValueError('invalid coastal batch completion')
        attempts = result.get('timing_attempts')
        validate_attempts(attempts)
        if (not attempts or attempts[:-1] != prior or attempts[-1]['attempt_id'] != current['attempt_id']
                or not attempts[-1]['timing_complete']
                or attempts[-1]['processing_elapsed_seconds'] < current['processing_elapsed_seconds']):
            raise ValueError('invalid completed coastal timing')
        current = attempts[-1]
        recorded = sum(x['processing_elapsed_seconds'] for x in attempts)
        timing_complete = all(x['timing_complete'] for x in attempts)
        if (result.get('recorded_processing_elapsed_seconds') != recorded
                or result.get('timing_complete') is not timing_complete
                or result.get('processing_elapsed_seconds') != (recorded if timing_complete else None)):
            raise ValueError('invalid completed coastal timing total')
    return completed, prior + [current]


def merge_attempts(prior, incoming):
    """Deduplicate overlapping resume ancestry without counting downtime."""
    merged = {x['attempt_id']: x for x in prior}
    for attempt in incoming:
        old = merged.get(attempt['attempt_id'])
        if old is None:
            merged[attempt['attempt_id']] = attempt
        elif old['timing_complete'] and attempt['timing_complete'] and old != attempt:
            raise ValueError('inconsistent completed checkpoint timing')
        elif attempt['processing_elapsed_seconds'] > old['processing_elapsed_seconds']:
            if old['timing_complete']:
                raise ValueError('checkpoint time exceeds completed attempt')
            merged[attempt['attempt_id']] = attempt
        elif attempt['timing_complete']:
            if attempt['processing_elapsed_seconds'] < old['processing_elapsed_seconds']:
                raise ValueError('completed checkpoint time precedes recorded work')
            merged[attempt['attempt_id']] = attempt
    return [merged[key] for key in sorted(merged)]


def merge_tiles(completed, recovered):
    for index, candidate in recovered.items():
        old = completed.get(index)
        if old is not None:
            # Generation time may differ; all scientific output must agree.
            semantic = lambda manifest: {k: v for k, v in manifest.items()
                                         if k not in ('processing_elapsed_seconds', 'stage_processing_elapsed_seconds')}
            if semantic(old[2]) != semantic(candidate[2]):
                raise ValueError('conflicting coastal checkpoints for the same tile')
            if old[1]['manifest_sha256'] <= candidate[1]['manifest_sha256']:
                continue
        completed[index] = candidate


def run_batch(snapshot,snapshot_sha,paths,pins,plan,plan_sha,out,width,height,check_metadata,*,metadata_pins,processing_started=None,resume_from=None,workers=1,shared_inputs=None):
 """Generate partial research tiles with fresh-output, authenticated continuation.

 Hash strings are caller assertions. Only the CLI validates pinned metadata and
 provides the required lineage callback; a completion record gates the batch.
 """
 if processing_started is None:processing_started=time.perf_counter()
 if workers is None:workers=available_workers()
 if type(workers) is not int or workers<1:raise ValueError('workers must be a positive integer')
 boxes=validate_plan(plan,width,height)
 names=('physical_rows','physical_runs','land_rows','land_runs')
 if set(paths)!=set(names) or set(pins)!=set(names):raise ValueError('four grid inputs required')
 if set(metadata_pins)!={'physical_report','land_report'} or any(not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for v in metadata_pins.values()):raise ValueError('two report SHA-256 pins required')
 if Path(coastal_shore_index_batch.__file__).resolve()!=Path(__file__).resolve().with_name('coastal_shore_index_batch.py'):
  raise ImportError('shoreline index builder resolved outside the selected checkout')
 code_paths={'algorithm':Path(tile.__file__),'core':Path(tile.core.__file__),'shore':Path(tile.core.shore.__file__),'geometry':Path(tile.core.shore.__file__),'accelerator':Path(tile.coastal_rect.__file__),
             'shore_index':Path(tile.coastal_shore_index.__file__)};code_pins={k:sha(v) for k,v in code_paths.items()}
 support_paths={'metadata':Path(pinned_coastal_metadata.__file__),'snapshot':Path(decision_snapshot.__file__),'land_lineage':Path(direct_lineage.__file__),'land_validator':Path(build_prefill_plan.__file__),'mixed_lineage':Path(selected_mixed_lineage.__file__),'overlay':Path(local_water_overlay.__file__),'output':Path(exclusive_outputs.__file__),'snapshot_input':Path(snapshot_input.__file__),'shore_index_builder':Path(coastal_shore_index_batch.__file__)};support_pins={k:sha(v) for k,v in support_paths.items()}
 identity={'snapshot_sha256':snapshot_sha,'plan_sha256':plan_sha,'grid':{'width':width,'height':height},'sealed_input_sha256':pins,'metadata_sha256':metadata_pins,'driver_sha256':CODE_SHA,'tile_code_sha256':code_pins,'support_code_sha256':support_pins}
 if shared_inputs is not None:
  from verified_water_inputs import VerifiedWaterInputs
  if not isinstance(shared_inputs,VerifiedWaterInputs):raise TypeError('a verified shared water input context is required')
  physical=shared_inputs.grid('physical',paths['physical_rows'],pins['physical_rows'],paths['physical_runs'],pins['physical_runs'],width,height)
  land=shared_inputs.grid('land',paths['land_rows'],pins['land_rows'],paths['land_runs'],pins['land_runs'],width,height)
  identity['shared_input_generation']=shared_inputs.provenance()
 inputs={k+'_sha256':pins[k] for k in names};inputs.update({k+'_sha256':v for k,v in metadata_pins.items()})
 check_metadata()
 completed={};prior=[]
 if resume_from is not None:
  sources=[resume_from] if isinstance(resume_from,(str,os.PathLike)) else list(resume_from)
  for candidate in sources:
   source=Path(candidate).resolve();destination=Path(out).resolve()
   if source==destination or source.is_relative_to(destination) or destination.is_relative_to(source):raise ValueError('resume source and new output must be disjoint')
   recovered,attempts=load_resume(candidate,identity,boxes,snapshot,inputs)
   merge_tiles(completed,recovered);prior=merge_attempts(prior,attempts)
 def check_code():
  if sha(Path(__file__))!=CODE_SHA or any(sha(path)!=code_pins[k] for k,path in code_paths.items()) or any(sha(path)!=support_pins[k] for k,path in support_paths.items()):raise ValueError('batch code changed during generation')
 with contextlib.ExitStack() as stack:
  sealed={};used=0
  shore_started=time.perf_counter()
  if shared_inputs is None:
   for k in names:
    fd,n=sealed_copy(paths[k],pins[k]);used+=n;sealed[k]=stack.enter_context(os.fdopen(fd,'rb'))
   physical=tile.open_grid(sealed['physical_rows'],sealed['physical_runs'],width,height);land=tile.open_grid(sealed['land_rows'],sealed['land_runs'],width,height)
   shore_started=time.perf_counter()
   shore_index=coastal_shore_index_batch.BatchedCoastalShoreIndex(physical,land,width,height)
   for values in (shore_index.offsets,shore_index.starts,shore_index.ends,shore_index.codes):values.flags.writeable=False
  else:
   used=sum(values.nbytes for grid in (physical,land) for values in grid)
   shore_index=shared_inputs.shore_index
  shore_elapsed=time.perf_counter()-shore_started
  root=create_directory_exclusive(out);sync_directory(root.parent);manifests=[];attempt_id=uuid.uuid4().hex
  start={'schema':'worldatlas-coastal-batch-start-v1','identity':identity,'attempt_id':attempt_id,'prior_attempts':prior,'processing_elapsed_seconds':time.perf_counter()-processing_started}
  publish_record(root/'batch-start.json',start)
  jobs={}
  if workers>1 and len(completed)<len(boxes):
   state=(snapshot,snapshot_sha,physical,land,root,width,height,inputs,plan['chunk'],shore_index)
   pool=stack.enter_context(ThreadPoolExecutor(max_workers=workers))
   jobs={i:pool.submit(copy_context().run,generate_tile,state,i,entry) for i,entry in enumerate(boxes) if i not in completed}
   # On failure cancel jobs not yet started before joining the worker pool.
   stack.callback(lambda:[job.cancel() for job in jobs.values()])
  for i,entry in enumerate(boxes):
   check_cancelled()
   box=entry['core'];dest=root/f'tile-{i:04d}'
   if i in completed:
    source,checkpoint,manifest=completed[i];create_directory_exclusive(dest)
    for name,digest in (('manifest.json',checkpoint['manifest_sha256']),('coastal-assignments.jsonl.gz',checkpoint['span_sha256'])):
     verified_copy(source/name,dest/name,digest)
   elif i in jobs:
    manifest=jobs[i].result()
   else:
    manifest=tile.run(snapshot,snapshot_sha,physical,land,dest,width,height,box,entry['latitude_pad_degrees'],inputs,chunk=plan['chunk'],allow_selected_research=True,longitude_pad_degrees=entry['longitude_pad_degrees'],shore_index=shore_index)
   if any(manifest[k+'_sha256']!=v for k,v in code_pins.items()):raise ValueError('tile code pin changed within batch')
   check_code()
   for name in ('manifest.json','coastal-assignments.jsonl.gz'):
    with open_checkpoint_readonly(dest/name) as stream:os.fsync(stream.fileno())
   sync_directory(dest)
   record={'schema':'worldatlas-coastal-tile-checkpoint-v1','identity_sha256':record_digest(identity),'tile':i,'box':box,'manifest_sha256':sha(dest/'manifest.json'),'span_sha256':manifest['span_file']['sha256'],'attempt_id':attempt_id,'attempt_processing_elapsed_seconds':time.perf_counter()-processing_started}
   publish_record(dest/'tile-complete.json',record)
   sync_directory(root)
   manifests.append({'tile':i,'box':box,'manifest_sha256':record['manifest_sha256']})
  check_metadata();check_code()
  result={'schema':'worldatlas-sealed-coastal-batch-v1','status':'complete-research-not-published',**identity,'sealed_input_bytes':used,'tiles':manifests,'checkpoint_identity_sha256':record_digest(identity),'batch_start_sha256':sha(root/'batch-start.json'),'resumed_tiles':len(completed),'parallel_workers':workers,'limitations':['Tiles remain research candidates and require separate global coverage, source and geographic review.','Sealed input bytes do not establish the correctness or acceptance of their source or decision metadata.','On-disk code hashes are change indicators, not proof of already-imported Python module bytes.']}
  result['shoreline_index']={'method':'exact-global-4neighbor-land-spans-v1','span_count':len(shore_index.starts),'coastal_cells':int(np.sum(shore_index.ends.astype(np.uint64)-shore_index.starts)),'storage_bytes':sum(a.nbytes for a in (shore_index.offsets,shore_index.starts,shore_index.ends,shore_index.codes)),'processing_elapsed_seconds':shore_elapsed}
  if shared_inputs is not None:result['shoreline_index']['reused_verified_generation']=True
  attempts=prior+[{'attempt_id':attempt_id,'processing_elapsed_seconds':time.perf_counter()-processing_started,'timing_complete':True}]
  result['timing_attempts']=attempts
  result['timing_complete']=all(x['timing_complete'] for x in attempts)
  result['recorded_processing_elapsed_seconds']=sum(x['processing_elapsed_seconds'] for x in attempts)
  result['processing_elapsed_seconds']=result['recorded_processing_elapsed_seconds'] if result['timing_complete'] else None
  result['timing_semantics']='Sum of recorded active invocation intervals; restart downtime excluded. An interrupted invocation has an unmeasured tail after its last durable checkpoint.'
  publish_record(root/'batch-complete.json',result);return result

CODE_SHA=sha(Path(__file__))

def main(argv=None, *, emit=print, shared_inputs=None):
 processing_started=time.perf_counter()
 ap=argparse.ArgumentParser(description=__doc__)
 for k in ('snapshot','snapshot-sha256','physical-rows','physical-rows-sha256','physical-runs','physical-runs-sha256','physical-report','physical-report-sha256','land-rows','land-rows-sha256','land-runs','land-runs-sha256','land-report','land-report-sha256','input-root','plan','plan-sha256','out'):ap.add_argument('--'+k,required=True)
 ap.add_argument('--workers',type=int,help='parallel independent tiles; defaults to available CPU count')
 ap.add_argument('--resume-from',action='append',help='read verified per-tile checkpoints from a preserved batch into a new --out; repeat for earlier attempts');ap.add_argument('--allow-unverified-snapshot',action='store_true');ap.add_argument('--allow-draft',action='store_true');ap.add_argument('--allow-selected-research-policy',action='store_true');a=ap.parse_args(argv)
 if not(a.allow_unverified_snapshot and a.allow_draft and a.allow_selected_research_policy):raise ValueError('all explicit research opt-ins are required')
 root=Path(a.input_root).resolve();out=Path(a.out).resolve();files={k:Path(getattr(a,k)).resolve() for k in ('snapshot','physical_rows','physical_runs','physical_report','land_rows','land_runs','land_report','plan')};expected={k:getattr(a,k+'_sha256') for k in files}
 if not root.is_dir() or any(not p.is_relative_to(root) for p in files.values()) or any(out==p or p.is_relative_to(out) for p in files.values()):raise ValueError('inputs must be inside input root and outside output')
 snapshot=decision_snapshot.read_snapshot(files['snapshot'],expected['snapshot'],allow_draft=True)
 plan=pinned_json(files['plan'],expected['plan']);width,height=131072,54614;validate_plan(plan,width,height)
 physical={'rows_sha256':expected['physical_rows'],'runs_sha256':expected['physical_runs']};land={'rows_sha256':expected['land_rows'],'runs_sha256':expected['land_runs'],'resolved_rows':files['land_rows'],'resolved_runs':files['land_runs']}
 def check_metadata():
  pinned_bytes(files['snapshot'],expected['snapshot']);pinned_bytes(files['plan'],expected['plan'])
  direct_lineage.validate_physical_report(files['physical_report'],expected['physical_report'],physical,width,height)
  direct_lineage.validate_direct_land(files['land_report'],expected['land_report'],physical,land,local_water_overlay.land_snapshot_hash(snapshot,expected['snapshot']),snapshot['decision_revision'],root,expected['physical_report'])
 grid={k:files[k] for k in ('physical_rows','physical_runs','land_rows','land_runs')};pins={k:expected[k] for k in grid}
 result=run_batch(snapshot,expected['snapshot'],grid,pins,plan,expected['plan'],out,width,height,check_metadata,metadata_pins={k:expected[k] for k in ('physical_report','land_report')},processing_started=processing_started,resume_from=a.resume_from,workers=a.workers,shared_inputs=shared_inputs)
 emit(json.dumps({'status':result['status'],'tiles':len(result['tiles']),'output':str(out)}))
if __name__=='__main__':main()

