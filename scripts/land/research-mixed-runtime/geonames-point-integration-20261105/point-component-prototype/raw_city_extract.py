#!/usr/bin/env python3
"""Extract a reviewed point from a pinned provider-original city JSON array.

This is a research prototype, not a geographic decision or a publisher. Source
CRS is an explicit reviewed assertion: this code cannot prove provider datum.
"""
import hashlib, json, math, re
from decimal import Decimal, InvalidOperation
from pathlib import Path

SCHEMA='raw-json-city-point-selection-v1'
MAX_BYTES=1024*1024
KEYS={'schema','record_id','id_property','name_property','expected_name','longitude_property','latitude_property','source_crs_assertion','point_geometry_sha256'}
HEX=re.compile(r'^[0-9a-f]{64}$')
NUM=re.compile(r'^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$')

def need(ok,msg):
    if not ok: raise ValueError(msg)

def no_duplicate_keys(pairs):
    obj={}
    for k,v in pairs:
        need(k not in obj,'duplicate JSON object key');obj[k]=v
    return obj

def reject_constant(_):
    raise ValueError('nonfinite JSON number')

def digest(b): return hashlib.sha256(b).hexdigest()

def geometry_sha(geometry):
    return digest(json.dumps(geometry,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8'))

def valid_text(v): return isinstance(v,str) and bool(v.strip()) and v==v.strip() and len(v)<=256

def decimal_coordinate(v,low,high,label):
    # The provider's raw JSON stores coordinate values as decimal strings.
    need(isinstance(v,str) and len(v)<=32 and NUM.fullmatch(v) is not None,'invalid '+label)
    try:d=Decimal(v)
    except InvalidOperation:raise ValueError('invalid '+label) from None
    need(d.is_finite() and Decimal(low)<=d<=Decimal(high),'out of range '+label)
    f=float(d);need(math.isfinite(f),'nonfinite '+label)
    return f

def extract(raw,expected_sha256,selection):
    need(type(raw) is bytes and 0<len(raw)<=MAX_BYTES,'source size outside limit')
    need(isinstance(expected_sha256,str) and HEX.fullmatch(expected_sha256) is not None and digest(raw)==expected_sha256,'source SHA-256 mismatch')
    need(isinstance(selection,dict) and set(selection)==KEYS and selection.get('schema')==SCHEMA,'invalid selection schema')
    for k in ('record_id','id_property','name_property','expected_name','longitude_property','latitude_property'):
        need(valid_text(selection[k]),'invalid '+k)
    fields=[selection[k] for k in ('id_property','name_property','longitude_property','latitude_property')]
    need(len(set(fields))==4,'field roles must be distinct')
    need(selection['source_crs_assertion']=='OGC:CRS84','unsupported CRS assertion')
    expected=selection['point_geometry_sha256'];need(isinstance(expected,str) and HEX.fullmatch(expected) is not None,'invalid point geometry pin')
    try:records=json.loads(raw,object_pairs_hook=no_duplicate_keys,parse_constant=reject_constant)
    except (UnicodeDecodeError,json.JSONDecodeError) as e:raise ValueError('invalid source JSON') from e
    need(isinstance(records,list) and all(isinstance(x,dict) for x in records),'source must be an array of objects')
    idkey=selection['id_property'];wanted=selection['record_id']
    matches=[x for x in records if idkey in x and type(x[idkey]) in (int,str) and str(x[idkey])==wanted]
    need(len(matches)==1,'record ID must resolve uniquely')
    record=matches[0];need(record.get(selection['name_property'])==selection['expected_name'],'record name mismatch')
    need(selection['longitude_property'] in record and selection['latitude_property'] in record,'coordinates missing')
    lon=decimal_coordinate(record[selection['longitude_property']],-180,180,'longitude')
    lat=decimal_coordinate(record[selection['latitude_property']],-90,90,'latitude')
    need(lon<180,'longitude 180 is ambiguous at global seam')
    geometry={'type':'Point','coordinates':[lon,lat]};actual=geometry_sha(geometry)
    need(actual==expected,'point geometry hash mismatch')
    return {'schema':'raw-json-city-point-extraction-v1','source_sha256':expected_sha256,'record_id':wanted,'record_name':selection['expected_name'],'source_crs_assertion':'OGC:CRS84','geometry':geometry,'geometry_sha256':actual,'limitations':['Source CRS is a selected assertion, not authenticated from the provider JSON.','The point does not establish identity of an entire connected component.']}

def extract_file(path,expected_sha256,selection):
    with Path(path).open('rb') as f: raw=f.read(MAX_BYTES+1)
    return extract(raw,expected_sha256,selection)
