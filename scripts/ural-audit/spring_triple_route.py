#!/usr/bin/env python3
"""Explore a mountain-to-three-basin-to-Ural route without an inserted north join.

The cell-edge interface is a model, not surveyed geography. This exploratory
construction keeps a continuous source-line intersection but still requires
independent justification for its spring-end join.
"""
import argparse,heapq,json
import numpy as np
from shapely.geometry import LineString
from shapely.ops import substring
from pyproj import Geod
from spring_connector_graph import basin_labels
from terrain_basin_screen import digest_file

G=Geod(ellps='WGS84')


def interfaces(labels,t,to_geo):
    graph={};edges={}; coords={}
    for other in (2,3):
        graph[other]={};edges[other]=set()
        def add(a,b):
            if b<a:a,b=b,a
            graph[other].setdefault(a,set()).add(b);graph[other].setdefault(b,set()).add(a);edges[other].add((a,b))
        a,b=labels[:,:-1],labels[:,1:];rs,cs=np.where(((a==1)&(b==other))|((a==other)&(b==1)))
        for r,c in zip(rs,cs):add((int(r),int(c+1)),(int(r+1),int(c+1)))
        a,b=labels[:-1,:],labels[1:,:];rs,cs=np.where(((a==1)&(b==other))|((a==other)&(b==1)))
        for r,c in zip(rs,cs):add((int(r+1),int(c)),(int(r+1),int(c+1)))
    for node in set(graph[2])|set(graph[3]):coords[node]=to_geo.transform(*(t*(node[1],node[0])))
    return graph,edges,coords


def route(labels,t,to_geo,retained,river):
    graph,edges,coords=interfaces(labels,t,to_geo);triples=set(graph[2])&set(graph[3]);line=LineString(retained)
    if not line.is_simple:raise ValueError('retained line not simple')
    def dist(a,b):return G.inv(*a,*b)[2]
    crosses=[]
    for u,v in edges[3]:
        inter=line.intersection(LineString([coords[u],coords[v]]));parts=list(inter.geoms) if hasattr(inter,'geoms') else [inter]
        for p in parts:
            if p.is_empty:continue
            if p.geom_type!='Point':raise ValueError('ambiguous line overlap')
            tail=substring(line,line.project(p),line.length);crosses.append((abs(G.geometry_length(tail)),tuple(p.coords[0]),u,v))
    def dijkstra(g,seeds):
        distances={n:d for n,d in seeds};prev={};queue=[(d,n) for n,d in seeds];heapq.heapify(queue)
        while queue:
            d,n=heapq.heappop(queue)
            if d!=distances[n]:continue
            for x in g[n]:
                value=d+dist(coords[n],coords[x])
                if value<distances.get(x,float('inf')):distances[x]=value;prev[x]=n;heapq.heappush(queue,(value,x))
        return distances,prev
    if not triples or not crosses:return {'intersections':len(crosses),'triple_nodes':len(triples),'status':'no connected three-basin construction found'}
    results=[]
    for removed,point,u,v in crosses:
        d3,p3=dijkstra(graph[3],[(u,dist(point,coords[u])),(v,dist(point,coords[v]))])
        for triple in triples.intersection(d3):
            d2,p2=dijkstra(graph[2],[(triple,0.)]);end=min(d2,key=lambda n:dist(coords[n],river));join=dist(coords[end],river)
            results.append((removed,d3[triple]+d2[end]+join,point,u,v,triple,end,d3[triple],d2[end],join,p3,p2))
    if not results:return {'intersections':len(crosses),'triple_nodes':len(triples),'status':'no connected path from retained line to three-basin junction'}
    results.sort(key=lambda x:(x[0],x[1]));removed,total,point,u,v,triple,end,len3,len2,join,p3,p2=results[0]
    p=[triple]
    while p[-1] in p3:p.append(p3[p[-1]])
    p.reverse();q=[end]
    while q[-1] in p2:q.append(p2[q[-1]])
    q.reverse();vertices=[list(point)]+[list(coords[n]) for n in p]+[list(coords[n]) for n in q[1:]]+[list(river)]
    candidate={'retained_intersection_lonlat':list(point),'triple_node_lonlat':list(coords[triple]),'river_interface_lonlat':list(coords[end]),'retained_tail_removed_wgs84_m':removed,'volga_ob_path_wgs84_m':len3,'volga_ural_path_wgs84_m':len2,'spring_join_wgs84_m':join,'candidate_length_wgs84_m':total,'coordinates':vertices}
    return {'intersections':len(crosses),'triple_nodes':len(triples),'viable_paths':len(results),'selection':'shortest removed retained-line tail, tie-break total modeled route length','candidate':candidate,'status':'exploratory; spring-end join remains unsupported'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--source-sha',required=True);p.add_argument('--mask');p.add_argument('--mask-sha');p.add_argument('--basin',nargs=3,action='append',required=True);p.add_argument('--bounds',nargs=4,type=float,required=True);p.add_argument('--retained',required=True);p.add_argument('--retained-sha',required=True);p.add_argument('--river',nargs=2,type=float,required=True);p.add_argument('--root',type=int,action='append',required=True);p.add_argument('--resolution',type=float,default=30);p.add_argument('--output',required=True);a=p.parse_args()
    if len(a.root)!=3 or len(set(a.root))!=3 or a.resolution<=0 or bool(a.mask)!=bool(a.mask_sha):raise ValueError('invalid roots, resolution or mask')
    with open(a.retained,'rb') as f:
        if digest_file(f)!=a.retained_sha:raise ValueError('retained-line excerpt checksum mismatch')
    labels,t,geo,unknown=basin_labels(a.source,a.source_sha,a.mask,a.mask_sha,a.basin,a.bounds,a.root,a.resolution)
    result=route(labels,t,geo,json.load(open(a.retained)),a.river);result.update({'source_sha256':a.source_sha,'retained_sha256':a.retained_sha,'bounds':a.bounds,'roots':a.root,'unclassified_valid':unknown,'caveats':['Preliminary: projected-neighbor D8 conversion pending.','Grid-corner connectivity is not surveyed geography.','The spring-end straight join requires evidence.','Candidate preserves source-line geometry only to the recorded intersection.']})
    with open(a.output,'x') as f:json.dump(result,f)
    summary={k:v for k,v in result.items() if k!='candidate'}
    if 'candidate' in result:summary['candidate']={k:v for k,v in result['candidate'].items() if k!='coordinates'}
    print(json.dumps(summary))
