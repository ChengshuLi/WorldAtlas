#!/usr/bin/env python3
"""Find intersections of the retained mountain line and a modeled basin interface.

Exploratory only: eliminates a constructed mountain-end join if an actual
source-line intersection exists; the headwater join remains unvalidated.
"""
import argparse,heapq,json
import numpy as np
from shapely.geometry import LineString
from shapely.ops import substring
from pyproj import Geod
from spring_connector_graph import basin_labels
from terrain_basin_screen import digest_file

G=Geod(ellps='WGS84')


def search(labels,t,to_geo,retained,river):
    h,w=labels.shape; graph={};edges=set()
    def edge(a,b):
        if b<a:a,b=b,a
        graph.setdefault(a,set()).add(b);graph.setdefault(b,set()).add(a);edges.add((a,b))
    a,b=labels[:,:-1],labels[:,1:];rr,cc=np.where(((a==1)&(b==2))|((a==2)&(b==1)))
    for r,c in zip(rr,cc):edge((int(r),int(c+1)),(int(r+1),int(c+1)))
    a,b=labels[:-1,:],labels[1:,:];rr,cc=np.where(((a==1)&(b==2))|((a==2)&(b==1)))
    for r,c in zip(rr,cc):edge((int(r+1),int(c)),(int(r+1),int(c+1)))
    coords={v:to_geo.transform(*(t*(v[1],v[0]))) for v in graph};line=LineString(retained)
    if not line.is_simple:raise ValueError('retained line not simple')
    def dist(a,b):return G.inv(*a,*b)[2]
    crosses=[]
    for u,v in edges:
        intersection=line.intersection(LineString([coords[u],coords[v]]))
        parts=list(intersection.geoms) if hasattr(intersection,'geoms') else [intersection]
        for p in parts:
            if p.is_empty:continue
            if p.geom_type!='Point':raise ValueError('ambiguous overlap')
            pos=line.project(p);tail=substring(line,pos,line.length)
            crosses.append({'point':tuple(p.coords[0]),'edge':(u,v),'removed_retained_wgs84_m':abs(G.geometry_length(tail))})
    if not crosses:return {'intersections':0,'status':'no exact intersection in modeled window'}
    candidates=[]
    for cross in crosses:
        u,v=cross['edge'];distance={u:dist(cross['point'],coords[u]),v:dist(cross['point'],coords[v])};previous={};queue=[(d,node) for node,d in distance.items()];heapq.heapify(queue)
        while queue:
            d,node=heapq.heappop(queue)
            if d!=distance[node]:continue
            for nxt in graph[node]:
                new=d+dist(coords[node],coords[nxt])
                if new<distance.get(nxt,float('inf')):distance[nxt]=new;previous[nxt]=node;heapq.heappush(queue,(new,nxt))
        end=min(distance,key=lambda n:dist(coords[n],river));join=dist(coords[end],river)
        path=[end]
        while path[-1] in previous:path.append(previous[path[-1]])
        path.reverse()
        candidates.append({**cross,'source_to_intersection_endpoints':[list(coords[u]),list(coords[v])],'spring_join_m_wgs84':join,'interface_path_m_wgs84':distance[end], 'coordinates':[list(cross['point'])]+[list(coords[n]) for n in path]+[list(river)]})
    candidates.sort(key=lambda c:(c['removed_retained_wgs84_m'],c['spring_join_m_wgs84']))
    best=candidates[0];del best['edge']
    return {'intersections':len(crosses),'selection':'smallest WGS84 retained-line tail removed, tie-break nearest spring join; no mountain-end join','candidate':best,'status':'exploratory; spring-end join unsupported'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--source-sha',required=True);p.add_argument('--mask');p.add_argument('--mask-sha');p.add_argument('--basin',nargs=3,action='append',required=True);p.add_argument('--bounds',nargs=4,type=float,required=True);p.add_argument('--retained',required=True);p.add_argument('--retained-sha',required=True);p.add_argument('--river',nargs=2,type=float,required=True);p.add_argument('--root',type=int,action='append',required=True);p.add_argument('--resolution',type=float,default=30);p.add_argument('--output',required=True);a=p.parse_args()
    if len(a.root)!=3 or len(set(a.root))!=3 or a.resolution<=0 or bool(a.mask)!=bool(a.mask_sha):raise ValueError('three distinct roots, positive resolution, paired mask and hash required')
    with open(a.retained,'rb') as f:
        if digest_file(f)!=a.retained_sha:raise ValueError('retained mountain excerpt hash mismatch')
    labels,t,geo,unknown=basin_labels(a.source,a.source_sha,a.mask,a.mask_sha,a.basin,a.bounds,a.root,a.resolution);result=search(labels,t,geo,json.load(open(a.retained)),a.river)
    result.update({'source_sha256':a.source_sha,'mask_sha256':a.mask_sha,'retained_sha256':a.retained_sha,'bounds':a.bounds,'roots':a.root,'resolution_m':a.resolution,'unclassified_valid':unknown,'caveats':['Retained-tail ranking sums WGS84 geodesic chords between source vertices and approximates coordinate-linear source path length; densification or an error check is required before using the ranking for a decision.','Terrain classification is a local DSM D8 model crosswalked to HydroBASINS, not a survey.','Local D8 neighbor distances use WGS84; the basin model is not surveyed geography.','Four-neighbor boundaries can join at corners.','Exact topological crossing is relative to raster cell edges and given line geometry.']})
    with open(a.output,'x') as f:json.dump(result,f)
    summary={k:v for k,v in result.items() if k!='candidate'}
    if 'candidate' in result:summary['candidate']={k:v for k,v in result['candidate'].items() if k!='coordinates'}
    print(json.dumps(summary))
