#!/usr/bin/env python3
"""Create CC-BY subject-footprint extracts from exact ESA WorldCover v200 tiles."""
from pathlib import Path
import gzip, hashlib, json, subprocess, urllib.request, datetime
import rasterio
from rasterio.mask import mask
from shapely.geometry import shape, box
from shapely.ops import unary_union

BASELINE = 'eddf3d98c725a768959e431462b16d9adf507a41'
FAMILY_ID = 'gap-source-batch:8875fd920e43656b5f36e704'
FAMILY_ROW_SHA256 = 'a08249214711d84d7d220a61fe10f2d4582e7bc64f1a5ae811436ddaf22d94b3'
CUSTODY_INDEX = 'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'
CUSTODY_INDEX_SHA256 = 'dfcca9fe2bb64805b94e784be89b3523f5683b95cbd4a617283965ca6187a77c'
PACKET = Path('research/geography/indonesia-borneo-source-fitness-20261007')
SRC = PACKET / 'sources/v1/.staging/worldcover'
OUT = PACKET / 'sources/v1/worldcover-crops'
TILES = ['S03E114']

def git_bytes(path):
    return subprocess.check_output(['git', 'show', f'{BASELINE}:{path}'])

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

report_path = 'coordination/engineering/global-actionability-routing-20261007/results/report.json'
report = json.loads(git_bytes(report_path))
route_dir = 'coordination/engineering/global-actionability-routing-20261007/results/'
parts = sorted((x for x in report['outputs'] if x['path'].startswith('families-')), key=lambda x: x['path'])
raw_family = b''.join(gzip.decompress(git_bytes(route_dir + p['path'])) for p in parts)
matching = [line for line in raw_family.splitlines() if line and FAMILY_ID.encode() in line]
if len(matching) != 1 or sha(matching[0]) != FAMILY_ROW_SHA256:
    raise SystemExit('Pinned family row missing, duplicated, or changed')
ids = set(json.loads(matching[0])['complete_component_ids'])
if len(ids) != 45:
    raise SystemExit('Pinned family membership is not 45 unique components')
index_bytes = git_bytes(CUSTODY_INDEX)
if sha(index_bytes) != CUSTODY_INDEX_SHA256:
    raise SystemExit('Custody index drift')
index = json.loads(index_bytes)
features = {}
for alias in index['aliases']:
    source_path = alias['original']['path']
    if '/components-v3/components-' not in source_path:
        continue
    raw = git_bytes(alias['payload'])
    descriptor = alias['original']
    if len(raw) != descriptor['bytes'] or sha(raw) != descriptor['sha256']:
        raise SystemExit('Component payload differs from custody alias: ' + source_path)
    decoded = gzip.decompress(raw)
    if len(decoded) != descriptor['uncompressed_bytes'] or sha(decoded) != descriptor['uncompressed_sha256']:
        raise SystemExit('Decoded component shard differs from custody alias: ' + source_path)
    for feature in json.loads(decoded)['features']:
        if feature['id'] in ids:
            if feature['id'] in features:
                raise SystemExit('Duplicate component identity in custody shards')
            features[feature['id']] = feature
if set(features) != ids:
    raise SystemExit('Pinned custody shards do not contain the complete selected roster')
geometries = [shape(features[identity]['geometry']) for identity in sorted(ids)]
if any(g.geom_type not in ('Polygon', 'MultiPolygon') or g.is_empty or not g.is_valid for g in geometries):
    raise SystemExit('Invalid original component geometry; no repair is allowed')
footprint = unary_union(geometries)
if footprint.is_empty or not footprint.is_valid:
    raise SystemExit('Invalid exact component union')

OUT.mkdir(parents=True, exist_ok=True)
SRC.mkdir(parents=True, exist_ok=True)
receipt_path = PACKET / 'sources/v1/worldcover-extract-receipts.json'
if receipt_path.exists():
    raise SystemExit('Refusing to replace an existing receipt: ' + str(receipt_path))
records = []
for tile in TILES:
    filename = f'ESA_WorldCover_10m_2021_v200_{tile}_Map.tif'
    original = SRC / filename
    url = f'https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/{filename}'
    if not original.is_file():
        request = urllib.request.Request(url, headers={'User-Agent': 'WorldAtlas source research/1.0'})
        with urllib.request.urlopen(request, timeout=120) as response, original.open('wb') as stream:
            while block := response.read(1024 * 1024): stream.write(block)
    head = urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=30)
    expected_bytes = int(head.headers.get('Content-Length', '0'))
    etag = head.headers.get('ETag')
    if expected_bytes != original.stat().st_size:
        raise SystemExit('Captured source tile size differs from official endpoint metadata')
    raw_hash = hashlib.sha256()
    with original.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            raw_hash.update(block)
    with rasterio.open(original) as ds:
        if ds.crs.to_epsg() != 4326 or ds.count != 1 or ds.dtypes[0] != 'uint8':
            raise SystemExit('Unexpected WorldCover raster frame/schema')
        bounds = ds.bounds
        tile_geom = box(bounds.left, bounds.bottom, bounds.right, bounds.top)
        if not footprint.intersects(tile_geom):
            raise SystemExit('Selected tile has no component coverage: ' + tile)
        data, transform = mask(ds, [footprint.__geo_interface__], crop=True, all_touched=True, nodata=0)
        profile = ds.profile.copy()
        profile.update(driver='GTiff', height=data.shape[1], width=data.shape[2], transform=transform,
                       count=1, dtype='uint8', nodata=0, compress='deflate', predictor=1,
                       tiled=True, blockxsize=256, blockysize=256)
        outpath = OUT / f'ESA_WorldCover_10m_2021_v200_{tile}_Map_source-extract-v1.tif'
        if outpath.exists():
            raise SystemExit('Refusing to replace an existing crop: ' + str(outpath))
        with rasterio.open(outpath, 'w-', **profile) as out:
            out.write(data)
            out.update_tags(source_product='ESA WorldCover 10 m 2021 v200', source_tile=tile,
                            source_sha256=raw_hash.hexdigest(), baseline_commit=BASELINE,
                            extraction='all_touched=true union of exact 45 original component polygons; exterior pixels set to source nodata 0')
        with rasterio.open(outpath) as crop:
            crop_bytes = outpath.read_bytes()
            crop_bounds = list(crop.bounds)
            crop_dimensions = [crop.width, crop.height]
        if len(crop_bytes) >= 32 * 1024 * 1024:
            raise SystemExit('Derived crop exceeds per-file evidence budget')
        records.append({'source_tile': tile, 'source_path': str(original), 'source_url': url,
                            'source_bytes': original.stat().st_size, 'source_sha256': raw_hash.hexdigest(),
                            'source_etag': etag,
                            'retrieved_at': datetime.datetime.fromtimestamp(original.stat().st_mtime, datetime.timezone.utc).isoformat(),
                            'crop_path': outpath.as_posix(),
                            'crop_bytes': len(crop_bytes), 'crop_sha256': sha(crop_bytes),
                            'crop_bounds': crop_bounds, 'crop_dimensions': crop_dimensions,
                            'crs': ds.crs.to_string(), 'source_pixel_size_degrees': [abs(ds.transform.a), abs(ds.transform.e)],
                            'nodata': ds.nodata})

receipt = {'version': 1, 'baseline_commit': BASELINE, 'family_id': FAMILY_ID,
           'family_row_sha256': FAMILY_ROW_SHA256, 'custody_index_sha256': CUSTODY_INDEX_SHA256,
           'component_count': len(ids), 'component_union_bounds': list(footprint.bounds),
           'retrieved_at': '2026-10-07', 'product_version': 'ESA WorldCover 10 m 2021 v200',
           'license': 'CC BY 4.0; source attribution required', 'records': records}
with receipt_path.open('x', encoding='utf-8') as stream:
    stream.write(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
for tile in TILES:
    (SRC / f'ESA_WorldCover_10m_2021_v200_{tile}_Map.tif').unlink()
if not any(SRC.iterdir()): SRC.rmdir()
print(json.dumps(receipt, indent=2))
