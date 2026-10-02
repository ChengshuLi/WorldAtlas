"""Aggregate every member's evidence quality; report-only audits preserve geography."""
import argparse,collections,copy,hashlib,json,pathlib
r=pathlib.Path(__file__).resolve().parents[1];d=r/'data'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
def main(data,report_only=True):
 u={x['id']:copy.deepcopy(x) for x in read(data/'hierarchy.json')};h=read(data/'hierarchy-report.json');low=collections.defaultdict(list);children=collections.Counter()
 inputs=['hierarchy.json','world-index.json']+read(data/'world-index.json')['parts']
 hashes={p:hashlib.sha256((data/p).read_bytes()).hexdigest() for p in inputs}
 for part in read(data/'world-index.json')['parts']:
  for f in read(data/part)['features']:
   children[f['properties']['parent_id']]+=1
   m=f['properties']['metadata'];overlap=m.get('framework_overlap',m.get('prefecture_overlap',1))
   if overlap<.8:low[f['properties']['parent_id']].append({'id':f['id'],'overlap':overlap})
 for x in u.values():
  if x['parent_id']:children[x['parent_id']]+=1
 for x in u.values():
  m=x['metadata'];source=m.get('source','');reasons=m.setdefault('review_reasons',[]);count=children[x['id']];m['child_count']=count
  if x['level'] in ['province','area'] and count==1 and not any('Single-child' in reason for reason in reasons):reasons.append('Single-child tier: geographic role requires individual review')
  if x['level']=='province' and count>25 and not any('25 locations' in reason for reason in reasons):reasons.append('More than 25 locations: review intermediate geographic groupings')
  if m.get('framework_status')=='retained-reference':m['source_url']='https://github.com/tdwg/wgsrpd' if 'WGSRPD' in source or 'Brummitt' in source else 'https://www.geoboundaries.org/'
  if 'ISTAT' in source:m['source_url']='https://maps.regione.umbria.it/server/rest/services/Hosted/Sistemi_Locali_del_Lavoro_2011_2018/FeatureServer/2'
  if x['id'] in low:
   reason='Some member locations overlap their reference parent by less than 80%'
   if reason not in reasons:reasons.append(reason)
   m['low_overlap_members']=low[x['id']]
   if m.get('framework_status')=='source-backed':m['framework_status']='review-required'
 h['review_queue']=[{'id':x['id'],'name':x['name'],'level':x['level'],'children':x['metadata']['child_count'],'reasons':x['metadata']['review_reasons'],'source':x['metadata'].get('source')} for x in u.values() if x['metadata']['review_reasons']]
 h['source_counts']=dict(collections.Counter(x['metadata'].get('framework_status','unclassified') for x in u.values()));h['semantic_review_complete']=False
 h['framework_audit']={'mode':'report-only' if report_only else 'metadata-update','input_sha256':hashes,'scope':'Current hierarchy and all member locations; derived diagnostics do not alter frozen source assessments. Earlier migration narrative retains its original snapshot.'}
 for p,expected in hashes.items():
  if hashlib.sha256((data/p).read_bytes()).hexdigest()!=expected:raise ValueError('Input changed during audit: '+p)
 if not report_only:
  write(data/'hierarchy.json',list(u.values()))
  for name in ['sources.json','granularity-report.json','location-policy.json']:
   p=data/name;x=read(p);x['framework_refinement']={'version':4,'source_manifest':'framework-sources/manifest.json','report':'hierarchy-report.json','italy':'610 named ISTAT local labour systems replace the 107 province-sized reference locations; original administrative sources remain parent crosswalk evidence.','review':'Remaining semantic tier reviews are enumerated, not certified complete.'};write(p,x)
 write(data/'hierarchy-report.json',h)
 print(json.dumps({'mode':h['framework_audit']['mode'],'review_groups':len(h['review_queue']),'low_overlap_groups':len(low),'source_counts':h['source_counts']}))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--data',type=pathlib.Path,default=d);mode=parser.add_mutually_exclusive_group();mode.add_argument('--report-only',dest='report_only',action='store_true');mode.add_argument('--update-metadata',dest='report_only',action='store_false',help='Explicit legacy mutation; invalidates frozen prepared asset hashes');parser.set_defaults(report_only=True);args=parser.parse_args();main(args.data,args.report_only)
