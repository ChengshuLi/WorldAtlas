"""Verify R2 readbacks and reconstruct raw-derived Caucasus model inputs locally."""
import argparse,hashlib,json,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def signature(e):return (e.tag,tuple(sorted(e.attrib.items())),tuple(signature(c) for c in e))
def merge(paths,out):
 root=ET.Element('osm',{'version':'0.6'});seen={}
 for p in paths:
  for obj in ET.parse(str(p)).getroot():
   if obj.tag not in ('node','way','relation'):continue
   key=(obj.tag,obj.get('id'));sig=signature(obj)
   if key in seen:
    if seen[key]!=sig:raise ValueError('conflicting OSM object '+str(key))
   else:seen[key]=sig;root.append(obj)
 ET.ElementTree(root).write(str(out),encoding='utf-8',xml_declaration=True)
 print(out.name,'objects',len(seen),flush=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--r2-readbacks',required=True);p.add_argument('--recipe',required=True);p.add_argument('--output',required=True);a=p.parse_args();raw=Path(a.r2_readbacks);out=Path(a.output);recipe=json.loads(Path(a.recipe).read_text());PINS=recipe['sources_sha256'];out.mkdir(parents=True,exist_ok=False)
 for name,h in PINS.items():
  if sha(raw/name)!=h:raise ValueError('R2 source hash mismatch '+name)
 for name in PINS:
  if name.endswith('.zip'):
   with zipfile.ZipFile(raw/name) as z:
    for member in z.infolist():
     if member.filename.endswith(('_DSM.tif','_MSK.tif','_STK.tif')):
      path=out/'original'/member.filename;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(member))
 with zipfile.ZipFile(raw/'osm-bundle') as z:
  manifest=json.loads(z.read('SHA256-MANIFEST.json'));osm=out/'osm';osm.mkdir()
  for item in manifest['files']:
   name=item['file']
   if Path(name).name!=name:raise ValueError('unsafe member')
   data=z.read(name)
   if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('OSM bundle member mismatch '+name)
   (osm/name).write_bytes(data)
 groups=recipe['osm_groups']
 for name,files in groups.items():merge([osm/f for f in files],out/(name+'.osm'))
 (out/'pins.json').write_text(json.dumps(PINS,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()
