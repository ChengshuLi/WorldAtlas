import unittest, xml.etree.ElementTree as ET
from audit_delta_source_topology import topology


def element(tag,identifier,version,refs=(),tags=()):
    e=ET.Element(tag,id=identifier,version=version)
    for r in refs:ET.SubElement(e,'nd',ref=r)
    for k,v in tags:ET.SubElement(e,'tag',k=k,v=v)
    return e


def fixture():
    river=ET.Element('osm');coast=ET.Element('osm');rel=ET.SubElement(river,'relation',id='214415',version='122')
    for w,role in [('22492011','main_stream'),('977035398','main_stream'),('22492112','side_stream'),('22492166','side_stream')]:
        ET.SubElement(rel,'member',type='way',ref=w,role=role)
    river.append(element('way','22492011','74',['0','241461340','241462578','7986845886'],[('waterway','river')]))
    river.append(element('way','977035398','4',['7986845886','241464871'],[('waterway','canal')]))
    river.append(element('way','22492112','20',['241461340','241461940']))
    river.append(element('way','22492166','10',['241461940','241462578']))
    coast.append(element('way','825215510','8',['1','241464871','2'],[('natural','coastline')]))
    coast.append(element('way','977035398','4',['7986845886','241464871'],[('waterway','canal')]))
    return river,coast


class DeltaTopology(unittest.TestCase):
    def test_valid_with_coastline_interior_node(self):
        a,b=fixture();self.assertEqual(topology(a,b)['coastal_node'],'241464871')
    def test_reversed_branch_join_rejected(self):
        a,b=fixture();w=a.find("way[@id='22492166']");w[0].set('ref','wrong')
        with self.assertRaises(ValueError):topology(a,b)
    def test_mislabelled_side_stream_rejected(self):
        a,b=fixture();a.find("relation/member[@ref='22492112']").set('role','main_stream')
        with self.assertRaises(ValueError):topology(a,b)
    def test_stale_coast_canal_rejected(self):
        a,b=fixture();b.find("way[@id='977035398']/nd").set('ref','wrong')
        with self.assertRaises(ValueError):topology(a,b)


if __name__=='__main__':unittest.main()
