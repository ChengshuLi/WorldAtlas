"""Restore five duplicated fields from complete ordinary original input bodies.

This targeted delivery adapter preserves the exact existing scientific bytes;
it does not rerun polygon comparisons or change coordinates/pointsets.
"""
import argparse,datetime,json,pathlib,re,subprocess,sys
import producer as p

HERE=pathlib.Path(__file__).resolve().parent
EXECUTION='104091cfecd9c83a53f3e6e62f95b0a0c8074351'
OWNED=p.OWNED
COMPONENT_FIELDS=('original_context','candidate_feature_sha256','candidate_geometry_sha256')
SOURCE_FIELDS=('record_sha256','coordinate_bytes_sha256')
COMPONENT_MARKER='complete_current_record_metadata_alias'
SOURCE_MARKER='complete_original_native_byte_hash_alias'
PATTERN=r'(components|sources|containers|retained-fragments|retained-contacts|retained-residues|lineage)-[0-9]{3}\.jsonl\.gz'

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def checked_path(path,repo,fresh=False):
    if not path.is_absolute() or '..' in path.parts or not path.resolve().is_relative_to(repo/'.cache'):
        raise ValueError('Require absolute owned-cache path')
    if fresh and path.exists():raise ValueError('Require fresh exclusive output')
    for part in (path,*path.parents):
        if part.is_symlink():raise ValueError('Symlink artefact path')
        if part==repo:break
    return path

def code_guard(repo,commit):
    if not re.fullmatch('[a-f0-9]{40}',commit) or p.git(repo,'rev-parse','HEAD').decode().strip()!=commit:
        raise ValueError('Exact current immutable transport commit required')
    closure=[]
    for name,selected in [('transport.py',commit)]+[(n,EXECUTION) for n in p.SCIENCE_FILES]:
        path=HERE/name
        if path.is_symlink() or not path.is_file():raise ValueError('Nonordinary executed dependency')
        raw=path.read_bytes()
        if raw!=p.git(repo,'show',selected+':'+OWNED+name):raise ValueError('Executed dependency changed')
        closure.append({'path':OWNED+name,'commit':selected,'bytes':len(raw),'sha256':p.digest(raw)})
    for module in (p,p.comparison,p.inputs,p.immutable,p.ellipsoidal_area):
        if pathlib.Path(module.__file__).resolve().parent!=HERE:raise ValueError('Imported dependency escaped')
    return closure

def descriptor(path,raw,decoded=None):
    value={'path':path,'bytes':len(raw),'sha256':p.digest(raw),'hash_kind':'file-bytes'}
    if decoded is not None:value.update(uncompressed_bytes=len(decoded),uncompressed_sha256=p.digest(decoded))
    return value

def original_bounds(desc):
    for key in ('bytes','uncompressed_bytes'):
        if type(desc.get(key)) is not int or not 0 <= desc[key] <= p.LIMIT:
            raise ValueError('Original scientific ordinary encoded/decoded bound')
    for key in ('sha256','uncompressed_sha256'):
        if re.fullmatch('[a-f0-9]{64}',desc.get(key,'')) is None:
            raise ValueError('Original scientific whole hash required')


def read_ordinary(directory,desc):
    original_bounds(desc)
    name=desc['path']
    if not re.fullmatch(PATTERN,name):raise ValueError('Unsafe/wrong scientific product name')
    path=directory/name
    if path.is_symlink() or not path.is_file():raise ValueError('Nonordinary/missing scientific product')
    raw=path.read_bytes();decoded=p.inputs.checked_decoded(raw,desc)
    return raw,decoded

class Context:
    def __init__(self,repo):
        config=json.loads((HERE/'input-config.json').read_bytes())
        current,lineage,receipts,reconstructor,audit=p.load_candidates(repo,config)
        self.components={}
        for row in current['components']:
            identity=row['id']
            if identity in self.components:raise ValueError('Duplicate current record')
            self.components[identity]=(row['properties'],p.digest(p.immutable.canonical_json(row)),p.digest(p.immutable.canonical_json(row['geometry'])))
        if len(self.components)!=95173:raise ValueError('Incomplete current record bijection')
        del current
        self.native=p.original_native(repo,config)
        self.native_rows={};offset=0;ordinal=0
        while offset<len(self.native):
            if offset+44>len(self.native):raise ValueError('Incomplete native original header')
            values=p.comparison.HEADER.unpack(self.native[offset:offset+44]);length=44+values[1]*8
            if offset+length>len(self.native) or values[0] in self.native_rows:raise ValueError('Incomplete/duplicate native original')
            self.native_rows[values[0]]=(offset,length,ordinal,list(values));offset+=length;ordinal+=1
        if offset!=len(self.native) or ordinal!=188612:raise ValueError('Incomplete native original bijection')
        self.receipts=receipts
        self.receipt={'complete_current_records':len(self.components),'complete_native_records':len(self.native_rows),'original_native_member_bytes':len(self.native),'original_native_member_sha256':p.digest(self.native),'input_receipts':receipts,'reconstruction':reconstructor}
    def component(self,row):
        identity=row['component_id']
        if identity not in self.components:raise ValueError('Wrong/missing current component')
        context,feature,geometry=self.components[identity]
        return dict(original_context=context,candidate_feature_sha256=feature,candidate_geometry_sha256=geometry)
    def source(self,row):
        identity=row['id']
        if type(identity)is not int or identity not in self.native_rows:raise ValueError('Wrong native source identity')
        offset,length,ordinal,values=self.native_rows[identity]
        if any(type(row.get(k))is not int for k in ('native_offset','native_record_bytes','ordinal','n')):
            raise ValueError('Noninteger original native position')
        if (row['native_offset'],row['native_record_bytes'],row['ordinal'],row['n'])!=(offset,length,ordinal,values[1]):
            raise ValueError('Wrong native byte position/size/ordinal')
        if p.immutable.canonical_json(row['header_native_values'])!=p.immutable.canonical_json(values):
            raise ValueError('Wrong whole original native header')
        return dict(record_sha256=p.digest(self.native[offset:offset+length]),coordinate_bytes_sha256=p.digest(self.native[offset+44:offset+length]))

def pack_row(row,kind,context):
    row=dict(row)
    if COMPONENT_MARKER in row or SOURCE_MARKER in row:raise ValueError('Already aliased/wrong product')
    fields=context.component(row) if kind=='components' else context.source(row) if kind=='sources' else None
    if fields is not None:
        for key,value in fields.items():
            if p.immutable.canonical_json(row.get(key))!=p.immutable.canonical_json(value):raise ValueError('Scientific duplicate field differs from full original')
            del row[key]
        row[COMPONENT_MARKER if kind=='components' else SOURCE_MARKER]='v1'
    return row

def restore_row(row,kind,context):
    row=dict(row)
    if kind in ('components','sources'):
        marker=COMPONENT_MARKER if kind=='components' else SOURCE_MARKER
        other=SOURCE_MARKER if kind=='components' else COMPONENT_MARKER
        fields=COMPONENT_FIELDS if kind=='components' else SOURCE_FIELDS
        if row.get(marker)!='v1' or other in row or any(k in row for k in fields):raise ValueError('Wrong/extra/missing alias product fields')
        del row[marker]
        row.update(context.component(row) if kind=='components' else context.source(row))
    elif COMPONENT_MARKER in row or SOURCE_MARKER in row:raise ValueError('Wrong alias product kind')
    return row

def exact_restore(encoded,packed_desc,original,kind,context):
    original_bounds(original)
    raw=p.inputs.checked_decoded(encoded,packed_desc)
    rows=[restore_row(json.loads(line),kind,context) for line in raw.splitlines()]
    restored=b''.join(p.immutable.canonical_json(r) for r in rows)
    if len(restored)>p.LIMIT:raise ValueError('Actual original scientific decoded bound')
    if len(restored)!=original['uncompressed_bytes'] or p.digest(restored)!=original['uncompressed_sha256']:
        raise ValueError('Restored whole scientific decoded bytes differ')
    body=p.immutable.deterministic_gzip(restored)
    if len(body)>p.LIMIT:raise ValueError('Actual original scientific encoded bound')
    if len(body)!=original['bytes'] or p.digest(body)!=original['sha256']:raise ValueError('Restored whole scientific encoded bytes differ')
    return body,rows

def pack(source,out,context):
    report_raw=(source/'report.json').read_bytes();report=json.loads(report_raw)
    if report['execution_commit']!=EXECUTION or report['component_count']!=95173 or report['source_record_count']!=188612:
        raise ValueError('Wrong/incomplete scientific family')
    if report['input_receipts']!=context.receipts:raise ValueError('Scientific ordinary input receipts differ')
    original=report['products']
    if len({d['path']for d in original})!=len(original):raise ValueError('Duplicate scientific product')
    if {x.name for x in source.iterdir()}!={d['path']for d in original}|{'report.json'}:raise ValueError('Extra/missing scientific family file')
    out.mkdir(parents=True,exist_ok=False)
    entries=[];seen_components=set();seen_sources=set()
    for old in original:
        body,raw=read_ordinary(source,old);kind=re.fullmatch(PATTERN,old['path']).group(1)
        rows=[json.loads(line) for line in raw.splitlines()]
        for row in rows:
            if kind in ('components','sources'):
                identity=row['component_id'] if kind=='components' else row['id'];seen=seen_components if kind=='components' else seen_sources
                if identity in seen:raise ValueError('Duplicate scientific alias record')
                seen.add(identity)
        packed_rows=[pack_row(row,kind,context)for row in rows]
        decoded=b''.join(p.immutable.canonical_json(r)for r in packed_rows);packed=p.immutable.deterministic_gzip(decoded)
        d=descriptor(old['path'],packed,decoded)
        restored,_=exact_restore(packed,d,old,kind,context)
        if restored!=body:raise ValueError('Actual original scientific body restoration differs')
        with (out/old['path']).open('xb')as stream:stream.write(packed)
        entries.append({'kind':kind,'original':old,'delivered':d})
    if seen_components!=set(context.components) or seen_sources!=set(context.native_rows):raise ValueError('Incomplete whole alias bijection')
    with (out/'report.json').open('xb')as stream:stream.write(report_raw)
    mapping={'version':1,'scientific_execution':EXECUTION,'meaning':'Five duplicate fields restored from complete ordinary original/current bodies; no changed scientific values or geometry calculations.','scientific_report':descriptor('report.json',report_raw),'complete_components':len(seen_components),'complete_sources':len(seen_sources),'entries':entries}
    with (out/'transport-map.json').open('xb')as stream:stream.write(p.immutable.canonical_json(mapping))
    return {'entries':entries,'original_encoded':sum(d['bytes']for d in original),'delivered_encoded':sum(e['delivered']['bytes']for e in entries),'complete_components':len(seen_components),'complete_sources':len(seen_sources)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--transport-commit',required=True);parser.add_argument('--source',type=pathlib.Path,required=True);parser.add_argument('--out',type=pathlib.Path,required=True);parser.add_argument('--receipt',type=pathlib.Path,required=True);args=parser.parse_args()
    repo=HERE.parents[2];closure=code_guard(repo,args.transport_commit)
    for path,fresh in ((args.source,False),(args.out,True),(args.receipt,True)):checked_path(path,repo,fresh)
    started=utc();context=Context(repo);result=pack(args.source,args.out,context)
    receipt={'result':'PASS','mode':'Actual complete lossless five-field transport and full original scientific byte restoration; no world comparison regeneration','command':sys.argv,'started_utc':started,'finished_utc':utc(),'transport_commit':args.transport_commit,'code':closure,'original_inputs':context.receipt,**result}
    with args.receipt.open('xb')as stream:stream.write(p.immutable.canonical_json(receipt))
    print(json.dumps({k:v for k,v in receipt.items()if k not in ('entries','original_inputs','code')}))
if __name__=='__main__':main()
