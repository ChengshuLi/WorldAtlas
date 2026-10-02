#!/usr/bin/env python3
"""Prepare read-only, source-pinned macro conventions and whole-territory proposals."""
import argparse, collections, hashlib, json, pathlib, sys
from shapely.geometry import shape, box, mapping, Polygon
from shapely.ops import unary_union, linemerge
from ellipsoidal_area import area

RIVER_SHA='bb854a900ecbd3b408df46d5e16e3e0f974ba55993f9d8b5c26e855273c0905a'
RIVER_URL='https://raw.githubusercontent.com/nvkelso/natural-earth-vector/ca96624a56bd078437bca8184e78163e5039ad19/geojson/ne_10m_rivers_lake_centerlines.geojson'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def stable(level,name): return 'atlas:macro-boundary:'+level+':'+hashlib.sha256(name.encode()).hexdigest()[:16]
def majority(a,b):
 if a > .5+1e-8 and b <= .5: return 'first'
 if b > .5+1e-8 and a <= .5: return 'second'
 return None

def river_mask(features,name):
 """Longest downstream path. Source branch stubs never become a fictitious divide."""
 merged=linemerge(unary_union([shape(f['geometry']) for f in features if f['properties'].get('name')==name]))
 segments=list(getattr(merged,'geoms',[merged])); main=sorted(segments,key=lambda s:s.length,reverse=True)
 if name=='Ural':
  # Natural Earth's lake/river intersections create short branches. Join the two
  # substantive main-channel segments at their exact common source coordinate.
  a,b=main[:2]; ca=list(a.coords); cb=list(b.coords)
  if ca[0]==cb[-1]: coords=cb+ca[1:]
  elif ca[-1]==cb[0]: coords=ca+cb[1:]
  else: raise ValueError('Pinned Ural main segments no longer meet exactly')
  if coords[0][1]<coords[-1][1]: coords.reverse()
  west=40; coords += [(west,coords[-1][1]),(west,coords[0][1]),coords[0]]
  mask=Polygon(coords); domain=box(40,mask.bounds[1],70,mask.bounds[3]); uncertainty=0
 else:
  # Suez source lake endpoints differ by ~84m. Explicitly retain that source
  # generalization, test a conservative 150m corridor around the entire line.
  paths=main[:3]; points=[]
  for line in paths:
   cs=list(line.coords)
   if cs[0][1]<cs[-1][1]: cs.reverse()
   points.append(cs)
  points.sort(key=lambda cs:cs[0][1],reverse=True); coords=[]
  for cs in points: coords += cs
  west=30; mask=Polygon(coords+[(west,coords[-1][1]),(west,coords[0][1]),coords[0]])
  domain=box(30,mask.bounds[1],36,mask.bounds[3]); uncertainty=.0016
 if not mask.is_valid: raise ValueError('Invalid source-derived divide polygon: '+name)
 return mask,domain,uncertainty

# These are declared geographic reporting conventions, not inferred ownership,
# drainage-basin borders, dated administration, or claims of universal agreement.
POLICIES={
'Africa': ('Africa mainland west of the Suez isthmus, African shelf islands and the listed Atlantic/Indian archipelago associations. Sinai is Asian. Socotra remains African by physical shelf/continental-fragment association. Azores are proposed for the European North Atlantic association; Madeira, Canaries and Cape Verde remain African. Southern remote-island associations are explicit exceptions to continental land.', ['africa','continental-boundaries','socotra','macaronesia','subantarctic']),
'Asia': ('Eurasian land east of the Ural mountain divide/Ural river and south of the Greater Caucasus crest, Anatolia east of the Turkish Straits, Sinai, Asian shelf islands and Wallacea. All New Guinea and its adjacent Sahul islands belong to Oceania irrespective of Indonesian sovereignty. Cyprus remains in Western Asia. Cocos and Christmas remain Asian Indian Ocean associations near the Sunda/Indian Ocean island system, irrespective of Australian ownership.', ['continental-boundaries','urals','ural-river','great-caucasus','sinai','new-guinea','wallacea','cyprus','cocos','christmas']),
'Europe': ('Western Eurasian peninsula west of the Ural divide/Ural river and north of the Greater Caucasus crest; Thrace west of the Turkish Straits. European Mediterranean and North Atlantic archipelago association includes Iceland, Svalbard and the proposed Azores assignment. Aegean island association is by named archipelago/geographic convention rather than sovereignty.', ['europe','continental-boundaries','urals','ural-river','great-caucasus','azores']),
'North America': ('North American mainland, Greenland and associated Arctic/North Atlantic islands, Central American isthmus north of the Darien divide, and Caribbean archipelagos. Bermuda is North Atlantic, outside the Caribbean subcontinent. Clipperton is a separately declared eastern-Pacific association. Mexico is wholly North American under this continental convention.', ['north-america','continental-boundaries','panama','bermuda','clipperton']),
'South America': ('Mainland south of the Darien isthmus transition and associated Galapagos/Falkland/South Georgia archipelagos. Caribbean island groups remain in North America even where their present owner is a South American state. Rapa Nui remains Polynesian/Oceanian regardless of Chilean ownership.', ['south-america','continental-boundaries','panama','polynesia','subantarctic']),
'Oceania': ('Australia and Zealandia; all New Guinea, Bismarck/Solomon archipelagos, and Melanesian, Micronesian and Polynesian island groups. Asian Wallacea is excluded. Hawaii and Rapa Nui are Polynesian irrespective of their political owners. The four listed southern Indian Ocean archipelagos are a declared reporting association after Antarctica exclusion, not continental shelf claims.', ['oceania','new-guinea','wallacea','melanesia','micronesia','polynesia','subantarctic']),
'Atlantic Islands': ('Remote African-associated South Atlantic archipelagos: Saint Helena, Ascension, Tristan da Cunha and Bouvet. This is a noncontiguous oceanic reporting group, not continental land; Bouvet is an explicit subantarctic exception.', ['continental-boundaries','subantarctic']),
'Central Africa': ('West-central African Gulf of Guinea/Congo-basin transition grouping. Its present Rwanda/Burundi membership is a botanical legacy exception, not proof that these East African Rift territories are central-African basins; propose their East African parent correction.', ['africa','great-lakes']),
'Eastern Africa': ('East African Rift/Great Lakes and Horn/Nile–northeast African geographic reporting group. Chad is a documented northeast/Sahel transition exception inherited from the source, not claimed as Horn of Africa. Socotra is included by African shelf association; propose Rwanda and Burundi into the East African Great Lakes branch.', ['africa','great-lakes','chad-geography','socotra']),
'Northern Africa': ('Mediterranean/Saharan mainland grouping west of Suez plus African-associated Macaronesia. Excludes Sinai. Azores move to the European North Atlantic association, while Madeira/Canary/Cape Verde archipelagos remain here. This is neither Arab political membership nor a vegetation map.', ['africa','sinai','macaronesia','continental-boundaries']),
'Southern Africa': ('Southern and south-tropical African plateau/coast grouping spanning the two existing geographic regions. It is a broad atlas reporting zone, not the narrower five-country UN statistical grouping and not a single drainage basin.', ['africa','southern-africa']),
'Western Africa': ('Atlantic West African coast and adjoining western Sahel/Sahara reporting zone. The source term tropical in regional names is not a claim that all member land is tropical vegetation. Political owners never determine the hierarchy at a selected year.', ['africa','continental-boundaries']),
'Indian Ocean Islands': ('African-associated western/central Indian Ocean archipelagos: Madagascar, Comoros, Mascarenes, Seychelles and Chagos. Chagos is an explicit central-ocean reporting exception rather than a claim of continental adjacency.', ['continental-boundaries','chagos']),
'Central Asia': ('Interior Asian Central Asian steppe/desert/mountain geographic reporting zone, using the existing Middle Asia member convention. Western-of-Ural Kazakhstan locations must move to Eastern Europe where source geometry proves a whole-location majority; no country is forced into one continent.', ['central-asia','ural-river','continental-boundaries']),
'Eastern Asia': ('East Asian geographic reporting zone constituted by China regional geography, Mongolian plateau reference, Korean Peninsula, Taiwan/coastal-island and Japanese archipelago branches. It is a geographic reporting convention rather than a claim that all branches are single natural regions.', ['continental-boundaries','new-guinea']),
'Northern Asia': ('Asian Siberian and Far Eastern geographic branches east of the Ural divide. Northern Russian land cannot be assigned by modern Russia ownership; the crest/river divide and named Arctic island associations are the determining conventions.', ['urals','ural-river','continental-boundaries']),
'Southeastern Asia': ('Mainland southeast Asia, Sunda islands, Philippines and Wallacea, plus named South China Sea island association. New Guinea/Sahul islands are Oceanian; Cocos/Christmas are separately listed Indian Ocean associations. The Wallace Line alone is not used as a continent divider.', ['wallacea','new-guinea','cocos','christmas','continental-boundaries']),
'Southern Asia': ('Indian subcontinent and adjacent Himalayan/island geographic reporting group. Afghanistan is retained as an explicitly documented South/Central Asian transition convention rather than inferred from a political bloc. No Himalayan watershed precision is claimed without a digitized divide.', ['afghanistan-geography','continental-boundaries']),
'Western Asia': ('Southwest Asian peninsular/Anatolian/Levant/Caucasus reporting zone plus Asian Sinai and Cyprus. Europe–Asia boundary is the Turkish Straits and Greater Caucasus crest, not national borders; crest-crossing memberships remain unresolved pending licensed exact divide geometry.', ['great-caucasus','sinai','cyprus','continental-boundaries']),
'Eastern Europe': ('Baltic and eastern-European plain grouping west of Ural crest/river and north of Greater Caucasus divide. The proposed west-of-Ural steppe clusters retain Kazakhstan ownership separately. Baltic classification is a stated eastern/northern European transition convention.', ['europe','urals','ural-river','continental-boundaries']),
'Northern Europe': ('British–Irish and Nordic geographic branches, including associated North Atlantic/Arctic islands. Isle of Man belongs to the British/Irish Sea branch, not Nordic by ownership. Baltic lands stay in the separately stated Eastern Europe convention.', ['europe','continental-boundaries']),
'Southern Europe': ('Iberian, Italian and southeast-European/Balkan geographic reporting branches, with explicit Mediterranean/North Atlantic island associations. The proposed Azores placement is a reporting association, not a claim of Iberian mainland or plate identity.', ['europe','continental-boundaries','azores']),
'Western Europe': ('Western and Central European geographic reporting branches: France/Channel coast, Low Countries and central-European transition. Rename to Western and Central Europe so the central-European branch is stated rather than concealed. This is an atlas convention, not a universal cultural definition.', ['europe','continental-boundaries']),
'Caribbean': ('Caribbean/West Indian and Bahamian archipelagos, including islands whose present owners are continental South American states. Excludes Bermuda, already corrected into the North Atlantic mainland-associated branch. Bahamas are an explicit West Indian archipelago convention.', ['north-america','bermuda','continental-boundaries']),
'Mesoamerica': ('All Mexico and the Central American isthmus geographic reporting group. Rename to Mexico and Central America: archaeological Mesoamerica covers neither all Mexico nor all Panama and cannot describe this footprint. Clipperton remains an explicit eastern-Pacific association.', ['north-america','mesoamerica','panama','clipperton']),
'Northern America': ('North American mainland north of the Mexico/Central America reporting zone, Greenland and associated Arctic/North Atlantic islands. Geographic regional branches cross the Canada/United States political border. Bermuda and Saint Pierre/Miquelon are oceanic/coastal associations.', ['north-america','bermuda','continental-boundaries']),
'Andean South America': ('Broad western South American reference grouping that includes Andean slopes and extensive Amazonian/Caribbean/Orinoco lowlands. Rename to Western South America because a literal Andean footprint does not cover these members. Further natural-region subdivision is a lower-tier review obligation.', ['south-america','andin']),
'Eastern South America': ('Eastern/central South American geographic reporting zone currently constituted by Brazilian macro-geographic branches. It includes Amazon, Cerrado, Atlantic and southern-basin lands; Brazil ownership is never consulted at a historical year. Cross-border natural-region refinements remain lower-tier work.', ['south-america','andin']),
'Northern South America': ('Orinoco/Guiana-shield and northern-mainland reporting group across Venezuelan/Guianan reference geography. It is not all coastline north of a latitude line and excludes Caribbean island groups. Border-parent source artifacts are handled by sourced geographic correspondence, not current owner.', ['south-america','continental-boundaries']),
'Southern South America': ('Southern-cone/Pampas/Chaco/Patagonian reporting group and associated South Atlantic islands. South Georgia is an explicit subantarctic association with this continent after Antarctica exclusion; it is not administratively included by owner.', ['south-america','subantarctic','continental-boundaries']),
'Australasia': ('Australian and New Zealand/Zealandia branches and specifically associated offshore/subantarctic islands. Macquarie belongs to the southwest-Pacific Australian association, not the Indian Ocean. Niue/Tokelau belong to Polynesia irrespective of New Zealand political relationships.', ['oceania','subantarctic','polynesia']),
'Melanesia': ('All New Guinea plus Bismarck, Solomon, Vanuatu, New Caledonia and Fiji geographic island groups. Western New Guinea remains here irrespective of Indonesia ownership. Samoa/Tonga/Cooks, Gilbert/Nauru and other Polynesian/Micronesian islands are excluded by named archipelago.', ['melanesia','new-guinea','oceania']),
'Micronesia': ('Mariana/Caroline/Marshall/Gilbert/Nauru/Wake island groups and documented equatorial associations. Kiribati ownership does not place its Line or Phoenix archipelagos here. An existing mislabeled Phoenix source remainder lacks true eastern Phoenix land and remains a source defect.', ['micronesia','oceania']),
'Polynesia': ('Hawaiian, eastern and western Polynesian island groups, including Samoa/Tonga/Tuvalu/Cooks/Niue/Tokelau/Wallis–Futuna and Rapa Nui. Political owners do not define island placement. Actual source omissions of eastern Phoenix land remain uncovered evidence rather than invented geometry.', ['polynesia','oceania']),
'Southern Ocean Islands': ('The four present southern Indian Ocean archipelagos: Crozet, Kerguelen, Amsterdam/Saint-Paul and Heard/McDonald. Rename to Subantarctic Indian Ocean Islands. Oceania is an explicit reporting association after Antarctica exclusion, not evidence of Australasian shelf or common ownership; Macquarie is excluded.', ['crozet','kerguelen','heard','amsterdam','saint-paul','subantarctic'])
}

SUPPLEMENTAL={
 'Eastern Asia':'east-asia','Southern Asia':'south-asia','Western Asia':'west-asia',
 'Western Africa':'west-africa','Eastern Africa':'east-africa','Central Africa':'central-africa','Northern Africa':'north-africa',
 'Western Europe':'central-europe','Northern Europe':'north-europe','Southern Europe':'south-europe',
 'Southern South America':'southern-cone','Northern South America':'guiana-shield','Northern Asia':'siberia','Caribbean':'caribbean','Australasia':'australasia'
}
SOURCE_FACTS={
 'east-asia':'The inspected contemporary geographic discussion names China, Japan, Korea and Mongolia, distinguishes alternative East Asian definitions, and treats Taiwan in its regional geography.',
 'south-asia':'The inspected discussion defines the Indian-subcontinental region and documents Afghanistan as a variable western transition membership.',
 'west-asia':'The inspected discussion describes southwest Asia and competing South Caucasus/Cyprus/Sinai inclusions; it does not make ownership a physical boundary.',
 'west-africa':'The inspected geography describes western mainland and Sahel coastal/interior transitions, providing a broad reporting zone rather than one biome.',
 'east-africa':'The inspected geography documents Rift/Great Lakes and Horn definitions and wider UN memberships; geographic definitions are broader than a single sovereign state.',
 'central-africa':'The inspected discussion distinguishes geographic/UN Middle Africa scope from wider Great Lakes usages; Rwanda/Burundi require an explicit East/Central transition decision.',
 'north-africa':'The inspected geography describes Mediterranean/Saharan North Africa and competing southern transition definitions; Sinai and Macaronesia require their separate continent associations.',
 'central-europe':'The inspected discussion states that Central Europe has multiple geographic and cultural definitions and geographic overlap with western/eastern Europe; a Western and Central Europe atlas name makes the choice explicit.',
 'north-europe':'The inspected discussion documents Nordic/British and Baltic alternative memberships; the atlas states its Baltic exception rather than claiming universal agreement.',
 'south-europe':'The inspected geographic discussion includes Iberian, Italian and Balkan/Mediterranean branches and competing island/transitional memberships.',
 'west-europe':'The inspected discussion shows varying geographic/statistical/cultural definitions; reference geography cannot infer Western Europe from political affiliations.',
 'southern-cone':'The inspected geographic discussion identifies southern South America and distinguishes broad political reporting definitions from physical Pampas/Chaco/Patagonian domains.',
 'guiana-shield':'The inspected physical discussion identifies the shield in northern South America extending across Venezuela and the Guianas into adjacent Brazil/Colombia; this is geographic evidence, not a national-owner partition.',
 'siberia':'The inspected geographic description places Siberia east of the Ural Mountains and documents alternative Far East inclusions; the atlas states its separate Far East branch.',
 'caribbean':'The inspected geographic discussion distinguishes the Caribbean sea/island region, Greater/Lesser Antilles and Bahamas/West Indies conventions; Bermuda is independently checked as North Atlantic.',
 'australasia':'The inspected discussion documents multiple Australasian definitions; Australia and New Zealand are the declared atlas scope while New Guinea is separately placed in Melanesia.'
}

def prepare(root):
 root=pathlib.Path(root); cache=root/'.cache/research/macro-boundary'; audit=json.loads((cache/'current-membership-audit.json').read_text()); h=json.loads((root/'data/hierarchy.json').read_text()); units={u['id']:u for u in h}; byname={u['name']:u for u in h if u['level'] in ['continent','subcontinent']}; allfeatures=[]; pins={}
 for relative in ['hierarchy.json','world-index.json']+json.loads((root/'data/world-index.json').read_text())['parts']:
  p=root/'data'/relative;pins['data/'+relative]=digest(p)
  if relative.startswith('geography/'): allfeatures += json.loads(p.read_text())['features']
 if pins!=audit['input_sha256']: raise ValueError('Membership audit no longer matches exact input bytes; regenerate first')
 for p in sorted((root/'data/geographic-decisions').glob('*.json')): pins[str(p.relative_to(root))]=digest(p)
 if set(POLICIES)!=set(byname): raise ValueError('Every active macro group needs exactly one independent convention')
 receipts=json.loads((cache/'fetches.json').read_text())+json.loads((cache/'additional-fetches.json').read_text())+json.loads((cache/'convention-fetches.json').read_text()); sources={}
 for r in receipts:
  if r.get('status')!=200: continue
  p=cache/(r['id']+'.txt')
  if digest(p)!=r['text_sha256']: raise ValueError('Changed inspected source text: '+r['id'])
  sources[r['id']]={**r,'inspected_fact':SOURCE_FACTS.get(r['id'],'Physical boundary or named archipelago reference inspected; see the specific geographic convention and source-backed assignment measurements.'),'license':'CC BY-SA 4.0 text; facts cited, source text not redistributed' if 'wikipedia.org' in r['url'] else 'Publisher terms; bibliographic citation and factual paraphrase only, no media or geometry reused'}
 rivers_path=cache/'river-lines.geojson'
 if digest(rivers_path)!=RIVER_SHA: raise ValueError('Changed pinned physical river source')
 sources['physical-rivers']={'id':'physical-rivers','url':RIVER_URL,'sha256':RIVER_SHA,'license':'Public domain','license_url':'https://www.naturalearthdata.com/about/terms-of-use/','vintage':'Pinned Natural Earth repository commit ca96624a56bd078437bca8184e78163e5039ad19; modern reference, not historical boundary'}
 rivers=json.loads(rivers_path.read_text())['features']; feats={f['properties']['id']:f for f in allfeatures}; locationrows={x['id']:x for x in audit['locations']}; groups=[]; geographic_proposals=[]; proposals=[]; tests=[]; unresolved=[]
 for macro in audit['groups']:
  convention,base_refs=POLICIES[macro['name']]; refs=base_refs+([SUPPLEMENTAL[macro['name']]] if macro['name'] in SUPPLEMENTAL else []); groups.append({k:macro[k] for k in ['id','name','level','parent_id','immediate_child_ids','descendant_group_ids','location_ids','location_count','bounds','invalid_location_ids']}|{'convention':convention,'source_ids':refs,'convention_status':'documented','boundary_status':'open' if macro['name'] in ['Asia','Europe','Africa','North America','South America','Central Asia','Northern Asia','Western Asia','Eastern Europe','Northern Africa','Central Africa','Eastern Africa','Southern Europe','Micronesia','Polynesia'] else 'supported-convention','semantic_status':'open','descendant_completion':'not implied by own convention/boundary review','definition_method':'Explicit stable geographic/archipelago reporting convention; exact membership represented by whole-location parent chains. No political owner field is used.'})
 for name,first,second,scope in [('Ural','Europe','Asia',(40,46.94,70,54.71)),('Suez Canal','Africa','Asia',(31.9,29.7,33.2,31.5))]:
  mask,domain,corridor=river_mask(rivers,name); other=domain.difference(mask); screen=box(*scope)
  for fid,f in feats.items():
   row=locationrows[fid]
   if units[row['chain']['continent']]['name'] not in [first,second]: continue
   g=shape(f['geometry'])
   if not g.intersects(screen): continue
   total=area(g); aa=area(g.intersection(mask))/total; bb=area(g.intersection(other))/total; uncertain=0
   # Verify even conservative source generalization does not decide a near tie.
   if corridor:
    line=mask.boundary.intersection(domain.buffer(-.00001)); band=line.buffer(corridor); uncertain=area(g.intersection(band))/total
   winner=majority(max(0,aa-uncertain),max(0,bb-uncertain)); proposed=first if winner=='first' else second if winner=='second' else None
   proof={'location_id':fid,'current_name':row['name'],'current_parent_id':row['parent_id'],'current_chain':row['chain'],'geometry_sha256':hashlib.sha256(json.dumps(f['geometry'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),'divide':name,'first_continent':first,'second_continent':second,'first_share':round(aa,12),'second_share':round(bb,12),'outside_surveyed_share':round(max(0,1-aa-bb),12),'source_uncertainty_share':round(uncertain,12),'proposed_continent':proposed,'source_ids':['physical-rivers','continental-boundaries','ural-river' if name=='Ural' else 'sinai'],'method':'WGS84 ellipsoid surface integral, 16-point quadrature; strict >50% of entire location land footprint. Unsurveyed land is included in denominator. Source geometry and historical records unchanged.'}
   tests.append(proof)
   if proposed and proposed!=units[row['chain']['continent']]['name']: proposals.append(proof)
   elif proposed is None: unresolved.append({'location_id':fid,'divide':name,'reason':'No surveyed side proves a strict whole-location majority; crest, coastal extension or source precision evidence required.'})
 # Add exact source-derived masks to the product for reproducible independent review.
 masks={name:{'first_side':mapping(river_mask(rivers,name)[0]),'surveyed_domain':mapping(river_mask(rivers,name)[1]),'source_generalization_degrees':river_mask(rivers,name)[2]} for name in ['Ural','Suez Canal']}
 # Pure tier-name changes preserve identity and do not create historical aliases.
 for old,new in [('Andean South America','Western South America'),('Mesoamerica','Mexico and Central America'),('Western Europe','Western and Central Europe'),('Southern Ocean Islands','Subantarctic Indian Ocean Islands')]:
  u=byname[old];geographic_proposals.append({'action':'rename','id':u['id'],'level':u['level'],'current_name':u['name'],'current_parent_id':u['parent_id'],'name':new,'reference_only':True,'source_ids':POLICIES[old][1],'rationale':POLICIES[old][0]})
 # Only whole pre-existing source areas are proposed when that membership itself
 # expresses a coherent geographical unit. Do not create continent-sized parent
 # polygons independent of their members.
 for area_name,target_region in [('Azores','Iberia'),('Rwanda','East Tropical Africa'),('Burundi','East Tropical Africa')]:
  candidates=[u for u in h if u['level']=='area' and u['name']==area_name]; targets=[u for u in h if u['level']=='region' and u['name']==target_region]
  if len(candidates)!=1 or len(targets)!=1: raise ValueError('Ambiguous exact geographic group name: '+area_name)
  u=candidates[0];target=targets[0];members=[fid for fid,r in locationrows.items() if r['chain']['area']==u['id']]
  geographic_proposals.append({'action':'reparent','id':u['id'],'level':u['level'],'current_name':u['name'],'current_parent_id':u['parent_id'],'parent_id':target['id'],'affected_location_ids':sorted(members),'reference_only':True,'source_ids':['continental-boundaries','azores'] if area_name=='Azores' else ['great-lakes','africa'],'rationale':'Explicit European North Atlantic archipelago association, independent of Portuguese sovereignty; retain Macaronesia as alternative geographic tag.' if area_name=='Azores' else 'East African Rift/Great Lakes geographic association; retained country reference owner does not determine this parent.'})
 # Scope-sensitive continent reassignment creates reference portions of existing
 # administrative clusters, preserving the existing administrative provenance.
 bucket=collections.defaultdict(list)
 for p in proposals: bucket[(p['divide'],p['proposed_continent'],p['current_parent_id'])].append(p)
 newgroups=[]; locationchanges=[]
 for (divide,continent,oldprovince),members in sorted(bucket.items()):
  old=units[oldprovince]
  if divide=='Ural':
   region=next(u for u in h if u['level']=='region' and u['name']==('Eastern European Plain' if continent=='Europe' else 'Middle Asia')); areaname=('West' if continent=='Europe' else 'East')+'-of-Ural steppe'; areaid=stable('area',areaname)
  else:
   # Suez crossing territory is a geographic north-western Sinai reference
   # cluster, not a claim that it belongs administratively to North Sinai.
   region=next(u for u in h if u['level']=='region' and u['name']=='Western Asia'); areaname='Sinai'; areaid=next(u for u in h if u['level']=='area' and u['name']==areaname)['id']
  if areaid not in units and not any(x['id']==areaid for x in newgroups): newgroups.append({'id':areaid,'name':areaname,'level':'area','parent_id':region['id'],'reference_only':True,'role':'Whole-location geographic cluster on the source-proven continental side of the divide'})
  pname=old['name']+' — '+((('west' if continent=='Europe' else 'east')+'-of-Ural geographic portion') if divide=='Ural' else 'east-of-Suez geographic portion'); pid=stable('province',oldprovince+'|'+divide+'|'+continent)
  newgroups.append({'id':pid,'name':pname,'level':'province','parent_id':areaid,'reference_only':True,'derived_from_id':oldprovince,'role':'Source administrative cluster restricted to source-proven whole-location geographic side; no dated administrative membership claimed'})
  for p in members: locationchanges.append({'id':p['location_id'],'current_name':p['current_name'],'current_parent_id':p['current_parent_id'],'parent_id':pid,'action':'reparent','reference_only':True,'geometry_sha256':p['geometry_sha256'],'evidence':p})
 unresolved_segments=[{'segment':'Ural mountain crest north of the measured river reach','reason':'Pinned river geometry does not represent a mountain watershed. No invented straight longitude or modern country boundary is accepted.'},{'segment':'Greater Caucasus crest','reason':'Source narratives establish a convention, but exact licensed crest geometry has not been verified; Russian, Georgian and Azerbaijani memberships require an independent whole-location majority.'},{'segment':'Darien watershed exact local crossing','reason':'Mainland continent association is documented; exact watershed alignment must be measured against crossing local territories before physical boundary closure.'},{'segment':'Aegean near-Anatolian islands','reason':'Competing geological, archipelago and conventional associations exist. Existing European/Asian assignments are retained as explicit reference exceptions pending exhaustive named-island crosswalk.'}]
 return {'version':1,'scope':'Every current continent and subcontinent independently inventoried; read-only reference-geography proposals; Antarctica excluded','reference_only':True,'input_sha256':pins,'input_content_sha256':{p:hashlib.sha256(json.dumps(json.loads((root/p).read_text()),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest() for p in pins},'algorithm_sha256':{str(p.relative_to(root)):digest(p) for p in [root/'scripts/prepare-macro-boundary-decisions.py',root/'scripts/ellipsoidal_area.py']},'sources':sources,'groups':groups,'source_divide_masks':masks,'whole_location_measurements':tests,'group_changes':geographic_proposals,'new_groups':newgroups,'location_changes':locationchanges,'unresolved_location_measurements':unresolved,'unresolved_physical_segments':unresolved_segments,'summary':{'continents':6,'subcontinents':29,'locations_inventoried':len(feats),'measured_crossing_locations':len(tests),'whole_location_reparents':len(locationchanges),'group_changes':len(geographic_proposals),'new_groups':len(newgroups),'unresolved_measured_locations':len(unresolved),'semantic_complete':False},'invariants':['Geographic parents are independent of owner, culture, religion and historical date.','All location identities, original geometry and temporal records remain unchanged.','Each proposed location has exactly one adjacent-tier parent.','Own boundary approval never implies descendant semantic completion.','Source-based majority uses the entire applicable footprint; source coverage gaps cannot shrink the denominator.']}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',default=str(pathlib.Path(__file__).resolve().parents[1]));p.add_argument('--output',default='data/macro-boundary-decisions.json');a=p.parse_args();result=prepare(a.root);path=pathlib.Path(a.root)/a.output;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result['summary']))
