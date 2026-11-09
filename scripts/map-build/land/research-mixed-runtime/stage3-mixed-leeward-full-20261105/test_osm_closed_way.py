"""Synthetic OSM map-export fixtures only; no real geographic records."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from osm_closed_way import extract
class WayTest(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)/'input.xml';self.xml='''<osm><bounds minlon="0" minlat="0" maxlon="0.1" maxlat="0.1"/><node id="1" visible="true" lon="0.02" lat="0.02"/><node id="2" visible="true" lon="0.08" lat="0.02"/><node id="3" visible="true" lon="0.08" lat="0.08"/><way id="7" version="2" visible="true"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="1"/><tag k="name" v="Demo"/><tag k="place" v="islet"/><tag k="natural" v="coastline"/></way></osm>''';self.bounds={'minlon':'0','minlat':'0','maxlon':'0.1','maxlat':'0.1'};self.tags={'name':'Demo','place':'islet','natural':'coastline'};g={'type':'MultiPolygon','coordinates':[[[[.02,.02],[.08,.02],[.08,.08],[.02,.02]]]]};self.geom=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest();self.write(self.xml)
 def write(self,s):self.p.write_text(s);self.sha=hashlib.sha256(self.p.read_bytes()).hexdigest()
 def runextract(self,**kw):return extract(self.p,kw.get('sha',self.sha),'7',kw.get('version','2'),kw.get('tags',self.tags),kw.get('bounds',self.bounds),kw.get('geom',self.geom))
 def test_valid_pinned_way(self):self.assertEqual(self.runextract()[1]['way_id'],'7')
 def test_reject_hash_identity_version_and_bounds(self):
  for kw in ({'sha':'0'*64},{'version':'3'},{'tags':dict(self.tags,name='Other')},{'bounds':dict(self.bounds,maxlon='0.09')},{'geom':'0'*64}):
   with self.subTest(kw=kw),self.assertRaises(ValueError):self.runextract(**kw)
 def test_reject_missing_open_duplicate_nonvisible_and_doctype(self):
  samples=[self.xml.replace('<nd ref="1"/><tag','<nd ref="2"/><tag'),self.xml.replace('<node id="3"','<node id="4"'),self.xml.replace('visible="true"','visible="false"',1),self.xml.replace('</osm>','<way id="7" version="2" visible="true"></way></osm>'),'<!DOCTYPE osm [<!ENTITY x "y">]>'+self.xml]
  for x in samples:
   self.write(x)
   with self.subTest(x=x[:60]),self.assertRaises(ValueError):self.runextract()
 def test_reject_outside_bounds(self):
  self.write(self.xml.replace('lon="0.08"','lon="0.11"'))
  with self.assertRaisesRegex(ValueError,'outside export'):self.runextract()
if __name__=='__main__':unittest.main()
