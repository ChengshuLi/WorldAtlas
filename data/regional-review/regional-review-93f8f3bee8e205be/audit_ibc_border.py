#!/usr/bin/env /usr/bin/python3
"""Map-only comparison of IBC Alaska boundary segments to the source/current Alaska outer edge."""
import json,gzip
from pathlib import Path
from osgeo import ogr,osr
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]; SRC=HERE/'sources';ogr.UseExceptions()
def read(p):
 p=Path(p)
 with gzip.open(p,'rt') if p.suffix=='.gz' else p.open() as f:return json.load(f)
def srs(epsg):
 s=osr.SpatialReference();s.ImportFromEPSG(epsg);s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);return s
src=srs(4326);dst=srs(3338);ct=osr.CoordinateTransformation(src,dst)
def geom(obj):
 g=ogr.CreateGeometryFromJson(json.dumps(obj,separators=(',',':')));g.AssignSpatialReference(src);g.TransformTo(dst)
 if not g.IsValid():g=g.MakeValid()
 return g
adm1=read(SRC/'geoboundaries-USA-ADM1.geojson');alaska=next(f for f in adm1['features'] if f['properties']['shapeName']=='Alaska');adm1g=geom(alaska['geometry'])
source2=read(SRC/'geoboundaries-USA-ADM2.geojson'); ids=set(read(HERE/'scope.json')['member_location_ids']);current=read(SRC/'current-scope-and-parents.geojson.gz')
predecessors=set()
for f in current['features']:
 p=f['properties']
 if p.get('parent_id') in ('framework:province:alaska:4057e2fddbc5','framework:province:alaska:d12fadcdd2dd'):
  predecessors.add(p.get('metadata',{}).get('original_id') or p['id'].rsplit(':',1)[-1])
source_by_id={f['properties']['shapeID']:f for f in source2['features']}
src_union=None
for sid in predecessors:
 g=geom(source_by_id[sid]['geometry']);src_union=g.Clone() if src_union is None else src_union.Union(g)
current_union=None
for f in current['features']:
 if f['properties'].get('parent_id') in ('framework:province:alaska:4057e2fddbc5','framework:province:alaska:d12fadcdd2dd'):
  g=geom(f['geometry']);current_union=g.Clone() if current_union is None else current_union.Union(g)

d=ogr.Open('/vsizip/'+str((SRC/'ibc-us-canada-boundary-v1-3.zip').resolve()));layer=d.GetLayer(0);records=[];joined=None
for f in layer:
 no=f.GetField('SectionNum')
 if no not in (27,28,29):continue
 g=f.GetGeometryRef().Clone();g.AssignSpatialReference(srs(4269));g.TransformTo(dst)
 joined=g.Clone() if joined is None else joined.Union(g)
 def screen(boundary):
  vals={}
  for m in (25,100,250,500,1000):
   buf=boundary.Buffer(m); vals[str(m)]=round(g.Intersection(buf).Length()/max(g.Length(),1)*100,5)
  return vals
 records.append({'section_num':no,'section_name':f.GetField('SectionEng'),'max_scale':f.GetField('MaxScale'),'length_km_epsg3338':round(g.Length()/1000,3),'within_m_of_reference_boundary_pct':{'2018_USA_ADM1_Alaska':screen(adm1g.Boundary()),'2018_USA_ADM2_county_union':screen(src_union.Boundary()),'current_assigned_location_union':screen(current_union.Boundary())},'interpretation':'The official IBC v1.3 segment is a mapping representation with source-declared scale limits; proximity screens are not a legal boundary determination.'})
report={'source':'International Boundary Commission US–Canada boundary shapefile v1.3 (2018-04-20), official digital boundary page; NAD83 EPSG:4269, reprojected temporarily to Alaska Albers EPSG:3338. The IBC page and embedded metadata say mapping use only; do not use to define the boundary.','source_feature_count':layer.GetFeatureCount(),'alaska_segments':records,'aggregate_selected_segment_length_km':round(joined.Length()/1000,3),'scope_source_predecessor_count':len(predecessors),'method':'Buffer the pinned official Alaska-related IBC section lines by 25, 100, 250, 500 and 1,000 m and measure line fraction inside each buffered boundary of the pinned 2018 ADM1 Alaska polygon, assigned 2018 ADM2 county union, and current assigned Alaska-location union. Temporary projected geometries only.','limitations':['The IBC source contains both Canada and U.S. metadata with a conflicting 29-vs-30 segment count; the retained Shapefile has 30 features.','IBC metadata describes sections and map scales; it expressly says the line is for mapping, generated from recent surveys and datum conversions, and is not intended to define the boundary beyond the segment scale.','Buffer proximity does not prove same line, ownership, legal delimitation, or a basis for changing released geography.','No official Canadian territorial polygon was separately compared here; coordinate with the Canadian-side packet/integrator before any correction proposal.']}
(HERE/'ibc-border-screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'sections':len(records),'length_km':report['aggregate_selected_segment_length_km'],'records':records},indent=2))
