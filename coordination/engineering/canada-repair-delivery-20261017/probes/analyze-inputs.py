import json,gzip,pathlib,subprocess,hashlib,collections
from shapely.geometry import shape
from shapely import union_all
D=pathlib.Path(__file__).resolve().parent;W=pathlib.Path((D/'workspace.txt').read_text().strip());H=(D/'base.txt').read_text().strip();Q='coordination/engineering/global-current-cell-work-queue-20261014/';S=json.load(open(D.parent/'screen-complex-large-packages-20261017/screening.json'));pkg=next(x for x in S['results'] if x['package']['primary_source']=='gb:CAN:ADM3')
def raw(p,h=H):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',h+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
def pin(p,h=H):
 b=raw(p,h);return {'path':p,'commit':h,'bytes':len(b),'sha256':sha(b),'git_blob_oid':subprocess.check_output(['git','-C',str(W),'rev-parse',h+':'+p]).decode().strip()}
rows=[r for p in sorted((W/'.scratch/frozen-repair').glob('block-*.gz')) for r in json.loads(gzip.decompress(p.read_bytes()))];assert sorted(rows)==sorted(json.loads(gzip.decompress((D.parent/'screen-complex-large-packages-20261017/gb-CAN-ADM3--repair-evaluation.json.gz').read_bytes())))
roster=json.loads(gzip.decompress(raw(Q+'source-feature-roster.json.gz')));rr={x['source_id']:x for x in roster};byindex={x['source_index']:x for x in roster};catp='coordination/engineering/original-geography-source-corpus-20261006/catalogue.json';cat=json.loads(raw(catp));familykeys=set();foreign=[];cells=collections.Counter();sources={};custody=[]
for y,a,z,owners,sids,kind in rows:
 for sid in sids:familykeys.add(':'.join(byindex[sid]['source_id'].split(':')[:3]))
 conflicts=[byindex[s] for s in sids if not byindex[s]['source_id'].startswith('gb:CAN:')]
 if conflicts:foreign.append([y,a,z,owners,sids,kind]);cells['foreign_territorial_overlap']+=z-a
 for f in conflicts:cells['foreign:'+f['source_id']]+=z-a
for c in cat['products']:
 if c['key'] not in familykeys:continue
 chunks=[]
 for p in c['parts']:
  b=raw(p['path']);assert len(b)==p['bytes'] and sha(b)==p['sha256'];z=gzip.decompress(b);assert len(z)==p['uncompressed_bytes'] and sha(z)==p['uncompressed_sha256'];chunks.append(z)
 b=b''.join(chunks);assert len(b)==c['original_bytes'] and sha(b)==c['original_sha256'];fs=json.loads(b)['features'];assert len(fs)==c['feature_count'];r=[]
 for f in fs:
  sid=c['key']+':'+f['properties']['shapeID'];assert sid in rr;g=shape(f['geometry']);sources[sid]=f;r.append({'id':sid,'name':f['properties']['shapeName'],'owners':rr[sid]['owners'],'geometry_valid':bool(g.is_valid)})
 custody.append({'record':c,'features':r});print('source',c['key'],len(fs),len(b),flush=True)
sel=json.loads(raw('data/ownership-selection.json'));bp=sel['selected_geography'];bb=raw(bp['path'],bp.get('commit',H));assert sha(bb)==bp['sha256'] and len(bb)==bp['bytes'];bank=json.loads(bb);features={};targetpins=[]
for commit,path in sorted({(o['target_pin']['commit'],o['target_pin']['path']) for o in pkg['owners']}):
 p=next(x for x in bank['unchanged_files']+bank['overrides'] if x['commit']==commit and x['path']==path);b=raw(path,commit);assert len(b)==p['bytes'] and sha(b)==p['sha256'];targetpins.append(p)
 if p.get('encoding')=='gzip':b=gzip.decompress(b);assert len(b)==p['decoded_bytes'] and sha(b)==p['decoded_sha256']
 features.update({x['id']:x for x in json.loads(b)['features']})
measure=[];physical=[];stage_estimate=0
for o in pkg['owners']:
 f=features[o['id']];assert f['properties']==o['target_properties'];m=f['properties']['metadata'];isphysical=m.get('source_id','').startswith('aafc:');estimated=sum(len(json.dumps({'target':s,'family':'can','consumed':sources[s],'selected':f},separators=(',',':')).encode()) for s in o['source_atoms']);stage_estimate+=estimated
 measure.append({'index':o['index'],'id':o['id'],'name':o['name'],'cells':o['candidate_cells'],'atoms':len(o['source_atoms']),'physical':isphysical,'estimated_all_member_stage_bytes':estimated})
 if isphysical:physical.append({'id':o['id'],'ecoregion_id':m['ecoregion_id'],'source_atoms':o['source_atoms'],'source_member_ids':m['source_member_ids'],'coastline_adjustments':m.get('coastline_adjustments',[])})
aafcp='data/regional-review/regional-review-a9f03b364bdefa4a/sources/aafc-baseline-arcgis-layer0.geojson';aafcb=raw(aafcp);af=json.loads(aafcb);print('AAFC keys',af.keys(),'first',af['features'][0]['properties'],flush=True)
result={'base':H,'original_cells':sum(r[2]-r[1] for r in rows),'original_intervals':len(rows),'physical_split':dict(collections.Counter({k:sum(z-a for y,a,z,o,s,c in rows if c==k) for k in ['land','inland-water']})),'complete_territorial_families':sorted(familykeys),'foreign_original_contact_cells':dict(cells),'foreign_features':{x['source_id']:x for r in foreign for s in r[4] for x in [byindex[s]] if not x['source_id'].startswith('gb:CAN:')},'target_pins':targetpins,'target_stage_estimates':measure,'all_member_stage_bytes':stage_estimate,'AAFC_baseline':pin(aafcp),'AAFC_features':len(af['features']),'physical_targets':physical,'limits':['Read-only source applicability and size analysis; no cell qualification or physical execution.']}
(D/'input-analysis.json').write_text(json.dumps(result,indent=2)+'\n');(D/'full-source-custody.json').write_text(json.dumps(custody,separators=(',',':'))+'\n');(D/'foreign-original-intervals.json.gz').write_bytes(gzip.compress((json.dumps(foreign,separators=(',',':'))+'\n').encode(),mtime=0))
print(json.dumps({k:v for k,v in result.items() if k not in ['target_pins','target_stage_estimates','physical_targets','foreign_features']}))
