#!/usr/bin/env python3
"""Extract one selected point from exact provider-original OSM API XML bytes."""
import hashlib,json,math,re,xml.etree.ElementTree as ET
from decimal import Decimal,InvalidOperation
from pathlib import Path

SCHEMA='osm-api-node-point-selection-v1';MAX_BYTES=256*1024
KEYS={'schema','node_id','node_version','expected_tags','source_crs','point_geometry_sha256'}
HEX=re.compile(r'^[0-9a-f]{64}$');DEC=re.compile(r'^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$');UINT=re.compile(r'^[1-9][0-9]{0,19}$')
def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(b):return hashlib.sha256(b).hexdigest()
def point_sha(g):return sha(json.dumps(g,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode())
def coordinate(value,low,high,label):
 need(isinstance(value,str) and len(value)<=32 and DEC.fullmatch(value) is not None,'invalid '+label)
 try:d=Decimal(value)
 except InvalidOperation:raise ValueError('invalid '+label) from None
 need(d.is_finite() and Decimal(low)<=d<=Decimal(high),'out of range '+label);f=float(d);need(math.isfinite(f),'nonfinite '+label);return f
def extract(raw,expected_sha256,selection):
 need(type(raw) is bytes and 0<len(raw)<=MAX_BYTES,'source size outside limit');need(isinstance(expected_sha256,str) and HEX.fullmatch(expected_sha256) is not None and sha(raw)==expected_sha256,'source SHA-256 mismatch')
 need(isinstance(selection,dict) and set(selection)==KEYS and selection.get('schema')==SCHEMA,'invalid selection schema')
 for k in ('node_id','node_version'):need(isinstance(selection[k],str) and UINT.fullmatch(selection[k]) is not None,'invalid '+k)
 tags=selection['expected_tags'];need(isinstance(tags,dict) and set(tags)>={'name','place'} and len(tags)<=32 and all(isinstance(k,str) and isinstance(v,str) and k and v and len(k)<=255 and len(v)<=255 for k,v in tags.items()),'invalid expected tags')
 need(selection['source_crs']=='OGC:CRS84','unsupported CRS');need(isinstance(selection['point_geometry_sha256'],str) and HEX.fullmatch(selection['point_geometry_sha256']) is not None,'invalid geometry pin')
 try:xml=raw.decode('utf-8','strict')
 except UnicodeDecodeError:raise ValueError('XML must be UTF-8') from None
 need('\x00' not in xml and '<!' not in xml,'XML declarations/entities/comments unsupported')
 try:root=ET.fromstring(xml)
 except ET.ParseError as e:raise ValueError('invalid OSM XML') from e
 need(root.tag=='osm' and root.get('version')=='0.6','OSM API 0.6 root required');children=list(root);need(len(children)==1 and children[0].tag=='node','exactly one node required');node=children[0]
 need(node.get('id')==selection['node_id'] and node.get('version')==selection['node_version'] and node.get('visible')=='true','node ID, version or visibility mismatch')
 parsed={}
 for t in node:
  need(t.tag=='tag' and set(t.attrib)=={'k','v'} and len(t)==0,'invalid node tag');k=t.get('k');v=t.get('v');need(k not in parsed,'duplicate node tag');parsed[k]=v
 need(all(parsed.get(k)==v for k,v in tags.items()),'selected node tags mismatch')
 lon=coordinate(node.get('lon'),-180,180,'longitude');lat=coordinate(node.get('lat'),-90,90,'latitude');need(lon<180,'longitude 180 is ambiguous at global seam')
 geometry={'type':'Point','coordinates':[lon,lat]};actual=point_sha(geometry);need(actual==selection['point_geometry_sha256'],'point geometry hash mismatch')
 return {'schema':'osm-api-node-point-extraction-v1','source_sha256':expected_sha256,'node_id':selection['node_id'],'node_version':selection['node_version'],'verified_tags':dict(sorted(tags.items())),'source_crs':'OGC:CRS84','geometry':geometry,'geometry_sha256':actual,'limitations':['Point and named-region label do not prove every physical component cell is the named island.','Original OSM attribution and applicable ODbL terms must accompany use.']}
def extract_file(path,expected_sha256,selection):
 with Path(path).open('rb') as f:raw=f.read(MAX_BYTES+1)
 return extract(raw,expected_sha256,selection)
