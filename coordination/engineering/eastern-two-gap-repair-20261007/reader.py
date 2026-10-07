"""Complete frozen ordinary inputs for the two approved physical-region repairs."""
from pathlib import Path
import gzip,hashlib,io,json,re,subprocess,tarfile
from evidence.immutable import canonical_json,safe_path
from world import load_world
from kernel import TARGETS
MAX=32*1024**2
PREFIX='coordination/engineering/retired-member-comparison-1255-20261006'
FAMILIES={'gap-source-batch:1305d963168bdcf95f84ed9f','gap-source-batch:a590be7f2f6a5682aaad902c','gap-source-batch:b74725e6fb2a9adf7e5d4a10','gap-source-batch:e581d9c70f45ade3d5a59cb8'}
def digest(raw):return hashlib.sha256(raw).hexdigest()
def checked_file(root,name):
    name=safe_path(name);p=Path(root)/name
    for item in [p,*p.parents]:
        if item.is_symlink():raise ValueError('Symlink input path')
        if item==Path(root).absolute():break
    if not p.is_file():raise ValueError('Missing ordinary input')
    raw=p.read_bytes()
    if len(raw)>MAX:raise ValueError('Encoded ordinary input cap')
    return raw
class Inputs:
    def __init__(self,root):
        self.root=Path(root);self.index=json.loads(checked_file(root,'input-index.json'));self.rows={};self.used=[]
        for row in self.index['aliases']:
            p=row['original']['path']
            if p in self.rows:raise ValueError('Duplicate declared original path')
            self.rows[p]=row
    def read(self,path):
        row=self.rows[path];pin=row['ordinary'];raw=checked_file(self.root,pin['path'])
        if len(raw)!=pin['bytes']or digest(raw)!=pin['sha256']:raise ValueError('Ordinary whole bytes mismatch: '+path)
        decoded=gzip.decompress(raw)if pin['path'].endswith('.gz')else raw
        if len(decoded)>MAX or len(decoded)!=pin['decoded_bytes']or digest(decoded)!=pin['decoded_sha256']:raise ValueError('Decoded whole bytes mismatch: '+path)
        original=row['original'];body=decoded if row['codec']=='lossless-whole-file-gzip'else raw
        if len(body)!=original['bytes']or digest(body)!=original['sha256']:raise ValueError('Original whole alias mismatch: '+path)
        self.used.append(path)
        return body
    def json(self,path):
        raw=self.read(path)
        if path.endswith('.gz')or self.rows[path]['group']=='complete-original-components':raw=gzip.decompress(raw)
        return json.loads(raw)
    def group(self,name):return sorted(p for p,r in self.rows.items()if r['group']==name)
    def authenticate_all(self,repo):
        for path,row in self.rows.items():
            raw=self.read(path);o=row['original'];c=o['commit']
            if not re.fullmatch('[a-f0-9]{40}',c):raise ValueError('Exact commit before Git')
            entry=subprocess.check_output(['git','-C',str(repo),'ls-tree','-z',c,'--',path]).decode().rstrip('\0')
            fields=entry.split('\t')
            if len(fields)!=2 or fields[1]!=path:raise ValueError('Exact ordinary source entry')
            mode,kind,oid=fields[0].split()
            if mode!=o['mode']or mode not in ('100644','100755')or kind!='blob'or oid!=o['git_blob_oid']:raise ValueError('Source mode/blob mismatch')
            original=subprocess.check_output(['git','-C',str(repo),'cat-file','blob',oid])
            if original!=raw:raise ValueError('Ordinary alias does not equal original source')
        for p in self.index['issue_baseline_pins']:
            c=p['commit']
            if not re.fullmatch('[a-f0-9]{40}',c):raise ValueError('Exact baseline before Git')
            raw=subprocess.check_output(['git','-C',str(repo),'cat-file','blob',c+':'+safe_path(p['path'])])
            if len(raw)!=p['bytes']or digest(raw)!=p['sha256']:raise ValueError('Issue original baseline pin mismatch')
        return {'ordinary_inputs':len(self.rows),'ordinary_encoded_bytes':sum(r['ordinary']['bytes']for r in self.rows.values()),'all_original_aliases_equal':True,'issue_baseline_pins':len(self.index['issue_baseline_pins'])}

def load(root,repo):
    inputs=Inputs(root);receipt=inputs.authenticate_all(repo)
    expected={p:{'logical_bytes':r['original']['bytes'],'logical_sha256':r['original']['sha256']}for p,r in inputs.rows.items()if r['group']=='complete-current-world'}
    world,world_receipt=load_world(str(repo),inputs.index['baseline_commit'],expected)
    # Verify the complete world is exactly the ordinary admitted alias world too.
    alias_world={f['id']:f for p in expected if p!='data/world-index.json'for f in inputs.json(p)['features']}
    if canonical_json(world)!=canonical_json(alias_world):raise ValueError('Ordinary/Git complete world differs')
    archive_index=inputs.json(PREFIX+'/input-index.json');archive={}
    for kind in ['encoded','decoded']:
        data=[];offset=0;spec=archive_index['archive'][kind]
        for part in spec['parts']:
            pin=part['ordinary'];raw=inputs.read(PREFIX+'/'+pin['path']);body=gzip.decompress(raw)if kind=='decoded'else raw
            if part['offset']!=offset or len(body)!=part['raw_bytes']or digest(body)!=part['raw_sha256']:raise ValueError('Complete original archive fragment/offset mismatch')
            data.append(body);offset+=len(body)
        raw=b''.join(data)
        if len(raw)!=spec['whole_bytes']or digest(raw)!=spec['whole_sha256']:raise ValueError('Original archive whole relationship')
        archive[kind]=raw
    if gzip.decompress(archive['encoded'])!=archive['decoded']:raise ValueError('Original encoded/decoded archive relationship')
    mids=set(world_receipt['fixedpoint_retired_member_ids']);retired=[f for f in json.loads(archive['decoded'])['locations']if f['id']in mids]
    if len(retired)!=477 or {f['id']for f in retired}!=mids:raise ValueError('Complete477 retired member allocation')
    registry=inputs.json('data/semantic-sources.json');pieces=[]
    for part in registry['archive_parts']:
        b=inputs.read('data/'+part['path'])
        if digest(b)!=part['sha256']:raise ValueError('Semantic original raw fragment changed')
        pieces.append(b)
    semantic=b''.join(pieces)
    if digest(semantic)!=registry['archive_sha256']:raise ValueError('Whole semantic original archive changed')
    selected={};native_names={'aafc-ecoregions.geojson','aafc-ecoprovinces.json','aafc-item.json'};pins={x['path']:x['sha256']for x in registry['files']}
    with tarfile.open(fileobj=io.BytesIO(semantic),mode='r|gz')as stream:
        for member in stream:
            name=member.name.removeprefix('./').split('/')[-1]
            if name in native_names:
                if name in selected or not member.isfile()or member.size>MAX:raise ValueError('Duplicate/unsafe native member')
                raw=stream.extractfile(member).read()
                if digest(raw)!=pins[name]:raise ValueError('Whole native original source pin mismatch')
                selected[name]=raw
    if set(selected)!=native_names:raise ValueError('Complete selected native original files absent')
    native=json.loads(selected['aafc-ecoregions.geojson'])['features']
    if len(native)!=218 or len({f['properties']['ECOREGION_ID']for f in native})!=194:raise ValueError('Complete218 untouched native records/194 source regions')
    sidset={world[s]['properties']['metadata']['source_id']for s in world_receipt['fixedpoint_current_subject_ids']}
    native_scope=[f for f in native if 'aafc:ecoregion:'+str(f['properties']['ECOREGION_ID'])in sidset]
    if len({'aafc:ecoregion:'+str(f['properties']['ECOREGION_ID'])for f in native_scope})!=24:raise ValueError('Complete24 native source regions')
    all_families=[]
    for p in inputs.group('complete-current-families'):
        if '/current-batches-'in p:all_families.extend(inputs.json(p))
    if len(all_families)!=15610 or len({f['id']for f in all_families})!=15610:raise ValueError('Complete15610 current native families')
    families=[r['original_complete_family']['family']for r in inputs.json('coordination/engineering/numeric-partition-diagnosis-20261006/run-one/families-000.json.gz')if r['original_complete_family']['family']['id']in FAMILIES]
    if len(families)!=4:raise ValueError('Complete four frozen families')
    ids={i for f in families for i in f['component_ids']}
    if len(ids)!=64 or ids!=set(inputs.index['physical_scope_component_ids']):raise ValueError('Exact64 full family scope')
    components={}
    for p in inputs.group('complete-original-components'):
        for f in inputs.json(p)['features']:
            if f['id']in ids:
                if f['id']in components:raise ValueError('Duplicate original component')
                components[f['id']]=f
    delta=inputs.json('coordination/engineering/worldwide-successor-1215-20261006/run-one/components-delta.json.gz')
    for identity in delta['removed_ids']:components.pop(identity,None)
    for f in delta['upsert_records']:
        if f['id']in ids:components[f['id']]=f
    if set(components)!=ids:raise ValueError('Complete current component reconstruction')
    physics={}
    for p in inputs.group('complete-physics-containing-products'):
        if '/results/components-'not in p:continue
        raw=gzip.decompress(inputs.read(p))
        for line in raw.splitlines():
            r=json.loads(line)
            if r['component_id']in ids:
                if r['component_id']in physics:raise ValueError('Duplicate physical component')
                physics[r['component_id']]=r
    if set(physics)!=ids:raise ValueError('Complete64 accepted physical observations')
    return {'inputs':inputs,'world':world,'retired':retired,'native':native,'native_scope':native_scope,'native_source_files':selected,'families':families,'components':components,'physics':physics,'all_families':all_families,'receipt':{**receipt,'world':world_receipt,'retired_count':len(retired),'native_count':len(native),'native_scope_count':len(native_scope),'families':len(families),'components':len(components),'geometry_operations':0}}
