import json,gzip,pathlib,subprocess,collections,hashlib
W=pathlib.Path.cwd();H=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()
def raw(p):return subprocess.check_output(['git','-c','protocol.allow=never','show',H+':'+p])
def js(p):return json.loads(raw(p))
s=js('data/semantic-report.json'); changes={c['id']:c for c in s['changes']};assert len(changes)==len(s['changes']);canon={f['id']:f for n in (2,29)for f in js(f'data/geography/part-{n}.json')['features']if f['properties'].get('reference_owner')=='Canada'}
cat=js('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json');prod=next(p for p in cat['products']if p['key']=='gb:CAN:ADM3');b=b''.join(gzip.decompress(raw(p['path']))for p in prod['parts']);assert hashlib.sha256(b).hexdigest()==prod['original_sha256'];orig={'gb:CAN:ADM3:'+f['properties']['shapeID']for f in json.loads(b)['features']}
physical={c['id']:set(c['replaces'])for c in s['changes']if c['id'].startswith('atlas:physical:CAN-')};byarea=collections.defaultdict(set)
for k,v in physical.items():byarea[k.split(':')[-1]].update(v)
phys=set().union(*physical.values());nonphys=collections.defaultdict(set)
for c in s['changes']:
 if not c['id'].startswith('atlas:physical:CAN-'):
  for a in c.get('replaces',[]):
   if a in orig:nonphys[a].add(c['id'])
retired={r['id']for r in s['retired']if r['id']in orig};direct=set(canon)&orig
memo={}
def leaf(n,trail=()):
 if n in orig:return {n}
 assert n not in trail,('Cycle',n)
 if n in memo:return memo[n]
 c=changes.get(n);assert c,('Missing semantic node',n)
 members=c['replaces'];assert members and len(members)==len(set(members))
 result=set().union(*(leaf(m,(*trail,n))for m in members));memo[n]=result;return result
covered=collections.defaultdict(set)
for n in canon:
 for a in leaf(n):covered[a].add(n)
nonphys_exclusive=set(nonphys)-phys
out={'kind':'independent-complete-AAFC-remainder-roster-conservation','baseline':H,'canonical_Canada_nodes':len(canon),'complete_original_count':len(orig),'physical_nodes':len(physical),'physical_distinct_originals':len(phys),'physical_area_counts':{a:len(v)for a,v in byarea.items()},'physical_multiple_areas':len([a for a in phys if sum(a in v for v in byarea.values())>1]),'physical_and_nonphysical_overlap':{a:sorted(nonphys[a])for a in phys&nonphys.keys()},'nonphysical_distinct_originals':len(nonphys_exclusive),'retained_direct_originals':len(direct),'unclassified_originals':sorted(orig-phys-nonphys.keys()-direct),'missing_from_current_canonical_transitive_closure':sorted(orig-covered.keys()),'retired_originals':len(retired),'physical_missing_from_retired':sorted(phys-retired),'retired_missing_any_semantic_change':sorted(retired-phys-nonphys.keys()),'foreign_physical_members':sorted(phys-orig),'limits':['Whole-country provenance conservation tests identity inventory, not geometric partition, per-area legal scope, or physical authority. Physical source_member_ids remain intersection witnesses; union across all 273 physical nodes supplies the complete old-atom remainder roster, not individual target geometry.']}
(W/'.scratch/remainder-conservation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
