"""Aggregate evidence quality across every member, never just the last member."""
import collections,json,pathlib
r=pathlib.Path(__file__).resolve().parents[1];d=r/'data'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
u={x['id']:x for x in read(d/'hierarchy.json')};h=read(d/'hierarchy-report.json');low=collections.defaultdict(list)
for part in read(d/'world-index.json')['parts']:
 for f in read(d/part)['features']:
  m=f['properties']['metadata'];overlap=m.get('framework_overlap',m.get('prefecture_overlap',1))
  if overlap<.8:low[f['properties']['parent_id']].append({'id':f['id'],'overlap':overlap})
for x in u.values():
 m=x['metadata'];source=m['source'];reasons=m.get('review_reasons',[]);m['review_reasons']=reasons;count=m.get('child_count',0)
 if x['level'] in ['province','area'] and count==1 and not any('Single-child' in r for r in reasons):reasons.append('Single-child tier: geographic role requires individual review')
 if x['level']=='province' and count>25 and not any('25 locations' in r for r in reasons):reasons.append('More than 25 locations: review intermediate geographic groupings')
 if m['framework_status']=='retained-reference':
  m['source_url']='https://github.com/tdwg/wgsrpd' if 'WGSRPD' in source or 'Brummitt' in source else 'https://www.geoboundaries.org/'
 if 'ISTAT' in source:m['source_url']='https://maps.regione.umbria.it/server/rest/services/Hosted/Sistemi_Locali_del_Lavoro_2011_2018/FeatureServer/2'
 if x['id'] in low:
  reason='Some member locations overlap their reference parent by less than 80%'
  if reason not in reasons:reasons.append(reason)
  m['low_overlap_members']=low[x['id']]
  if m['framework_status']=='source-backed':m['framework_status']='review-required'
h['review_queue']=[{'id':x['id'],'name':x['name'],'level':x['level'],'children':x['metadata']['child_count'],'reasons':x['metadata']['review_reasons'],'source':x['metadata']['source']} for x in u.values() if x['metadata']['review_reasons']]
h['source_counts']=dict(collections.Counter(x['metadata']['framework_status'] for x in u.values()))
h['semantic_review_complete']=False
write(d/'hierarchy.json',list(u.values()));write(d/'hierarchy-report.json',h)
print(json.dumps({'review_groups':len(h['review_queue']),'low_overlap_groups':len(low),'source_counts':h['source_counts']}))

for name in ['sources.json','granularity-report.json','location-policy.json']:
 p=d/name;x=read(p);x['framework_refinement']={'version':4,'source_manifest':'framework-sources/manifest.json','report':'hierarchy-report.json','italy':'610 named ISTAT local labour systems replace the 107 province-sized reference locations; original administrative sources remain parent crosswalk evidence.','review':'Remaining semantic tier reviews are enumerated, not certified complete.'};write(p,x)
