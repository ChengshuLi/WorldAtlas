"""Select exact existing full source-relative GSHHG result rows; no detector rerun."""
import gzip,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=ROOT.parents[2]
OLD=REPO/'coordination/engineering/global-physical-comparison-20261006'
scope=json.loads((ROOT/'inputs/immutable-scope-and-inputs.json').read_text())
want=set(scope['components']); found={}; files=[]
def sha(b):return hashlib.sha256(b).hexdigest()
for path in sorted((OLD/'results').glob('components-*.jsonl.gz')):
 raw=path.read_bytes(); decoded=gzip.decompress(raw)
 files.append({'path':str(path.relative_to(REPO)),'encoded_bytes':len(raw),'encoded_sha256':sha(raw),'decoded_bytes':len(decoded),'decoded_sha256':sha(decoded)})
 for line in decoded.splitlines():
  row=json.loads(line)
  if row.get('component_id') in want:
   if row['component_id'] in found:raise ValueError('Duplicate existing source row')
   found[row['component_id']]=(row,path)
if set(found)!=want:raise ValueError(f'Existing source row set differs; missing={len(want-set(found))}, extra={len(set(found)-want)}')
rows=[]
for cid in sorted(want):
 row,path=found[cid]
 rows.append({'existing_output_path':str(path.relative_to(REPO)),'component_id':cid,'row':row})
out=ROOT/'inputs/existing-physical-row-scope.json'
out.write_text(json.dumps({'source_comparison':'issue1261 complete GSHHG2.3.7 comparison, reused without rerun','source_readme_sha256':sha((OLD/'README.md').read_bytes()),'source_input_config_sha256':sha((OLD/'input-config.json').read_bytes()),'source_evidence_quality_sha256':sha((OLD/'evidence-quality.json').read_bytes()),'whole_output_files':files,'selected_whole_rows':rows,'selected_count':len(rows),'physical_authority':'unapproved','physical_status':'unknown-source-fitness-and-observation-date'},ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps({'selected':len(rows),'source_result_files':len(files),'receipt_bytes':out.stat().st_size,'receipt_sha256':sha(out.read_bytes())}))
