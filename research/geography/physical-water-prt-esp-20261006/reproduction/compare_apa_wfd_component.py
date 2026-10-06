#!/usr/bin/env python3
"""Reproduce spatial coincidence of APA WFD river line members with the full retained gap polygon.

This is a source comparison only. It does not infer wetted area, channel width, ownership,
or correct/repair the input component.
"""
import gzip, hashlib, json, pathlib, sys, xml.etree.ElementTree as ET
from pyproj import Transformer
from shapely.geometry import LineString, MultiLineString, shape
from shapely.ops import transform, unary_union

ROOT = pathlib.Path(__file__).resolve().parents[4]
OWNED = ROOT / 'research/geography/physical-water-prt-esp-20261006'
SHARD = ROOT / 'coordination/engineering/geographic-components-946-20261005-local06/components-v2/components-004.json.gz'
TARGET = 'gap:ad2052defbeba8e89287bcc4344e641225c6579f9afd584497b381fe8fd8eedc'
PAGE0 = OWNED / 'sources/official-api-responses/apa-wfd-explicit-full-aoi-page-0.xml'
PAGE1 = OWNED / 'sources/official-api-responses/apa-wfd-explicit-full-aoi-page-1.xml'
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else OWNED / 'reproduction/apa-wfd-full-component-comparison.json'
NS = {'wfs':'http://www.opengis.net/wfs/2.0','gml':'http://www.opengis.net/gml/3.2'}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load_gap():
    raw = gzip.decompress(SHARD.read_bytes())
    data = json.loads(raw)
    matches = [f for f in data['features'] if f.get('id') == TARGET]
    if len(matches) != 1: raise RuntimeError(f'expected exactly one target feature, found {len(matches)}')
    return shape(matches[0]['geometry']), hashlib.sha256(SHARD.read_bytes()).hexdigest()

def parse_page(path):
    root = ET.parse(path).getroot()
    count = int(root.attrib.get('numberReturned','-1'))
    members=[]
    for member in root.findall('wfs:member', NS):
        feat = next(iter(member), None)
        if feat is None: continue
        fid=feat.attrib.get('{http://www.opengis.net/gml/3.2}id')
        geom_el=feat.find('.//gml:MultiCurve', NS)
        if geom_el is None: raise RuntimeError(f'missing MultiCurve on {fid}')
        lines=[]
        for ls in geom_el.findall('.//gml:LineString', NS):
            pos=ls.find('gml:posList', NS)
            if pos is None or not (pos.text or '').strip(): continue
            vals=list(map(float,pos.text.split()))
            dim=int(pos.attrib.get('srsDimension','2'))
            if dim != 2 or len(vals)%2: raise RuntimeError(f'unsupported posList dimension/count {fid}')
            # EPSG:4326 GML uses latitude, longitude axis order here; convert to x=lon,y=lat.
            coords=[(vals[i+1], vals[i]) for i in range(0,len(vals),2)]
            if len(coords)>=2: lines.append(LineString(coords))
        if not fid: raise RuntimeError('missing native gml:id')
        members.append((fid, lines))
    if len(members)!=count: raise RuntimeError(f'numberReturned={count} but parsed {len(members)} members')
    return root, members

def main():
    gap, shard_sha=load_gap()
    to_m=Transformer.from_crs('EPSG:4326','EPSG:25829',always_xy=True).transform
    gap_m=transform(to_m, gap)
    if gap.geom_type != 'Polygon': raise RuntimeError(f'unexpected target type {gap.geom_type}')
    coord_count=len(gap.exterior.coords)+sum(len(r.coords) for r in gap.interiors)
    if not gap.is_valid: raise RuntimeError('target component polygon is invalid; no repair attempted')
    root0, members0=parse_page(PAGE0); root1, members1=parse_page(PAGE1)
    ids=[fid for fid,_ in members0]
    if len(ids)!=len(set(ids)): raise RuntimeError('duplicate native feature IDs on page 0')
    if members1: raise RuntimeError('page 1 not exhausted')
    records=[]
    intersections=[]
    total_length=0.0
    for fid, lines in members0:
        projected=[transform(to_m,l) for l in lines]
        linegeom=MultiLineString(projected) if len(projected)>1 else (projected[0] if projected else None)
        if linegeom is None: continue
        inter=linegeom.intersection(gap_m)
        length=float(inter.length)
        total_length += length
        if not inter.is_empty:
            intersections.append(inter)
            records.append({'native_id':fid,'geometry_type':inter.geom_type,'coincident_length_m':length,'nonempty_intersection':True})
    unique_union_length=float(unary_union(intersections).length) if intersections else 0.0
    result={
      'method':'source-line coincidence only; no buffer, snap, repair, or water classification',
      'target_component_id':TARGET,
      'component_input':{'path':'coordination/engineering/geographic-components-946-20261005-local06/components-v2/components-004.json.gz','sha256':shard_sha,'source_crs':'OGC:CRS84 longitude,latitude'},
      'target_component_geometry':{'type':gap.geom_type,'is_valid':gap.is_valid,'coordinate_count_including_closed_ring':coord_count,'bounds_crs84':list(gap.bounds)},
      'analysis_crs':'EPSG:25829 ETRS89 / UTM zone 29N',
      'source':{'dataset':'APA/SNIAmb AM.WaterBodyForWFD','native_crs':'EPSG:4326, GML coordinates parsed latitude then longitude','page0_sha256':sha(PAGE0),'page1_sha256':sha(PAGE1),'page0_timestamp':root0.attrib.get('timeStamp'),'page1_timestamp':root1.attrib.get('timeStamp'),'page0_numberReturned':int(root0.attrib.get('numberReturned','-1')),'page0_numberMatched':root0.attrib.get('numberMatched'),'page1_numberReturned':int(root1.attrib.get('numberReturned','-1')),'page1_numberMatched':root1.attrib.get('numberMatched'),'unique_native_members':len(ids),'native_ids':ids},
      'comparison':{'members_with_nonempty_intersection':len(records),'sum_of_per_member_line_intersection_lengths_m':total_length,'unique_union_line_length_inside_component_m':unique_union_length,'intersections':records},
      'limitations':['Provider reports numberMatched=unknown on vector pages; separate hits query reported 59, page 0 returned 59 and subsequent page returned 0. Page timestamps differ, so this is not a stable transactional snapshot.','WFD river features are water-planning objects, not observations of surface wetness or measured channel polygons.','Line coincidence cannot establish channel width, wetted extent, whole-cell water, land/water proportions, administrative ownership, or legal boundary.','This result covers the full retained gap component, not only the administrative comparison residual.']
    }
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'output':str(OUT),'sha256':sha(OUT),'member_count':len(ids),'intersecting_members':len(records),'length_m':total_length},indent=2))
if __name__=='__main__': main()
