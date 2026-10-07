#!/usr/bin/env python3
"""Exercise the exact producer's valid and invalid input paths; retain concise receipts."""
import gzip, hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent; WORK=ROOT.parents[2]; INPUTS=ROOT/'inputs'; PRODUCER=ROOT/'produce.py'; PYTHON=Path(sys.executable).resolve()
METHOD='complete-source-overlay'
def sha(b): return hashlib.sha256(b).hexdigest()
def invoke(label, args, expected):
    with tempfile.TemporaryDirectory(prefix='worldatlas-1344-') as td:
        out=Path(td)/'output'
        cmd=[str(PYTHON),str(PRODUCER),'--inputs',str(INPUTS),'--output',str(out),*args]
        p=subprocess.run(cmd,cwd=WORK,text=True,capture_output=True)
    stderr=p.stderr.strip()
    try: receipt=json.loads(stderr.splitlines()[0])
    except Exception: receipt={'status':'unparseable','reason':stderr[:2000]}
    passed=p.returncode!=0 and receipt.get('status')=='rejected' and expected in receipt.get('reason','')
    return {'case':label,'command':cmd,'exit_code':p.returncode,'observed':receipt,'expected_reason_contains':expected,'outcome':'passed' if passed else 'failed'}
def main():
    features=json.loads(gzip.decompress((INPUTS/'baseline/candidate-source.gz').read_bytes()))['features']
    cand=next(f for f in features if f['id']=='physical-gap:1624:42:d40fef6eb0e28f8ab7556c90e2a934b6d2114f155c633c17d324cbf319058184')
    # Keep this modified candidate temporary: it is a synthetic rejection fixture, not evidence.
    with tempfile.TemporaryDirectory(prefix='worldatlas-1344-controls-') as td:
      over=Path(td)/'candidate-geometry.json'; altered=json.loads(json.dumps(cand)); altered['geometry']['coordinates'][0][0][0]+=0.000001; over.write_text(json.dumps(altered))
      metadata_over=Path(td)/'candidate-metadata.json'; metadata_altered=json.loads(json.dumps(cand)); point=metadata_altered['properties']['exact_location_contacts'][0]['geometry']['coordinates'][0][0]; point[0]=point[0]+0.000001; metadata_over.write_text(json.dumps(metadata_altered))
      cases=[invoke('missing-contact',['--control','omit-contact'],'candidate contact roster missing'),
             invoke('duplicate-contact',['--control','duplicate-contact'],'duplicate candidate contact ID'),
             invoke('foreign-subject',['--control','foreign-subject'],'candidate contact roster missing or foreign'),
             invoke('candidate-geometry-byte-change',['--candidate-override',str(over)],'candidate full feature binding mismatch'),
             invoke('candidate-same-geometry-contact-metadata-byte-change',['--candidate-override',str(metadata_over)],'candidate full feature binding mismatch')]
    # Reuse unchanged files by hard link; replace only the single tampered source product.
    with tempfile.TemporaryDirectory(prefix='worldatlas-1344-source-tamper-') as td:
      copied=Path(td)/'inputs'; shutil.copytree(INPUTS,copied,copy_function=shutil.copy2)
      product=copied/'source-products/geoBoundaries-BLR-ADM2_simplified.geojson'
      raw=bytearray(product.read_bytes()); original_sha=sha(raw); original_bytes=len(raw); offset=len(raw)//2; raw[offset]^=1; product.write_bytes(raw)
      changed_sha=sha(raw)
      cmd=[str(PYTHON),str(PRODUCER),'--inputs',str(copied),'--output',str(Path(td)/'out')]
      p=subprocess.run(cmd,cwd=WORK,text=True,capture_output=True)
      try: obs=json.loads(p.stderr.strip().splitlines()[0])
      except Exception: obs={'status':'unparseable','reason':p.stderr[:2000]}
      passed=p.returncode!=0 and obs.get('status')=='rejected' and 'whole-file custody mismatch' in obs.get('reason','')
      cases.append({'case':'changed-source-bytes','command_shape':['python',str(PRODUCER),'--inputs','temporary exact input-tree copy with one BLR byte changed','--output','temporary'],'exit_code':p.returncode,'fixture':{'path':'source-products/geoBoundaries-BLR-ADM2_simplified.geojson','original_bytes':original_bytes,'original_sha256':original_sha,'changed_sha256':changed_sha,'changed_byte_offset':offset},'observed':obs,'outcome':'passed' if passed else 'failed'})
    result={'method_id':METHOD,'kind':'negative-control','outcome':'passed' if all(c['outcome']=='passed' for c in cases) else 'failed','controls':cases}
    (ROOT/'controls/negative-control.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    one=json.loads((ROOT/'runs/run-one/run-summary.json').read_text()); two=json.loads((ROOT/'runs/run-two/run-summary.json').read_text())
    positive={'method_id':METHOD,'kind':'positive-control','outcome':'passed','run_one_source_custody_sha256':one['source_custody_sha256'],'run_two_source_custody_sha256':two['source_custody_sha256'],'run_one_summary_sha256':sha((ROOT/'runs/run-one/run-summary.json').read_bytes()),'run_two_summary_sha256':sha((ROOT/'runs/run-two/run-summary.json').read_bytes()),'scope':{'family_id':one['family_id'],'component_id':one['component_id'],'candidate_id':one['candidate_id'],'contact_count':one['complete_current_contacts']},'positive_result':'Both unmodified full source runs completed and produced identical generated output hashes.'}
    (ROOT/'controls/positive-control.json').write_text(json.dumps(positive,sort_keys=True,indent=2)+'\n')
    print(json.dumps(result,sort_keys=True))
    if result['outcome']!='passed': raise SystemExit(1)
if __name__=='__main__': main()
