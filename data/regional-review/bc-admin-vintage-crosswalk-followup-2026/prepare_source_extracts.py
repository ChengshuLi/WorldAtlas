#!/usr/bin/env python3
"""Rebuild bounded BC extracts from the pinned #485 sources and StatCan 2016 DBF."""
from __future__ import annotations
import hashlib, json, zipfile
from pathlib import Path
import shapefile
from pyproj import CRS, Transformer
from shapely.geometry import shape, mapping
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PARENT = ROOT / 'data/regional-review/regional-review-4254da254d94f450'
ASSESSMENT = PARENT / 'assessment.json'
GB_SOURCE = PARENT / 'sources/geoboundaries-CAN-ADM3-2016.geojson'
ZIP = OUT / 'sources/statistics-canada-2016-census-subdivisions-digital-boundary.zip'
EXPECTED_ZIP_BYTES = 23822515
EXPECTED_ZIP_SHA256 = '1bc5638e964d07c289fcdb34553dc593dd16600ec01db16d202c1df28682dd1b'

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def write_json(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')

assessment=json.loads(ASSESSMENT.read_text())
assert ZIP.stat().st_size==EXPECTED_ZIP_BYTES and sha(ZIP)==EXPECTED_ZIP_SHA256
rows=[]
for loc in assessment['locations']:
    if loc['current_parent_id']!='framework:province:british-columbia:83abeaaac0ca': continue
    for m in loc['source_identity_and_vintage'].get('members',[]):
        rows.append({'source_shape_id':m['source_shape_id'],'source_name':m['source_name'],'location_id':loc['location_id'],'location_name':loc['name'],'current_parent_id':loc['current_parent_id'],'complete_parent_chain':[{'id':a['id'],'name':a['name'],'parent_id':a.get('parent_id')} for a in loc['full_parent_chain']],'best_2021_csd_id':m['best_2021_csd_id'],'best_2021_csd_name':m['best_2021_csd_name'],'name_matches_2021_csd_within_cd':m['name_matches_2021_csd_within_cd'],'prior_overlap_pct':m['overlap_pct']})
ids=[r['source_shape_id'] for r in rows]
assert len(rows)==376 and len(set(ids))==376
src=json.loads(GB_SOURCE.read_text())
features={f['properties']['shapeID']:f for f in src['features']}
assert len(features)==5162 and set(ids)<=features.keys()
sel=[features[i] for i in sorted(ids)]
# Keep bounded extracts deterministic; the source IDs are retained on every feature.
for part in range(4):
    subset=sel[part*94:(part+1)*94]
    write_json(OUT/f'geoboundaries-bc-2016-members-part-{part+1:02d}-of-04.geojson',{'type':'FeatureCollection','features':subset})

with zipfile.ZipFile(ZIP) as z:
    shp=z.open('lcsd000a16a_e.shp'); shx=z.open('lcsd000a16a_e.shx'); dbf=z.open('lcsd000a16a_e.dbf')
    reader=shapefile.Reader(shp=shp,shx=shx,dbf=dbf,encoding='latin1')
    fields=[f[0] for f in reader.fields[1:]]
    ix={k:fields.index(k) for k in ['CSDUID','CSDNAME','CSDTYPE','PRUID','PRNAME','CDUID','CDNAME','CDTYPE']}
    prj=z.read('lcsd000a16a_e.prj').decode('utf-8')
    to_wgs=Transformer.from_crs(CRS.from_wkt(prj),CRS.from_epsg(4326),always_xy=True).transform
    out_features=[]
    for sr in reader.iterShapeRecords():
        rec=list(sr.record)
        if str(rec[ix['PRUID']]).strip()!='59': continue
        geom=shape(sr.shape.__geo_interface__)
        geom=transform(to_wgs,geom)
        out_features.append({'type':'Feature','id':str(rec[ix['CSDUID']]).strip(),'properties':{k:str(rec[ix[k]]).strip() for k in ix},'geometry':mapping(geom)})
write_json(OUT/'statistics-canada-british-columbia-census-subdivisions-2016.geojson',{'type':'FeatureCollection','features':sorted(out_features,key=lambda f:f['id'])})

write_json(OUT/'source-member-roster.json',{'source_id':'geoBoundaries-CAN-ADM3-2016','baseline_commit':'c2464fceb8481d5f1273793dbc3869fcb4262727','baseline_assessment_path':str(ASSESSMENT.relative_to(ROOT)),'baseline_assessment_sha256':sha(ASSESSMENT),'baseline_sources_manifest_path':str((PARENT/'sources-manifest.json').relative_to(ROOT)),'baseline_sources_manifest_sha256':sha(PARENT/'sources-manifest.json'),'source_baseline_path':str(GB_SOURCE.relative_to(ROOT)),'source_baseline_sha256':sha(GB_SOURCE),'source_baseline_bytes':GB_SOURCE.stat().st_size,'source_archive_url':'https://github.com/wmgeolab/geoBoundaries/releases/tag/9469f09','source_archive_metadata_path':str((PARENT/'sources/geoboundaries-CAN-ADM3-source-metadata.json').relative_to(ROOT)),'statcan_2016_archive_path':str(ZIP.relative_to(ROOT)),'statcan_2016_archive_sha256':sha(ZIP),'statcan_2016_archive_bytes':ZIP.stat().st_size,'member_count':len(rows),'members':sorted(rows,key=lambda x:x['source_shape_id'])})
print(json.dumps({'source_rows':len(sel),'source_extract_bytes':[ (OUT/f'geoboundaries-bc-2016-members-part-{p:02d}-of-04.geojson').stat().st_size for p in range(1,5)],'statcan_2016_bc_csd_count':len(out_features),'statcan_2016_extract_bytes':(OUT/'statistics-canada-british-columbia-census-subdivisions-2016.geojson').stat().st_size,'statcan_2016_zip_sha256':sha(ZIP)},indent=2))
