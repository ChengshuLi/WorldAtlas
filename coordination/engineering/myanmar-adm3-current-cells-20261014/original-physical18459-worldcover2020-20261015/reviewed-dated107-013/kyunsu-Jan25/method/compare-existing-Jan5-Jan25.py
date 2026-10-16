import json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parent;WS=P.parents[3];D=P.parent;O=P/'selected-date-comparisons';O.mkdir(exist_ok=True);newpath=P/'actual-native-blocks-001/S2A_47PMP_20200125_0_L2A/native-observations.json';new=json.loads(newpath.read_text());inputs=[WS/'.cache/mmr-myeik2793-dated-imagery-001/actual-native-blocks-001/S2A_47PMP_20200105_0_L2A/native-observations.json']
for folder,tile in [('kyunsu179-PLP-native-001','PLP'),('kyunsu-next-PMN-native-009','PMN'),('kyunsu-next-PLN-native-010','PLN'),('kyunsu-next-PMQ-native-012','PMQ'),('kyunsu-next-PLQ-native-013','PLQ')]:inputs.append(D/folder/'actual-native-blocks-001'/('S2A_47'+tile+'_20200105_0_L2A')/'native-observations.json')
key=lambda p:tuple(p['original_key'][k]for k in ['owner','y','x']);wanted={key(p)for p in new['points']};lookup={};inputpins=[]
for path in inputs:
 b=path.read_bytes();doc=json.loads(b);pin={'path':str(path),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};inputpins.append(pin)
 for q in doc['points']:
  if key(q)in wanted:lookup[key(q)]={'item':doc['item'],'native_body':pin,'point':q,'frame_base':path.parent}
p=D/'retained-PMP2-native-011/actual-two-native-contexts.json';b=p.read_bytes();doc=json.loads(b);pin={'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};inputpins.append(pin)
for q in doc['points']:
 if key(q)in wanted:lookup[key(q)]={'item':doc['item'],'native_body':pin,'point':q,'frame_base':inputs[0].parent}
assert set(lookup)==wanted;selected=[2,7,14,17,19,20,23,28,34,35,43,44,52,53,57,80,5,37,46,63,66,73,10];rows=[];images={}
for j,index in enumerate(selected):
 point=new['points'][index];old=lookup[key(point)];prior=old['point'];assert prior['longitude']==point['longitude']and prior['latitude']==point['latitude'];panel=Image.new('RGB',(528,158),'white');frames=[]
 for t,(pt,base,date)in enumerate([(prior,old['frame_base'],'Jan5'),(point,newpath.parent,'Jan25')]):
  r,c=pt['assets']['red']['local_pixel'];br,bc=pt['physical_block'];folder=base/f'block-{br:02d}-{bc:02d}'
  for k,name in enumerate(['rgb-native.png','nir-red-green-native.png']):
   fp=folder/name
   if str(fp)not in images:images[str(fp)]=Image.open(fp).convert('RGB')
   im=images[str(fp)];left,top=c-32,r-32;box=(max(0,left),max(0,top),min(im.width,c+32),min(im.height,r+32));patch=Image.new('RGB',(64,64),(100,100,100));patch.paste(im.crop(box),(box[0]-left,box[1]-top));x=(t*2+k)*132;panel.paste(patch.resize((128,128),Image.Resampling.NEAREST),(x,0));dr=ImageDraw.Draw(panel);cx=x+65;cy=65
   for line in[(cx-7,cy,cx-3,cy),(cx+3,cy,cx+7,cy),(cx,cy-7,cx,cy-3),(cx,cy+3,cx,cy+7)]:dr.line(line,fill='yellow',width=1)
   b=fp.read_bytes();frames.append({'date':date,'file':str(fp),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 dr=ImageDraw.Draw(panel);dr.text((1,129),f'Jan5 {old["item"]} p{prior["index"]} | Jan25 p{index}',fill='black');k=point['original_key'];dr.text((1,143),f'{k["owner"]}/{k["y"]}/{k["x"]}  RGB,NIR | RGB,NIR',fill='black')
 if j%12==0:sheet=Image.new('RGB',(1056,948),'white')
 sheet.paste(panel,((j%2)*528,((j%12)//2)*158))
 if j%12==11 or j==len(selected)-1:sheet.save(O/f'comparison-{j//12:02d}.png')
 rows.append({'new_point_index':index,'original_key':point['original_key'],'prior_Jan5':{'item':old['item'],'native_body':old['native_body'],'point':prior},'existing_frame_pins':frames,'comparison_page':j//12})
record={'all81_key_exact_Jan5_references':[{ 'new_point_index':i,'prior_Jan5':{'item':lookup[key(p)]['item'],'native_body':lookup[key(p)]['native_body'],'point':lookup[key(p)]['point']}}for i,p in enumerate(new['points'])],'all_input_source_body_pins':inputpins,'selected22proposals_plusheld_pondgrid':rows,'source_or_native_raster_kernel_calls':0,'method':'ExistingPNGpixelcomparisononly,nearest2x,crossatcontainingnativepixel;grayoutsideexistingwindowisunavailable,notwater/nodata. Jan5andJan25independent20dayacquisitions,sameoriginalcoordinates,notclaimofexactgroundregistration/shoreequivalence.'};(O/'comparisons.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'all81exactprior_Jan5contexts_found':81,'selected_comparisons':len(rows),'sourcecalls':0,'pages':2}))
