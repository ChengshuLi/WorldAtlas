#!/usr/bin/env python3
"""Extract the recorded county sample from the pinned 2025 Census TIGER ZIP.
Requires pyshp==2.3.1. Writes only to this script's owned evidence directory.
"""
import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path
import shapefile

ARCHIVE_SHA256 = '9c6e9d9076abce2670d1de255de3710c35ecca00a7005d88e012dec52d95f763'
GEOIDS = {'05001','22023','22045','22057','22075','22087','22101','22109','22113'}
OUT = Path(__file__).resolve().parent / 'counties-coastal-sample-2025.geojson'
parser = argparse.ArgumentParser()
parser.add_argument('--archive', required=True, type=Path, help='Restored Census archive; its hash is verified before reading')
args = parser.parse_args()
assert shapefile.__version__ == '2.3.1', shapefile.__version__
raw = args.archive.read_bytes()
assert hashlib.sha256(raw).hexdigest() == ARCHIVE_SHA256, 'Census archive SHA-256 mismatch'
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    shp = next(name for name in archive.namelist() if name == 'tl_2025_us_county.shp')
    dbf = shp[:-4] + '.dbf'
    reader = shapefile.Reader(shp=io.BytesIO(archive.read(shp)), dbf=io.BytesIO(archive.read(dbf)))
    fields = [field[0] for field in reader.fields[1:]]
    features = []
    for record in reader.iterShapeRecords():
        properties = dict(zip(fields, record.record))
        if properties['GEOID'] in GEOIDS:
            features.append({'type':'Feature','geometry':record.shape.__geo_interface__,'properties':properties})
assert len(features) == len(GEOIDS)
OUT.write_text(json.dumps({'type':'FeatureCollection','features':sorted(features,key=lambda feature:feature['properties']['GEOID'])},separators=(',',':'))+'\n')
print(json.dumps({'archive_sha256':ARCHIVE_SHA256,'archive_shapefile':shp,'feature_count':len(features),'excerpt_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'excerpt_bytes':OUT.stat().st_size},indent=2))
