"""Publication gate: inspect every source role, name, geometry and hierarchy.

A machine audit cannot certify every historical/geographic judgement. The report
separates exhaustive structural checks from recorded source-selection decisions.
"""
import collections,gzip,hashlib,json,math,pathlib,re,tarfile,unicodedata
from shapely import STRtree
from shapely.geometry import shape,Point
ROOT=pathlib.Path(__file__).resolve().parents[1];D=ROOT/'data'
def read(p):return json.loads(p.read_text())
def validated_source_creations(features,data):
 """Accept new source land only through the installed, byte-pinned proof chain."""
 new={f['id']:f for f in features if f['properties']['metadata'].get('reference_version')!=3}
 if not new:return set()
 bundle=data/'macro-improvements/combined-restoration'
 installed=read(data/'publication-geography-receipt.json')
 raw=gzip.decompress((bundle/'aggregate-source-receipt.json.gz').read_bytes());receipt=json.loads(raw)
 assert hashlib.sha256(raw).hexdigest()==installed['sources']['sourceReceipt']['sha256'],'Creation receipt differs from installed proof'
 assert receipt['geometry_stage_validated'] is True and receipt['historical_claims_transferred'] is False
 assert receipt['after_footprints_sha256']==installed['after_footprints_sha256']
 proofs={p['location_id']:p for p in receipt['creation_proofs']}
 approved={f['id']:f for f in receipt['added_features']}
 assert len(proofs)==len(receipt['creation_proofs']) and len(approved)==len(receipt['added_features'])
 assert set(new)==set(proofs)==set(approved)==set(receipt['added_ids']),'Unreceipted source role'
 index=json.loads(gzip.decompress((bundle/'installation-proof-index.json.gz').read_bytes()))
 archive=bundle/index['archive']['path'];body=archive.read_bytes()
 assert index['history_transfer'] is False and len(body)==index['archive']['bytes'] and hashlib.sha256(body).hexdigest()==index['archive']['sha256']
 with tarfile.open(archive) as sources:
  for identifier,feature in new.items():
   assert feature==approved[identifier],f'Created feature differs from reviewed source record: {identifier}'
   assert feature['properties']['metadata'].get('reference_version') is None,'New source land must not impersonate a legacy version'
   proof=proofs[identifier];source=proof['source'];member=sources.getmember(source['path'])
   assert member.isfile() and not pathlib.PurePosixPath(member.name).is_absolute() and '..' not in pathlib.PurePosixPath(member.name).parts
   raw=sources.extractfile(member).read();assert hashlib.sha256(raw).hexdigest()==source['sha256']
   document=json.loads(raw);matches=[f for f in document.get('features',[document]) if f.get('id')==source['identity']]
   assert len(matches)==1 and matches[0]['geometry']==feature['geometry'],'Created footprint differs from exact named source'
   assert source['license'] and source['attribution'] and source['url'].startswith(('https://','http://'))
   assert source['supported_from']!=0 and source['supported_to']!=0 and source['supported_from']<source['supported_to']
   assert proof['identity_review']['status']=='distinct-new-territory'
 return set(new)
def area(g):
 pieces=list(g.geoms) if g.geom_type=='MultiPolygon' else [g]
 return sum(p.area*12364*math.cos(math.radians(p.representative_point().y)) for p in pieces)
fs=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']];units={u['id']:u for u in read(D/'hierarchy.json')};semantic=read(D/'semantic-report.json');policy=read(D/'location-policy.json');rows=[];issues=[];semantic_warnings=[];owners=collections.defaultdict(list);geoms=[]
created_source_ids=validated_source_creations(fs,D)
bad=re.compile(r'unnamed|unknown|unorganized|unorganised|unincorporated|^region\s+\d|^division\s*(?:no\.?\s*)?\d|^\d+$|^\?+$|^N/?A$|Not mapped|\*$|\ufffd',re.I)
assert len({f['id'] for f in fs})==len(fs)
for u in units.values():
 if not u['name'] or bad.search(u['name']):issues.append({'id':u['id'],'issue':'Unresolved hierarchy label','name':u['name']})
for f in fs:
 p=f['properties'];m=p['metadata'];g=shape(f['geometry']);geoms.append(g);a=area(g)
 if not g.is_valid or g.is_empty or g.geom_type not in ['Polygon','MultiPolygon']:issues.append({'id':f['id'],'issue':'Invalid polygon'})
 if bad.search(p['name']):
  target=semantic_warnings if m.get('name_evidence_status')=='unknown' else issues
  target.append({'id':f['id'],'name':p['name'],'issue':'Unresolved source label','source_name':m.get('original_source_name')})
 parent=p['parent_id'];chain=[]
 for level in ['province','area','region','subcontinent','continent']:
  assert parent in units,(f['id'],parent);u=units[parent];assert u['level']==level,(f['id'],level);chain.append(parent);parent=u['parent_id']
 assert parent is None and units[chain[-1]]['name']!='Antarctica'
 assert (m.get('source_name') and m.get('source_url') and m.get('reference_version')==3) or f['id'] in created_source_ids,f['id']
 row={'id':f['id'],'name':p['name'],'owner':p.get('reference_owner'),'area_km2':round(a,3),'basis':m.get('location_basis',m.get('source_role',m.get('administrative_level'))),'province_id':chain[0]};rows.append(row);owners[p.get('reference_owner') or 'Unknown reference owner'].append(a)
# Whole-world overlap check, including every new physical partition and seam.
tree=STRtree(geoms)
for i,g in enumerate(geoms):
 for j in tree.query(g,predicate='intersects'):
  j=int(j)
  if j>i and g.intersection(geoms[j]).area>1e-10:issues.append({'id':fs[i]['id'],'other':fs[j]['id'],'issue':'Overlapping interiors'})
for name,id in [('Hong Kong','atlas:territory:HKG'),('Singapore','atlas:territory:SGP'),('London','atlas:city:GBR-Greater London'),('Mumbai','atlas:city:IND-Mumbai')]:
 f=next((f for f in fs if f['id']==id),None)
 if f is None:issues.append({'id':id,'issue':'Missing coherent city territory'})
 if name in ['Hong Kong','Singapore'] and f and sum(x['properties'].get('reference_owner')==f['properties'].get('reference_owner') for x in fs)!=1:issues.append({'id':id,'issue':'Fragmented compact city territory'})
for change in semantic['changes']:
 if change['basis']=='Disconnected components of the same named source district':
  names={''.join(c for c in unicodedata.normalize('NFKD',n).casefold() if c.isalnum()) for n in change.get('source_names',[])}
  if len(names)!=1 or '' in names:issues.append({'id':change['id'],'issue':'Multipart merge combines distinct source district names','names':sorted(names)})
by_id={f['id']:f for f in fs}
# Independently published city memberships protect against partial ward unions.
for id,count in [('atlas:city:GBR-Greater London',33),('atlas:city:USA-New-York-City',5),('atlas:city:IND-Mumbai',2),('atlas:city:KOR-11',25),('atlas:city:KOR-10',16),('atlas:city:KOR-18',5),('atlas:city:TWN-1166',12),('atlas:city:TWN-1167',29),('atlas:city:TWN-1156',38),('atlas:city:TWN-1164',7)]:
 members=by_id.get(id,{}).get('properties',{}).get('metadata',{}).get('source_member_ids',[])
 if len(members)!=count:issues.append({'id':id,'issue':'Incomplete published city membership','expected':count,'actual':len(members)})
 if any(m in by_id for m in members):issues.append({'id':id,'issue':'City still has active constituent wards'})
for name,xy in [('Moscow',(37.613577,55.75411)),('Saint Petersburg',(30.314074,59.94096)),('Bishkek',(74.583258,42.875025)),('French Guiana',(-53,4)),('Reunion',(55.5,-21.1)),('Martinique',(-61,14.7)),('Mayotte',(45.15,-12.8)),('Svalbard',(16,78))]:
 hits=tree.query(Point(*xy),predicate='intersects')
 if len(hits)!=1:issues.append({'name':name,'issue':'Missing or duplicate reference territory coverage','matches':len(hits)})
assert len([u for u in units.values() if u['level']=='continent'])==6
counts={l:sum(u['level']==l for u in units.values()) for l in ['province','area','region','subcontinent','continent']}
report={'version':1,'scope':'Every active location: source role, label, polygon validity, overlap, complete single-parent hierarchy, area distribution. Country-level source decisions and all aggregation/refinement crosswalks are recorded separately. Geographic and historical truth are not certified by structural validation.','locations':len(fs),'counts':counts,'country_policies':len(policy['countries']),'issues':issues,'semantic_warnings':semantic_warnings,'checks':{'unique_ids':True,'hierarchy_complete':True,'six_continents':True,'overlap_pairs':sum(x['issue']=='Overlapping interiors' for x in issues),'unresolved_labels':sum(x['issue']=='Unresolved source label' for x in issues)},'countries':{o:{'locations':len(a),'min_km2':round(min(a),2),'median_km2':round(sorted(a)[len(a)//2],2),'max_km2':round(max(a),2)} for o,a in sorted(owners.items())},'locations_audited':rows,'coarse_units':[r for r in rows if r['area_km2']>50000],'small_units':[r for r in rows if r['area_km2']<25]}
report['input_sha256']={p:hashlib.sha256((D/p).read_bytes()).hexdigest() for p in ['world-index.json','hierarchy.json','location-policy.json','semantic-report.json','coverage-report.json','administrative-sources.json','granularity-report.json','semantic-sources.json','framework-sources/manifest.json','global-refinement-report.json','regional-membership-report.json','border-parent-review.json','reference-polity-report.json','macro-corrections.json']+read(D/'world-index.json')['parts']}
(D/'granularity-audit.json').write_text(json.dumps(report,ensure_ascii=False,separators=(',',':')))
h=read(D/'hierarchy-report.json');children=collections.Counter(f['properties']['parent_id'] for f in fs);children.update(u['parent_id'] for u in units.values() if u['parent_id']);h.update(locations=len(fs),counts=counts,missing_chains=0,whole_territory_units=[{'id':u['id'],'name':u['name'],'level':u['level']} for u in units.values() if u['level']=='province' and children[u['id']]==1]);(D/'hierarchy-report.json').write_text(json.dumps(h,ensure_ascii=False,separators=(',',':')))
print(json.dumps({'locations':len(fs),'counts':counts,'issues':len(issues),'coarse':len(report['coarse_units']),'small':len(report['small_units'])}),flush=True)
assert not issues,issues[:30]
