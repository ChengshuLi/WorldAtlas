import gzip,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'configured-existing-runtime:worldcover-reader')
import numpy as np
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent;N=ROOT/'worldcover-native-001';source=ROOT/'authored-interpretation-001/open-physical-questions.jsonl.gz';raw=source.read_bytes();rows=[json.loads(x)for x in gzip.decompress(raw).splitlines()if json.loads(x)['category']=='unresolved-native-context-coverage'];assert len(rows)==4;results=[]
def pixel(tile,r,c):
 br,bc=r//1024,c//1024;name='new-block-%02d-%02d.npz'%(br,bc);p=N/'tiles'/tile/name
 if not p.exists():p=OUT/tile/name
 q=json.loads(p.with_suffix('.json').read_text());b=p.read_bytes();assert len(b)==q['array']['bytes']and hashlib.sha256(b).hexdigest()==q['array']['sha256'];header=json.loads((N/'tiles'/tile/'source.json').read_text());assert header['crs']=='EPSG:4326'and header['shape']==[36000,36000]and header['transform'][0]==1/12000 and header['transform'][4]==-1/12000 and header['transform'][2]==96;assert q['source_identity']==header['source_identity'];w=q['window']
 with np.load(p)as a:code=int(a['codes'][r-w['row_off'],c-w['col_off']]);mask=int(a['masks'][r-w['row_off'],c-w['col_off']])
 return code,mask,{'retained_array':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'tile':tile,'row':r,'col':c,'window':w,'transform':header['transform'],'source_identity':header['source_identity']}
for row in rows:
 r,c=row['native_row'],row['native_col'];codes=[];masks=[];positions=[]
 for dr in(-1,0,1):
  cr=[];mr=[];pr=[]
  for dc in(-1,0,1):
   tile='N12E096';rr=r+dr
   if rr<0:tile='N15E096';rr+=36000
   if rr>=36000:tile='N09E096';rr-=36000
   code,mask,p=pixel(tile,rr,c+dc);cr.append(code);mr.append(mask);pr.append(p)
  codes.append(cr);masks.append(mr);positions.append(pr)
 assert codes[1][1]==row['source_observation']['class_code'];valid=all(v==255 for x in masks for v in x);wet={80,90,95};allcodes={v for x in codes for v in x};kind=None
 if valid and allcodes=={80}:kind='annual2020-source-supported-water-body-location'
 elif valid and codes[1][1]in{10,20,30,40,50,60}and not allcodes&wet:kind='annual2020-source-supported-specific-cover-body-location'
 result={'original_open_row':row,'actual_complete_cross_frame_codes':codes,'actual_complete_cross_frame_masks':masks,'actual_native_pixel_positions':positions,'source_year':2020,'grid_registration':'Allthree actual sourceheaders nativeEPSG4326 1/12000degree east/south spacing,sameoriginlongitude96; frames meet atlatitude15 and12. Exactnine containing/nativeadjacent cells assembled without resampling/clamping.','category':kind or'unresolved-water-wet-cover-edge-location','proposed_bounded_answer':kind is not None,'proposed_answer':row['specific_annual_source_fact']if kind else None,'remaining_physical_question':None if kind else'Complete actual cross-framecontext now available, but water/wet-covertransition at actualcentre leaves exactshore/ground/water andsource-registration relation unsupported.','status':'AUTHOR-PROPOSED; independentreview/Mainadoptionpending'if kind else'OPEN; improved actualcontext does notresolvephysicalrelation','new_adopted_count':0};results.append(result)
(OUT/'four-authored-outcomes.json').write_text(json.dumps({'kind':'four-original-frameedge-actual-source-context-outcomes','raw_original_open_sha256':hashlib.sha256(raw).hexdigest(),'actual_new_block_read':'actual-two-block-read.json','original_keys':4,'proposals':sum(r['proposed_bounded_answer']for r in results),'open':sum(not r['proposed_bounded_answer']for r in results),'outcomes':results,'remote_blocks_reread':0,'repair_or_native_credit':0},indent=2)+'\n')
print(json.dumps([{'point_index':r['original_open_row']['point_index'],'key':r['original_open_row']['original_key'],'codes':r['actual_complete_cross_frame_codes'],'proposal':r['proposed_bounded_answer']}for r in results]))
