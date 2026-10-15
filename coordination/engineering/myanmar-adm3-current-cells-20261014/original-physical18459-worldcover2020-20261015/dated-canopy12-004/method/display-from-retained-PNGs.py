from pathlib import Path
import json,gzip,hashlib,collections
from PIL import Image,ImageDraw,ImageFont
D=Path(__file__).resolve().parent;OUT=D/'sentinel564-saved-displays';OUT.mkdir(exist_ok=True)
rs=[json.loads(l)for l in gzip.decompress((D.parent/'worker1-mmr-bulk-physical-20261015-001/retained-residual564.jsonl.gz').read_bytes()).splitlines()];docs={};images={};manifest=[]
rs.sort(key=lambda r:(r['retained_native_observation']['item'],tuple(r['retained_native_observation']['physical_block']),int(r['retained_native_observation']['pointer'].split('/')[-1])))
for i,r in enumerate(rs):
 ref=r['retained_native_observation'];sp=Path(ref['path'])
 if str(sp)not in docs:docs[str(sp)]=json.loads(sp.read_bytes())
 doc=docs[str(sp)];n=int(ref['pointer'].split('/')[-1]);p=doc['points'][n];assert p['original_key']==r['original_key'];br,bc=p['physical_block'];folder=sp.parent/f'block-{br:02d}-{bc:02d}';row,col=p['assets']['red']['local_pixel'];panel=Image.new('RGB',(264,158),'white');draw=ImageDraw.Draw(panel)
 for j,kind in enumerate(['rgb-native.png','nir-red-green-native.png']):
  fp=folder/kind
  if str(fp)not in images:images[str(fp)]=Image.open(fp).convert('RGB')
  crop=images[str(fp)].crop((col-32,row-32,col+32,row+32)).resize((128,128),Image.Resampling.NEAREST);panel.paste(crop,(j*132,0));dr=ImageDraw.Draw(panel);cx=j*132+65;cy=65
  for x1,y1,x2,y2 in[(cx-7,cy,cx-3,cy),(cx+3,cy,cx+7,cy),(cx,cy-7,cx,cy-3),(cx,cy+3,cx,cy+7)]:dr.line((x1,y1,x2,y2),fill='yellow',width=1)
 label=f'{i} {"PMM"if"PMM"in ref["item"]else"PMP"} p{n} W{r["source_observation"]["class_code"]} S{p["assets"]["scl"]["value"]}'
 draw=ImageDraw.Draw(panel);draw.text((1,129),label,fill='black');draw.text((1,143),f'key {r["original_key"]["owner"]}/{r["original_key"]["y"]}/{r["original_key"]["x"]}',fill='black')
 if i%24==0:sheet=Image.new('RGB',(1056,948),'white')
 sheet.paste(panel,((i%4)*264,((i%24)//4)*158))
 if i%24==23 or i==len(rs)-1:sheet.save(OUT/f'page-{i//24:02d}.png')
 manifest.append({'display_index':i,'page':i//24,'source_point':n,'item':ref['item'],'original_key':r['original_key'],'original_bulk_index':r['point_index'],'WC':r['source_observation']['class_code'],'SCL':p['assets']['scl']['value'],'native_block':[br,bc],'local_pixel':[row,col],'native_observation_path':str(sp),'RGB':str(folder/'rgb-native.png'),'NIR':str(folder/'nir-red-green-native.png'),'RGBNIR_values':{k:p['assets'][k]['value']for k in['red','green','blue','nir']},'original_open_category':r['category']})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'keys':len(rs),'pages':(len(rs)+23)//24,'localPNGused':len(images),'source_calls':0,'new_source_reads':0}))
