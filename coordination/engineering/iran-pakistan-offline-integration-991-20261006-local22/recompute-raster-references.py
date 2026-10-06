#!/usr/bin/env python3
"""Recompute only two repaired footprints from exact original climate/terrain rasters."""
import hashlib
import importlib.util
import json
import pathlib
import platform
import subprocess
import sys
import zipfile
import zlib
import gzip

import numpy
import rasterio
import shapely
import pyproj
from shapely.geometry import shape

sys.dont_write_bytecode = True
root = pathlib.Path(__file__).resolve().parents[3]
prefix = pathlib.Path(__file__).resolve().parent.relative_to(root).as_posix()
head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
baseline = 'd0cc67eac85038159f88a673acbc39b77ab7461d'
inputs = []
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
def git_read(commit, name):
    raw = subprocess.check_output(['git', '-C', str(root), 'show', commit + ':' + name])
    inputs.append({'commit': commit, 'path': name, 'bytes': len(raw), 'sha256': digest(raw)})
    return raw
def git_json(commit, name):
    raw = git_read(commit, name)
    return json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)
code_names = [prefix+'/recompute-raster-references.py', 'scripts/prepare-reference-incremental.py',
              'scripts/prepare-ownership-incremental.py', 'scripts/majority.py', 'scripts/recheck-vegetation.py',
              'scripts/prepare-topography.py', 'scripts/ellipsoidal_area.py', 'scripts/prepare-reference-attributes.py']
code = []
for name in code_names:
    raw = git_read(head, name)
    assert raw == (root/name).read_bytes(), 'Commit exact executed source before generation'
    code.append(inputs[-1])
output = pathlib.Path(sys.argv[1]).resolve()
assert output.is_relative_to(root/prefix) and not output.exists()
index = git_json(baseline, 'data/reference-attributes/index.json')
receipt = git_json(head, prefix+'/release-proof-v3/migration-receipt.json')
summary = git_json(head, prefix+'/results-v2/summary.json')
after = git_json(summary['candidate_geometry_commit'], summary['candidate_geometry_file']['path'])
before = {row['id']: row['feature']['geometry'] for row in receipt['archives']}
assert sorted(before) == sorted(after) == sorted(receipt['changed_ids']) and len(after) == 2
assert index['footprints_sha256'] == receipt['before_footprints_sha256']
original_rows = {id: [] for id in after}
for name in index['parts']:
    raw = git_read(baseline, 'data/reference-attributes/'+name)
    assert digest(raw) == index['parts_sha256'][name]
    for id, rows in json.loads(gzip.decompress(raw)):
        if id in original_rows:
            original_rows[id].extend(rows)
sys.path.insert(0, str(root/'scripts'))
spec = importlib.util.spec_from_file_location('original_reference_incremental', root/'scripts/prepare-reference-incremental.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
cache = root/'.cache/reference-repair-991'
climate = cache/'koppen-geiger-v3-original.zip'
terrain = cache/'terrain-original.tif'
assert helper.sha(climate) == index['inputs']['climate_archive']
topo_type = next(i for i,t in enumerate(index['types']) if t['attribute'] == 'topography')
assert helper.sha(terrain) == index['types'][topo_type]['metadata']['source_sha256']
climate_types = helper.type_schema(index)
sources = [{'kind':'climate-original-archive','bytes':climate.stat().st_size,'sha256':helper.sha(climate)},
           {'kind':'terrain-original-tiff','bytes':terrain.stat().st_size,'sha256':helper.sha(terrain)}]
computed = {'before':{id:[] for id in after}, 'after':{id:[] for id in after}}
native_entries = []
with zipfile.ZipFile(climate) as archive:
    for begin, end in [(1901,1930),(1931,1960),(1961,1990),(1991,2020)]:
        name = f'{begin}_{end}/koppen_geiger_0p00833333.tif'
        entry = archive.getinfo(name)
        entry_sha = hashlib.sha256(); crc = 0; size = 0
        with archive.open(name) as stream:
            while chunk := stream.read(1048576):
                entry_sha.update(chunk); crc = zlib.crc32(chunk, crc); size += len(chunk)
        assert size == entry.file_size and crc == entry.CRC
        native_entries.append({'path':name,'bytes':size,'sha256':entry_sha.hexdigest(),'crc32':crc})
        with rasterio.open('/vsizip/'+str(climate)+'/'+name) as raster:
            assert raster.crs.to_epsg() == 4326 and raster.dtypes[0] == 'uint8' and raster.transform.e < 0
            for vintage, geometries in [('before',before),('after',after)]:
                for id in sorted(after):
                    result, reason = helper.climate_summary(helper.canonical(shape(geometries[id])), raster)
                    assert result is not None, (id, begin, vintage, reason)
                    category, share, coverage = result
                    original_type = climate_types[begin]
                    import ast
                    tree = ast.parse((root/'scripts/prepare-reference-attributes.py').read_text())
                    classes = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='classes' for t in n.targets))
                    value = index['values'].index(classes[category])
                    computed[vintage][id].append([original_type,value,share,coverage])
                    if begin == 1991:
                        computed[vintage][id].append([climate_types[2026],value,share,coverage])
with rasterio.open(terrain) as raster:
    assert (raster.crs.to_epsg(),raster.width,raster.height,raster.dtypes[0]) == (4326,43200,16800,'uint8')
    for vintage, geometries in [('before',before),('after',after)]:
        for id in sorted(after):
            result,reason,coverage = helper.TOPO.summarize(helper.canonical(shape(geometries[id])),helper.RasterGrid(raster),raster.transform)
            assert result is not None, (id,vintage,reason,coverage)
            category,share,coverage = result
            computed[vintage][id].append([topo_type,index['values'].index(helper.TOPO.CLASSES[category]),share,coverage])
expected = {id:sorted([row for row in rows if index['types'][row[0]]['attribute'] in ('climate','topography')]) for id,rows in original_rows.items()}
actual_before = {id:sorted(rows) for id,rows in computed['before'].items()}
assert expected == actual_before, {'expected':expected,'recomputed_before':actual_before}
assert helper.sha(climate) == sources[0]['sha256'] and helper.sha(terrain) == sources[1]['sha256']
report = {'version':1,'execution_commit':head,'executed_sources':code,'inputs':inputs,'native_sources':sources,
          'native_archive_entries':native_entries,'before_footprints_sha256':receipt['before_footprints_sha256'],
          'after_footprints_sha256':receipt['after_footprints_sha256'],'changed_ids':sorted(after),
          'computed':computed,'original_before_values_exactly_reproduced':True,'derived_records':12,
          'runtime':{'python':platform.python_version(),'numpy':numpy.__version__,'shapely':shapely.__version__,
                     'geos':shapely.geos_version_string,'pyproj':pyproj.__version__,'rasterio':rasterio.__version__,'gdal':rasterio.__gdal_version__},
          'remaining_attributes':['vegetation'],'source_intervals_unchanged':True,'historical_claims_transferred':False,
          'installed':False,'published':False}
output.write_text(json.dumps(report, separators=(',',':'))+'\n')
print(json.dumps({'locations':2,'derived_records':12,'original_before_values_exactly_reproduced':True,'installed':False}),flush=True)
