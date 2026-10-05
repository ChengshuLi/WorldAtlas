#!/usr/bin/env python3
"""Crosswalk the complete issue roster to Stats SA's published 2022 municipality table."""
import argparse,csv,hashlib,json,re,unicodedata,ssl,urllib.request,subprocess,sys
import certifi
from pathlib import Path
from pypdf import PdfReader
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]
PDF_SHA='ae03e2d95153d9885e9b1cf956f19c807f94627da1331f82f18ac3d6e5ae10b4'
PROVINCES={'EC':'Eastern Cape','FS':'Free State','GT':'Gauteng','KZN':'KwaZulu-Natal','LIM':'Limpopo','MP':'Mpumalanga','NC':'Northern Cape','NW':'North West','WC':'Western Cape'}
# Verified name continuity from Stats SA's 2018 boundary-change section; Sol Plaatjie is a spelling correction.
ALIASES={'Greater Tubatse/Fetakgomo':'Fetakgomo Tubatse','Ventersdorp/Tlokwe':'JB Marks','Mbombela':'City of Mbombela','Mafikeng':'Mahikeng','Mbizana':'Winnie Madikizela-Mandela','Sol Plaatjie':'Sol Plaatje','Kheis':'!Kheis','Kai Garib':'Kai !Garib','Modimolle/Mookgophong':'Modimolle-Mookgophong','Mbizana':'Winnie Madikizela-Mandela'}
REGEX=re.compile(r'^(EC|FS|GT|KZN|LIM|MP|NC|NW|WC) ([AB]) (\S+) (.+?) (DC\d+|[A-Z]{3}) (.+?) ([\d ]+(?:,[\d]+)?)\s*$')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=HERE/'statsa-review.tsv');a=ap.parse_args()
 pdf=HERE/'.scratch/Provinces_at_a_Glance.pdf'
 if not pdf.exists():
  pdf.parent.mkdir(parents=True,exist_ok=True)
  url='https://census.statssa.gov.za/assets/documents/2022/Provinces_at_a_Glance.pdf'
  raw=urllib.request.urlopen(url,context=ssl.create_default_context(cafile=certifi.where()),timeout=60).read()
  pdf.write_bytes(raw)
 if sha(pdf)!=PDF_SHA:raise SystemExit('Stats SA PDF checksum mismatch')
 lines=[]
 for page in PdfReader(pdf).pages[79:87]:lines.extend((page.extract_text() or '').replace('KhÃ¢i-Ma','Khâi-Ma').splitlines())
 records=[]
 for line in lines:
  m=REGEX.match(line)
  if m:
   prov,cat,code,name,dcode,dname,area=m.groups();records.append({'province_code':prov,'province':PROVINCES[prov],'category':cat,'municipal_code':code,'municipality':name,'district_code':dcode,'district':dname,'reported_area_km2':area.replace(' ','').replace(',','.')})
 if len(records)!=213 or len({r['municipal_code'] for r in records})!=213:raise SystemExit('Stats SA inventory parse failed: expected 213 unique municipalities')
 idx={norm(r['municipality']):r for r in records};scope=json.loads((HERE/'sources/issue-436-scope.json').read_text());crosswalk_path=HERE/'.scratch/source-crosswalk.json'
 if not crosswalk_path.exists():subprocess.run([sys.executable,str(HERE/'reproduce.py'),'--output',str(crosswalk_path)],check=True)
 x=json.loads(crosswalk_path.read_text());parents=json.loads((HERE/'parent-review.json').read_text());pmap={r['id']:r for r in parents['parents']}
 out=[];used=set()
 for row in x['rows']:
  expected=ALIASES.get(row['name'],row['name']);r=idx.get(norm(expected))
  if not r:raise SystemExit('No Stats SA match for '+row['id']+' ('+row['name']+' => '+expected+')')
  if r['municipal_code'] in used:raise SystemExit('Non-unique Stats SA municipal match: '+row['name'])
  used.add(r['municipal_code']);p=pmap[row['parent_id']]
  metro=r['category']=='A';parent_match= (norm(p['name'])==norm(r['municipality']) if metro else norm(p['name'])==norm(r['district']))
  # District names changed in official 2018 re-determination; normalization does not map these aliases.
  district_alias={'Eden':'Garden Route','Siyanda':'Z F Mgcawu','Uthungulu':'King Cetshwayo','Sisonke':'Harry Gwala','Greater Sekhukhune':'Sekhukhune'}
  if not metro and norm(district_alias.get(p['name'],p['name']))==norm(r['district']):parent_match=True
  if not parent_match:raise SystemExit('Official parent mismatch for '+row['id']+': Atlas '+p['name']+' vs Stats SA '+r['district'])
  atlas_area=next(q['atlas_area_km2'] for q in x['rows'] if q['id']==row['id']);reported_area=float(r['reported_area_km2']);area_delta=abs(atlas_area-reported_area)/reported_area
  status='insufficient-evidence' if row['name']=='Mbizana' else ('correction-needed' if row['name'] in ALIASES else 'insufficient-evidence')
  part_mismatch=any(q['id']==row['id'] for q in x['component_count_mismatches'])
  out.append({'id':row['id'],'atlas_name':row['name'],'pinned_source_name':row['source_shapeName'],'StatsSA_2022_name':r['municipality'],'StatsSA_2022_code':r['municipal_code'],'province':r['province'],'category_A_or_B':r['category'],'current_district_name':r['district'],'reported_area_km2':f'{reported_area:.3f}','atlas_geodesic_area_km2':f'{atlas_area:.3f}','relative_area_difference_vs_statsa':f'{area_delta:.6f}','component_count_mismatch':part_mismatch,'alias_basis':('2018 merger documented by Stats SA' if row['name'] in {'Greater Tubatse/Fetakgomo','Ventersdorp/Tlokwe','Mbombela','Modimolle/Mookgophong'} else ('Current official candidate; predecessor ID lineage unresolved' if row['name']=='Mbizana' else ('Current official spelling/name differs; predecessor linkage not separately dated' if row['name'] in ALIASES else 'normalized exact match'))),'atlas_parent_id':row['parent_id'],'atlas_parent_name':p['name'],'parent_role_match':parent_match,'classification':status,'boundary_status':'insufficient-evidence','note':('Official table identifies a current name differing from the pinned source; preserve ID and verify geometry before any correction.' if status=='correction-needed' else 'Current official name, category, province and parent grouping crosswalk; current legal polygon completeness remains unverified.')})
 if len(out)!=196 or len(used)!=196:raise SystemExit('Incomplete issue crosswalk')
 sibling=json.loads((HERE/'sources/issue-435-eastern-cape-complement.json').read_text())
 ids435=sibling['complement_ids']; ids436=scope['member_location_ids']
 if len(ids435)!=17 or set(ids435)&set(ids436):raise SystemExit('Eastern Cape sibling complement scope mismatch/overlap')
 if len(set(ids435)|set(ids436))!=213:raise SystemExit('Two Eastern Cape review packets do not cover 213 distinct South African local/metro IDs')
 adm3=HERE/'sources/geoboundaries-zaf-adm3/geoBoundaries-ZAF-ADM3.geojson.lfs-pointer.txt'
 pointer=adm3.read_text()
 m=re.search(r'oid sha256:([0-9a-f]{64})',pointer)
 if not m:raise SystemExit('Pinned 2020 ADM3 source LFS pointer missing')
 parts=sorted((HERE/'sources/geoboundaries-zaf-adm3').glob('geoBoundaries-ZAF-ADM3-part-*-of-*.geojson'));source_features=[]
 for part in parts:source_features.extend(json.loads(part.read_text())['features'])
 if len(source_features)!=213 or {i.rsplit(':',1)[1] for i in ids435+ids436} != {f['properties']['shapeID'] for f in source_features}:
  raise SystemExit('Combined issues do not cover the pinned 213-feature source roster')
 area_counts={p['name']:sum(r['province']==p['name'] for r in out) for p in scope['area_scopes']}
 expected={p['name']:p['owned_member_location_count'] for p in scope['area_scopes']}
 if area_counts!=expected:raise SystemExit('Issue area membership mismatch: '+repr(area_counts))
 full_counts={p['name']:sum(r['province']==p['name'] for r in records) for p in scope['area_scopes']}
 if any(full_counts[p['name']]!=p['full_area_location_count'] for p in scope['area_scopes']):raise SystemExit('Official 2022 area population differs from issue contract')
 # Refresh only the per-packet parent assessment derived from this issue's official table.
 parent_path=HERE/'parent-review.json';parent_doc=json.loads(parent_path.read_text())
 name_alias={'Eden':'Garden Route','Siyanda':'Z F Mgcawu','Uthungulu':'King Cetshwayo','Sisonke':'Harry Gwala','Greater Sekhukhune':'Sekhukhune'}
 for p in parent_doc['parents']:
  child_rows=[r for r in out if r['atlas_parent_id']==p['id']]
  cats={r['category_A_or_B'] for r in child_rows}
  if not child_rows:raise SystemExit('Parent has no owned issue children: '+p['id'])
  if cats=={'A'}:
   official=child_rows[0]['StatsSA_2022_name'];role='Category A metropolitan municipality'
  elif cats=={'B'}:
   official=child_rows[0]['current_district_name'];role='Category C district municipality'
  else:raise SystemExit('Mixed metro and district municipality children under '+p['id'])
  mapped=name_alias.get(p['name'],p['name'])
  if norm(mapped)!=norm(official):raise SystemExit('Parent official name mismatch: '+p['name']+' => '+official)
  p['current_2022_name']=official;p['current_2022_statutory_role']=role;p['scoped_child_categories']=sorted(cats)
  p['name_matches_current_2022_official']=norm(p['name'])==norm(official)
  p['classification']='insufficient-evidence'
  p['tier_limit']='Formal current municipal role is sourced; whether Atlas framework:province is a suitable internal parent tier remains an engineering semantic decision.'
 parent_doc['current_role_counts']={'Category A metropolitan municipality':sum(p['current_2022_statutory_role']=='Category A metropolitan municipality' for p in parent_doc['parents']),'Category C district municipality':sum(p['current_2022_statutory_role']=='Category C district municipality' for p in parent_doc['parents'])}
 parent_doc['current_2022_name_mismatches']=[{'id':p['id'],'atlas_name':p['name'],'current_name':p['current_2022_name']} for p in parent_doc['parents'] if not p['name_matches_current_2022_official']]
 parent_path.write_text(json.dumps(parent_doc,ensure_ascii=False,indent=2)+'\n')
 with a.output.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=out[0].keys(),delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(sorted(out,key=lambda r:r['id']))
 measurement_rows=[]
 for r in sorted(out,key=lambda q:q['id']):
  measurement_rows.append({'id':r['id'],'reported_area_km2':round(float(r['reported_area_km2']),3),'atlas_geodesic_area_km2':round(float(r['atlas_geodesic_area_km2']),3),'relative_area_difference_vs_statsa':round(float(r['relative_area_difference_vs_statsa']),6)})
 measurement={'method_id':'south-africa-area-review','source_pdf_sha256':PDF_SHA,'baseline_part28_sha256':sha(ROOT/'data/geography/part-28.json'),'rows':measurement_rows,'summary':{'scope_count':len(out),'official_inventory_count':len(records),'area_difference_over_5pct':sum(float(r['relative_area_difference_vs_statsa'])>.05 for r in out),'area_difference_max':max(float(r['relative_area_difference_vs_statsa']) for r in out)}}
 (HERE/'unit-measurements.json').write_text(json.dumps(measurement,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'pdf_sha256':sha(pdf),'official_2022_inventory':len(records),'category_counts':{c:sum(r['category']==c for r in records) for c in ['A','B']},'scoped_units':len(out),'scoped_category_counts':{c:sum(r['category_A_or_B']==c for r in out) for c in ['A','B']},'exact_name_matches':sum(r['atlas_name']==r['StatsSA_2022_name'] for r in out),'name_review_required':sum(r['classification']=='correction-needed' for r in out),'boundary_review_required':sum(r['boundary_status']=='insufficient-evidence' for r in out),'parent_matches':sum(r['parent_role_match'] for r in out),'parent_statutory_role_counts':parent_doc['current_role_counts'],'parent_name_mismatches':parent_doc['current_2022_name_mismatches'],'area_difference_over_5pct':sum(float(r['relative_area_difference_vs_statsa'])>.05 for r in out),'area_difference_max':max(float(r['relative_area_difference_vs_statsa']) for r in out),'unique_statsa_codes':len(used),'issue435_complement_ids':len(ids435),'combined_435_436_coverage':len(set(ids435)|set(ids436)),'area_counts':area_counts,'full_official_area_counts':full_counts,'scope_435_sha256':sibling['original_issue_scope_sha256']},indent=2))
if __name__=='__main__':main()
