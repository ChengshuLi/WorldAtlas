"""Reference geographic territories and political owners are separate identities."""
import json,pathlib,collections,re,csv
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
features=read(R/'.cache/ne_10m_admin_0_countries.json')['features'];byname={};byiso={}
for f in features:
 p=f['properties']
 for key in ['ADMIN','NAME','NAME_LONG']:byname[p[key]]=p
 for key in ['ADM0_A3','ISO_A3_EH','ISO_A3']:
  if p.get(key) and p[key]!='-99':byiso[p[key]]=p
for row in csv.DictReader((R/'.cache/country-codes.csv').open()):
 ref=byiso.get(row['ISO3166-1-Alpha-3'])
 if ref:
  for key in ['official_name_en','UNTERM English Short','CLDR display name']:
   if row.get(key):byname.setdefault(row[key],ref)
counts=collections.Counter()
for part in read(D/'world-index.json')['parts']:
 x=read(D/part)
 for f in x['features']:
  p=f['properties'];m=p['metadata'];ref=byname.get(p['reference_owner']) or byiso.get(m.get('regional_match',{}).get('reference_iso'))
  if not ref:
   match=re.search(r'(?:natural-earth:|atlas:city:)([A-Z]{3})-',m.get('source_id',''));ref=byiso.get(match[1]) if match else None
  if not ref:continue
  name=None if ref['TYPE']=='Indeterminate' else ref['SOVEREIGNT'] if ref['TYPE'] in ['Country','Dependency','Lease'] and ref['SOVEREIGNT'] in byname else ref['ADMIN'];owner=byname.get(name,ref)
  m['reference_polity']=name;m['reference_owner_id']=('owner:'+owner['WIKIDATAID'] if owner.get('WIKIDATAID') and owner['WIKIDATAID']!='-99' else 'owner:reference:'+owner['ADM0_A3']) if name else None
  m['reference_polity_status']='disputed' if name is None else 'reference';m['reference_polity_evidence']={'source':'Natural Earth pinned administrative and sovereignty reference; dates vary','source_url':'https://github.com/nvkelso/natural-earth-vector/tree/ca96624a56bd078437bca8184e78163e5039ad19','reference_territory':ref['ADMIN'],'classification':ref['TYPE'],'note':ref.get('NOTE_BRK'),'uncertainty':bool(ref.get('NOTE_BRK') or ref['BRK_DIFF'])};counts[name or 'unresolved']+=1
 write(D/part,x)
write(D/'reference-polity-report.json',{'scope':'All matched modern reference territories. Dependencies/SARs inherit the cited reference polity; indeterminate territories remain unresolved. Dated direct evidence takes precedence. This is not a verified 2026 political snapshot.','owners':dict(counts)})
print('Modern reference polity assignments:',sum(counts.values()),'unresolved:',counts['unresolved'])
