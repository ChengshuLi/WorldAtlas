"""Research-only proximity and directed-network search on an OSM XML extract.

Nearest-way/node matching is approximate. A matched name is not proof that a
modeled path joins a stream, nor that OSM is complete, correctly directed, or
identical to an external gazetteer entry.
"""
import math
import xml.etree.ElementTree as ET
from shapely.geometry import LineString,Point
from shapely.ops import transform
from shapely.strtree import STRtree
from pyproj import CRS,Transformer


class WaterGraph:
    def __init__(self,osm_file,epsg):
        crs=CRS.from_epsg(epsg)
        if not crs.is_projected or any(axis.unit_conversion_factor!=1 for axis in crs.axis_info):
            raise ValueError('a suitable projected metre CRS is required')
        project=Transformer.from_crs(4326,epsg,always_xy=True)
        root=ET.parse(osm_file).getroot()
        self.nodes={n.attrib['id']:Point(project.transform(float(n.attrib['lon']),float(n.attrib['lat'])))
                    for n in root.findall('node')}
        self.ways=[];self.geometries=[];self.graph={};self.river_names={};self.incomplete=0
        for way in root.findall('way'):
            tags={tag.attrib['k']:tag.attrib['v'] for tag in way.findall('tag')}
            if tags.get('waterway') not in ('river','stream','canal','drain','ditch'):continue
            ids=[node.attrib['ref'] for node in way.findall('nd')]
            if len(ids)<2 or any(i not in self.nodes for i in ids):
                self.incomplete+=1;continue
            self.ways.append((way.attrib['id'],ids))
            self.geometries.append(LineString([self.nodes[i] for i in ids]))
            for first,second in zip(ids,ids[1:]):self.graph.setdefault(first,set()).add(second)
            if tags.get('waterway')=='river' and tags.get('name'):
                for node in ids:self.river_names.setdefault(node,set()).add(tags['name'])
        self.index=STRtree(self.geometries)

    def downstream_names(self,node):
        seen=set();todo=[node];names=set()
        while todo:
            current=todo.pop()
            if current in seen:continue
            seen.add(current);names.update(self.river_names.get(current,()))
            todo.extend(self.graph.get(current,()))
        return tuple(sorted(names))

    def first_contact(self,points,way_distance,node_distance):
        if not all(math.isfinite(x) and x>0 for x in (way_distance,node_distance)):
            raise ValueError('positive finite thresholds required')
        for coordinates in points:
            point=Point(coordinates)
            candidates=[int(i) for i in self.index.query(point.buffer(way_distance))
                        if self.geometries[int(i)].distance(point)<=way_distance]
            if not candidates:continue
            i=min(candidates,key=lambda k:(self.geometries[k].distance(point),self.ways[k][0]))
            way,ids=self.ways[i]
            node=min(ids,key=lambda n:(self.nodes[n].distance(point),n))
            distance=self.nodes[node].distance(point)
            if distance>node_distance:
                return {'status':'node_too_far','way_id':way,'node_distance_m':distance,'names':()}
            return {'status':'matched','way_id':way,'node_id':node,
                    'node_distance_m':distance,'names':self.downstream_names(node)}
        return {'status':'no_nearby_way','names':()}
