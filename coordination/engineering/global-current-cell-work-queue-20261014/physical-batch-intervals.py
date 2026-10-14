"""Export an exact physical investigation scope. Python standard library only; no ownership edits."""
import argparse,gzip,hashlib,json,time
from pathlib import Path
P=argparse.ArgumentParser(description=__doc__);P.add_argument('package_id',nargs='?');P.add_argument('output',nargs='?',type=Path);P.add_argument('--data',type=Path,default=Path(__file__).resolve().parent);P.add_argument('--verify-all',action='store_true');args=P.parse_args();D=args.data;started=time.monotonic();sha=lambda b:hashlib.sha256(b).hexdigest()
queue=json.loads((D/'physical-package-queue.json').read_bytes());packages=queue['packages'];byid={p['package_id']:p for p in packages}
def checked(pin):
 raw=(D/pin['path']).read_bytes()
 if len(raw)!=pin['bytes'] or sha(raw)!=pin['sha256']:raise ValueError('Whole input hash/length mismatch: '+pin['path'])
 return raw
def checked_rows(pin):
 if not pin.get('parts'):return json.loads(gzip.decompress(checked(pin)))
 rows=[];prior=-1
 for part in pin['parts']:
  raw=gzip.decompress(checked(part))
  if len(raw)!=part['decoded_bytes'] or sha(raw)!=part['decoded_sha256']:raise ValueError('Decoded transport part differs: '+part['path'])
  for row in json.loads(raw):
   if not part['row_start']<=row['y']<part['row_end'] or row['y']<=prior:raise ValueError('Overlapping or foreign transport row')
   rows.append(row);prior=row['y']
 canonical=(json.dumps(rows,separators=(',',':'))+'\n').encode()
 if len(canonical)!=pin['decoded_bytes'] or sha(canonical)!=pin['decoded_sha256']:raise ValueError('Reconstructed logical source block differs')
 return rows
def merge(rs):
 result=[]
 for a,b in sorted((r[0],r[1]) for r in rs):
  if result and a<=result[-1][1]:result[-1][1]=max(result[-1][1],b)
  else:result.append([a,b])
 return result
def subtract(physical,covered):
 out=[];j=0
 for lo,hi in physical:
  while j<len(covered) and covered[j][1]<=lo:j+=1
  k=j;at=lo
  while k<len(covered) and covered[k][0]<hi:
   a,b=covered[k]
   if a>at:out.append([at,min(a,hi)])
   at=max(at,b)
   if at>=hi:break
   k+=1
  if at<hi:out.append([at,hi])
 return out
def derived(pin):
 land=json.loads(gzip.decompress(checked(pin['physical_input'])));territorial=checked_rows(pin['territorial_input']);coverage={r['y']:merge(r['runs']) for r in territorial};out=[]
 for row in land:
  runs=subtract(row['runs'],coverage.get(row['y'],[]))
  if runs:out.append({'y':row['y'],'runs':runs})
 canonical=(json.dumps(out,separators=(',',':'))+'\n').encode()
 if sha(canonical)!=pin['derived_canonical_sha256']:raise ValueError('Derived physical-only intervals differ: block '+str(pin['block']))
 return out
def selected(rows,selector):
 for row in rows:
  y=row['y']
  if not selector['row_start']<=y<selector['row_end']:continue
  for a,b in row['runs']:
   a=max(a,selector['x_start']);b=min(b,selector['x_end'])
   if a<b:yield [y,a,b]
if args.verify_all:
 scopes=[p for p in packages if p['accounting_role']=='disjoint-counted-global-work-domain'];facts={r['block']:r for p in scopes for r in p['input_blocks']};counts={p['package_id']:0 for p in scopes};segments={p['package_id']:0 for p in scopes}
 for block,pin in sorted(facts.items()):
  rows=derived(pin);total=sum(b-a for r in rows for a,b in r['runs']);assigned=0
  for p in scopes:
   if block not in p['native_blocks']:continue
   for y,a,b in selected(rows,p['selector']):counts[p['package_id']]+=b-a;segments[p['package_id']]+=1;assigned+=b-a
  if assigned!=total:raise ValueError('Incomplete or duplicated package coverage in block '+str(block))
 for p in scopes:
  if counts[p['package_id']]!=p['native_cells'] or segments[p['package_id']]!=p['interval_segments']:raise ValueError('Package accounting mismatch '+p['package_id'])
 report={'pass':True,'current_commit':queue['current_commit'],'packages_checked':len(scopes),'whole_blocks_derived_and_hash_checked':len(facts),'exact_disjoint_cells':sum(counts.values()),'counts':counts,'seconds':time.monotonic()-started,'method':'Independently derive physical-only from complete physical-support minus complete territorial interval union, check canonical hashes and exact disjoint package counts.'};print(json.dumps(report));raise SystemExit(0)
if args.package_id not in byid or args.output is None:P.error('Provide a known package_id and a new output directory, or use --verify-all.')
p=byid[args.package_id];args.output.mkdir(parents=True,exist_ok=False);count=0;segments=0;records=[]
if p['category']=='excluded-domain-policy-review':
 records=[m for m in json.loads(checked(p['evidence']['special_source_records'])) if m['category']=='excluded-antarctica']
 if len(records)!=p['excluded_source_records']:raise ValueError('Incomplete excluded source roster')
elif p['category']=='invalid-source-coverage-investigation':
 records=[m for m in json.loads(checked(p['evidence']['special_source_records'])) if m['id']==2380]
 with gzip.open(args.output/'intervals.jsonl.gz','wt',encoding='utf-8') as f:
  for pin in p['input_blocks']:
   for row in json.loads(gzip.decompress(checked(pin))):
    for a,b in row['runs']:f.write(json.dumps([row['y'],a,b],separators=(',',':'))+'\n');count+=b-a;segments+=1
 if count!=p['envelope_cells']:raise ValueError('Unknown envelope count mismatch')
else:
 with gzip.open(args.output/'intervals.jsonl.gz','wt',encoding='utf-8') as f:
  for pin in p['input_blocks']:
   for y,a,b in selected(derived(pin),p['selector']):f.write(json.dumps([y,a,b],separators=(',',':'))+'\n');count+=b-a;segments+=1
 if count!=p['native_cells'] or segments!=p['interval_segments']:raise ValueError('Exported package scope mismatch')
if records:(args.output/'source-records.json').write_text(json.dumps(records,indent=2)+'\n')
(args.output/'package.json').write_text(json.dumps(p,indent=2)+'\n');manifest={'package_id':p['package_id'],'current_commit':queue['current_commit'],'queue_sha256':sha((D/'physical-package-queue.json').read_bytes()),'extracted_scope_cells':count,'counted_global_work_cells':p['native_cells'] if p['accounting_role']=='disjoint-counted-global-work-domain' else 0,'known_repair_cells':None,'interval_segments':segments,'source_records':len(records),'accounting_role':p['accounting_role'],'seconds':time.monotonic()-started,'files':[]}
for file in sorted(args.output.iterdir()):
 if file.is_file():raw=file.read_bytes();manifest['files'].append({'path':file.name,'bytes':len(raw),'sha256':sha(raw)})
(args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest))
