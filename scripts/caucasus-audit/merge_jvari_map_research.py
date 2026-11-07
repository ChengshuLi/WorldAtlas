import xml.etree.ElementTree as E
files=('jvari-south-map-research.osm','jvari-north-map-research.osm');out=E.Element('osm',{'version':'0.6'});seen={}
def sig(e):return (e.tag,tuple(sorted(e.attrib.items())),tuple(sig(x) for x in e))
for f in files:
 root=E.parse(f).getroot()
 for x in root:
  if x.tag not in ('node','way','relation'):continue
  key=(x.tag,x.get('id'));v=sig(x)
  if key in seen:
   if seen[key]!=v:raise ValueError('conflicting object %s'%str(key))
   continue
  seen[key]=v;out.append(x)
E.ElementTree(out).write('jvari-expanded-merged-research.osm',encoding='utf-8',xml_declaration=True);print('objects',len(seen))
