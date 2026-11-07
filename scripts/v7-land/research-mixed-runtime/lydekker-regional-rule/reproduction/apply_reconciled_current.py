#!/usr/bin/env python3
"""Read-only whole-component rule with current snapshot and archived replay."""
import hashlib,importlib.util,json,sys
from pathlib import Path
R=Path.cwd();D=R/'regional-lydekker-rule-work';sys.path.insert(0,str(D))
from regional_rule import SOURCE_ID,SOURCE_VERSION,SOURCE_PDF_SHA256
from regional_workflow import research,APPROVED_LINE_ID,APPROVED_GEOMETRY

def H(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(8<<20),b''):h.update(c)
 return h.hexdigest()
def J(p):return json.loads(Path(p).read_bytes())
p=D/'reconstructed-current-selected170.json';assert H(p)=='1f4a21b9468b7434813648ae8dc6b8784d8b0858ab23af2f57c461ac5ef043cd';x=J(p)
file=R/'boo-boundary-broader-20261105/boo-east-candidate.json';assert H(file)=='bb7a9c4621646c98d25c4cc4685346fbb6bc468db6015f2d7a3926780c27a02e';geom={'type':'LineString','coordinates':J(file)['coordinates']}
obs={'line_id':APPROVED_LINE_ID,'geometry_sha256':APPROVED_GEOMETRY,'geometry':geom,'source_id':SOURCE_ID,'source_version':SOURCE_VERSION,'status':'research','provenance':{'source_pdf_sha256':SOURCE_PDF_SHA256}}
pairpath=R/'pr4-mixed-runtime-preserve-20261105/scripts/v7-land/research-mixed-runtime/stage2-geodesic-20261104';sys.path.insert(0,str(pairpath));from run_pair import run_pair
mp=R/'aegean-archive-containment-integrated-20261105/group-label-multipolygon-prototype/mixed_claims.py';assert H(mp)=='1800e87cc53f597ed4f6e58be41ba8b35f7370e2408f30b5856146c6e24264bc';spec=importlib.util.spec_from_file_location('mixed_runtime',mp);mixed=importlib.util.module_from_spec(spec);spec.loader.exec_module(mixed)
rows={'path':str(R/'fresh-components-output-20261104/rows.u32le'),'sha256':'4beda178bfc7beeb2d30cbdfa5901a48f9a41bb82c69e534d4c8cddfdb09aea7'};runs={'path':str(R/'fresh-components-output-20261104/runs.u32le'),'sha256':'18d7f36fa22c5728662cdd40487bf684108da030c074fec6d22ac378d0df0961'};grid={'width':131072,'height':54614,'west':-180,'north':90,'step':360/131072};bounds=[115,-12,145,8]
source={'path':str(R/'indonesia-geonames-research-20261105/r2-readback.zip'),'sha256':'2a1966f22f1eda5b099270b8382b93fe347a81b3f858b891349da7d4c9fe3718','source_id':'geonames-country-id','source_version':'2026-11-05-2a1966f22f1e','country':'ID'}
print('Applying whole-component rule and satellite convention',flush=True)
out=research(rows,runs,grid,bounds,obs,x['compiled'],J(R/'shared-regional-replay-20261105/snapshot170.raw.json'),x['reports'],set(x['protected_roots']),mixed,run_pair,None,line_pin={'line_id':APPROVED_LINE_ID,'geometry_sha256':APPROVED_GEOMETRY},max_satellite_cells=20,max_gap_m=5000,pending_claims=(),anchor_source=source)
out.update(status='current-snapshot-reconciled-archived-resolvers-provisional-rule-not-selection',snapshot_sha256=x['snapshot_sha256'],replay_reconciliation_sha256=H(p),limitations=x['limitations']+['20-cell and 5-km nearest-island thresholds are provisional operational assumptions, not source-defined group membership.','GeoNames point-on-land does not itself prove the physical component identity.','No complete set of source-pending group conflicts was supplied; review outputs before selection.'])
dest=D/'current-selected170-rule-diagnostic.json';assert not dest.exists();dest.write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');print('wrote',dest,'sha256',H(dest),flush=True)
