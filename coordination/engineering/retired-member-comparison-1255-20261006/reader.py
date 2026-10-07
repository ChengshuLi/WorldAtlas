"""Strict frozen ordinary byte reader for this one member comparison job."""
import gzip,hashlib,json,pathlib,re,subprocess,sys
from evidence.immutable import canonical_json as canon,safe_path
SHA=lambda b:hashlib.sha256(b).hexdigest()


class Inputs:
    def __init__(self,repo,commit,prefix):
        if not re.fullmatch('[a-f0-9]{40}',commit):raise ValueError('Immutable code commit required')
        self.repo=pathlib.Path(repo).resolve();self.commit=commit;self.prefix=safe_path(prefix)
        self.pins=[];self.used={}
        self.process=subprocess.Popen(['git','cat-file','--batch'],cwd=self.repo,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    def read(self,path,pin=None,decode=False):
        path=safe_path(path);full=self.prefix+'/'+path
        self.process.stdin.write((self.commit+':'+full+'\n').encode());self.process.stdin.flush()
        h=self.process.stdout.readline().split()
        if len(h)!=3 or h[1]!=b'blob':raise ValueError('Missing frozen ordinary input')
        if int(h[2])>32*1024*1024:raise ValueError('Oversized ordinary input')
        b=self.process.stdout.read(int(h[2]));assert self.process.stdout.read(1)==b'\n'and len(b)==int(h[2])
        mode=subprocess.check_output(['git','ls-tree',self.commit,'--',full],cwd=self.repo).decode().split()[0]
        if mode not in ('100644','100755'):raise ValueError('Ordinary input mode required')
        if pin and(len(b)!=pin['bytes']or SHA(b)!=pin['sha256']):raise ValueError('Changed input bytes')
        raw=gzip.decompress(b)if decode else b
        if len(raw)>32*1024*1024:raise ValueError('Oversized decoded ordinary input')
        if decode and pin and 'decoded_sha256'in pin and(len(raw)!=pin['decoded_bytes']or SHA(raw)!=pin['decoded_sha256']):raise ValueError('Changed decoded bytes')
        if full not in self.used:
            p={'commit':self.commit,'path':full,'bytes':len(b),'sha256':SHA(b),'git_blob_oid':h[0].decode(),'mode':mode}
            if decode:p.update(decoded_bytes=len(raw),decoded_sha256=SHA(raw))
            self.used[full]=p;self.pins.append(p)
        return raw
    def original(self,commit,path,index,parse=True):
        x=next((x for x in index['aliases']if x['original']['commit']==commit and x['original']['path']==path),None)
        if x is None:raise ValueError('Original whole containing input omitted')
        pin=x['ordinary'];b=self.read(pin['path'],pin)
        raw=gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b
        o=x['original']
        if len(raw)>32*1024*1024:raise ValueError('Oversized decoded alias')
        self.used[self.prefix+'/'+pin['path']].update(decoded_bytes=len(raw),decoded_sha256=SHA(raw))
        if len(b)!=o['bytes']or SHA(b)!=o['sha256']or len(raw)!=o['decoded_bytes']or SHA(raw)!=o['decoded_sha256']:raise ValueError('Original alias relationship mismatch')
        return json.loads(raw)if parse else raw
    def archive(self,index):
        streams={}
        for kind,g in index['archive'].items():
            parts=[];offset=0
            for part in g['parts']:
                if part['offset']!=offset:raise ValueError('Missing/reordered archive fragment')
                raw=self.read(part['ordinary']['path'],part['ordinary'],decode=kind=='decoded')
                if len(raw)!=part['raw_bytes']or SHA(raw)!=part['raw_sha256']:raise ValueError('Changed archive fragment')
                parts.append(raw);offset+=len(raw)
            body=b''.join(parts)
            if len(body)!=g['whole_bytes']or SHA(body)!=g['whole_sha256']:raise ValueError('Archive whole bytes mismatch')
            streams[kind]=body
        if set(streams)!={'encoded','decoded'}or gzip.decompress(streams['encoded'])!=streams['decoded']:raise ValueError('Original encoded/decoded archive relationship mismatch')
        o=index['archive_original']
        if SHA(streams['encoded'])!=o['sha256']or SHA(streams['decoded'])!=o['decoded_sha256']:raise ValueError('Original whole archive pin mismatch')
        return json.loads(streams['decoded'])
    def close(self):
        self.process.terminate();self.process.wait()


def authenticate_executed_modules(repo,commit,paths):
    if not isinstance(commit,str)or not re.fullmatch('[a-f0-9]{40}',commit):raise ValueError('Immutable execution commit required before Git')
    root=pathlib.Path(repo).resolve();receipt=[]
    for path in paths:
        path=safe_path(path);local=root/path
        b=subprocess.check_output(['git','show',commit+':'+path],cwd=root)
        if local.is_symlink()or not local.is_file()or local.read_bytes()!=b:raise ValueError('Executed local project code differs from frozen commit')
        receipt.append({'path':path,'sha256':SHA(b),'bytes':len(b),'commit':commit})
    return receipt


def output_target(repo,prefix,value):
    safe_path(value);root=pathlib.Path(repo).resolve();owned=root/safe_path(prefix);target=root/value
    if not value.startswith(prefix+'/'):raise ValueError('Output outside owned namespace')
    for parent in [target,*target.parents]:
        if parent.exists()and parent.is_symlink():raise ValueError('Symlink output destination')
        if parent==root:break
    if not target.resolve().is_relative_to(owned.resolve()):raise ValueError('Escaped output destination')
    if target.exists():raise ValueError('Existing output destination')
    return target


def validate_family_scope(scope,families,counts=(2476,20032,2438,869)):
    if len(families)!=counts[0]or len(scope['component_ids'])!=counts[1]or len(scope['member_ids'])!=counts[2]or len(scope['contact_ids'])!=counts[3]:raise ValueError('Complete fixed scope counts differ')
    for key in ['family_ids','component_ids','member_ids','contact_ids']:
        if scope[key]!=sorted(set(scope[key])):raise ValueError('Duplicate or unordered scope roster')
    if sorted(families)!=scope['family_ids']:raise ValueError('Whole family roster differs')
    components=[];members=set();contacts=set()
    for f in families.values():
        if f['component_ids']!=sorted(set(f['component_ids']))or len(f['component_ids'])!=f['component_count']or SHA(canon(f['component_ids']))!=f['component_ids_sha256']:raise ValueError('Family count/digest changed')
        components.extend(f['component_ids']);contacts.update(f['contact_ids'])
        if any(s['kind']!='physical-adaptation-processing-reproduction'for s in f['source_families']):raise ValueError('Wrong source role')
        for s in f['source_families']:members.update(s.get('original_source_member_ids',[]))
    if sorted(components)!=scope['component_ids']or sorted(members)!=scope['member_ids']or sorted(contacts)!=scope['contact_ids']:raise ValueError('Complete component/member/contact closure differs')
    for field,key in [('families','family_ids'),('components','component_ids'),('members','member_ids')]:
        if SHA(canon(scope[key]))!=scope['roster_canonical_sha256'][field]:raise ValueError('Scope roster digest changed')


def validate_pointsets(scope,features,members):
    featurepins={r['id']:r for r in scope['existing_current_component_and_member_pins']}
    memberpins={r['id']:r for r in scope['retired_member_complete_record_pins']}
    if len(featurepins)!=len(scope['existing_current_component_and_member_pins'])or sorted(featurepins)!=scope['component_ids']or sorted(features)!=scope['component_ids']:raise ValueError('Missing/duplicate full current component bindings')
    if len(memberpins)!=len(scope['retired_member_complete_record_pins'])or sorted(memberpins)!=scope['member_ids']or not set(memberpins)<=set(members):raise ValueError('Missing/duplicate original member bindings')
    for i,b in featurepins.items():
        f=features[i]
        if SHA(canon(f))!=b['canonical_feature_sha256']or SHA(canon(f['geometry']))!=b['geometry_sha256']:raise ValueError('Full current feature or geometry representation differs')
    for i,b in memberpins.items():
        r=members[i]
        if SHA(canon(r))!=b['canonical_record_sha256']or SHA(canon(r['geometry']))!=b['canonical_geometry_sha256']or canon(r['metadata'])!=canon(b['metadata']):raise ValueError('Original member geometry or metadata representation differs')
