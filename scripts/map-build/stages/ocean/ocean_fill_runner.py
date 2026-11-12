"""Command-line entry point for the ocean fill stage."""
import argparse,json,re,time
from pathlib import Path
from map_build.water.ocean.engine import run,sha,HEX

def main(argv=None, *, emit=print):
    processing_started=time.perf_counter()
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot','snapshot-sha256','physical-rows','physical-runs','prefill-dir','prefill-plan','out'):p.add_argument('--'+name,required=True)
    p.add_argument('--allow-unverified-snapshot',action='store_true');p.add_argument('--tile-height',type=int,default=256)
    p.add_argument('--allow-draft-snapshot',action='store_true');p.add_argument('--candidate-build');p.add_argument('--candidate-build-sha256')
    a=p.parse_args(argv)
    if not a.allow_unverified_snapshot:raise ValueError('authenticated Neon export is not verified by this runner; explicit test-only flag required')
    if not HEX.fullmatch(a.snapshot_sha256) or sha(a.snapshot)!=a.snapshot_sha256:raise ValueError('snapshot hash mismatch')
    snapshot=json.loads(Path(a.snapshot).read_text())
    if snapshot.get('source')=='local-user-directed-overlay-not-neon':
        from decision_snapshot import read_snapshot
        snapshot=read_snapshot(Path(a.snapshot),a.snapshot_sha256,allow_draft=a.allow_draft_snapshot)
    plan=json.loads(Path(a.prefill_plan).read_text())
    prefill=Path(a.prefill_dir).resolve();audit=json.loads((prefill/'prefill-audit.json').read_text());out=Path(a.out).resolve()
    sources=[Path(a.snapshot).resolve(),Path(a.prefill_plan).resolve(),Path(a.physical_rows).resolve(),Path(a.physical_runs).resolve(),prefill]
    if any(s==out or s.is_relative_to(out) or (s.is_dir() and out.is_relative_to(s)) for s in sources):raise ValueError('output must be separate from all inputs')
    if audit.get('source_plan_sha256')!=sha(a.prefill_plan) or audit.get('decision_snapshot_sha256')!=a.snapshot_sha256:raise ValueError('prefill audit plan/snapshot mismatch')
    if audit.get('decision_revision')!=snapshot.get('decision_revision',{}).get('id') or audit.get('entity_revision')!=snapshot.get('decision_revision',{}).get('entity_revision'):raise ValueError('prefill revision mismatch')
    status=snapshot.get('decision_revision',{}).get('status')
    candidate=None
    if status=='draft':
        if not a.allow_draft_snapshot or not a.candidate_build or not a.candidate_build_sha256:
            raise ValueError('draft run requires explicit opt-in and a pinned candidate build manifest')
        if not HEX.fullmatch(a.candidate_build_sha256) or sha(a.candidate_build)!=a.candidate_build_sha256:
            raise ValueError('candidate build manifest hash mismatch')
        candidate=json.loads(Path(a.candidate_build).read_text())
        if (candidate.get('schema')!='worldatlas-direct-candidate-build-v1' or candidate.get('status')!='unverified-research-not-published'
            or candidate.get('decision_snapshot_sha256')!=a.snapshot_sha256
            or candidate.get('decision_revision')!=snapshot.get('decision_revision',{}).get('id')
            or candidate.get('entity_revision')!=snapshot.get('decision_revision',{}).get('entity_revision')
            or candidate.get('physical_rows_sha256')!=sha(a.physical_rows)
            or candidate.get('physical_runs_sha256')!=sha(a.physical_runs)
            or candidate.get('physical_mask_sha256')!=audit.get('physical_mask_sha256')):
            raise ValueError('candidate build does not bind snapshot and physical grid')
    elif a.candidate_build or a.candidate_build_sha256:
        raise ValueError('candidate build manifest is only for draft research')
    expected_mask=candidate.get('physical_mask_sha256') if candidate else snapshot.get('build',{}).get('physical_grid_sha256')
    if audit.get('physical_mask_sha256')!=expected_mask or not HEX.fullmatch(str(expected_mask or '')):raise ValueError('physical grid revision pin mismatch')
    if (plan.get('decision_snapshot_sha256')!=a.snapshot_sha256 or plan.get('decision_revision')!=audit['decision_revision']
        or plan.get('entity_revision')!=audit['entity_revision']):raise ValueError('prefill plan decision binding mismatch')
    pr=plan['rle_inputs']['physical']; grid=plan['grid']; width,height=grid['width'],grid['height']
    if pr.get('physical_mask_sha256')!=audit['physical_mask_sha256']:raise ValueError('prefill plan physical mask binding mismatch')
    if (width,height)!=(131072,54614):raise ValueError('unexpected production grid')
    if candidate and (candidate.get('grid',{}).get('width')!=width or candidate.get('grid',{}).get('height')!=height):raise ValueError('candidate build grid mismatch')
    if sha(a.physical_rows)!=pr['rows_sha256'] or sha(a.physical_runs)!=pr['runs_sha256']:raise ValueError('physical file hash mismatch')
    output=audit['output'];rr=prefill/output['rows_path'];ru=prefill/output['runs_path']
    if not rr.resolve().is_relative_to(prefill) or not ru.resolve().is_relative_to(prefill) or sha(rr)!=output['rows_sha256'] or sha(ru)!=output['runs_sha256']:raise ValueError('prefill RLE path or hash mismatch')
    pins={'physical_rows_sha256':pr['rows_sha256'],'physical_runs_sha256':pr['runs_sha256'],'physical_mask_sha256':audit['physical_mask_sha256'],
          'prefill_rows_sha256':output['rows_sha256'],'prefill_runs_sha256':output['runs_sha256'],'prefill_audit_sha256':sha(prefill/'prefill-audit.json')}
    if candidate:pins['candidate_build_sha256']=a.candidate_build_sha256
    def verify_unchanged():
        checks=[(a.snapshot,a.snapshot_sha256),(a.prefill_plan,audit['source_plan_sha256']),
                (a.physical_rows,pr['rows_sha256']),(a.physical_runs,pr['runs_sha256']),
                (rr,output['rows_sha256']),(ru,output['runs_sha256']),
                (prefill/'prefill-audit.json',pins['prefill_audit_sha256'])]
        if candidate:checks.append((a.candidate_build,a.candidate_build_sha256))
        if any(sha(path)!=expected for path,expected in checks):raise ValueError('input changed during ocean fill')
    run(snapshot,a.snapshot_sha256,a.physical_rows,a.physical_runs,rr,ru,out,width,height,pins,a.tile_height,software_versions=candidate.get('software_versions',{}) if candidate else None,pre_finalize=verify_unchanged,processing_started=processing_started)
    emit(json.dumps({'status':'candidate-only','output':str(out),'summary_sha256':sha(out/'run-summary.json')}))

if __name__=='__main__':main()
