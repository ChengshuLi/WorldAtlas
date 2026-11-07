#!/usr/bin/env python3
"""Deterministically reconstruct an outer-only OSM relation from pinned raw XML.

The returned geometry is ephemeral runtime data. It is not a selected decision,
an authenticated capture, or evidence that a source contains every island.
"""
import collections, hashlib, json, math, xml.parsers.expat as expat
from pathlib import Path

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def read_graph(path,relation_id,version,guard=lambda:None,expected_source_sha256=None):
    """Stream the exact hashed bytes through Expat, rejecting all DTD/entity declarations."""
    nodes={};ways={};relation=None;stack=[];current_way=None;current_relation=None
    parser=expat.ParserCreate()
    def reject(*args):raise ValueError('DTD and entity declarations are forbidden')
    parser.StartDoctypeDeclHandler=reject
    parser.EntityDeclHandler=reject
    parser.UnparsedEntityDeclHandler=reject
    parser.NotationDeclHandler=reject
    parser.ExternalEntityRefHandler=reject
    parser.SkippedEntityHandler=reject
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    def start(name,attrs):
        nonlocal current_way,current_relation
        stack.append(name);depth=len(stack)
        if depth==1:
            if name!='osm':raise ValueError('expected OSM document')
        elif depth==2 and name=='node':
            i=int(attrs['id']);lon=float(attrs['lon']);lat=float(attrs['lat'])
            if i in nodes or not math.isfinite(lon) or not math.isfinite(lat) or not -180<=lon<=180 or not -90<=lat<=90:raise ValueError('invalid or duplicate node')
            nodes[i]=(lon,lat)
        elif depth==2 and name=='way':
            i=int(attrs['id'])
            if i in ways:raise ValueError('duplicate way')
            current_way=(i,[])
        elif depth==3 and name=='nd' and stack[-2]=='way':
            if current_way is None:raise ValueError('way state error')
            current_way[1].append(int(attrs['ref']))
        elif depth==2 and name=='relation':
            if int(attrs['id'])==relation_id:
                if relation is not None or attrs.get('version')!=str(version):raise ValueError('duplicate relation or version mismatch')
                current_relation=([],{})
            else:current_relation=None
        elif depth==3 and stack[-2]=='relation' and current_relation is not None:
            if name=='member':current_relation[0].append((attrs.get('type'),int(attrs['ref']),attrs.get('role','')))
            elif name=='tag':
                k=attrs['k']
                if k in current_relation[1]:raise ValueError('duplicate relation tag')
                current_relation[1][k]=attrs['v']
    def end(name):
        nonlocal current_way,current_relation,relation
        if not stack or stack[-1]!=name:raise ValueError('invalid XML nesting')
        if len(stack)==2 and name=='way':
            if current_way is None or len(current_way[1])<2:raise ValueError('invalid way')
            ways[current_way[0]]=current_way[1];current_way=None
        elif len(stack)==2 and name=='relation' and current_relation is not None:
            relation=current_relation;current_relation=None
        stack.pop()
    parser.StartElementHandler=start;parser.EndElementHandler=end
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        while True:
            chunk=f.read(1<<20)
            if not chunk:break
            digest.update(chunk);parser.Parse(chunk,False);guard()
        parser.Parse(b'',True)
    if expected_source_sha256 is not None and digest.hexdigest()!=expected_source_sha256:raise ValueError('parsed source hash mismatch')
    if relation is None:raise ValueError('relation not found')
    members,tags=relation
    if tags.get('type')!='multipolygon' or not members:raise ValueError('not a multipolygon')
    if any(t!='way' or role!='outer' for t,_,role in members):raise ValueError('only explicit outer-way members are supported')
    ids=[i for _,i,_ in members]
    if len(ids)!=len(set(ids)) or any(i not in ways for i in ids):raise ValueError('duplicate or missing way member')
    selected={i:ways[i] for i in ids}
    if any(n not in nodes for refs in selected.values() for n in refs):raise ValueError('missing member node')
    return nodes,selected,tags

def assemble_rings(ways):
    """Follow unambiguous degree-two endpoint graph in sorted way-ID order."""
    by_endpoint=collections.defaultdict(list);closed=[];unvisited=set()
    for wid,refs in ways.items():
        if len(refs)<2:raise ValueError('short way')
        if refs[0]==refs[-1]:closed.append((wid,refs[:]))
        else:
            by_endpoint[refs[0]].append(wid);by_endpoint[refs[-1]].append(wid);unvisited.add(wid)
    if any(len(owners)!=2 for owners in by_endpoint.values()):raise ValueError('open or branched relation')
    rings=closed[:]
    while unvisited:
        first=min(unvisited);seq=ways[first][:];unvisited.remove(first);start=seq[0];end=seq[-1]
        while end!=start:
            options=[i for i in by_endpoint[end] if i in unvisited]
            if len(options)!=1:raise ValueError('ambiguous or incomplete ring')
            wid=options[0];part=ways[wid];unvisited.remove(wid)
            if part[0]==end:seq.extend(part[1:])
            elif part[-1]==end:seq.extend(reversed(part[:-1]))
            else:raise ValueError('disconnected way')
            end=seq[-1]
        rings.append((first,seq))
    rings.sort(key=lambda r:r[0]);result=[]
    for _,ring in rings:
        if len(ring)<4 or ring[0]!=ring[-1] or any(a==b for a,b in zip(ring,ring[1:])):raise ValueError('invalid ring')
        result.append(ring)
    if not result:raise ValueError('no outer rings')
    return result

def extract(path,source_sha256,relation_id,relation_version,expected_geometry_sha256,guard=lambda:None):
    """Return binary64 GeoJSON MultiPolygon after source, graph, hash and GEOS checks.

    Caller must independently authenticate raw custody and pin this code and the
    GDAL/GEOS runtime. This outer-only adapter fails closed for inner rings,
    nested relations, unsupported roles, missing nodes and ambiguous joins.
    """
    from osgeo import ogr
    if digest(path)!=source_sha256:raise ValueError('raw OSM hash mismatch')
    nodes,ways,tags=read_graph(path,int(relation_id),int(relation_version),guard,source_sha256)
    rings=assemble_rings(ways);geometry={'type':'MultiPolygon','coordinates':[[[list(nodes[n]) for n in ring]] for ring in rings]}
    for polygon in geometry['coordinates']:
        ring=polygon[0]
        if any(abs(a[0]-b[0])>180 for a,b in zip(ring,ring[1:])):raise ValueError('unsupported antimeridian crossing')
    canonical=json.dumps(geometry,sort_keys=True,separators=(',',':'),allow_nan=False).encode();gh=hashlib.sha256(canonical).hexdigest()
    if gh!=expected_geometry_sha256:raise ValueError('reconstructed geometry hash mismatch')
    g=ogr.CreateGeometryFromJson(canonical.decode())
    if g is None or g.IsEmpty() or not g.IsValid():raise ValueError('invalid reconstructed multipolygon')
    if digest(path)!=source_sha256:raise ValueError('raw OSM changed')
    return geometry,{'source_sha256':source_sha256,'relation_id':str(relation_id),'relation_version':str(relation_version),'geometry_sha256':gh,'outer_ring_count':len(rings),'tags':{k:tags.get(k) for k in ('name','name:en','place','type','wikidata')}}
