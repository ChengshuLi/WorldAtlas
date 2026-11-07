"""Compare exact binary64 vertices without asserting construction provenance."""
import argparse
from collections import defaultdict
import hashlib
import json
import math


def match_runs(selected,source):
    by_coordinate=defaultdict(list)
    for index,point in enumerate(source):by_coordinate[tuple(point)].append(index)
    pairs={(i,j) for i,p in enumerate(selected) for j in by_coordinate.get(tuple(p),())}
    runs=[]
    for direction in (1,-1):
        for i,j in sorted(pairs):
            if (i-1,j-direction) in pairs:continue
            length=1
            while (i+length,j+direction*length) in pairs:length+=1
            if length>=2:runs.append({'selected_start':i,'source_start':j,'length':length,'source_direction':direction})
    return {'matched_selected_vertices':len({i for i,j in pairs}),
            'coordinate_pairs':len(pairs),
            'ambiguous_selected_vertices':sum(len(by_coordinate.get(tuple(p),()))>1 for p in selected),
            'runs':sorted(runs,key=lambda x:(-x['length'],x['selected_start'],x['source_start']))}


def line_coordinates(geometry):
    if not isinstance(geometry,dict) or geometry.get('type')!='LineString':raise ValueError('LineString geometry required')
    points=geometry.get('coordinates')
    if not isinstance(points,list) or len(points)<2:raise ValueError('at least two coordinates required')
    for point in points:
        if not isinstance(point,list) or len(point)!=2 or any(not isinstance(x,(int,float)) or isinstance(x,bool) or not math.isfinite(x) for x in point):
            raise ValueError('finite two-dimensional coordinates required')
    return points


def geometry_hash(geometry):
    coordinates=line_coordinates(geometry)
    normal=dict(geometry)
    normal['coordinates']=[[float(value) for value in point] for point in coordinates]
    canonical=json.dumps(normal,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selected',required=True,help='WGS84 GeoJSON LineString geometry')
    p.add_argument('--selected-canonical-sha256',required=True,help='binary64 sorted compact geometry SHA-256')
    p.add_argument('--source',required=True,help='GeoJSON FeatureCollection')
    p.add_argument('--source-file-sha256',required=True)
    p.add_argument('--feature-index',type=int,required=True,help='zero-based source feature position')
    p.add_argument('--output',required=True,help='new private JSON output')
    args=p.parse_args()
    source_bytes=open(args.source,'rb').read()
    if hashlib.sha256(source_bytes).hexdigest()!=args.source_file_sha256:raise ValueError('source file hash mismatch')
    collection=json.loads(source_bytes)
    if collection.get('type')!='FeatureCollection' or not 0<=args.feature_index<len(collection.get('features',[])):
        raise ValueError('source must contain the selected feature')
    selected=json.load(open(args.selected,encoding='utf-8'))
    if geometry_hash(selected)!=args.selected_canonical_sha256:raise ValueError('selected geometry hash mismatch')
    source=line_coordinates(collection['features'][args.feature_index]['geometry'])
    result=match_runs(selected['coordinates'],source)
    with open(args.output,'x',encoding='utf-8') as out:json.dump(result,out,indent=2)
    print('matched selected vertices:',result['matched_selected_vertices'],'longest run:',result['runs'][0]['length'] if result['runs'] else 0)


if __name__=='__main__':main()
