#!/usr/bin/env python3
"""Create reproducible WCA point and edge-matched context subsets from #479 originals."""
from __future__ import annotations
import gzip,hashlib,json,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parent
REPO=ROOT.parents[2]
PRIOR=REPO/'data/regional-review/regional-review-9d08839e1cdb0c8f/sources'
OUT=ROOT/'sources';OUT.mkdir(exist_ok=True)
COUNTRIES=['Nigeria','Sénégal','Senegal','Sierra Leone','Niger','Benin','Cameroon','Chad','Mauritania','Mali','Guinea','Guinea-Bissau','The Gambia','Gambia','Liberia']
COUNTRIES=list(dict.fromkeys(COUNTRIES))
POINT_COUNTRIES=['Nigeria','Senegal','Sierra Leone']
records=[]
def extract(archive_name,level,layerdir,layername,outname,where_field,countries=COUNTRIES):
 archive_gz=PRIOR/archive_name
 if not archive_gz.exists(): raise FileNotFoundError(archive_gz)
 with tempfile.TemporaryDirectory(prefix='wa478-') as td:
  t=pathlib.Path(td); z=t/'src.zip';z.write_bytes(gzip.decompress(archive_gz.read_bytes()))
  shp=f'/vsizip/{z}/{layerdir}/{layername}.shp' if layerdir else f'/vsizip/{z}/{layername}.shp'
  out=t/'subset.geojson'
  country_sql=','.join("'"+x.replace("'","''")+"'" for x in countries)
  where=f"{where_field} IN ({country_sql})"
  run=subprocess.run(['ogr2ogr','-f','GeoJSON','-lco','RFC7946=YES','-where',where,str(out),shp],capture_output=True,text=True)
  if run.returncode: raise RuntimeError(run.stderr[-4000:])
  raw=out.read_bytes(); gz=gzip.compress(raw,mtime=0);target=OUT/outname;target.write_bytes(gz)
  j=json.loads(raw);rec={'file':f'sources/{outname}','feature_count':len(j['features']),
   'countries':sorted({str(f['properties'].get(where_field) or '') for f in j['features']}),
   'restored_bytes':len(raw),'restored_sha256':hashlib.sha256(raw).hexdigest(),'gzip_bytes':len(gz),
   'gzip_sha256':hashlib.sha256(gz).hexdigest(),'source_archive':'data/regional-review/regional-review-9d08839e1cdb0c8f/sources/'+archive_name,
   'source_archive_gzip_sha256':hashlib.sha256(archive_gz.read_bytes()).hexdigest(),'where':where,
   'ogr_version':subprocess.check_output(['ogr2ogr','--version'],text=True).strip()}
  records.append({'level':level,**rec})

extract('hdx-wca-wca_pplp_ocha.zip.gz','settlement-points','', 'wca_pplp_ocha','wca-settlement-points-region-subset.geojson.gz','admin0Name',POINT_COUNTRIES)
for level,dirname,layer,source_file,outname in [
 (0,'wca_admbnda_adm0_edgematched_942026','wca_admbnda_adm0_edgematched','hdx-wca-wca_admbnda_adm0_edgematched_942026.zip.gz','wca-adm0-region-neighbors.geojson.gz'),
 (1,'wca_admbnda_adm1_edgematched_942026','wca_admbnda_adm1_edgematched','hdx-wca-wca_admbnda_adm1_edgematched_942026.zip.gz','wca-adm1-region-neighbors.geojson.gz')]:
 extract(source_file,f'adm{level}',dirname,layer,outname,'adm0_name')
(ROOT/'context-extract.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(records,ensure_ascii=False,indent=2))
