import json,gzip,pathlib,subprocess,hashlib,collections,numpy as np
from shapely.geometry import shape
from shapely import union_all,points,covers,STRtree
D=pathlib.Path(__file__).resolve().parent;W=pathlib.Path((D/'workspace.txt').read_text().strip());H=(D/'base.txt').read_text().strip();S=json.load(open(D.parent/'screen-complex-large-packages-20261017/screening.json'));pkg=next(x for x in S['results'] if x['package']['primary_source']=='gb:CAN:ADM3');phys={o['index']:o for o in pkg['owners'] if o['target_properties']['metadata'].get('source_id','').startswith('aafc:')}
def raw(p,h=H):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',h+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
def readpin(p):
 b=raw(p['path'],p.get('commit',H));assert len(b)==p['bytes'] and sha(b)==p['sha256']
 if p.get('decoded_bytes'):
  b=gzip.decompress(b);assert len(b)==p['decoded_bytes'] and sha(b)==p['decoded_sha256']
 return b
sel=json.loads(raw('data/ownership-selection.json'));mb=raw(sel['manifest_path']);assert sha(mb)==sel['sha256'];manifest=json.loads(mb);lat=np.frombuffer(readpin(manifest['native_latitudes']),dtype='<f8');assert len(lat)==262166
origp='data/regional-review/regional-review-a9f03b364bdefa4a/sources/aafc-baseline-arcgis-layer0.geojson';ob=raw(origp);orig=json.loads(ob);origmap=collections.defaultdict(list);
for f in orig['features']:origmap[f['properties']['ECOREGION_ID']].append(f)
officialp='data/regional-review/regional-review-a9f03b364bdefa4a/sources/aafc-terrestrial-ecoregions-v2.2.geojson';ofb=raw(officialp);off=json.loads(ofb);print('CRS',orig.get('crs'),off.get('crs'),'count',len(origmap),len(off['features']),'props',off['features'][0]['properties'],flush=True)
rows=[r for p in sorted((W/'.scratch/frozen-repair').glob('block-*.gz')) for r in json.loads(gzip.decompress(p.read_bytes()))];allrows=collections.defaultdict(list)
for y,a,z,ows,sids,k in rows:
 if ows[0] in phys:allrows[ows[0]].append((y,a,z,k))
geos=[shape(f['geometry']) for f in orig['features']];tree=STRtree(geos);out=[];total=collections.Counter();records=[]
for own,rs in allrows.items():
 o=phys[own];eco=o['target_properties']['metadata']['ecoregion_id'];selected=origmap[eco];g=union_all([shape(f['geometry']) for f in selected]);ys=np.asarray([y for y,a,z,k in rs for x in range(a,z)]);xs=np.asarray([x for y,a,z,k in rs for x in range(a,z)]);ps=points((xs+.5)/262166*360-180,lat[ys]);same=np.asarray(covers(g,ps));matches=tree.query(ps,predicate='intersects');comp=np.zeros(len(xs),dtype=bool);missing=np.ones(len(xs),dtype=bool)
 for pi,gi in zip(*matches):
  missing[pi]=False
  if orig['features'][gi]['properties']['ECOREGION_ID']!=eco:comp[pi]=True
 c={'all':len(xs),'within_intended_ecoregion':int(same.sum()),'outside_intended_ecoregion':int((~same).sum()),'other_ecoregion_contact':int(comp.sum()),'no_ecoregion_contact':int(missing.sum()),'same_without_competitor':int((same&~comp).sum())};total.update(c);out.append({'index':own,'id':o['id'],'name':o['name'],'ecoregion_id':eco,'source_geometry_valid':bool(g.is_valid),'counts':c,'coastline_adjustments':o['target_properties']['metadata'].get('coastline_adjustments',[])})
 for y,x,a,b,c in zip(ys.tolist(),xs.tolist(),same.tolist(),comp.tolist(),missing.tolist()):records.append([y,x,own,a,b,c])
 print(own,o['name'],c,flush=True)
res={'kind':'read-only-AAFC-native-centre-applicability-screening','base':H,'grid_size':262166,'latitudes_pin':manifest['native_latitudes'],'baseline_source':{'path':origp,'sha256':sha(ob),'bytes':len(ob),'feature_count':len(orig['features']),'crs':orig.get('crs')},'official_source':{'path':officialp,'sha256':sha(ofb),'bytes':len(ofb),'feature_count':len(off['features']),'crs':off.get('crs')},'counts':dict(total),'targets':out,'limits':['Shapely complete-source point predicate screening, not native scanline qualification or final authority. Boundary observations require unchanged constructor verification.','Outside-ecoregion cells have not been accepted through historic coastline adjustment. #887 clipping/completeness obligations remain open.']}
(D/'aafc-applicability.json').write_text(json.dumps(res,indent=2)+'\n');(D/'aafc-point-observations.json.gz').write_bytes(gzip.compress((json.dumps(records,separators=(',',':'))+'\n').encode(),mtime=0));print(json.dumps(res['counts']))
