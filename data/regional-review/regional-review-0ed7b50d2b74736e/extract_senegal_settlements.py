#!/usr/bin/env python3
"""Extract the licensed 2017 Senegal OCHA settlement points from retained source bytes."""
import gzip,hashlib,json,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parent;SRC=ROOT/'sources';archive=SRC/'hdx-senegal-settlements-2017.zip.gz'
with tempfile.TemporaryDirectory(prefix='wa478-sen-settlements-') as td:
 t=pathlib.Path(td);z=t/'source.zip';z.write_bytes(gzip.decompress(archive.read_bytes()))
 shp='/vsizip/'+str(z)+'/sen_plpp_gov_ocha_09082017.shp';out=t/'senegal-settlements.geojson'
 subprocess.run(['ogr2ogr','-f','GeoJSON','-lco','RFC7946=YES',str(out),shp],check=True)
 raw=out.read_bytes();gz=gzip.compress(raw,mtime=0);dest=SRC/'senegal-settlements-2017.geojson.gz';dest.write_bytes(gz)
 data=json.loads(raw);result={'file':'sources/'+dest.name,'features':len(data['features']),'restored_bytes':len(raw),
  'restored_sha256':hashlib.sha256(raw).hexdigest(),'gzip_bytes':len(gz),'gzip_sha256':hashlib.sha256(gz).hexdigest(),
  'source_archive':'sources/hdx-senegal-settlements-2017.zip.gz','source_archive_gzip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
  'ogr_version':subprocess.check_output(['ogr2ogr','--version'],text=True).strip(),'filter':'none; full Senegal country file'}
(ROOT/'senegal-settlement-extract.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,indent=2))
