#!/usr/bin/env python3
"""Measure the source-only San Miguel–Puerto Asís edge against current boundaries."""
import gzip,json,pathlib,subprocess,tempfile,re,hashlib
HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[2]
ids=['7082276B25468013916959','7082276B42533804398270']; lids=['gb:COL:ADM2:'+x for x in ids]
src=json.loads(gzip.decompress((HERE.parent/'regional-review-b2e551685bf2e064/sources/geoboundaries-COL-ADM2-2020.geojson.gz').read_bytes())); by={f['properties']['shapeID']:f for f in src['features']}
idx=json.loads((ROOT/'data/world-index.json').read_text()); curr={}
for fn in idx['parts']:
 for f in json.loads((ROOT/'data'/fn).read_text())['features']:
  if f['properties']['id'] in lids: curr[f['properties']['metadata']['original_id']]=f
if set(curr)!=set(ids): raise SystemExit('baseline pair missing')
features=[]
for version, collection in [('source',[by[x] for x in ids]),('current',[curr[x] for x in ids])]:
 for f in collection:
  p=f['properties']; key=p.get('shapeID',p.get('metadata',{}).get('original_id'))
  features.append({'type':'Feature','geometry':f['geometry'],'properties':{'version':version,'id':key}})
fc={'type':'FeatureCollection','features':features}; raw=json.dumps(fc,separators=(',',':')).encode()
with tempfile.TemporaryDirectory(prefix='worldatlas-putumayo-') as td:
 td=pathlib.Path(td); geo=td/'pair.geojson'; projected=td/'pair-utm.geojson'; geo.write_bytes(raw)
 subprocess.run(['ogr2ogr','-f','GeoJSON','-t_srs','EPSG:32618',str(projected),str(geo)],check=True,capture_output=True,text=True)
 sql="""SELECT ST_Length(ST_Intersection(ST_Boundary(sa.geometry),ST_Boundary(sb.geometry))) AS source_common_edge_m, ST_Length(ST_Intersection(ST_Boundary(ca.geometry),ST_Boundary(cb.geometry))) AS current_exact_shared_edge_m, ST_Length(ST_Intersection(src.line,ST_Buffer(ST_Boundary(ca.geometry),5))) AS source_edge_within_5m_of_current_a_m, ST_Length(ST_Intersection(src.line,ST_Buffer(ST_Boundary(cb.geometry),5))) AS source_edge_within_5m_of_current_b_m, ST_Length(ST_Intersection(src.line,ST_Buffer(ST_Boundary(ca.geometry),25))) AS source_edge_within_25m_of_current_a_m, ST_Length(ST_Intersection(src.line,ST_Buffer(ST_Boundary(cb.geometry),25))) AS source_edge_within_25m_of_current_b_m FROM 'pair' sa JOIN 'pair' sb ON sa.version='source' AND sb.version='source' AND sa.id='7082276B25468013916959' AND sb.id='7082276B42533804398270' JOIN 'pair' ca ON ca.version='current' AND ca.id=sa.id JOIN 'pair' cb ON cb.version='current' AND cb.id=sb.id JOIN (SELECT ST_Intersection(ST_Boundary(a.geometry),ST_Boundary(b.geometry)) AS line FROM 'pair' a JOIN 'pair' b ON a.version='source' AND b.version='source' AND a.id='7082276B25468013916959' AND b.id='7082276B42533804398270') src ON 1=1"""
 out=subprocess.run(['ogrinfo','-q','-dialect','SQLite','-sql',sql,str(projected)],check=True,capture_output=True,text=True).stdout
 fields={}
 for key,val in re.findall(r'^\s+([a-z0-9_]+) \(Real\) = ([0-9.eE+-]+)',out,re.M): fields[key]=float(val)
 expected=['source_common_edge_m','current_exact_shared_edge_m','source_edge_within_5m_of_current_a_m','source_edge_within_5m_of_current_b_m','source_edge_within_25m_of_current_a_m','source_edge_within_25m_of_current_b_m']
 if set(fields)!=set(expected): raise SystemExit(f'could not parse OGR metrics: {out}')
result={'units':'metres after OGR reprojection to EPSG:32618','municipalities':[{'id':lids[0],'name':'San Miguel (La Dorada)'},{'id':lids[1],'name':'Puerto Asís'}],'source_uncompressed_sha256':hashlib.sha256(gzip.decompress((HERE.parent/'regional-review-b2e551685bf2e064/sources/geoboundaries-COL-ADM2-2020.geojson.gz').read_bytes())).hexdigest(),'metrics':fields,'interpretation':'Source boundaries share an 8.262 km line. Current simplified boundaries have zero exact shared-line length, but 8.185 km of that source line lies within 5 m of each current boundary. This is consistent with a small vertex/precision representation difference. It is not evidence to move either unit; named source precision and full geometry validation remain open.'}
(HERE/'putumayo-pair-investigation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(result,ensure_ascii=False,indent=2))
