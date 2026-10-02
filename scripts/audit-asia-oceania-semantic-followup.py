"""Read-only, complete Asia/Oceania follow-up; never approves an unresearched branch.

The frozen first-round inventories are retained. This report reconciles them to
current IDs, checks actual pinned source metadata, and measures original-source
land retention. Run --refresh-research to refresh bounded public metadata reads;
ordinary reruns reuse receipts embedded in the two report files.
"""
import argparse, collections, concurrent.futures, datetime, gzip, hashlib
import importlib.util, json, pathlib, re, urllib.request
from shapely import make_valid, union_all, STRtree
from shapely.geometry import shape
from pyproj import Geod

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/geographic-semantic-followup'
GEO = Geod(ellps='WGS84')
LEVELS = ['continent', 'subcontinent', 'region', 'area', 'province', 'location']
NOTES = {
 'AFG': 'Wuleswali districts are local territorial candidates; verify complete Kabul/other city envelopes and provincial membership against the 2014 district vintage, rather than assume a district is an urban core.',
 'ARE': 'Emirates are broad constituent territories. Abu Dhabi ecological portions and six whole other emirates serve different local purposes; assess functional-city plus coherent hinterland alternatives. Seven emirates cannot automatically become seven equal-purpose locations.',
 'ARM': 'The 2020 municipal-community layer has only 39 territories; assess exact community reforms and complete settlement/rural coverage before equating these with municipality-sized neighbors.',
 'AZE': 'Use the retained complete 79 district/city to 14 economic-region proposal, preserving Nakhchivan geography. Economic regions are functional province candidates; this does not establish that every district/city is one whole settlement.',
 'BGD': 'The 64 districts are local references beneath eight division clusters. Review upazila/city/hinterland alternatives systematically and preserve the Chittagong Hill Tracts exception; a finer ADM integer is insufficient.',
 'BHR': 'The whole archipelago can be a compact-territory exception, but government governorates are not cities and reclaimed/offshore land coverage needs a source-vintage decision.',
 'BRN': 'Four districts recur as location and province. Assess mukim/local-city alternatives and Temburong separation; keep a documented district/compact exception only if purpose is supported.',
 'BTN': 'Twenty named polygons are district (dzongkhag) references, while the pinned upstream metadata calls them Dzongdeys. This label is unverified and must not be treated as independent district-role evidence; inspect the authoritative district/gewog hierarchy.',
 'CHN': 'County-level local units, urban municipal aggregations and prefecture clusters require one complete source-code/urban-envelope crosswalk; every China regional branch is included, including remote western units and islands. Named prefectures must not be multiplied by botanical-area splits.',
 'CYP': 'Six administrative districts, northern reference coverage, buffer-zone land and sovereign bases have distinct source scopes. Whole Cyprus geographic membership is independent of sovereignty; never silently merge overlapping administrative claims.',
 'EGY': 'Only Sinai/Suez-side members occur in this continent. Marakiz and urban aqsam are mixed roles; audit complete city envelopes and preserve the whole-location physical-side decisions, not country-based continent assignment.',
 'GEO': 'Municipalities and self-governing cities require exact complete parent identities, including disputed/reference territories. Caucasus membership follows the declared physical convention independently of ownership.',
 'GRC': 'Eastern Aegean municipal-island members are an explicit continental convention. Municipality clusters and whole island coverage must be independently validated; Greek ownership does not define an Asian region.',
 'HKG': 'The full compact Hong Kong source union is one location; preserve its complete predecessor crosswalk. Its Pearl River geographic parents must not become sovereign region identities.',
 'IDN': 'Regencies and cities are mixed local roles. Asian Sunda/Wallacea geography and Oceanian New Guinea geography require full whole-location source and parent crosswalks; Papua administrative reforms cannot be inferred from old shapes.',
 'IND': 'All state/UT, district and local/city/physical adaptations need source-code membership and city-envelope review. Physical rural subdivisions are not administrative districts; preserve Siachen and island source-scope questions separately.',
 'IRN': 'County/shahrestan local territories require supported province identities and complete Tehran/other city envelopes; large desert counties need sourced physical exceptions, not equal-area splits.',
 'IRQ': 'District/qadha local references require full governorate membership and city envelopes; 2019-era source shapes do not resolve disputed governance or all later reforms.',
 'ISR': 'Subdistricts are broad statistical/admin territory candidates rather than settlement-sized cities. Assess the six district clusters and complete local/urban/rural alternatives without owner-based regional reassignment.',
 'JOR': 'Liwa district candidates require exact governorate membership and supported complete urban envelopes; numbered or residual coverage cannot be assigned to nearest settlements.',
 'JPN': 'The complete 47-prefecture membership proposal consolidates 15 duplicate prefecture identities. The mixed municipality/ward source role does not mean all 1,688 locations are urban fragments; each actual municipality/ward/aggregate needs a classified code crosswalk.',
 'KAZ': 'Districts, city territories and sparse physical adaptations need complete source-parent identity. Europe/Asia whole-location majority assignments must remain independent of Kazakhstan ownership.',
 'KGZ': 'Raion/city local roles and regional clusters require exact named membership; the independent reference remainder needs original-source land and purpose evidence.',
 'KHM': 'District/khan/municipal roles need per-feature classification beneath province clusters, including complete Phnom Penh urban extent. A source generic District does not certify every feature.',
 'KOR': 'Si/gun/gu and source-city aggregation roles differ; verify the full municipal/urban crosswalk and independently significant cities, preserving source identities rather than assuming every gu is a location.',
 'KWT': 'Six whole governorates repeat province identities. Assess coherent city/rural territory alternatives or source-backed compact exceptions; governorate geometry is not evidence of a whole Kuwait City location.',
 'LAO': 'Districts require full named province membership, remote-rural exceptions and separate municipality/urban intent; assess retained source remainders against actual source scope.',
 'LBN': 'Qadaa districts serve local references beneath governorates; verify Beirut/other urban envelopes and district/gubernate vintage, not a generic ADM role.',
 'LKA': 'Twenty-five districts repeat province names and are coarse beside nearby local units. Research divisional-secretariat/city plus complete rural coverage before accepting a different granularity.',
 'MAC': 'One compact Macau location can be a justified reference territory; region/subcontinent grouping must be Pearl River/South China geography independently of jurisdiction.',
 'MDV': 'Administrative atolls, named island coverage and Male aggregation need complete actual-land membership, with every disconnected island inspected. Tiny area does not justify assigning arbitrary canonical cells.',
 'MMR': 'Township local territories and state/region province clusters need full code membership, urban envelopes and rural exceptions; territorial governance and source names must retain their supported vintage.',
 'MNG': 'Soum/district local territories mix sparse steppe and Ulaanbaatar urban districts. Assess coherent urban aggregation and named sparse-rural exceptions with exact provincial membership.',
 'MYS': 'Daerah/district, city and Sabah/Sarawak administrative divisions differ. Borneo and peninsular physical parents must be geographic and whole-source memberships exact.',
 'NPL': 'The 75-district source predates the 77-district reform. Preserve its vintage; assess municipality/rural-municipality local roles and exact split/replacement evidence rather than silently calling old boundaries current.',
 'OMN': 'Wilayat candidates and governorate clusters need complete named membership and city/rural purpose; source remainders and disconnected Musandam/Madha require supported exceptions.',
 'PAK': 'District local references and province/territory clusters require dated source-code membership, complete city envelopes, mountain rural exceptions and separately scoped disputed-reference land.',
 'PHL': 'Municipalities and cities are suitable named candidates when complete code membership is supported. Review metropolitan city unions, island-land completeness and independent component cities globally across the branch.',
 'PRK': 'County/city urban districts need per-feature classification and full city-envelope review. Northern administrative names and source completeness are not certified by a mixed ADM metadata role.',
 'PSE': 'Governorate boundaries and reference political footprints serve different scopes. Verify complete local-territory alternatives, source vintages and explicit border/claim uncertainty; geographic parents do not follow ownership.',
 'QAT': 'Municipalities repeat broad local/province identity; assess Doha functional urban extent and rural/island coverage or document a supported compact exception.',
 'RUS': 'Rayon/city and physical Siberian adaptations differ greatly in purpose. All Asian Russian branches and Ural-side whole-location decisions are included; ecology-derived units need exact source membership and remote exceptions.',
 'SAU': 'Governorates and ecological desert portions are different local roles. Assess complete city territories, province membership, source coastline/islands and named desert exceptions rather than area quotas.',
 'SGP': 'A whole compact Singapore territory can have a sourced single-member tier exception. Planning/electoral subareas should not become locations merely because they are available; offshore/reclaimed land still needs source coverage.',
 'SYR': 'District/mintaqa local references need exact governorate membership, complete city envelopes and compatible source vintage; contemporary control is a separate dated attribute.',
 'THA': 'Amphoe/khet mixed local roles need complete Bangkok city versus district classification and named province membership; do not interpret every administrative polygon as a separate city.',
 'TJK': 'District/city local roles and province/region clusters need exact identity membership, independent urban envelopes and named mountain-rural exceptions.',
 'TKM': 'Etrap local roles, Ashgabat/city special territories and physical desert adaptations need source-supported classification and full parent membership; Unknown upstream canonical role is not approval.',
 'TLS': 'Administrative posts/subdistricts beneath municipality clusters need exact supported membership, Atauro status/vintage and complete Dili urban geography. Old label counts alone do not prove current administration.',
 'TUR': 'Ilce local territories and il/province clusters need complete metropolitan city versus rural district classification; Thrace/Anatolia geographic placement is independent of country ownership.',
 'TWN': 'Township/district and source-city aggregations need complete county/city parent code membership. Penghu/Kinmen/Matsu geographic purpose and all offshore land require explicit island evidence.',
 'UZB': 'Tuman/urban district local references and viloyat clusters need complete urban envelopes and exact supported source membership, including physical desert exceptions.',
 'VNM': 'The district-level 2020-era source is a dated reference, not evidence of the current post-reorganization administration. Preserve identities; verify exact administrative reform and complete city/rural roles before replacement.',
 'YEM': 'Districts beneath governorate clusters require exact parent membership and island/urban purpose. Whole Socotra geographic placement and island completeness do not follow its political owner.',
 'AUS': 'LGAs, urban territories and 435 IBRA/LGA ecological portions serve different purposes. ASGS/LGA and IBRA are independent sources: classify all adaptations, verify supported whole-city envelopes and remote ecological exceptions.',
 'CHL': 'Only Easter Island geography occurs in Oceania. Commune reference scope and physical archipelago membership are separate from Chilean ownership.',
 'COK': 'Natural Earth island references require complete island/atoll membership and distinct northern/southern physical grouping; administrative sovereignty is not a continent/region rule.',
 'FJI': 'The 15 named source features include 14 provinces plus Rotuma. Province-level atoll/island territories may need documented local-purpose exceptions or sourced subprovince city/rural coverage.',
 'FSM': 'Four state-level archipelago locations are broad and disconnected. Assess complete named island/atoll clusters and coherent local-purpose alternatives; state counts do not establish local granularity.',
 'GUM': 'The compact whole Guam territory can be an explicit exception; village/district lists do not automatically supply territorial land coverage or whole urban identities.',
 'HMD': 'Heard/McDonald are separate remote islands; compact repeated tiers need source-supported archipelago and local-purpose exceptions. Antarctica remains excluded.',
 'KIR': 'Three upstream features are named Gilbert, Phoenix and Line Islands, but the retained Phoenix-labeled source atom has western land only. Restore original eastern source land only through an audited licensed geometry migration; never rename western land Phoenix.',
 'MHL': 'Twenty-four source units are atolls/islands with separate actual land pieces. Atoll municipality purpose and original land retention must be verified individually; website casino content is not a census/source authority.',
 'MNP': 'Four municipalities are distinct named island/city territories; canonical reference-owner USA does not remove this source profile. Northern islands need justified disconnected/remote exceptions.',
 'NCL': 'Three province-level Natural Earth locations are much coarser than local communes. Evaluate full commune plus rural/island coverage before replacing broad provincial references.',
 'NIU': 'Compact whole Niue may have a sourced repeated-tier exception; village availability does not justify city-point territories or artificial cell assignment.',
 'NFK': 'Whole Norfolk island territory requires explicit remote-island local-purpose and repeated-tier exceptions; geography is independent of Australian ownership.',
 'NRU': 'One compact whole-island location can be retained with a sourced single-member exception. Fourteen administrative districts do not automatically improve coherent local-purpose granularity.',
 'NZL': 'The source includes 21 Auckland local boards, 66 other territorial authorities and one offshore remainder. Local boards are not separate territorial authorities; distinguish these actual roles and research complete Auckland functional territory plus offshore island identities.',
 'PCN': 'The whole Pitcairn territory contains separate islands with distinct settlement/habitation context; require actual complete archipelago land and named local-purpose exceptions.',
 'PLW': 'Sixteen state-level island territories require source role confirmation, exact whole island membership and compact/multipart exceptions; Unknown source canonical role is not approval.',
 'PNG': 'LLGs are local territorial candidates beneath district clusters, but urban LLGs can be only city parts. Inspect complete named city territories and rural exceptions; source 2019 does not prove later district membership.',
 'PYF': 'Five Natural Earth administrative subdivisions/archipelagos are broad references. Assess commune/local archipelago purpose and land completeness, especially Tuamotu-Gambier and distant islands.',
 'SLB': 'Nine provinces plus Honiara form broad source territories. Finer constituencies split Honiara and are electoral, so full city/rural geographic coverage must precede any refinement.',
 'TON': 'Five named island-group divisions need explicit archipelago/local-purpose and repeated-tier exceptions; political country membership alone cannot create physical regions.',
 'TUV': 'Eight atoll/island references need exact all-islet land membership and compact/remote exceptions; no nearest-cell reassignment or distant-atoll merges.',
 'UMI': 'Each named remote island/atoll needs actual land membership and region association separately. Geographic Pacific/Indian Ocean grouping must not follow United States ownership.',
 'USA': 'Hawaii county/local roles, American Samoa districts and Northern Mariana municipalities have separate sources despite shared canonical owner. Validate all profiles independently; a county name does not certify city granularity.',
 'VUT': 'Six source provinces group island chains and are broad beside local LLG/municipal neighbors. Review complete local alternatives or justified archipelago exceptions, preserving full Port Vila/Luganville intent.',
 'WLF': 'Three customary kingdoms are local political-cultural references with distinct island membership. Province/area repeated tiers need sourced purpose, not ADM integer inference.',
 'WSM': 'Whole Samoa combines two main islands and smaller offshore land; decide named local district/island clusters or an evidenced compact exception. Do not fabricate an urban rank for the whole territory.',
 'ATF': 'Non-Antarctic southern island districts are reference archipelagos. Adelie Land is excluded; each remaining district needs complete land and an explicit continent convention unrelated to French ownership.',
}
AUTHORITY_URLS = {
 'BTN': ['https://www.nsb.gov.bt/', 'https://www.gov.bt/'],
 'JPN': ['https://www.english.metro.tokyo.lg.jp/municipalities-within-tokyo'],
 'AZE': ['https://www.stat.gov.az/source/regions/?lang=en'],
 'NZL': ['https://www.lgnz.co.nz/local-government-in-nz/new-zealands-councils/', 'https://www.aucklandcouncil.govt.nz/local-boards/all-local-boards/Pages/default.aspx'],
 'FJI': ['https://www.statsfiji.gov.fj/'],
 'KIR': ['https://www.mfa.gov.ki/our-country/'],
 'PNG': ['https://www.nso.gov.pg/'],
 'VUT': ['https://vnso.gov.vu/'],
 'TUV': ['https://stats.gov.tv/'],
 'PLW': ['https://www.palaugov.pw/'],
 'MHL': ['https://www.rmiembassyus.org/'],
 'NPL': ['https://censusnepal.cbs.gov.np/'],
 'PHL': ['https://psa.gov.ph/classification/psgc'],
 'BHR': ['https://www.bahrain.bh/'],
 'ATF': ['https://taaf.fr/collectivite/presentation/'],
 'HMD': ['https://heardisland.antarctica.gov.au/'],
 'AUS': ['https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/non-abs-structures/local-government-areas'],
}

def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def area(g):
    if g.geom_type == 'Polygon':
        x,y=g.exterior.xy
        return max(0, abs(GEO.polygon_area_perimeter(x,y)[0])-sum(abs(GEO.polygon_area_perimeter(*ring.xy)[0]) for ring in g.interiors))/1e6
    return sum(area(p) for p in getattr(g,'geoms',[]))

def fetch(url):
    result={'url':url,'retrieved_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        request=urllib.request.Request(url,headers={'User-Agent':'WorldAtlas-source-review/1.0'})
        with urllib.request.urlopen(request,timeout=15) as response:
            raw=response.read(2*1024*1024+1)
            result.update(http_status=response.status,final_url=response.url,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        if len(raw)>2*1024*1024: raise ValueError('Bounded source response exceeds 2 MiB; not inspected')
        if 'metaData.json' in url:
            data=json.loads(raw)
            result.update(status='metadata-inspected',metadata={k:data.get(k) for k in ['boundaryISO','boundaryType','boundaryYear','boundaryCanonical','boundaryLicense','licenseDetail','licenseSource','boundarySource','boundarySourceURL','admUnitCount']})
        else:
            text=re.sub(r'<[^>]+>',' ',raw.decode('utf-8','replace'))
            text=re.sub(r'\s+',' ',text)
            snippets=[]
            for term in ['dzongkhag','district','territorial authorit','local board','province','Rotuma','Phoenix','Gilbert','Line Islands','gewog','municipal']:
                match=re.search(term,text,re.I)
                if match: snippets.append({'term':term,'text':text[max(0,match.start()-120):match.end()+350]})
            result.update(status='response-retrieved',role_snippets=snippets,substantive_administrative_confirmation=False,note='Retrieval and excerpts only. A homepage, bot response or role word alone is not independent administrative or geographic approval.')
    except Exception as error:
        result.update(status='not-inspected',error=str(error))
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--refresh-research',action='store_true');parser.add_argument('--skip-source-land',action='store_true');parser.add_argument('--restore-sources',action='store_true');args=parser.parse_args()
    paths=['hierarchy.json','world-index.json','world-review.json','global-semantic-closure.json.gz','pixel-audit.json','administrative-sources.json','location-policy.json','geographic-decisions/asia.json','geographic-decisions/oceania.json']
    pins={name:sha(ROOT/'data'/name) for name in paths}
    hierarchy=read(ROOT/'data/hierarchy.json');by={r['id']:r for r in hierarchy}
    world=read(ROOT/'data/world-review.json');closure=read(ROOT/'data/global-semantic-closure.json.gz');admin=read(ROOT/'data/administrative-sources.json');policy=read(ROOT/'data/location-policy.json')['countries']
    features=[]
    for name in read(ROOT/'data/world-index.json')['parts']:
        pins[name]=sha(ROOT/'data'/name);features.extend(read(ROOT/'data'/name)['features'])
    current={f['id']:f for f in features};loc_review={r['id']:r for r in closure['locations']};group_review={r['id']:r for r in closure['groups']};grid={r['id']:r for r in read(ROOT/'data/pixel-audit.json')['records']}
    for name,digest in closure['input_sha256'].items():
        file=ROOT/'data'/name
        if name in pins and sha(file)!=digest:raise ValueError('Stale closure context: '+name)
    def chain(id):
        output=[];seen=set()
        while id:
            if id in seen or id not in by:raise ValueError('Invalid current chain: '+id)
            seen.add(id);output.append(by[id]);id=by[id]['parent_id']
        if [r['level'] for r in output]!=['province','area','region','subcontinent','continent']:raise ValueError('Skipped tier')
        return output
    selected={name:[] for name in ['Asia','Oceania']}
    for f in features:
        c=chain(f['properties']['parent_id'])
        if c[-1]['name'] in selected:selected[c[-1]['name']].append(f)
    source_ids=sorted({a.rsplit(':',1)[0] for rows in selected.values() for f in rows for a in loc_review[f['id']]['checks']['fragmented_source_identity']['fact']['source_atoms'] if a.startswith('gb:')})
    requests={id:f'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/{id.split(":")[1]}/{id.split(":")[2]}/geoBoundaries-{id.split(":")[1]}-{id.split(":")[2]}-metaData.json' for id in source_ids}
    for iso,urls in AUTHORITY_URLS.items():
        for i,url in enumerate(urls):requests[f'authority:{iso}:{i}']=url
    receipts={}
    if args.refresh_research:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            futures={pool.submit(fetch,url):id for id,url in requests.items()}
            for future in concurrent.futures.as_completed(futures):receipts[futures[future]]=future.result()
    else:
        for name in ['asia','oceania']:
            file=OUT/(name+'.json.gz')
            if not file.exists():file=OUT/(name+'.json')
            if file.exists():receipts.update(read(file).get('source_research',{}))
        missing=set(requests)-set(receipts)
        if missing:raise ValueError('Run --refresh-research for new source receipts: '+str(sorted(missing)))
    # Measure every relevant original source atom against ALL current atlas users,
    # including members on the other side of a continental convention.
    atom_users=collections.defaultdict(list)
    for r in closure['locations']:
        for atom in r['checks']['fragmented_source_identity']['fact']['source_atoms']:
            if atom.rsplit(':',1)[0] in source_ids:atom_users[atom].append(r['id'])
    raw_sources={};source_cache_receipts={};atom_results={}
    if not args.skip_source_land:
        all_ids=list(current);all_geometries=[make_valid(shape(current[id]['geometry']))for id in all_ids];spatial=STRtree(all_geometries);geometry_by_id=dict(zip(all_ids,all_geometries))
        for id in source_ids:
            _,iso,level=id.split(':');file=ROOT/'.cache/geoboundaries'/(iso+'-'+level+'.json');declared=admin.get(id,{}).get('sha256')
            tracked=ROOT/'data/global-sources'/(iso+'-'+level+'.geojson.gz');tracked_metadata=ROOT/'data/global-sources'/(iso+'-'+level+'-metadata.json')
            if not file.exists() and tracked.exists() and tracked_metadata.exists():
                file=tracked;declared=read(tracked_metadata).get('sha256');pins[str(tracked.relative_to(ROOT/'data'))]=sha(tracked);pins[str(tracked_metadata.relative_to(ROOT/'data'))]=sha(tracked_metadata)
            if not file.exists() and args.restore_sources:
                url=admin.get(id,{}).get('gjDownloadURL')
                if not url or not declared:raise ValueError('No pinned restoration source: '+id)
                url=url.replace('https://github.com/','https://media.githubusercontent.com/media/').replace('/raw/','/')
                with urllib.request.urlopen(url,timeout=60)as response:raw=response.read(100*1024*1024+1)
                if len(raw)>100*1024*1024 or hashlib.sha256(raw).hexdigest()!=declared:raise ValueError('Restored source hash/size mismatch: '+id)
                file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(raw)
            if not file.exists():source_cache_receipts[id]={'status':'unavailable','source_url':admin.get(id,{}).get('gjDownloadURL')};continue
            digest=hashlib.sha256(gzip.decompress(file.read_bytes())).hexdigest()if file.suffix=='.gz'else sha(file)
            if declared and digest!=declared:source_cache_receipts[id]={'status':'hash-mismatch','actual_sha256':digest,'declared_sha256':declared};continue
            data=read(file);raw_sources[id]={id+':'+r['properties']['shapeID']:r for r in data['features']}
            source_cache_receipts[id]={'status':'inspected-pinned-geometry','sha256':digest,'features':len(data['features']),'source_url':admin.get(id,{}).get('gjDownloadURL')or read(tracked_metadata).get('download_url')if tracked_metadata.exists()else admin.get(id,{}).get('gjDownloadURL'),'tracked_source_file':str(file.relative_to(ROOT))if file.is_relative_to(ROOT/'data')else None}
        for atom,users in sorted(atom_users.items()):
            source_id=atom.rsplit(':',1)[0];original=raw_sources.get(source_id,{}).get(atom)
            if not original:atom_results[atom]={'status':'unresolved-source-atom','location_ids':users};continue
            raw=make_valid(shape(original['geometry']));union=union_all([geometry_by_id[id] for id in users]);original_area=area(raw);overlap=area(raw.intersection(union));current_area=area(union)
            uncovered=None;other_ids=[]
            if original_area and overlap/original_area<.95:
                missing=raw.difference(union);hits=spatial.query(missing,predicate='intersects');other_ids=sorted(all_ids[int(i)]for i in hits if all_ids[int(i)]not in users);uncovered=area(missing.difference(union_all([all_geometries[int(i)]for i in hits])))
            atom_results[atom]={'source_name':original['properties'].get('shapeName'),'source_iso':original['properties'].get('shapeISO'),'source_wgs84_km2':round(original_area,6),'current_union_wgs84_km2':round(current_area,6),'retained_source_km2':round(overlap,6),'retained_source_share':round(overlap/original_area,6) if original_area else None,'current_outside_source_km2':round(max(0,current_area-overlap),6),'location_ids':users,'uncovered_in_all_current_land_km2':round(uncovered,6)if uncovered is not None else None,'other_source_location_ids':other_ids,'status':'measured-diagnostic','semantic_approval':False}
    OUT.mkdir(parents=True,exist_ok=True)
    for continent,rows in selected.items():
        old=read(ROOT/'data/geographic-decisions'/((slug:=continent.lower())+'.json'))
        group_ids={r['id'] for f in rows for r in chain(f['properties']['parent_id'])};children=collections.defaultdict(list);members=collections.defaultdict(list)
        for id in group_ids:
            if by[id]['parent_id']:children[by[id]['parent_id']].append(id)
        for f in rows:
            children[f['properties']['parent_id']].append(f['id'])
            for r in chain(f['properties']['parent_id']):members[r['id']].append(f['id'])
        profiles=collections.defaultdict(list)
        for f in rows:profiles[f['properties']['reference_owner']].append(f)
        territory_matrix=[]
        used_receipts=set();used_atoms=set();used_sources=set()
        for owner,fs in sorted(profiles.items()):
            ids={f['id'] for f in fs};w=next(r for r in world['territories'] if r['owner']==owner);codes=set(w.get('source_country_codes',[]));atom_codes=set()
            if not codes and re.fullmatch('[A-Z]{3}',w.get('iso','')):codes.add(w['iso'])
            for f in fs:
                for atom in loc_review[f['id']]['checks']['fragmented_source_identity']['fact']['source_atoms']:
                    used_atoms.add(atom)
                    if atom.startswith('gb:'):atom_codes.add(atom.split(':')[1]);used_sources.add(atom.rsplit(':',1)[0]);used_receipts.add(atom.rsplit(':',1)[0])
            used_receipts.update(key for key in receipts if key.startswith('authority:') and key.split(':')[1] in codes|atom_codes)
            role_counts=collections.Counter((f['properties']['metadata'].get('location_basis') or f['properties']['metadata'].get('source_role') or 'not independently established') for f in fs)
            sources=[]
            for id in sorted({f['properties']['metadata'].get('source_id','unresolved') for f in fs}):
                same=[f for f in fs if f['properties']['metadata'].get('source_id','unresolved')==id];m=same[0]['properties']['metadata'];sources.append({'id':id,'locations':len(same),'declared_role':m.get('source_role'),'vintage':m.get('reference_year'),'license':m.get('license'),'url':m.get('source_url'),'geometry_receipt':source_cache_receipts.get(id),'metadata_receipt_id':id if id in receipts else None})
            checks=collections.Counter(k for id in ids for k,v in loc_review[id]['checks'].items() if v['status'] in ['attention','open'])
            territory_matrix.append({'reference_owner':owner,'source_country_codes':sorted(codes),'source_atom_country_codes':sorted(atom_codes),'location_count':len(fs),'province_ids':sorted({f['properties']['parent_id'] for f in fs}),'policy_profiles':{code:policy.get(code) for code in sorted(codes)},'actual_declared_roles':dict(role_counts),'sources':sources,'assessment': [NOTES[code] for code in sorted(codes) if code in NOTES] or ['Natural Earth fallback reference; independently establish local/archipelago scope, exact island membership, full-source land retention and a sourced repeated-tier exception. No country-number, ADM integer or compact-area cutoff supplies approval.'],'open_checks':dict(checks),'status':'source-and-current-members-assessed-open','all_locations_independently_approved':False})
        proposals=[]
        for collection in ['decisions','location_changes','location_metadata_changes']:
            for i,d in enumerate(old.get(collection,[])):
                if d.get('action') in ['open','retain'] or d.get('boundary_status')=='open' and d.get('action')=='open':continue
                id=d.get('id');active=id in by or id in current;now=by.get(id,current.get(id,{}).get('properties',{}));state='pending-current-identity' if active else 'predecessor-only-or-create'
                if d.get('action')=='rename' and now.get('name')==d.get('new_name'):state='already-installed-name'
                if d.get('action')=='reparent' and now.get('parent_id')==d.get('new_parent_id'):state='already-installed-parent'
                if d.get('action')=='create' and active and now.get('name')==d.get('new_name') and now.get('parent_id')==d.get('new_parent_id'):state='already-installed-created-group'
                if collection=='location_metadata_changes' and active and all(now.get('metadata',{}).get(k)==v for k,v in d.get('changes',{}).items()):state='already-installed-metadata'
                proposals.append({'frozen_proposal_pointer':f'data/geographic-decisions/{slug}.json#{collection}/{i}','current_state':state,'current_id':id,'current_name':now.get('name'),'proposal':d,'approval_scope':'Only the exact sourced correction. Does not approve local purpose, neighboring units, descendant branches, historical labels or claim transfer.'})
        locations=[]
        for f in rows:
            r=loc_review[f['id']];p=f['properties'];g=grid[f['id']];atoms=r['checks']['fragmented_source_identity']['fact']['source_atoms'];check_status={k:v['status'] for k,v in r['checks'].items()}
            locations.append({'id':f['id'],'name':p['name'],'province_id':p['parent_id'],'reference_owner':p['reference_owner'],'footprint_sha256':r['footprint_sha256'],'source_atoms':atoms,'checks':''.join({'supported':'s','not-applicable':'n','open':'o','attention':'a'}[value]for value in check_status.values()),'pixel':[g['cells'],g['relative_area_error']],'status':'open' if any(x in ['open','attention']for x in check_status.values())else 'supported'})
        groups=[]
        for id in sorted(group_ids,key=lambda id:(LEVELS.index(by[id]['level']),id)):
            u=by[id];r=group_review[id];groups.append({'id':id,'name':u['name'],'level':u['level'],'parent_id':u['parent_id'],'child_ids':sorted(children[id]),'locations':len(members[id]),'footprint_sha256':r['footprint_sha256'],'tier_basis':u.get('metadata',{}).get('basis'),'declared_source':u.get('metadata',{}).get('source'),'source_url':u.get('metadata',{}).get('source_url'),'checks':{k:v['status'] for k,v in r['checks'].items()},'status':r['status'],'descendant_approval':False})
        old_ids=set(old['inventory']['location_ids']);new_ids={f['id'] for f in rows}
        source_fields=['source_name','source_iso','source_wgs84_km2','current_union_wgs84_km2','retained_source_km2','retained_source_share','current_outside_source_km2','location_ids','uncovered_in_all_current_land_km2','other_source_location_ids']
        source_land={k:([atom_results[k].get(field)for field in source_fields]if atom_results[k]['status']=='measured-diagnostic'else atom_results[k])for k in sorted(used_atoms)if k in atom_results}
        output={'version':1,'continent':continent,'audit_order':LEVELS,'scope':'Every current continent, subcontinent, region, area, province, location and reference-owner/source-profile crosswalk. Explicit open semantics are preserved; an inventory, source metadata or geometry diagnostic is never approval.','semantic_complete':False,'active_geography_modified':False,'historical_claims_modified':False,'input_sha256':pins,'compact_fields':{'location_checks':list(loc_review[rows[0]['id']]['checks']),'check_codes':{'s':'supported','n':'not-applicable','o':'open','a':'attention'},'pixel':['cells','relative_area_error'],'original_source_land':source_fields,'note':'Compact arrays preserve every outcome while staying within the source-hosting file limit. Source arrays are measurements, never semantic approval.'},'summary':{'locations':len(rows),'groups':len(groups),'levels':dict(collections.Counter([g['level'] for g in groups]+['location']*len(rows))),'reference_owner_groups':len(territory_matrix),'source_policy_profiles':len({code for t in territory_matrix for code,p in t['policy_profiles'].items() if p is not None}),'source_metadata_responses_inspected':sum(receipts[k]['status']=='metadata-inspected' for k in used_receipts),'original_source_atoms_measured':sum(a in atom_results and atom_results[a]['status']=='measured-diagnostic' for a in used_atoms),'independently_approved_locations':0,'independently_approved_branches':0,'current_pixel_missing':sum(g['pixel'][0]==0 for g in locations),'old_location_ids_no_longer_in_this_continent':len(old_ids-new_ids),'new_current_location_ids':len(new_ids-old_ids),'prior_proposal_states':dict(collections.Counter(p['current_state']for p in proposals))},'previous_snapshot_reconciliation':{'frozen_inspection_file':f'data/geographic-decisions/{slug}.json','old_only_location_ids':sorted(old_ids-new_ids),'current_only_location_ids':sorted(new_ids-old_ids),'note':'A removed or reparented identity is accounted for, never silently deleted or falsely called an unaudited omission. Existing immutable migration archives/crosswalks retain predecessors.'},'groups':groups,'locations':locations,'territory_matrix':territory_matrix,'source_research':{k:receipts[k]for k in sorted(used_receipts)if k in receipts},'source_geometry_receipts':{k:source_cache_receipts[k]for k in sorted(used_sources)if k in source_cache_receipts},'original_source_land':source_land,'source_land_method':'WGS84 ring areas, hole subtraction, actual source/current intersection and union of ALL active users of each original source atom. Diagnostic make_valid is in memory only. Ratios do not prove modern boundaries or prescribe an automatic repair. Antimeridian-bearing source fragments require independent inspection before a migration.','prior_sourced_corrections':proposals,'open_work':'Every unsupported local-purpose/urban envelope/island completeness/weak parent/repeated-tier/neighbor granularity check requires independently sourced outcomes. Metadata retrieval does not close it.'}
        output['code_sha256']=sha(pathlib.Path(__file__))
        output['source_land_interpretation']='Original administrative source polygons can include lagoons, tidal or maritime surfaces. Their uncovered area is a footprint discrepancy, not independently proved missing dry land. Validate source land semantics and all neighboring coverage before a restoration migration; no arbitrary coastal fill or name transfer.'
        output['source_land_attention']=[{'source_atom':id,'source_name':r['source_name'],'location_ids':r['location_ids'],'source_footprint_km2':r['source_wgs84_km2'],'uncovered_in_all_current_land_km2':r['uncovered_in_all_current_land_km2'],'status':'open-source-footprint-coverage','required_action':'Compare actual original island/coastal land and all neighboring source scopes; source license/geometry validity/overlap and predecessor history must pass before a restoration migration.'}for id in sorted(used_atoms)if (r:=atom_results.get(id))and r.get('source_wgs84_km2',0)>1 and (r.get('uncovered_in_all_current_land_km2')or 0)>r['source_wgs84_km2']*.5]
        output['summary']['source_land_over_half_uncovered_attention']=len(output['source_land_attention'])
        raw=(json.dumps(output,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf8');file=OUT/(slug+'.json.gz');file.write_bytes(gzip.compress(raw,mtime=0));assert gzip.decompress(file.read_bytes())==raw
        legacy_raw=OUT/(slug+'.json')
        if legacy_raw.exists():legacy_raw.unlink()
        if file.stat().st_size>=16*1024*1024:raise ValueError('Report exceeds Site source file limit')
        print(continent,json.dumps(output['summary']),file.stat().st_size,'bytes',flush=True)
    for name,digest in pins.items():
        if sha(ROOT/'data'/name)!=digest:raise ValueError('Input changed during review: '+name)

if __name__=='__main__':main()
