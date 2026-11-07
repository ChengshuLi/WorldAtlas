#!/usr/bin/env python3
"""Bounded overlay diagnostic: replay proposals against historical draft163/V7 pairs.

No map output. This does not infer current geography: unproposed roots remain at
historical draft163 for calculation only. A root's whole-component effects
outside the box are not represented. The prior line-side labels and claims in
coverage.json are expressly ignored.
"""
import argparse, collections, hashlib, json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
COVERAGE=ROOT/'lydekker-regional-coverage-20261105/report.json'
SPARSE=ROOT/'sparse-residual163-20261105/residual-spans.jsonl'
SPARSE_REPORT=ROOT/'sparse-residual163-20261105/report.json'
EXPECTED_LINE='lydekker-anu-figure81-regional-boo-east-v2'
EXPECTED_GEOMETRY='87514ff08498fa2e2a27bfe2f0a1026511b3c5f01acfbaecbf1f753392c33655'
EXPECTED_COMPONENT={'rows':'4beda178bfc7beeb2d30cbdfa5901a48f9a41bb82c69e534d4c8cddfdb09aea7','runs':'18d7f36fa22c5728662cdd40487bf684108da030c074fec6d22ac378d0df0961'}
EXPECTED_BOX=[115.0,-12.0,145.0,8.0]

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for chunk in iter(lambda:f.read(8<<20),b''): h.update(chunk)
 return h.hexdigest()

def compare(coverage,proposals):
 totals=collections.Counter(); root_results=[]
 for item in coverage['components']:
  root=item['root']; proposal=proposals.get(root)
  before=after=changed=improved=regressed=0
  for pair in item['pairs']:
   n=pair['cells']; old=pair['draft163_code']; reference=pair['v7_code']; new=proposal['code'] if proposal else old
   before+=n*(old!=reference);after+=n*(new!=reference);changed+=n*(new!=old)
   improved+=n*(old!=reference and new==reference);regressed+=n*(old==reference and new!=reference)
  assert after==before-improved+regressed
  totals.update({'baseline_mismatch':before,'overlay_mismatch':after,'changed':changed,'improved':improved,'regressed':regressed})
  if before or after or changed:
   root_results.append({'root':root,'baseline_mismatch':before,'overlay_mismatch':after,'changed':changed,'improved':improved,'regressed':regressed,'proposal':proposal})
 return totals,root_results

def main():
 ap=argparse.ArgumentParser();ap.add_argument('result',type=Path);ap.add_argument('output',type=Path); args=ap.parse_args()
 assert not args.output.exists()
 c=json.loads(COVERAGE.read_bytes()); s=json.loads(SPARSE_REPORT.read_bytes()); result=json.loads(args.result.read_bytes())
 assert sha(COVERAGE)=='7a82beeab97bfe0874bff5c88b85210996e67b9ee889abdf129770c97b116133'
 assert c['box_lonlat']==EXPECTED_BOX and len(c['components'])==6486 and len({i['root'] for i in c['components']})==6486
 assert sum(i['cells_in_box'] for i in c['components'])==15263342
 assert all(sum(p['cells'] for p in i['pairs'])==i['cells_in_box'] for i in c['components'])
 assert result['regional_bounds']==EXPECTED_BOX and result['line_id']==EXPECTED_LINE and result['geometry_sha256']==EXPECTED_GEOMETRY and result['component_input_sha256']==EXPECTED_COMPONENT
 assert sha(SPARSE)==s['spans_sha256'] and s['residual_cells']==9585 and s['distinct_component_roots']==551
 # Validate that the pair data and sparse historical residual describe exactly the
 # same root-wise mismatch footprint within the box, independent of old line sides.
 step=360/131072; lo=math.ceil((115+180)/step-.5);hi=math.ceil((145+180)/step-.5); sparse=collections.Counter()
 for line in SPARSE.open():
  o=json.loads(line); lat=90-(o['row']+.5)*step
  if -12<=lat<=8:
   n=max(0,min(o['end'],hi)-max(o['start'],lo));sparse[o['component_id']]+=n
 sparse=+sparse
 pair_roots={i['root']:sum(p['cells'] for p in i['pairs'] if p['draft163_code']!=p['v7_code']) for i in c['components']}
 assert {k:v for k,v in pair_roots.items() if v}==dict(sparse) and sum(sparse.values())==2147 and len(sparse)==536
 proposals={int(k):v for k,v in result['proposals'].items()}; roots={i['root'] for i in c['components']}
 assert set(proposals)<=roots and all(type(v['code']) is int and v['code'] in (18,22) and isinstance(v['basis'],str) for v in proposals.values())
 totals,per_root=compare(c,proposals)
 output={'status':'bounded-historical-overlay-diagnostic-not-map','comparison_box_lonlat':EXPECTED_BOX,'baseline_revision':'v7-list1-wgs84-draft-163','reference':'historical V7; comparison only, not geographic authority','assignment_revision':result.get('decision_revision'),'assignment_snapshot_sha256':result.get('snapshot_sha256'),'line_id':EXPECTED_LINE,'geometry_sha256':EXPECTED_GEOMETRY,'component_input_sha256':EXPECTED_COMPONENT,'proposal_roots':len(proposals),'review_roots':len(result['review']),'counts':dict(totals),'roots_with_overlay_mismatch':sum(bool(r['overlay_mismatch']) for r in per_root),'roots_changed':sum(bool(r['changed']) for r in per_root),'roots':per_root,'input_sha256':{'coverage_report':sha(COVERAGE),'sparse_report':sha(SPARSE_REPORT),'sparse_spans':sha(SPARSE),'assignment_result':sha(args.result)},'limitations':['Applies proposals to the historical draft163 grid, not the current Neon map. Unproposed or review roots retain historical values only for this diagnostic.','Window only: whole-component changes outside this box are excluded. Physical-mask differences are excluded.','Historical V7 is a comparison baseline, not a source of geographic truth.','The old line-side labels and historical claims stored in the coverage report are ignored.','Does not select decisions, write a grid, rebuild, or publish a map.']}
 args.output.write_text(json.dumps(output,sort_keys=True,indent=2)+'\n'); print(json.dumps({k:output[k] for k in ('counts','proposal_roots','review_roots','roots_with_overlay_mismatch','roots_changed')},indent=2))
if __name__=='__main__': main()
