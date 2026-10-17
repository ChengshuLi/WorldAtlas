import json,subprocess,pathlib,gzip,collections,hashlib
W=pathlib.Path.cwd();H=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()
def raw(p,h=H):return subprocess.check_output(['git','-c','protocol.allow=never','show',h+':'+p])
def js(p,h=H):return json.loads(raw(p,h))
canon={f['id']:f for p in ['data/geography/part-2.json','data/geography/part-29.json']for f in js(p)['features']};lineage=js('data/semantic-report.json');sem=collections.defaultdict(list);forward=collections.defaultdict(list)
for c in lineage['changes']:
 sem[c['id']].append(c)
 for m in c.get('replaces',[]):forward[m].append(c['id'])
sel=js('data/ownership-selection.json');rel=js(sel['additive_release']['path']);rp=rel['logical_asset_map']['owner_roster'];roster=json.loads(gzip.decompress(raw(rp['path'],rp['commit'])));owners={r['id']:(i+1,r)for i,r in enumerate(roster)}
cat=js('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json');product=next(p for p in cat['products']if p['key']=='gb:CAN:ADM3');source=b''.join(gzip.decompress(raw(p['path']))for p in product['parts']);originals={'gb:CAN:ADM3:'+f['properties']['shapeID']:f for f in json.loads(source)['features']};assert len(originals)==product['feature_count']
errors=[]
def backward(n,trail=(),canonical=False):
 if n in trail:raise ValueError('Cycle '+n)
 if n in originals:return {n}
 cs=sem[n]
 if canonical and n in canon:members=canon[n]['properties']['metadata'].get('source_member_ids')
 else:
  assert len(cs)==1,('Missing/duplicate semantic identity',n)
  members=cs[0]['replaces']
 assert members and len(members)==len(set(members)),('Missing/duplicate members',n)
 out=set()
 for m in members:out.update(backward(m,(*trail,n),canonical))
 return out

def walk(n,trail=()):
 if n in trail:raise ValueError('Cycle '+n)
 if n in owners:
  assert n in canon,('Terminal canonical missing',n)
  return {n}
 edges=forward[n];assert edges and len(edges)==len(set(edges)),('Missing/duplicate descendant',n)
 out=set()
 for c in edges:
  assert len(sem[c])==1,('Duplicate semantic descendant',c)
  out.update(walk(c,(*trail,n)))
 return out
failures=json.load(open(W/'.scratch/prefilter-membership-result.json'))['failures'];reports=[];terminals=set()
for f in failures:
 n=f['source_id']
 try:
  reached=walk(n);observed=set()
  for i,c in canon.items():
   if c['properties'].get('reference_owner')!='Canada':continue
   try:
    if n in backward(i,canonical=True):observed.add(i)
   except AssertionError as e:raise AssertionError(('Incomplete Canada canonical reverse inventory',i,str(e)))
  assert reached==observed,('Forward/canonical expanded inventory differs',n,sorted(reached),sorted(observed))
  terminals.update(reached);reports.append({'source_id':n,'descendants':sorted(reached),'ancestor_nodes':sorted({n,*reached}),'complete_against_selected_canonical':True})
 except Exception as e:errors.append({'source_id':n,'error':str(e)})
checks=[]
for n in sorted(terminals):
 c=sem[n][0];p=canon[n]['properties'];m=p.get('metadata',{});leaves=backward(n);fields={'canonical_id':p.get('id')==n,'complete_members':sorted(m.get('source_member_ids',[]))==sorted(c['replaces']),'basis':m.get('location_basis')==c.get('basis'),'source_url':m.get('source_url')==c.get('source'),'parent':p.get('parent_id')==owners[n][1].get('province_id'),'all_atoms_in_complete_family':leaves<=originals.keys()};checks.append({'id':n,'source_id':m.get('source_id'),'parent_id':p.get('parent_id'),'owner_parent_id':owners[n][1].get('province_id'),'atomic_members':len(leaves),'checks':fields})
out={'kind':'independent-complete-negative-ancestry-screen','baseline':H,'negative_sources':len(failures),'closed_sources':len(reports),'terminal_descendants':len(terminals),'source_errors':errors,'terminal_checks':checks,'closed':reports,'limits':['Establishes accepted source-member graph closure only; source_member_ids of physical locations are intersection witnesses. No positive territorial allocation or partition coverage follows.','This graph screen is not a revised constructor and does not relax current rejection. All complete original negative polygons remain the veto operands.']};(W/'.scratch/negative-closure-screen.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items()if k not in ['closed','terminal_checks']},indent=2));print('TERMINAL_MISMATCHES',json.dumps([c for c in checks if not all(c['checks'].values())],indent=2))
