import json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parent;WS=P.parents[3];BASE=WS/'.cache/mmr-myeik2793-dated-imagery-001/actual-native-blocks-001';d=json.loads((P/'actual-two-native-contexts.json').read_text());out=Image.new('RGB',(792,414),'white');pins=[]
for i,p in enumerate(d['points']):
 rr,cc=p['assets']['red']['local_pixel']
 for j,name in enumerate(['rgb-native.png','nir-red-green-native.png']):
  meta=next(x for x in d['retained_source_block']['displays']if x['path'].endswith('/'+name));path=BASE/meta['path'];b=path.read_bytes();assert len(b)==meta['bytes']and hashlib.sha256(b).hexdigest()==meta['sha256'];im=Image.open(path).convert('RGB');patch=Image.new('RGB',(64,64),(100,100,100));left,top=cc-32,rr-32;box=(max(0,left),max(0,top),min(im.width,cc+32),min(im.height,rr+32));patch.paste(im.crop(box),(box[0]-left,box[1]-top));out.paste(patch.resize((384,384),Image.Resampling.NEAREST),(j*396,i*207));draw=ImageDraw.Draw(out);cx=j*396+195;cy=i*207+195
  for line in [(cx-12,cy,cx-4,cy),(cx+4,cy,cx+12,cy),(cx,cy-12,cx,cy-4),(cx,cy+4,cx,cy+12)]:draw.line(line,fill='yellow',width=1)
  pins.append({'point_index':i,'source_frame':str(path),'bytes':len(b),'sha256':meta['sha256'],'exact_native_local_pixel':[rr,cc]})
 # separate two individualpairedframes avoids imageoverlap
 if i==0:out.crop((0,0,792,414)).save(P/'point-8056-existing-RGB-NIR.png');out=Image.new('RGB',(792,414),'white')
 if i==1:
  # secondrowoffset undone below by cropping its actualrange
  pass
# Rebuild secondpair usingsameexistingframes and no raster access, fixedlayout.
p=d['points'][1];rr,cc=p['assets']['red']['local_pixel'];imout=Image.new('RGB',(792,414),'white')
for j,name in enumerate(['rgb-native.png','nir-red-green-native.png']):
 meta=next(x for x in d['retained_source_block']['displays']if x['path'].endswith('/'+name));im=Image.open(BASE/meta['path']).convert('RGB');left,top=cc-32,rr-32;box=(max(0,left),max(0,top),min(im.width,cc+32),min(im.height,rr+32));patch=Image.new('RGB',(64,64),(100,100,100));patch.paste(im.crop(box),(box[0]-left,box[1]-top));imout.paste(patch.resize((384,384),Image.Resampling.NEAREST),(j*396,0));draw=ImageDraw.Draw(imout);cx=j*396+195;cy=195
 for line in[(cx-12,cy,cx-4,cy),(cx+4,cy,cx+12,cy),(cx,cy-12,cx,cy-4),(cx,cy+4,cx,cy+12)]:draw.line(line,fill='yellow',width=1)
imout.save(P/'point-8082-existing-RGB-NIR.png');(P/'display-source-pins.json').write_text(json.dumps({'pins':pins,'no_source_raster_or_native_renderer':True,'gray_padding_is_unavailable_saved_context':True},indent=2)+'\n')
