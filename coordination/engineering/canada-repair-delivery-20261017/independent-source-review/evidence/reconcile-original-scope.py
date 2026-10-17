import json,gzip,pathlib,collections,subprocess,hashlib,bisect
ROOT=pathlib.Path('/workspace/scratch/127991fc8b8e');W=pathlib.Path.cwd();H=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip();sha=lambda b:hashlib.sha256(b).hexdigest()
def raw(p,h=H):return subprocess.check_output(['git','-c','protocol.allow=never','show',h+':'+p])
def pinned(p):
 b=raw(p['path'],p.get('commit',H));assert len(b)==p['bytes']and sha(b)==p['sha256'];return json.loads(b)
S=ROOT/'screen-complex-large-packages-20261017';b=(S/'gb-CAN-ADM3--repair-evaluation.json.gz').read_bytes();assert sha(b)=='de73b3cb9cb9dca404b5b306e68bf7acc805866b368dd534d35eb8beb75621a5';rows=json.loads(gzip.decompress(b));byrow=collections.defaultdict(list);kinds=collections.Counter();owners=collections.Counter();source_types=collections.Counter()
for y,a,z,os,ss,k in rows:
 assert z>a and len(os)==1 and len(set(ss))==len(ss)
 byrow[y].append((a,z,os[0],k));kinds[k]+=z-a;owners[os[0]]+=z-a
for y,rs in byrow.items():
 rs.sort();assert all(p[1]<=q[0]for p,q in zip(rs,rs[1:]))
source_receipts=[];cat=json.loads(raw('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json'));lookup={}
for k in ['gb:CAN:ADM1','gb:CAN:ADM2','gb:CAN:ADM3','gb:USA:ADM1']:
 p=next(p for p in cat['products'] if p['key']==k);bs=[]
 for q in p['parts']:
  b=raw(q['path']);assert len(b)==q['bytes']and sha(b)==q['sha256'];d=gzip.decompress(b);assert len(d)==q['uncompressed_bytes']and sha(d)==q['uncompressed_sha256'];bs.append(d)
 b=b''.join(bs);assert len(b)==p['original_bytes']and sha(b)==p['original_sha256'];x=json.loads(b);ids=[f['properties']['shapeID']for f in x['features']];assert len(ids)==len(set(ids))==p['feature_count'];source_receipts.append({key:p[key]for key in ['key','feature_count','original_bytes','original_sha256','recorded_license','source_represented_year_claim']});del b,x,bs
sel=json.loads(raw('data/ownership-selection.json'));rel=pinned(sel['additive_release']);patch=pinned(rel['logical_asset_map']['patch']);overlap=0
for r in patch['rows']:
 for a,z,o in r['runs']:
  for l,h,owner,k in byrow.get(r['y'],[]):overlap+=max(0,min(z,h)-max(a,l))
A=ROOT/'canada-repair-author-20261017';foreign=json.loads(gzip.decompress((A/'foreign-original-intervals.json.gz').read_bytes()));F={(y,x,os[0])for y,a,z,os,ss,k in foreign for x in range(a,z)};native=json.load(open(A/'native-aafc-screen.json'));N={(r['y'],r['x'],r['owner'])for r in native['held']};obs=json.loads(gzip.decompress((A/'aafc-point-observations.json.gz').read_bytes()));T={(y,x,o)for y,x,o,yes,other,no in obs if not yes};assert N==T
for y,x,o in F|N:assert any(a<=x<z and oo==o for a,z,oo,k in byrow[y])
out={'baseline':H,'source_originals':source_receipts,'territorial_original_features':sum(p['feature_count']for p in source_receipts),'territorial_original_bytes':sum(p['original_bytes']for p in source_receipts),'original_scope':{'cells':sum(kinds.values()),'intervals':len(rows),'owners':len(owners),'physical_classes':dict(kinds),'nonoverlapping_intervals':True},'current_accepted_cumulative_cells':sum(z-a for r in patch['rows']for a,z,o in r['runs']),'current_overlap_cells':overlap,'held_native_source_keys':{'foreign':len(F),'physical_mismatch':len(N),'intersection':len(F&N),'union':len(F|N),'all_inside_original':True,'shapely_native_agree':True},'limits':['Foreign and physical hold observations are independently reconciled against frozen original keys; this run authenticates complete territorial source bytes but does not repeat either geometry classifier.','438062 minus103 =437959 is only a preliminary ceiling, not a qualified repair total; remaining native physical/membership predicates remain mandatory.']};(W/'.scratch/scope-reconciliation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
