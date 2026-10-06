#!/usr/bin/env python3
"""Small known-coordinate positive/negative controls for WFD axis-order/project/intersection method."""
import json, pathlib
from pyproj import Transformer
from shapely.geometry import LineString, box
from shapely.ops import transform
OUT=pathlib.Path(__file__).resolve().parents[1]/'validation'
METHOD='apa-wfd-line-geometry-intersection'
project=Transformer.from_crs('EPSG:4326','EPSG:25829',always_xy=True).transform
inverse=Transformer.from_crs('EPSG:25829','EPSG:4326',always_xy=True).transform
# A known 1 km square and 800 m transverse line in the method's analysis CRS.
area=box(650000,4400000,651000,4401000)
line_xy=LineString([(650100,4400500),(650900,4400500)])
lonlat=[inverse(*xy) for xy in line_xy.coords]
# Encode exactly like the API's EPSG:4326 GML axis tuple: latitude, longitude.
api_latlon=[(lat,lon) for lon,lat in lonlat]
parsed=LineString([(lon,lat) for lat,lon in api_latlon])
projected=transform(project,parsed)
positive=projected.intersection(area)
# Negative case offsets the same line 2 km north, outside this 1 km square.
negative_xy=LineString([(650100,4403000),(650900,4403000)])
negative_coords=[inverse(*xy) for xy in negative_xy.coords]
negative_latlon=[(lat,lon) for lon,lat in negative_coords]
negative_projected=transform(project,LineString([(lon,lat) for lat,lon in negative_latlon]))
negative_intersection=negative_projected.intersection(area)
err=max(abs(projected.coords[i][j]-line_xy.coords[i][j]) for i in range(2) for j in range(2))
assert err < .001 and abs(positive.length-800)<.001 and not positive.is_empty
assert negative_intersection.is_empty and negative_intersection.length==0
OUT.mkdir(parents=True,exist_ok=True)
for kind,actual,expected in [
 ('positive-control',{'projected_roundtrip_max_error_m':err,'intersection_type':positive.geom_type,'intersection_length_m':positive.length,'is_empty':positive.is_empty},{'maximum_roundtrip_error_m':0.001,'intersection_length_m':800.0}),
 ('negative-control',{'projected_roundtrip_max_error_m':err,'intersection_type':negative_intersection.geom_type,'intersection_length_m':negative_intersection.length,'is_empty':negative_intersection.is_empty},{'intersection_empty':True,'intersection_length_m':0.0})]:
 out=OUT/f'{kind}.json'; out.write_text(json.dumps({'version':1,'method_id':METHOD,'kind':kind,'outcome':'passed','control_coordinates_analysis_crs':'EPSG:25829','control_exchange_axis':'EPSG:4326 GML latitude,longitude; parsed to x=longitude,y=latitude','actual':actual,'expected':expected,'interpretation':'Tests axis order, CRS roundtrip and line-polygon intersection behavior only; does not validate source positional accuracy or physical wetness.'},indent=2)+'\n')
 print(out,positive.length,negative_intersection.is_empty)
