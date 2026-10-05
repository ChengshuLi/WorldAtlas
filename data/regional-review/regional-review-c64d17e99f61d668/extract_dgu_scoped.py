#!/usr/bin/env python3
"""Re-extract scoped Croatia unit identity evidence from the pinned DGU GML.

First restore source/official-croatia/dgu-inspire-administrative-units.zip
from the official ATOM URL in dgu-inspire-administrative-units-atom.xml.
The large archive is intentionally not committed; this extractor requires its
exact SHA-256 and fails closed if it changes. It retains only names, IDs, level,
county parent, and effective-date metadata for scoped units; no geometries.
"""
import difflib, hashlib, json, pathlib, unicodedata, zipfile, xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parent
SRC=ROOT/'source'/'official-croatia'
SCOPE=json.loads((ROOT/'scope.json').read_text())
IDS=[x for x in SCOPE['member_location_ids'] if x.startswith('gb:HRV:ADM2:')]
COUNTY={
 'framework:province:pozega-slavonia:9c0b252675e1':'Požeško-slavonska županija',
 'framework:province:virovitica-podravina:05b25891ba1e':'Virovitičko-podravska županija',
 'framework:province:brod-posavina:ed1f1a57cc5b':'Brodsko-posavska županija',
 'framework:province:osijek-baranja:150cf19feca3':'Osječko-baranjska županija',
 'framework:province:vukovar-syrmia:063bde629720':'Vukovarsko-srijemska županija'}
def norm(s):
 s=unicodedata.normalize('NFKD',s or '')
 return ''.join(c for c in s if not unicodedata.combining(c)).casefold().replace('opcina ','').replace('grad ','').strip()
def sha_file(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
zip_path=SRC/'dgu-inspire-administrative-units.zip'
expected='4a6b9f23e438861f2462b0d6aa06bd4140112e82947a4cdee06ce7a3b40ae23f'
if not zip_path.is_file() or sha_file(zip_path)!=expected: raise SystemExit('Restore exact DGU archive; missing or SHA-256 differs')
atlas={}
for f in (ROOT.parents[2]/'data'/'geography').glob('part-*.json'):
 for x in json.loads(f.read_text())['features']:
  if x['id'] in IDS: atlas[x['id']]=x['properties']
source_path=SRC/'dgu-inspire-administrative-units-atom.xml'
ET.parse(source_path) # ensure retained ATOM source still parses
if len(atlas)!=len(IDS): raise SystemExit('Atlas target scope mismatch')
name_by_id={}
source=json.loads((ROOT/'source'/'geoboundaries-9469f09'/'HRV'/'ADM2'/'geoBoundaries-HRV-ADM2.geojson').read_text())
for f in source['features']:
 p=f['properties']; key=f"gb:HRV:ADM2:{p['shapeID']}"
 if key in IDS: name_by_id[key]=p['shapeName']
want={}
for key,name in name_by_id.items(): want.setdefault(norm(name),[]).append(key)
rows={k:[] for k in IDS}; near={k:[] for k in IDS}
archive_size=zip_path.stat().st_size; archive_sha=sha_file(zip_path)
gml_sha=hashlib.sha256(); root_meta={}; gml_name='AdministrativeUnit.gml'; feature_count=matched_total=third_order=0
with zipfile.ZipFile(zip_path) as z:
 with z.open(gml_name) as stream:
  for event,elem in ET.iterparse(stream,events=('start','end')):
   if event=='start' and not root_meta and elem.tag.endswith('}FeatureCollection'):
    root_meta={k:elem.attrib.get(k) for k in ('numberMatched','numberReturned','timeStamp','next')}
   if event=='end' and elem.tag=='{http://www.opengis.net/wfs/2.0}member':
    feature_count+=1
    unit=next((x for x in elem if x.tag.endswith('}AdministrativeUnit')),None)
    if unit is not None:
     vals=lambda suf:[e.text for e in unit.iter() if e.tag.endswith(suf) and e.text]
     level=next((e.attrib.get('{http://www.w3.org/1999/xlink}href','').rsplit('/',1)[-1] for e in unit.iter() if e.tag.endswith('}nationalLevel')),None)
     if level=='3rdOrder':
      third_order+=1
      names=vals('}text')
      county=next((e.attrib.get('{http://www.w3.org/1999/xlink}title') for e in unit.iter() if e.tag.endswith('}upperLevelUnit')),None)
      rec={'official_name':names[0] if names else None,'national_code':next(iter(vals('}nationalCode')),None),'inspire_local_id':next(iter(vals('}localId')),None),'dgu_gml_id':unit.attrib.get('{http://www.opengis.net/gml/3.2}id'),'level':level,'parent_title':county,'valid_from':next(iter(vals('}beginLifespanVersion')),None)}
      for n in names:
       cands=want.get(norm(n),[])
       matches=[k for k in cands if COUNTY.get(atlas[k].get('parent_id'))==county]
       if len(matches)==1: rows[matches[0]].append(rec)
      # Keep a near-name candidate only when it belongs to the exact target county.
      for k in IDS:
       if rows[k] or COUNTY.get(atlas[k].get('parent_id'))!=county: continue
       a=norm(name_by_id[k]); b=norm(rec['official_name'])
       if difflib.SequenceMatcher(None,a,b).ratio()>=0.90: near[k].append(rec)
    elem.clear()
    member=elem
    member.clear()
# Hash the uncompressed official source member independently of the scoped extract.
with zipfile.ZipFile(zip_path) as z, z.open(gml_name) as f:
 for b in iter(lambda:f.read(1024*1024),b''): gml_sha.update(b)
province={x['id']:x['name'] for x in SCOPE['province_scopes']}
items=[]
for k in IDS:
 items.append({'atlas_location_id':k,'geoBoundaries_name':name_by_id[k],'atlas_parent_province':province.get(atlas[k].get('parent_id')),'official_matches':rows[k]})
near_clean={k:v for k,v in near.items() if v and not rows[k]}
out={'notice':'Derived scoped extract; geometry omitted. Extracted from DGU INSPIRE GML using municipality/city 3rdOrder names and county parent titles. DGU open data terms require source attribution and a modification statement.','attribution':'State Geodetic Administration (DGU), Republic of Croatia, Open Data. Source dataset: INSPIRE Administrative Units, GML 3.2.1, ETRS89/LAEA.','modification_statement':'Only scoped Croatia name/code/level/parent/date metadata is retained; geometries and out-of-scope units are omitted. No extracted name/code/level/parent/date value was edited.','retrieved_at':'2026-10-05','source_url':'https://geoportal.dgu.hr/services/atom/INSPIRE_Administrative_Units_(AU).zip','source_atom_url':'https://geoportal.dgu.hr/services/atom/au/xml','archive_sha256':archive_sha,'archive_bytes':archive_size,'gml_member_name':gml_name,'gml_member_bytes':z.getinfo(gml_name).file_size,'gml_member_sha256':gml_sha.hexdigest(),'gml_features_returned':feature_count,'gml_declared_number_returned':int(root_meta.get('numberReturned','0')),'gml_features_matched':int(root_meta.get('numberMatched','0')),'gml_return_count_consistent':feature_count==int(root_meta.get('numberReturned','0')),'gml_time_stamp':root_meta.get('timeStamp'),'gml_next_page_url':root_meta.get('next'),'gml_3rd_order_in_returned_page':third_order,'scope_rows':items,'near_name_candidates':near_clean}
if archive_sha!=expected or feature_count!=int(root_meta.get('numberMatched','0')) or feature_count!=50192 or len([x for x in rows.values() if len(x)==1])!=126 or len(near_clean)!=1: raise SystemExit(f'Scoped DGU extraction totals differ: returned={feature_count}, matches={sum(len(x)==1 for x in rows.values())}, near={near_clean}')
out_path=SRC/'dgu-scoped-unit-crosswalk.json'; out_path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'archive_sha256':archive_sha,'gml_sha256':gml_sha.hexdigest(),'actual_feature_members':feature_count,'declared_numberReturned':out['gml_declared_number_returned'],'matched':out['gml_features_matched'],'return_count_consistent':out['gml_return_count_consistent'],'3rdOrder_returned_page':third_order,'exact_target_matches':sum(len(v)==1 for v in rows.values()),'unmatched_ids':[k for k,v in rows.items() if not v],'near_candidates':near_clean},ensure_ascii=False,indent=2))
