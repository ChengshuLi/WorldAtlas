import hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parent;O=P/'authored-display81';O.mkdir(exist_ok=True);native=P/'actual-native-blocks-001/S2A_47PMP_20200125_0_L2A/native-observations.json';doc=json.loads(native.read_text());chosen=json.loads((P/'chosen-centres.json').read_text())['records'];images={};manifest=[]
for i,point in enumerate(doc['points']):
 record=chosen[i];assert point['original_key']=={k:record[k]for k in['owner','y','x']};br,bc=point['physical_block'];folder=native.parent/f'block-{br:02d}-{bc:02d}';row,col=point['assets']['red']['local_pixel'];panel=Image.new('RGB',(264,158),'white');draw=ImageDraw.Draw(panel);pins={}
 for j,name in enumerate(['rgb-native.png','nir-red-green-native.png']):
  fp=folder/name
  if str(fp)not in images:images[str(fp)]=Image.open(fp).convert('RGB')
  image=images[str(fp)];left,top=col-32,row-32;right,bottom=col+32,row+32;clip=(max(0,left),max(0,top),min(image.width,right),min(image.height,bottom));patch=Image.new('RGB',(64,64),(100,100,100));patch.paste(image.crop(clip),(clip[0]-left,clip[1]-top));panel.paste(patch.resize((128,128),Image.Resampling.NEAREST),(j*132,0));dr=ImageDraw.Draw(panel);cx=j*132+65;cy=65
  for line in[(cx-7,cy,cx-3,cy),(cx+3,cy,cx+7,cy),(cx,cy-7,cx,cy-3),(cx,cy+3,cx,cy+7)]:dr.line(line,fill='yellow',width=1)
  raw=fp.read_bytes();pins[name]={'path':str(fp),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'native_source_local_pixel':[row,col],'display_gray_meaning':'Unavailableoutsidealready-savedPNGwindow,notphysicalsourceclassorwater'}
 original=record['original_current_question_record'];key=point['original_key'];draw=ImageDraw.Draw(panel);draw.text((1,129),f'p{i} bulk{original["point_index"]} W{original["source_observation"]["class_code"]} S{point["assets"]["scl"]["value"]}',fill='black');draw.text((1,143),f'{key["owner"]}/{key["y"]}/{key["x"]}',fill='black')
 if i%24==0:sheet=Image.new('RGB',(1056,948),'white')
 sheet.paste(panel,((i%4)*264,((i%24)//4)*158))
 if i%24==23 or i==len(doc['points'])-1:sheet.save(O/f'page-{i//24:02d}.png')
 manifest.append({'point_index':i,'original_bulk_point_index':original['point_index'],'original_key':key,'page':i//24,'source_frame_pins':pins,'source_body_pointer':'/points/'+str(i),'literal_RGBNIR':{k:point['assets'][k]['value']for k in['red','green','blue','nir']},'literal_SCL3x3':point['assets']['scl']['neighbourhood']})
(O/'manifest.json').write_text(json.dumps({'input_native_body':{'path':str(native),'bytes':native.stat().st_size,'sha256':hashlib.sha256(native.read_bytes()).hexdigest()},'points':manifest,'no_source_raster_native_kernel_reread':True,'gray_unavailable_window_not_water':True},indent=2)+'\n');print(json.dumps({'actual_points':len(manifest),'pages':4,'existing_native_PNGframes':len(images),'sourcecalls':0}))
