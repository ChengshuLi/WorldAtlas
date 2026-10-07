"""Complete ordinary custody and scoped original-row restoration for issue1300."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'legacy'))
import producer as old
import transport

LIMIT=33554432
ROUTING='coordination/engineering/global-actionability-routing-20261007/results/'
PHYSICAL='coordination/engineering/global-physical-comparison-20261006/'

def canonical(value):
    return old.immutable.canonical_json(value)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def safe_path(root,name):
    old.inputs.safe_path(name)
    path=root/name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Input escaped owned root')
    for part in (path,*path.parents):
        if part.is_symlink():raise ValueError('Input symlink')
        if part==root:break
    if not path.is_file():raise ValueError('Input must be ordinary file')
    return path

def checked(root,pin):
    raw=safe_path(root,pin['path']).read_bytes()
    return old.inputs.checked_decoded(raw,pin)

def scope_rosters(scope):
    selected={row['component']:row for row in scope['rows']}
    complement=set(scope['complement_ids'])
    if len(selected)!=26276 or len(scope['rows'])!=26276 or len(complement)!=68897 or len(scope['complement_ids'])!=68897 or selected.keys()&complement:
        raise ValueError('Incomplete/duplicate numeric scope or complement')
    if len({row['family'] for row in selected.values()})!=3503 or len({row['operational_batch'] for row in selected.values()})!=253:
        raise ValueError('Incomplete numeric family/batch scope')
    return selected,complement

def routing_alias(row,line,ordinal,expected):
    if expected['actual_routing_row_ordinal']!=ordinal or expected['actual_routing_row_sha256']!=digest(line+b'\n'):
        raise ValueError('Changed complete routing row alias')
    if any(row[key]!=expected[key] for key in ('current_feature_sha256','current_geometry_sha256','whole_physical_row_sha256','family','operational_batch')):
        raise ValueError('Scope routing metadata differs')

def current_feature(feature,row):
    if digest(canonical(feature))!=row['current_feature_sha256'] or digest(canonical(feature['geometry']))!=row['current_geometry_sha256']:
        raise ValueError('Changed whole current candidate feature/pointset')

def physical_roster(seen,state):
    if len(seen)!=95173 or seen!=set(state['context'].components):
        raise ValueError('Complete physical/current/complement bijection differs')

class ComponentContext:
    """Only component restoration; never instantiate source/native Context."""
    def __init__(self,features):
        self.components={}
        for row in features:
            identity=row['id']
            if identity in self.components:raise ValueError('Duplicate complete current component')
            self.components[identity]=(row['properties'],digest(canonical(row)),digest(canonical(row['geometry'])))
        if len(self.components)!=95173:raise ValueError('Incomplete current whole roster')
    component=transport.Context.component

def load(repo):
    index=json.loads((HERE/'input-index.json').read_bytes())
    if index['actual_merge']!='0198938719a5666b6726fb6a1e45779926eefeb2':
        raise ValueError('Wrong actual merged routing vintage')
    pins=index['files'];names=[x['path'] for x in pins]
    if len(names)!=179 or len(set(names))!=179 or sum(x['bytes'] for x in pins)!=182875702:
        raise ValueError('Incomplete complete input-index roster')
    originals={x['original_path']:x for x in pins if 'original_path' in x}
    if len(originals)!=178:raise ValueError('Duplicate original input body alias')
    receipts=[]
    for pin in pins:
        decoded=checked(HERE,pin)
        if 'original_path' in pin:
            encoded=old.inputs.ordinary_git(repo,pin['original_commit'],pin['original_path'],pin)
            if encoded!=safe_path(HERE,pin['path']).read_bytes():raise ValueError('Immutable containing input alias differs')
        receipts.append(dict(pin,actual_decoded_bytes=len(decoded),actual_decoded_sha256=digest(decoded)))
    scope=json.loads(checked(HERE,next(x for x in pins if x['path']=='scope.json.gz')))
    if scope['routing_source']['actual_merge']!=index['actual_merge']:
        raise ValueError('Scope vintage differs')
    selected,complement=scope_rosters(scope)
    report=json.loads(checked(HERE,originals[ROUTING+'report.json']))
    routing={};pending=b'';whole=hashlib.sha256();count=0;last=''
    entry=next(x for x in report['complete_whole_raw_bodies'] if x['name']=='components')
    if len(entry['parts'])!=25:raise ValueError('Incomplete whole routing stream')
    for pin in entry['parts']:
        actual=originals[ROUTING+pin['path']]
        if any(actual[k]!=pin[k] for k in ('bytes','sha256','uncompressed_bytes','uncompressed_sha256')):
            raise ValueError('Routing report part pin differs')
        decoded=checked(HERE,actual);whole.update(decoded)
        lines=(pending+decoded).split(b'\n');pending=lines.pop()
        for line in lines:
            row=json.loads(line);identity=row['component']
            if identity<=last:raise ValueError('Unsorted/duplicate whole routing roster')
            last=identity
            if row['next_prerequisite']=='engineering-numeric-closure-first':
                if identity not in selected:raise ValueError('Omitted numeric component')
                expected=selected[identity]
                routing_alias(row,line,count,expected)
                routing[identity]=row
            elif identity not in complement:raise ValueError('Omitted complement')
            count+=1
    if pending or count!=95173 or len(routing)!=26276 or whole.hexdigest()!=entry['sha256']:
        raise ValueError('Incomplete whole delivered routing bytes/roster')
    if len({r['family'] for r in routing.values()})!=3503 or len({r['operational_batch'] for r in routing.values()})!=253:
        raise ValueError('Incomplete numeric family/batch roster')
    original_config=json.loads((HERE/'legacy/input-config.json').read_bytes())
    derived=dict(original_config,inputs=[row for row in original_config['inputs'] if row['kind']!='archive_part'])
    if len(original_config['inputs'])!=44 or len(derived['inputs'])!=40:
        raise ValueError('Wrong original/derived component-only source view')
    current,lineage,source_receipts,reconstructor,audit=old.load_candidates(repo,derived)
    consumed={(x['sha256'],x['bytes']) for x in pins}
    if any((x['sha256'],x['bytes']) not in consumed for x in source_receipts):
        raise ValueError('Actual original candidate loader consumed undeclared whole body')
    context=ComponentContext(current['components'])
    candidates={row['id']:row for row in current['components'] if row['id'] in selected}
    if len(candidates)!=26276 or set(context.components)!=set(selected)|complement:
        raise ValueError('Current candidate roster differs from full routing')
    for identity,row in routing.items():
        feature=candidates[identity]
        current_feature(feature,row)
    del current
    physical_report=json.loads(checked(HERE,originals[PHYSICAL+'results/report.json']))
    return dict(index=index,originals=originals,scope=scope,routing=routing,candidates=candidates,
                context=context,receipts=receipts,reconstructor=reconstructor,audit=audit,lineage=lineage,
                physical_report=physical_report,
                original_config_sha256=digest(canonical(original_config)),
                derived_component_only_config_sha256=digest(canonical(derived)),source_receipts=source_receipts)

def physical_rows(state):
    seen=set()
    state['physical_restore_receipts']=[]
    originals=state['originals']
    original_products={pin['path']:pin for pin in state['physical_report']['products']}
    names=sorted(path for path in originals if path.startswith(PHYSICAL+'results/components-') and path.endswith('.jsonl.gz'))
    if len(names)!=71:raise ValueError('Incomplete71 whole physical scientific shards')
    for path in names:
        pin=originals[path]
        original=original_products[path.rsplit('/',1)[-1]]
        transport.original_bounds(original)
        decoded=checked(HERE,pin)
        restored_body=bytearray()
        for ordinal,line in enumerate(decoded.splitlines()):
            row=json.loads(line)
            identity=row['component_id']
            if identity in seen:raise ValueError('Duplicate full physical component')
            seen.add(identity)
            restored=transport.restore_row(row,'components',state['context'])
            restored_row=canonical(restored)
            if len(restored_body)+len(restored_row)>LIMIT:
                raise ValueError('Actual original104 restored ordinary body bound')
            restored_body.extend(restored_row)
            if identity not in state['routing']:continue
            routing=state['routing'][identity]
            packed_sha=digest(canonical(row))
            if routing['whole_physical_containing_file']!=path or packed_sha!=routing['whole_physical_row_sha256']:
                raise ValueError('Whole delivered packed scientific row binding differs')
            yield identity,restored,dict(path=pin['path'],original_path=path,row_ordinal=ordinal,
                whole_delivered_packed_row_sha256=packed_sha,
                packed_row_hash_domain='complete-delivered-packed-canonical-row',
                restored_whole_row_sha256=digest(canonical(restored)),
                restored_row_hash_domain='original104-scientific-row-with-current-context-fields-restored',
                complete_current_feature_sha256=routing['current_feature_sha256'])
        if len(restored_body)!=original['uncompressed_bytes'] or digest(restored_body)!=original['uncompressed_sha256']:
            raise ValueError('Whole original104 restored scientific file differs')
        encoded=old.immutable.deterministic_gzip(bytes(restored_body))
        if len(encoded)!=original['bytes'] or digest(encoded)!=original['sha256']:
            raise ValueError('Whole original104 restored encoded scientific file differs')
        state['physical_restore_receipts'].append(dict(original,complete_original_row_restoration=True,
            actual_restored_encoded_bytes=len(encoded),actual_restored_encoded_sha256=digest(encoded),
            actual_restored_decoded_bytes=len(restored_body),actual_restored_decoded_sha256=digest(restored_body)))
    physical_roster(seen,state)
