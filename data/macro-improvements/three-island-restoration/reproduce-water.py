#!/usr/bin/env python3
"""Optional source audit: reconstruct retained water/municipal derivatives from original OSM bytes.
Requires osmium==4.2.0 only for this offline check, not the application or producer.
"""
import argparse,gzip,hashlib,json,pathlib,tempfile,tarfile,io,zipfile
import osmium
from shapely import from_wkb,to_wkb
from shapely.geometry import Point
P=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
a=argparse.ArgumentParser();a.add_argument('--root',required=True);args=a.parse_args();root=pathlib.Path(args.root);p=json.loads((P/'proposal.json').read_bytes())
rows=json.loads(gzip.decompress((P/'water-source-features.json.gz').read_bytes()));expected={(r['source_type'],r['id']):r for r in rows if r['id']!=2184073};factory=osmium.geom.WKBFactory();seen=set();targets={r['slug']:from_wkb(gzip.decompress((root/r['coast_path']).read_bytes())) for r in p['locations']}
class Audit(osmium.SimpleHandler):
 def area(self,a):
  key=('way' if a.from_way() else 'relation',a.orig_id());tags=dict(a.tags)
  relevant=((tags.get('natural')=='water' or tags.get('waterway')=='riverbank' or tags.get('landuse')=='reservoir') and tags.get('water')!='sea') or tags.get('boundary')=='administrative'
  if not relevant:return
  g=from_wkb(factory.create_multipolygon(a))
  if not any(g.intersects(t) for t in targets.values()) or key==('relation',2184073):return
  if key not in expected:raise ValueError('Original extract contains unretained relevant water or admin polygon')
  row=expected[key]
  if not g.is_valid or sha(to_wkb(g))!=row['wkb_sha256'] or tags!=row['tags'] or a.version!=row['source_version'] or str(a.timestamp)!=row['source_timestamp']:raise ValueError('Retained assembly differs from original PBF')
  seen.add(key)
source=root/'data/macro-improvements/macro-coverage-africa-americas/osm/greenland-latest.osm.pbf'
if sha(source.read_bytes())!=p['source_inputs'][source.relative_to(root).as_posix()]:raise ValueError('Original PBF bytes changed')
Audit().apply_file(str(source),locations=True)
if seen!=set(expected):raise ValueError('Missing original water/admin assembly')
# Separately verify the named-island identities against retained original GeoNames ZIP bytes.
with tarfile.open(root/'data/macro-improvements/macro-coverage-africa-americas/geonames-country-dumps.tar.gz') as tf:
 source_rows={}
 for m in tf:
  if pathlib.Path(m.name).name not in ['GL.zip','SH.zip']:continue
  country=pathlib.Path(m.name).stem;z=zipfile.ZipFile(io.BytesIO(tf.extractfile(m).read()));source_rows.update({r.split('\t')[0]:r.split('\t') for r in z.read(country+'.txt').decode().splitlines()})
for row in p['locations']:
 original=source_rows[str(row['geonames_id'])]
 if original!=row['geonames_original_row'] or original[7]!='ISL' or not targets[row['slug']].covers(Point(float(original[5]),float(original[4]))):raise ValueError('Named source identity/coordinate mismatch')
print(json.dumps({'verified':True,'mapped_water_and_municipal_assemblies':len(seen),'exact_original_named_island_rows':3,'original_PBF_sha256':sha(source.read_bytes()),'mapped_water_completeness_not_hydrological_completeness':True}))
