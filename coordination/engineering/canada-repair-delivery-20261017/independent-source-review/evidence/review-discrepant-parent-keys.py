exec(open('.scratch/review-archived-parent-discrepancies.py').read().split('mismatches=json.load')[0])
import numpy as np,collections
from shapely import points,STRtree
D=pathlib.Path('/workspace/scratch/127991fc8b8e/canada-repair-author-20261017');A=pathlib.Path((D/'workspace.txt').read_text().strip());screen=json.load(open(D.parent/'screen-complex-large-packages-20261017/screening.json'));package=next(x for x in screen['results']if x['package']['primary_source']=='gb:CAN:ADM3');owners={o['index']:o for o in package['owners']};wanted={6636:'New Brunswick',6643:'Ontario'};sel=js('data/ownership-selection.json');manifest=js(sel['manifest_path']);lp=manifest['native_latitudes'];lb=subprocess.check_output(['git','-c','protocol.allow=never','show',lp['commit']+':'+lp['path']]);assert hashlib.sha256(lb).hexdigest()==lp['sha256'];ld=gzip.decompress(lb);assert hashlib.sha256(ld).hexdigest()==lp['decoded_sha256'];lat=np.frombuffer(ld,dtype='<f8');rows=collections.defaultdict(list)
for f in (A/'.scratch/frozen-repair').glob('block-*.gz'):
 for y,a,b,ow,s,c in json.load(gzip.open(f)):
  if ow[0]in wanted:rows[ow[0]].extend((y,x)for x in range(a,b))
reports=[];held=[];tree=STRtree([g for p,g in admin1])
for owner,name in wanted.items():
 coords=sorted(rows[owner]);ps=points([(x+.5)/262166*360-180 for y,x in coords],[lat[y]for y,x in coords]);matches=tree.query(ps,predicate='intersects');bykey=collections.defaultdict(list)
 for pi,fi in zip(*matches):bykey[int(pi)].append(admin1[int(fi)][0]['shapeName'])
 counts=collections.Counter();contrary=[];absent=[]
 for i,key in enumerate(coords):
  names=bykey[i];bad=[n for n in names if n!=name];counts['all']+=1;counts['intended']+=name in names;counts['no_ADM1']+=not names;counts['other_ADM1']+=bool(bad)
  if bad:contrary.append({'y':key[0],'x':key[1],'owner':owner,'other_names':bad});held.append(contrary[-1])
  if not names:absent.append({'y':key[0],'x':key[1],'owner':owner})
 reports.append({'id':owners[owner]['id'],'owner':owner,'counts':dict(counts),'contrary':contrary,'source_absence':absent})
foreign=json.load(gzip.open(D/'foreign-original-intervals.json.gz'));foreigntot=collections.Counter()
for y,a,b,ow,s,c in foreign:foreigntot[(ow[0],owners[ow[0]]['id'])]+=b-a
out={'kind':'bounded-discrepant-parent-original-key-screen','baseline':H,'source_pins':pins,'counts':{k:sum(r['counts'][k]for r in reports)for k in ['all','intended','no_ADM1','other_ADM1']},'targets':reports,'foreign_complete_original_contacts':[{'owner':i,'id':n,'cells':v,'physical':owners[i]['target_properties']['metadata'].get('source_id','').startswith('aafc:')}for (i,n),v in foreigntot.items()],'limits':['Exact original keys screened using Shapely only; full native confirmation remains independent. Source absence is not itself an automatic veto or evidence of legal territory.']};(W/'.scratch/discrepant-parent-keys.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({**{k:v for k,v in out.items()if k!='targets'},'targets':[{k:v for k,v in r.items()if k not in ['source_absence']}for r in reports]},indent=2))
