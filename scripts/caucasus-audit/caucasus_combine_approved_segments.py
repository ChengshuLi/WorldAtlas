"""Combine approved Anapa and Abin source-derived lines without a map build."""
import argparse,hashlib,json
from pathlib import Path
from shapely.geometry import LineString,Point,mapping
from shapely.ops import substring
PINS={'anapa':'e3dd7f326c0247f4d9f4c4c61b7c31782a5fc1b9e850d164cf46e729cbb60929','abin':'8f1b5d00ef48c049c185066290000bf3713afd46ad1c918810122e675eed2d45'}
EXPECTED='3fe216ececc3e371de5722098885fe43cb21777481cb979870235cf89b14b2fd'
def read(path):
 data=Path(path).read_bytes();return data,json.loads(data)
def canonical(g):return json.dumps(g,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('anapa','abin','output'):p.add_argument('--'+n,required=True)
 a=p.parse_args(); raw_a,geo_a=read(a.anapa);raw_b,geo_b=read(a.abin)
 if hashlib.sha256(canonical(geo_a)).hexdigest()!=PINS['anapa'] or hashlib.sha256(raw_b).hexdigest()!=PINS['abin']:raise ValueError('source geometry hash mismatch')
 source=LineString(geo_a['coordinates']);cut=LineString(geo_b['coordinates']);start,end=Point(cut.coords[0]),Point(cut.coords[-1]);x,y=source.project(start),source.project(end)
 if source.distance(start)>1e-10 or source.distance(end)>1e-10 or not x<y:raise ValueError('joins do not match')
 pre=substring(source,0,x);post=substring(source,y,source.length);out=LineString(list(pre.coords)+list(cut.coords)[1:]+list(post.coords)[1:]);data=canonical(mapping(out))
 if not out.is_simple or out.coords[0]!=source.coords[0] or out.coords[-1]!=source.coords[-1] or hashlib.sha256(data).hexdigest()!=EXPECTED:raise ValueError('combined geometry mismatch')
 with open(a.output,'xb') as f:f.write(data)
 if Path(a.anapa).read_bytes()!=raw_a or Path(a.abin).read_bytes()!=raw_b:raise RuntimeError('input changed during processing')
 print('geometry_sha256',EXPECTED,'vertices',len(out.coords))
if __name__=='__main__':main()
