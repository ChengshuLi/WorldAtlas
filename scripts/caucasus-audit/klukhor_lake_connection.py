"""Mapped Klukhor lake topology and WGS84 gaps, not asserted outlet flow."""
import json,xml.etree.ElementTree as ET
from geodesic_line import GeodesicLine,distance
root=ET.parse('caucasus-klukhor-osm.xml').getroot();nodes={v.get('id'):(float(v.get('lon')),float(v.get('lat'))) for v in root.findall('node')};ways={w.get('id'):[v.get('ref') for v in w.findall('nd')] for w in root.findall('way')}
lake=ways['86304196'];stream=ways['86304879'];river=ways['86306314'];line=GeodesicLine(json.load(open('caucasus-line.json'))['coordinates']);head=nodes[stream[0]]
print('mapped_stream_head',stream[0],head,'nearest_selected',line.closest(head))
print('lake_stream_shared_nodes',sorted(set(lake)&set(stream)))
print('lake_river_shared_nodes',sorted(set(lake)&set(river)))
# Endpoints obtained independently by running klukhor_offset_d8_screen.py in both modes.
for source,endpoint in [('jaxa',(41.86541666666667,43.24708333333333)),('copernicus',(41.86555555555555,43.24722222222222))]:
 print(source,'known_pit_to_mapped_stream_head_m',distance(endpoint,head))
