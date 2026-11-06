"""Pin exact rerun parity and raster coverage for wrapped research water."""
import hashlib,json
from pathlib import Path
ORIGINAL='wgs84-coastal-4neighbor-center-v2 (research, not an approved decision)'
WRAPPED='wgs84-wrapped-certified-with-streamed-full-fallback-v1 (research, not an approved decision)'
REFERENCE='8ca9ec9dda142ffca121ffeb5afa2d29aa76cb43b82810ceb37ab834facd3917'
VERIFIER='12b36078109460436cd89f8aa95b75e780224618c848de39992ea2fd5a8e620c'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def read(spec,key,base,root):
 item=spec.get(key);need(isinstance(item,dict) and set(item)=={'path','sha256'},'missing wrapped evidence')
 p=Path(item['path']);p=p if p.is_absolute() else base/p;p=p.resolve();need(p.is_relative_to(root.resolve()) and p.is_file() and sha(p)==item['sha256'],'wrapped evidence pin mismatch');return json.loads(p.read_bytes())
def need(x,msg):
 if not x:raise ValueError(msg)
def validate(manifest,manifest_sha,spec,base,root):
 audit=manifest.get('nearest_assignment_audit') or {};method=audit.get('shore_method')
 if method==ORIGINAL:
  need(not any(k in audit for k in ('index_optimization','wrapped_bounds_sha256','streamed_fallback_sha256','wrapped_narrow_cells','wrapped_fallback_cells','wrapped_full_fallback_cells')),'original method has wrapped optimization metadata')
  return
 need(method==WRAPPED and manifest.get('source',{}).get('decision_id')=='seavox-24119','unsupported wrapped method');need(isinstance(spec,dict) and set(spec)=={'comparison','coverage'},'missing wrapped evidence')
 comp=read(spec,'comparison',base,root);proof=read(spec,'coverage',base,root);tile=manifest['tiles'][0]['span_file']['sha256'];result=proof.get('result',{});src=manifest['source'];tot={'cells':manifest['physical_water_cells'],'spans':manifest['span_count'],'rows':manifest['row_count']}
 need(comp.get('schema')=='worldatlas-bering-full-rerun-comparison-v1' and comp.get('status')=='complete-research-not-published' and comp.get('all_rows_and_spans_equal') is True and comp.get('reference_manifest_sha256')==REFERENCE and comp.get('candidate_manifest_sha256')==manifest_sha and comp.get('candidate_span_sha256')==tile and comp.get('reference_span_sha256')==tile and comp.get('candidate_totals')==tot and comp.get('reference_totals')==tot and comp.get('counts',{}).get('different_rows')==0,'wrapped comparison mismatch')
 need(proof.get('schema')=='worldatlas-bering-independent-raster-coverage-proof-v1' and proof.get('status')=='raster-to-span-match' and proof.get('manifest_sha256')==manifest_sha and proof.get('verifier_sha256')==VERIFIER and proof.get('policy_sha256')==src['policy_sha256'] and proof.get('physical_rows_sha256')==src['physical_rows_sha256'] and proof.get('physical_runs_sha256')==src['physical_runs_sha256'] and result.get('status')=='raster-to-span-match' and result.get('cells')==tot['cells'] and result.get('spans')==tot['spans'] and result.get('assignment_sha256')==tile and result.get('raster_sha256')==manifest['rasterization']['source_mask_sha256'],'wrapped coverage mismatch')
