#!/usr/bin/env python3
"""Stage census religion evidence; never write DB or prepared reference indexes.

Use --cache pointing at downloaded source files. ABS boundary conversion uses the
existing mapshaper CLI with 2% keep-shapes; source correspondence is diagnostic,
not a population weighting operation. Public input receipts retain exact hashes.
"""
import argparse,csv,gzip,hashlib,io,json,pathlib,subprocess,unicodedata,zipfile
from collections import Counter,defaultdict
from shapely.geometry import shape
from shapely import make_valid
from shapely.strtree import STRtree
from shapely.ops import unary_union
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data/demographic-evidence'
def load(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def norm(s):return unicodedata.normalize('NFC',s).strip().casefold()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def csvrows(b):return list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
CATEGORIES={'Christianity':'religion:Q5043','Islam':'religion:Q432','Buddhism':'religion:Q748','Hinduism':'religion:Q9089','Judaism':'religion:Q9268','Sikhism':'religion:Q9316','No religion':'religion:unaffiliated','Other religion':'religion:census-other-unspecified','Secular beliefs':'religion:secular-beliefs','Other spiritual beliefs':'religion:other-spiritual-beliefs','Indigenous Australian traditional religions':'religion:australian-indigenous-traditions'}
UK_COLUMNS={'Religion: No religion':'No religion','Religion: Christian':'Christianity','Religion: Buddhist':'Buddhism','Religion: Hindu':'Hinduism','Religion: Jewish':'Judaism','Religion: Muslim':'Islam','Religion: Sikh':'Sikhism','Religion: Other religion':'Other religion'}
AU_COLUMNS={'Buddhism_P':'Buddhism','Christianity_Tot_P':'Christianity','Hinduism_P':'Hinduism','Islam_P':'Islam','Judaism_P':'Judaism','Othr_Rel_Sikhism_P':'Sikhism','Othr_Rel_Aust_Abor_Trad_Rel_P':'Indigenous Australian traditional religions','Othr_Reln_Other_reln_groups_P':'Other religion','SB_OSB_NRA_NR_P':'No religion','SB_OSB_NRA_SB_P':'Secular beliefs','SB_OSB_NRA_OSB_P':'Other spiritual beliefs'}
URL_UK='https://www.nomisweb.co.uk/output/census/2021/census2021-ts030.zip'
URL_AU='https://www.abs.gov.au/census/find-census-data/datapacks/download/2021_GCP_LGA_for_AUS_short-header.zip'
def make_record(location_id,source_id,counts,total,unknown,metadata):
 assert total>=0 and unknown>=0 and all(isinstance(v,int)and v>=0 for v in counts.values())
 ranking=sorted(counts.items(),key=lambda x:(-x[1],x[0]));winner,winning=ranking[0];runner=ranking[1][1]
 category_sum=sum(counts.values())+unknown
 tolerance=abs(total-category_sum)+20
 unresolved=not total or winning<=runner+unknown+tolerance
 metadata={**metadata,'population_universe':total,'counts':counts,'not_answered':unknown,'share':winning/total if total else None,'reported_plurality':winner,'winning_count':winning,'runner_up_count':runner,'category_total_difference':category_sum-total,'disclosure_guard_persons':tolerance,'assignment_rule':'Largest published religious-affiliation population count, only when its lead exceeds all nonresponses plus the disclosed-table arithmetic guard. This is not a >50% majority requirement. No country/area priors.','precision':'Published integer census estimates with statistical disclosure perturbation; not exact person identities.','uncertainty':'Self-reported affiliation is not belief/practice; census reference footprint and current display footprint may differ slightly within the documented correspondence tolerance.','reason':'Nonresponse, disclosure differences or zero population can change the dominant affiliation; primary religion stays unknown.' if unresolved else 'The reported affiliation leads all other categories even if all nonresponses favour the runner-up.'}
 return {'id':'demographic:'+source_id+':'+hashlib.sha256(location_id.encode()).hexdigest()[:20],'location_id':location_id,'attribute':'religion','value':None if unresolved else winner,'category_id':None if unresolved else CATEGORIES[winner],'valid_from':2021,'valid_to':2022,'source_id':source_id,'source':'ONS Census 2021 TS030 religion' if source_id=='ons:2021:TS030' else 'ABS Census 2021 G14 religious affiliation','source_url':URL_UK if source_id=='ons:2021:TS030'else URL_AU,'method':'derived','status':'unknown' if unresolved else 'derived','is_example':0,'metadata':{**metadata,'source_url':URL_UK if source_id=='ons:2021:TS030'else URL_AU}}
def prepare(cache):
 OUT.mkdir(parents=True,exist_ok=True)
 world=load(ROOT/'data/world-index.json');features=[f for p in world['parts']for f in load(ROOT/'data'/p)['features']];props={f['properties']['id']:f['properties']for f in features};geo={f['properties']['id']:make_valid(shape(f['geometry']))for f in features if f['properties']['metadata'].get('source_id') in ['gb:AUS:ADM2','gb:GBR:ADM2']};records=[];crosswalk=[];rejections=[]
 uk=zipfile.ZipFile(cache/'nomis.zip');utla=csvrows(uk.read('census2021-ts030-utla.csv'));ltla=csvrows(uk.read('census2021-ts030-ltla.csv'));regional=csvrows(uk.read('census2021-ts030-rgn.csv'))
 rawgb=load(ROOT/'.cache/geoboundaries/GBR-ADM2.json');rawnames={x['properties']['shapeID']:x['properties']['shapeName']for x in rawgb['features']};rawgeo={x['properties']['shapeID']:make_valid(shape(x['geometry']))for x in rawgb['features']};byname={norm(x['geography']):x for x in utla};bycode={x['geography code']:x for x in utla}
 # Current whole county/source territories only, no district attributes spread
 # across independently refined locations. Explicit two-unit union is complete.
 for p in props.values():
  m=p['metadata'];sid=m.get('source_id');r=None;method=None
  if sid=='gb:GBR:ADM2':
   original=rawnames.get(m.get('original_id'));r=byname.get(norm(original or''));method='Exact original ONS county/unitary name to unique Census2021 upper-tier code'
   if original=='Rhondda Cynon Taf':r=bycode['W06000016'];method='Explicit one-to-one published spelling correspondence Rhondda Cynon Taf/Taff, W06000016'
   if original=='Northamptonshire':
    parts=[byname['north northamptonshire'],byname['west northamptonshire']];r={'geography':'Northamptonshire','geography code':'+'.join(x['geography code']for x in parts),**{k:str(sum(int(x[k])for x in parts))for k in parts[0]if k.startswith('Religion: ')}};method='Complete union of 2021 North/West Northamptonshire reference subdivisions over the retained county territory'
  elif p['id']=='atlas:city:GBR-Greater London':
   aliases={norm(x)for x in m.get('search_aliases',[])};boroughs=[x for x in ltla if x['geography code'].startswith('E09')];assert len(boroughs)==33 and all(norm(x['geography'])in aliases for x in boroughs);r=next(x for x in regional if x['geography']=='London');method='All 33 London borough census members explicitly present in current city source aliases; use independently published London regional total, avoid summing perturbed subcounts'
  if not r:continue
  current=make_valid(shape(next(f['geometry']for f in features if f['properties']['id']==p['id'])))
  if p['id']=='atlas:city:GBR-Greater London':
   original_footprint=unary_union([rawgeo[x['properties']['shapeID']]for x in rawgb['features']if norm(x['properties']['shapeName'])in aliases])
  else:original_footprint=rawgeo[m['original_id']]
  overlap=current.intersection(original_footprint).area;shares=(overlap/current.area,overlap/original_footprint.area)
  if min(shares)<.99:
   rejections.append({'location_id':p['id'],'name':p['name'],'source':'ons:2021:TS030','reason':'County census identity matches, but current/pinned whole-source footprint correspondence is below99% in at least one direction. Do not copy full-population affiliations to a partial/coarsened display territory.','current_in_source_share':shares[0],'source_in_current_share':shares[1]});continue
  counts={label:int(r[col])for col,label in UK_COLUMNS.items()};e={'census_geography':r['geography'],'census_code':r['geography code'],'geographic_assignment':method,'current_in_source_share':shares[0],'source_in_current_share':shares[1],'correspondence_precision':'Planar bidirectional identity diagnostic against pinned whole ONS source footprint; only >=99% correspondence. Source identity aliases do not override incomplete current coverage.','source_observation_date':'2021-03-21','source_release_date':'2022-11-29','licence':'Open Government Licence; ONS Crown copyright','geographic_reference_vintage':m.get('reference_year'),'boundary_limitation':'The source county/authority identity matches, but current display topology is a modern reference; this is not an ancient/historical boundary reconstruction.'}
  record=make_record(p['id'],'ons:2021:TS030',counts,int(r['Religion: Total: All usual residents']),int(r['Religion: Not answered']),e);records.append(record);crosswalk.append({'location_id':p['id'],'location_name':p['name'],'source_id':'ons:2021:TS030',**e})
 for f in features:
  p=f['properties']
  if p['reference_owner']=='United Kingdom' and not any(x['location_id']==p['id'] for x in crosswalk+rejections):rejections.append({'location_id':p['id'],'name':p['name'],'source':'ons:2021:TS030','reason':'No matching England/Wales county/authority census territory; Scotland/NI use separate censuses. No neighbouring/country faith assignment.'})
 au=zipfile.ZipFile(cache/'aus-gcp.raw');csvpath=next(x for x in au.namelist()if 'G14' in x and x.endswith('.csv'));au_rows=csvrows(au.read(csvpath));counts_bycode={r['LGA_CODE_2021'].removeprefix('LGA'):r for r in au_rows};official=load(cache/'aus-lga2021.geojson')['features'];official=[f for f in official if f.get('geometry')];official_geo=[make_valid(shape(f['geometry']))for f in official];tree=STRtree(official_geo)
 raw=load(ROOT/'.cache/geoboundaries/AUS-ADM2.json')['features'];rawbyid={f['properties']['shapeID']:f for f in raw}
 for p in props.values():
  m=p['metadata'];sid=m.get('source_id','')
  if sid.startswith('ibra:'):
   rejections.append({'location_id':p['id'],'name':p['name'],'source':'abs:2021:G14','reason':'Current territory is a partial IBRA adaptation of an LGA. Full LGA religion counts cannot be distributed by land area or assigned to every fragment.'});continue
  if sid!='gb:AUS:ADM2':continue
  current=geo[p['id']];original=rawbyid.get(m.get('original_id'));matches=[]
  for idx in tree.query(current):
   census=official_geo[idx]
   if not current.area or not census.area:continue
   covered=current.intersection(census).area;shares=(covered/current.area,covered/census.area)
   # Unit-level correspondence is symmetric; tiny residuals inside a large
   # LGA never qualify. It is not a majority-population spatial assignment.
   if min(shares)>=.99:matches.append((int(idx),shares))
  if len(matches)!=1:
   rejections.append({'location_id':p['id'],'name':p['name'],'source':'abs:2021:G14','reason':'No unique >=99% bidirectional official Census2021/current footprint correspondence; administrative changes, coastal clipping or disconnected residuals remain open.','qualifying_matches':len(matches)});continue
  idx,shares=matches[0];o=official[idx]['properties'];row=counts_bycode.get(o['LGA_CODE21'])
  if not row:raise ValueError('No G14 row for official geography '+o['LGA_CODE21'])
  counts={label:int(row[col])for col,label in AU_COLUMNS.items()};e={'census_geography':o['LGA_NAME21'],'census_code':o['LGA_CODE21'],'geographic_assignment':'Unique bidirectional >=99% footprint correspondence to official Census2021 LGA; no area-weighted religion/population assignment','current_in_census_share':shares[0],'census_in_current_share':shares[1],'correspondence_precision':'Planar identity diagnostic against 2% keep-shapes simplified official 2021 LGA geometry; not an ellipsoidal ownership measurement.','source_observation_date':'2021-08-10','licence':'Creative Commons Attribution 4.0 International; Commonwealth of Australia, ABS','original_administrative_shape_id':m.get('original_id'),'geographic_reference_vintage':m.get('reference_year'),'boundary_limitation':'Same named/countable source territory within documented correspondence tolerance; residual geometry remains disclosed.'}
  record=make_record(p['id'],'abs:2021:G14',counts,int(row['Tot_P']),int(row['Religious_affiliation_ns_P']),e);records.append(record);crosswalk.append({'location_id':p['id'],'location_name':p['name'],'source_id':'abs:2021:G14',**e})
 assert len({(r['location_id'],r['attribute'],r['valid_from'])for r in records})==len(records)
 assert all(r['location_id']in props and r['valid_from']==2021 and r['valid_to']==2022 and r['attribute']=='religion'for r in records)
 # Preserve the small actual source tables and metadata; huge input boundary ZIP
 # remains cache-only with exact digest and reproducible conversion command.
 source_dir=OUT/'sources';source_dir.mkdir(exist_ok=True)
 for name in ['census2021-ts030-utla.csv','census2021-ts030-ltla.csv','census2021-ts030-rgn.csv','metadata/ts030-2021-1.txt']:(source_dir/pathlib.Path(name).name).write_bytes(uk.read(name))
 for name in ['nomis-copyright.raw','abs-license.raw']:(source_dir/name).write_bytes((cache/name).read_bytes())
 (source_dir/'aus-lga2021.geojson.gz').write_bytes(gzip.compress((cache/'aus-lga2021.geojson').read_bytes(),mtime=0))
 (source_dir/'2021Census_G14_AUST_LGA.csv').write_bytes(au.read(csvpath));(source_dir/'Metadata_2021_GCP_DataPack_R1_R2.xlsx').write_bytes(au.read('Metadata/Metadata_2021_GCP_DataPack_R1_R2.xlsx'))
 receipts=[{'id':'ons:2021:TS030','url':URL_UK,'sha256':sha(cache/'nomis.zip'),'bytes':(cache/'nomis.zip').stat().st_size,'licence_evidence_url':'https://www.nomisweb.co.uk/home/copyright.asp','licence_evidence_sha256':sha(cache/'nomis-copyright.raw'),'supported_interval':[2021,2022]}, {'id':'abs:2021:G14','url':URL_AU,'sha256':sha(cache/'aus-gcp.raw'),'bytes':(cache/'aus-gcp.raw').stat().st_size,'licence_evidence_url':'https://www.abs.gov.au/website-privacy-copyright-and-disclaimer','licence_evidence_sha256':sha(cache/'abs-license.raw'),'supported_interval':[2021,2022],'geographic_source_url':'https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files/LGA_2021_AUST_GDA2020_SHP.zip','geographic_input_sha256':sha(cache/'aus-lga2021.raw'),'geographic_conversion':'node_modules/.bin/mapshaper INPUT.zip -simplify 2% keep-shapes -o format=geojson OUTPUT.geojson','geographic_comparison_sha256':sha(cache/'aus-lga2021.geojson')}]
 save(OUT/'religion-records.json',records);save(OUT/'location-crosswalk.json',crosswalk);save(OUT/'unassigned-locations.json',rejections);save(OUT/'source-receipts.json',receipts);save(OUT/'categories.json',[{'id':i,'kind':'religion','name':name,'source_id':'ons:2021:TS030'if name in UK_COLUMNS.values()else'abs:2021:G14','source':'ONS TS030 / ABS G14 published religion categories','metadata':{'taxonomy':'Broad census affiliation category, not a denomination inference'}}for name,i in CATEGORIES.items()])
 summary={'version':1,'status':'staged-not-published','records':len(records),'resolved_values':sum(r['value']is not None for r in records),'explicit_unknowns':sum(r['value']is None for r in records),'counts_by_source':dict(Counter(r['source_id']for r in records)),'counts_by_value':dict(Counter(r['value']or'Unknown'for r in records)),'supported_years':[2021],'culture_records':0,'rejected_location_assignments':len(rejections),'location_index_sha256':sha(ROOT/'data/world-index.json'),'record_sha256':sha(OUT/'religion-records.json'),'completion':'Observation-year-only census affiliations; globally incomplete. No ancient or 2026 backfill, no citizenship/language culture inference, no country faith priors, no LGA values copied to physical fragments.'}
 sources=[{'id':r['id'],'name':'ONS Census 2021 TS030 Religious affiliation (England and Wales)'if r['id']=='ons:2021:TS030'else'ABS Census 2021 G14 Religious affiliation (Australia)','url':r['url'],'license':'Open Government Licence; Crown copyright'if r['id']=='ons:2021:TS030'else'Creative Commons Attribution 4.0 International; Commonwealth of Australia, ABS','vintage':'2021-03-21; released 2022-11-29'if r['id']=='ons:2021:TS030'else'2021-08-10; Census 2021 General Community Profile release','supported_from':2021,'supported_to':2022,'status':'historical','metadata':{**r,'support_precision':'Observation year only, no extrapolation','population_concept':'Usual residents, self-reported religious affiliation','staging_only':True}}for r in receipts]
 save(OUT/'sources.json',sources)
 summary.update({'record_parts':[{'path':'religion-records.json','sha256':sha(OUT/'religion-records.json'),'records':len(records)}],'sources_path':'sources.json','sources_sha256':sha(OUT/'sources.json'),'categories_path':'categories.json','categories_sha256':sha(OUT/'categories.json'),'receipts_sha256':sha(OUT/'source-receipts.json'),'footprints_sha256':subprocess.check_output(['node','scripts/stamp-prepared.mjs','--hash'],cwd=ROOT,text=True).strip(),'hierarchy_sha256':sha(ROOT/'data/hierarchy.json'),'location_index_hash_method':'SHA-256 of raw data/world-index.json bytes; separate footprints_sha256 uses canonical footprintHash(features) from scripts/check-prepared.mjs.','preparation_algorithm_sha256':sha(pathlib.Path(__file__))})
 save(OUT/'index.json',summary);print(json.dumps(summary,indent=2));return summary
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--cache',type=pathlib.Path,default=pathlib.Path('/workspace/scratch/demographic-research'));prepare(parser.parse_args().cache)
