"""Directed OSM waterway network and WGS84 geodesic proximity screening.

Matches are approximate; named topology, map direction, coverage and terrain
traces require independent verification. Threshold and way ties are unresolved.
"""
import math
import xml.etree.ElementTree as ET
from geodesic_line import GeodesicLine,distance,SEARCH_TOLERANCE_M

class WaterGraph:
    def __init__(self,osm_file):
        root=ET.parse(osm_file).getroot()
        self.nodes={n.attrib['id']:(float(n.attrib['lon']),float(n.attrib['lat'])) for n in root.findall('node')}
        self.ways=[];self.graph={};self.river_names={};self.incomplete=0
        for way in root.findall('way'):
            tags={tag.attrib['k']:tag.attrib['v'] for tag in way.findall('tag')}
            if tags.get('waterway') not in ('river','stream','canal','drain','ditch'):continue
            ids=[node.attrib['ref'] for node in way.findall('nd')]
            if len(ids)<2 or any(i not in self.nodes for i in ids):self.incomplete+=1;continue
            try:line=GeodesicLine([self.nodes[n] for n in ids])
            except ValueError:self.incomplete+=1;continue
            self.ways.append((way.attrib['id'],ids,line))
            for first,second in zip(ids,ids[1:]):self.graph.setdefault(first,set()).add(second)
            if tags.get('waterway')=='river' and tags.get('name'):
                for node in ids:self.river_names.setdefault(node,set()).add(tags['name'])

    def downstream_names(self,node):
        seen=set();todo=[node];names=set()
        while todo:
            current=todo.pop()
            if current in seen:continue
            seen.add(current);names.update(self.river_names.get(current,()))
            todo.extend(self.graph.get(current,()))
        return tuple(sorted(names))

    def first_contact(self,points,way_distance,node_distance):
        if not all(math.isfinite(x) and x>SEARCH_TOLERANCE_M for x in (way_distance,node_distance)):
            raise ValueError('thresholds must exceed WGS84 search tolerance')
        tol=SEARCH_TOLERANCE_M
        for point in points:
            candidates=[]
            for way,ids,line in self.ways:
                result=line.closest(point);d=result['distance_m']
                if d<=way_distance+tol:candidates.append((d,way,ids,result))
            if not candidates:continue
            candidates.sort(key=lambda x:(x[0],x[1]));d,way,ids,result=candidates[0]
            if abs(d-way_distance)<=tol:return {'status':'way_threshold_ambiguous','names':()}
            if len(candidates)>1 and candidates[1][0]-d<=2*tol:
                return {'status':'way_tie_ambiguous','names':()}
            node_candidates=sorted((distance(self.nodes[n],point),n) for n in ids)
            nd,node=node_candidates[0]
            if abs(nd-node_distance)<=tol:return {'status':'node_threshold_ambiguous','way_id':way,'names':()}
            if nd>node_distance:return {'status':'node_too_far','way_id':way,'node_distance_m':nd,'names':()}
            if len(node_candidates)>1 and node_candidates[1][0]-nd<=2*tol:
                return {'status':'node_tie_ambiguous','way_id':way,'names':()}
            return {'status':'matched','way_id':way,'node_id':node,'node_distance_m':nd,'names':self.downstream_names(node)}
        return {'status':'no_nearby_way','names':()}
