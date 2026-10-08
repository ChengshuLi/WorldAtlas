"""Whole-file multi-vintage metadata IO with prospective complete data/code caps.
No source/geometry method, approval, native-runtime or kernel certification.
"""
import gzip,hashlib,io,json,os,re,subprocess
from pathlib import Path
FILE=33554432;PHASE=268435456;SHARD=8388608;RECEIPT=4096

def need(ok,msg):
    if not ok:raise ValueError(msg)

def sha(raw):return hashlib.sha256(raw).hexdigest()

def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()

def safe(path):
    need(isinstance(path,str) and not path.startswith('/') and '\\' not in path and all(s not in ('','.','..') for s in path.split('/')),'Unsafe immutable path')
    return path

def cost(pin):
    for k in ('bytes','uncompressed_bytes') if 'uncompressed_bytes' in pin else ('bytes',):need(type(pin.get(k)) is int and 0<=pin[k]<=FILE,'Ordinary encoded/decoded cap')
    for k in ('sha256','uncompressed_sha256') if 'uncompressed_bytes' in pin else ('sha256',):need(re.fullmatch('[a-f0-9]{64}',pin.get(k,'')),'Whole encoded/decoded SHA required')
    return pin['bytes']+pin.get('uncompressed_bytes',0)

def ordinary(path):
    p=Path(path);need(p.is_absolute() and '..' not in p.parts and all(not x.is_symlink() for x in (p,*p.parents)),'Ordinary contained path required')
    return p

class Phase:
    def __init__(self,repo,destination,pins,reserve):
        self.repo=ordinary(repo).resolve();self.destination=ordinary(destination)
        need(self.destination.parent.is_dir() and not os.path.lexists(self.destination),'Fresh whole run destination required')
        need(self.destination.resolve().is_relative_to(self.repo/'coordination/engineering/global-gap-candidate-funnel-20261008/vintages'),'Owned run containment required')
        need(type(reserve) is int and reserve>=0,'Complete prospective output reserve')
        self.pins={};self.reads=set();self.outputs={};self.reserve=reserve
        for p in pins:
            safe(p['path']);need(re.fullmatch('[a-f0-9]{40}',p.get('commit','')),'Immutable input vintage required');cost(p)
            key=(p['commit'],p['path']);need(key not in self.pins,'Duplicate declared input');self.pins[key]=p
        self.input_cost=sum(cost(p) for p in pins)
        need(len(pins)<512 and self.input_cost+reserve+RECEIPT<=PHASE,'Complete prospective input/code/output budget')
    def read(self,p):
        key=(p['commit'],p['path']);need(self.pins.get(key)==p,'Undeclared actual input')
        tree=subprocess.check_output(['git','-C',str(self.repo),'ls-tree','-z',p['commit'],'--',p['path']]).decode().rstrip('\0')
        need('\t' in tree,'Missing immutable input');meta,name=tree.split('\t');mode,kind,blob=meta.split()
        need(name==p['path'] and mode in ('100644','100755') and kind=='blob','Ordinary Git input required')
        need(int(subprocess.check_output(['git','-C',str(self.repo),'cat-file','-s',blob]))==p['bytes'],'Whole original size drift')
        raw=subprocess.check_output(['git','-C',str(self.repo),'cat-file','blob',blob]);need(len(raw)==p['bytes'] and sha(raw)==p['sha256'],'Whole original encoded drift')
        if 'uncompressed_bytes' in p:
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as g:body=g.read(p['uncompressed_bytes']+1);need(not g.read(1),'Trailing decoded bytes')
            need(len(body)==p['uncompressed_bytes'] and sha(body)==p['uncompressed_sha256'],'Whole original decoded drift');raw=body
        self.reads.add(key);return raw
    def output(self,name,raw,compressed=False):
        need(re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}',name) and name!='publication.json' and name not in self.outputs,'Unique plain output name')
        need(type(raw) is bytes and len(raw)<=FILE,'Whole output ordinary cap')
        encoded=gzip.compress(raw,mtime=0) if compressed else raw;p={'path':name,'bytes':len(encoded),'sha256':sha(encoded)}
        if compressed:p.update(uncompressed_bytes=len(raw),uncompressed_sha256=sha(raw))
        need(sum(cost(p) for p,_ in self.outputs.values())+cost(p)<=self.reserve,'Complete actual output reserve')
        self.outputs[name]=(p,encoded)
    def finish(self,facts):
        need(self.reads==set(self.pins),'Declared actual code/data input not consumed')
        need(len(self.pins)+len(self.outputs)+1<=512,'Complete input/output descriptor bound')
        records=[dict(p,path=str((self.destination/name).relative_to(self.repo))) for name,(p,_) in self.outputs.items()]
        inventory=canonical({'version':1,'facts':facts,'inputs':list(self.pins.values()),'outputs':records,'input_encoded_decoded_bytes':self.input_cost,'output_encoded_decoded_bytes':sum(cost(p) for p,_ in self.outputs.values())})
        self.output('inventory.json.gz',inventory,True)
        records.append(dict(self.outputs['inventory.json.gz'][0],path=str((self.destination/'inventory.json.gz').relative_to(self.repo))))
        receipt=canonical({'version':1,'status':'complete','facts':facts,'inventory':records[-1],'output_descriptor_count':len(records),'complete_phase_bytes':self.input_cost+sum(cost(p) for p,_ in self.outputs.values())+RECEIPT})
        need(len(receipt)<=RECEIPT and len(self.pins)+len(self.outputs)+1<=512,'Complete final receipt bounds')
        ordinary(self.destination);need(not os.path.lexists(self.destination),'Output collision before publication')
        self.destination.mkdir()
        for name,(_,raw) in self.outputs.items():
            with (self.destination/name).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        for name,(pin,raw) in self.outputs.items():
            actual=(self.destination/name).read_bytes();need(actual==raw and sha(actual)==pin['sha256'],'Whole output readback drift')
        with (self.destination/'.publication-incomplete').open('xb') as f:f.write(receipt);f.flush();os.fsync(f.fileno())
        os.link(self.destination/'.publication-incomplete',self.destination/'publication.json');(self.destination/'.publication-incomplete').unlink()
        return json.loads(receipt)
