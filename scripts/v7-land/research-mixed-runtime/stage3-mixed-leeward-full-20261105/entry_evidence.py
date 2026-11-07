"""Authenticate revision-bound human-reviewed List 1 citations, never selectors."""
import hashlib,re
from pathlib import Path
H=re.compile(r'^[0-9a-f]{64}$')
def need(x,m):
 if not x: raise ValueError(m)
def text(x): return isinstance(x,str) and bool(x.strip()) and len(x)<=8192

def resolve(snapshot,compiled,files):
 links=snapshot.get('list1_entry_evidence_sources',[])
 need(isinstance(links,list) and len(links)<=10000,'invalid evidence links')
 need(isinstance(files,list) and len(files)<=10000,'invalid evidence files')
 def keyed(items):
  d={}
  for x in items:
   need(isinstance(x,dict) and text(x.get('source_id')) and text(x.get('version')),'invalid evidence source')
   k=(x['source_id'],x['version']);need(k not in d,'duplicate evidence source');d[k]=x
  return d
 sources=keyed(snapshot.get('sources',[]));assets=keyed(snapshot.get('source_lineage_assets',[]));local=keyed(files);deps=snapshot.get('source_lineage_dependencies');need(isinstance(deps,list) and all(isinstance(d,dict) for d in deps),'source lineage missing')
 allowed=set(compiled['entry_ids']);keys=set();used=set();result={eid:[] for eid in allowed}
 for l in links:
  need(isinstance(l,dict) and set(l)=={'decision_revision','entry_id','role','source_id','source_version','citation_section','interpretation','limitations'},'invalid evidence link shape')
  eid=l['entry_id'];k=(l['source_id'],l['source_version']);uid=(eid,l['role'],*k,l['citation_section'])
  need(l['decision_revision']==compiled['revision'] and eid in allowed and l['role']=='geographic_membership_evidence' and all(text(l[x]) for x in ('source_id','source_version','citation_section','interpretation')) and isinstance(l['limitations'],list) and l['limitations'] and len(l['limitations'])<=100 and all(text(x) for x in l['limitations']) and uid not in keys,'invalid or duplicate evidence link')
  keys.add(uid);s=sources.get(k);a=assets.get(k);f=local.get(k)
  need(all(isinstance(x,dict) for x in (s,a,f)),'missing linked evidence source')
  need(set(f)=={'source_id','version','path','sha256','size_bytes','r2_bucket','r2_key'},'invalid evidence file pin')
  need(all(type(x.get('size_bytes')) is int for x in (s,a,f)),'invalid evidence size pins')
  for field in ('sha256','size_bytes','r2_bucket','r2_key'):
   need(s.get(field)==a.get(field)==f.get(field),'evidence catalog pin mismatch')
  prov=a.get('provenance');need(isinstance(prov,dict),'invalid raw evidence metadata')
  representation=prov.get('representation')
  need(representation in ('provider_original','third_party_mirror_scan','official-repository capture','official-repository original','HTML source capture'),'invalid raw evidence metadata')
  if representation in ('official-repository capture','official-repository original','HTML source capture'):
   need(text(prov.get('verification')) and text(prov.get('reuse_terms')),'invalid captured-source provenance')
  if representation=='third_party_mirror_scan':
   limits=prov.get('limitations')
   need(text(prov.get('scope')) and text(prov.get('verification')) and isinstance(limits,list) and 0<len(limits)<=100 and all(text(x) for x in limits),'invalid mirror provenance')
  need(a.get('kind')=='raw' and not any((d.get('source_id'),d.get('version'))==k for d in deps) and text(a.get('source_uri')) and text(a.get('provider')) and text(a.get('attribution')) and text(a.get('license_name')) and text(a.get('license_uri')) and isinstance(s['sha256'],str) and H.fullmatch(s['sha256']) and type(s['size_bytes']) is int and 0<s['size_bytes'] and text(s['r2_bucket']) and text(s['r2_key']),'invalid raw evidence metadata')
  item={'role':l['role'],'source_id':k[0],'source_version':k[1],'source_sha256':s['sha256'],'source_uri':a['source_uri'],'provider':a['provider'],'attribution':a['attribution'],'license_name':a['license_name'],'license_uri':a['license_uri'],'citation_section':l['citation_section'],'interpretation':l['interpretation'],'interpretation_status':'selected_interpretation','verification_limitation':'Source bytes are checked; cited section and interpretation are not machine-verified.','limitations':l['limitations']}
  if representation in ('official-repository capture','official-repository original','HTML source capture'):
   item.update(source_representation=representation,source_provenance_verification_claim=prov['verification'],source_reuse_terms_claim=prov['reuse_terms'],source_provenance_limitation='Source provenance and reuse terms are catalog claims, not independently authenticated by byte checks.')
  if representation=='third_party_mirror_scan':
   item.update(source_representation=representation,source_provenance_scope=prov['scope'],source_provenance_verification_claim=prov['verification'],source_provenance_limitations=list(prov['limitations']),original_provider_bytes_limitation='The byte check does not establish that this third-party scan is identical to original-provider bytes.',license_limitation='The cataloged license URI does not itself establish redistribution rights.')
  result[eid].append(item)
  used.add(k)
 need(set(local)==used,'unused or missing evidence file')
 for k in sorted(used):
  f=local[k];p=Path(f['path']).resolve(strict=True);need(p.is_file(),'evidence file missing');h=hashlib.sha256();size=0
  with p.open('rb') as stream:
   while True:
    b=stream.read(1<<20)
    if not b:break
    size+=len(b);need(size<=f['size_bytes'],'evidence size exceeded');h.update(b)
  need(size==f['size_bytes'] and h.hexdigest()==f['sha256'],'evidence bytes mismatch')
 return {eid:sorted(v,key=lambda x:(x['source_id'],x['source_version'],x['citation_section'])) for eid,v in sorted(result.items())}
