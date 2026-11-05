"""No-build provisional source-extent convention for two northern groups."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'regional-lydekker-rule-work')
from component_scan import scan
from regional_rule import Line
from regional_group_convention import apply_groups
R=Path.cwd();D=R/'regional-lydekker-rule-work'
def H(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
p=D/'current-selected170-rule-diagnostic.json';assert H(p)=='afbf8ac40503c509267c12f306bb92d6c0ab3ec6ccccbee4cef3f86bf084ad26';j=json.loads(p.read_bytes())
for k in ('proposals','review'):j[k]={int(r):v for r,v in j[k].items()}
pdf=R/'indonesia-geonames-research-20261105/pub164-official-r2-readback.pdf';assert H(pdf)=='f71a16ba2095e200a51edfc4a7ea8c029f284f56380f99f58bd65f6272f9d903'
source={'source_id':'nga-sailing-directions-pub164-project-copy','source_version':'2009-f71a16ba2095-official','sha256':H(pdf),'purpose':'Inferred whole-root geographic convention within described group extent; rectangle is not source proof of island membership.'}
linefile=R/'boo-boundary-broader-20261105/boo-east-candidate.json';assert H(linefile)=='bb7a9c4621646c98d25c4cc4685346fbb6bc468db6015f2d7a3926780c27a02e';line=Line({'type':'LineString','coordinates':json.loads(linefile.read_bytes())['coordinates']})
rows={'path':str(R/'fresh-components-output-20261104/rows.u32le'),'sha256':'4beda178bfc7beeb2d30cbdfa5901a48f9a41bb82c69e534d4c8cddfdb09aea7'};runs={'path':str(R/'fresh-components-output-20261104/runs.u32le'),'sha256':'18d7f36fa22c5728662cdd40487bf684108da030c074fec6d22ac378d0df0961'};grid=j['grid'];windows=[]
for name,bounds,section in [('kawio',[125+19/60,4+13/60,125+42/60,4+45/60],'1.9'),('sangihe',[125,2,126,4],'1.13-1.14')]:
 print('Scanning',name,flush=True);windows.append({'group_id':name,'code':18,'source':dict(source,section=section,extent=bounds),'components':scan(rows,runs,grid,bounds,line)})
out=apply_groups(j,windows);out['status']='provisional-sourced-extent-groups-not-selection';out['limitations'].append('Group extents are inferred whole-component conventions based on NGA geographic descriptions, not proof of source-named membership. Complete current pending-group exclusions remain unauthenticated.')
dest=D/'current-selected170-endpoint-groups-preview.json';assert not dest.exists();dest.write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');print('group stats',json.dumps(out['regional_group_diagnostics']),'new',len(out['regional_group_proposals']),'sha',H(dest),flush=True)
