#!/usr/bin/env python3
"""Exhaustively screen GSHHG high-resolution land features in four island windows.

This is a diagnostic source comparison, not a legal boundary classifier. Run with
explicit external GSHHS_f_L1.shp path and write only into this owned packet.
"""
import argparse,json,hashlib
from pathlib import Path
import shapefile
from shapely.geometry import shape,box
from shapely.ops import transform
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
IDS=['atlas:coverage:ATF-5916','atlas:coverage:ATF-5917','atlas:coverage:ATF-5918','atlas:coverage:HMD+00?']
SITE={IDS[0]:'Kerguelen',IDS[1]:'Crozet',IDS[2]:'Amsterdam-Saint-Paul',IDS[3]:'Heard-McDonald'}
WINDOWS={'Kerguelen':(67.5,-50.5,71.6,-47.8),'Crozet':(49.5,-47.2,53,-45.5),'Amsterdam-Saint-Paul':(77.2,-39,78,-37.5),'Heard-McDonald':(72.5,-53.6,74.5,-52.5)}
def features():
 for p in sorted((ROOT/'data/geography').glob('part-*.json')):
  for f in json.loads(p.read_text())['features']:
   if f.get('id') in IDS:yield f
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--shapefile',required=True,type=Path);ap.add_argument('--output',default=OUT/'shoreline-screen.json',type=Path);ap.add_argument('--check',action='store_true');args=ap.parse_args()
if not args.output.resolve().is_relative_to(OUT.resolve()):raise SystemExit('output must stay in the owned packet')
records_path=OUT/'shoreline-records.jsonl'
current={f['id']:shape(f['geometry']) for f in features()}
if set(current)!=set(IDS):raise SystemExit('baseline location set differs')
project=Transformer.from_crs(4326,6933,always_xy=True).transform
current_m={SITE[i]:transform(project,g) for i,g in current.items()}
reader=shapefile.Reader(str(args.shapefile)); rows=[]
for sr in reader.iterShapeRecords():
 g=shape(sr.shape.__geo_interface__);contexts=[n for n,w in WINDOWS.items() if g.intersects(box(*w))]
 if not contexts:continue
 d=dict(zip([x[0] for x in reader.fields[1:]],sr.record));name=contexts[0];gm=transform(project,g)
 rows.append({'context':name,'gshhg_id':str(d['id']),'level':int(d['level']),'source_code':d['source'],'bbox_wgs84':list(g.bounds),'area_attribute_km2':float(d['area']),'area_epsg6933_km2':gm.area/1e6,'distance_to_current_m':gm.distance(current_m[name])})
rows.sort(key=lambda r:(r['context'],int(r['gshhg_id'])))
summary={}
for n in WINDOWS:
 rs=[x for x in rows if x['context']==n]
 summary[n]={'features_screened':len(rs),'features_over_1km2':sum(x['area_epsg6933_km2']>1 for x in rs),'features_over_1km2_outside_500m':sum(x['area_epsg6933_km2']>1 and x['distance_to_current_m']>500 for x in rs),'total_screened_area_epsg6933_km2':sum(x['area_epsg6933_km2'] for x in rs),'unmatched_over_1km2':[x['gshhg_id'] for x in rs if x['area_epsg6933_km2']>1 and x['distance_to_current_m']>500]}
base={'source':'GSHHG 2.3.7 high-resolution GSHHS_f_L1 shoreline','official_url':'https://www.soest.hawaii.edu/pwessel/gshhg/','license':'GNU LGPL 3.0 as stated by the distributed GSHHG release','method':'Enumerate every level-1 GSHHS polygon intersecting each fixed WGS84 window, project to EPSG:6933 and measure its distance/area against the current atlas location polygon. Current atlas geometry and the canonical region membership are read-only. 500 m is only a diagnostic coast-tolerance; >1 km2 is a reporting threshold, not an island definition. Overlapping/nearby islands and source-scale differences prevent using counts/areas as authoritative unit totals. GSHHG has mixed source lineage; do not treat it as an administrative or ownership authority.','baseline_commit':json.loads((OUT/'baseline-extract.json').read_text())['baseline_commit'],'shapefile_sha256':sha(args.shapefile),'shapefile_bytes':args.shapefile.stat().st_size,'component_counts_current':{i:(len(g.geoms) if hasattr(g,'geoms') else 1) for i,g in current.items()},'windows_wgs84':{n:list(v) for n,v in WINDOWS.items()},'screen_summary':summary,'record_count':len(rows),'records_path':records_path.name}
records=''.join(json.dumps(x,separators=(',',':'))+'\n' for x in rows)
base['records_sha256']=hashlib.sha256(records.encode()).hexdigest()
summary_payload=json.dumps(base,indent=2)+'\n'
if args.check:
 if not records_path.exists() or records_path.read_text()!=records or not args.output.exists() or args.output.read_text()!=summary_payload:raise SystemExit('shoreline screen differs; review source changes before regeneration')
else:
 records_path.write_text(records);args.output.write_text(summary_payload)
print(json.dumps({'result':'passed' if args.check else 'written','records':len(rows),'summary':summary},indent=2))
