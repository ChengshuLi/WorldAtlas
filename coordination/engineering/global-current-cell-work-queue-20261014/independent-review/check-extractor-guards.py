from pathlib import Path
import json,subprocess,shutil,tempfile
D=Path('/workspace/scratch/127991fc8b8e/global-unassigned-census-20261014');review=Path(__file__).parent;T=Path(tempfile.mkdtemp(prefix='relocated-selector-',dir=review));q=json.load(open(D/'source-package-queue.json'));pkg=next(p for p in q['packages'] if p['package_id']=='gb-LSO-ADM1--repair-evaluation'); shutil.copy(D/'source-batch-intervals.mjs',T/'source-batch-intervals.mjs');shutil.copy(D/'source-package-queue.json',T/'source-package-queue.json')
for f in q['input_sha256']: (T/f).symlink_to(D/f)
for b in pkg['native_blocks']:
 for pref in ['source-candidates','physical-support','inland-water-support']:
  f=f'{pref}-block-{b:03}.json.gz';(T/f).symlink_to(D/f)
def run(dest):return subprocess.run(['node','--max-old-space-size=512',str(T/'source-batch-intervals.mjs'),pkg['package_id'],str(T/dest)],capture_output=True,text=True)
good=run('successful-output');assert good.returncode==0,good.stderr
roster=T/'source-feature-roster.json';body=roster.read_bytes();roster.unlink();roster.write_bytes(body+b' ');bad_roster=run('bad-roster-output');assert bad_roster.returncode!=0 and 'Shared input hash mismatch: source-feature-roster.json' in bad_roster.stderr;roster.write_bytes(body)
block=T/'source-candidates-block-037.json.gz';body=block.read_bytes();block.unlink();block.write_bytes(body+b' ');bad_block=run('bad-block-output');assert bad_block.returncode!=0 and 'Encoded interval hash mismatch' in bad_block.stderr;block.write_bytes(body)
collision=run('successful-output');assert collision.returncode!=0 and 'EEXIST' in collision.stderr
assert not (T/'bad-roster-output'/'package.json').exists() and not (T/'bad-block-output'/'package.json').exists()
result={'package':pkg['package_id'],'relocated_module_relative_root':'pass','source_input_hash_guard':'pass','encoded_block_hash_guard':'pass','exclusive_output_collision_guard':'pass','no_completion_marker_on_failure':'pass','success_result':json.loads(good.stdout),'script_sha256':__import__('hashlib').sha256((T/'source-batch-intervals.mjs').read_bytes()).hexdigest(),'fixture':str(T)}
(review/'extractor-guard-review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
