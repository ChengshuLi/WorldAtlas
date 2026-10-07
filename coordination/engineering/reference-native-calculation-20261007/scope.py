"""Complete sequential original-world and exact reviewed two-feature join."""
import gzip
import hashlib
import json

Q = 'coordination/engineering/eastern-two-gap-repair-20261007/'
TARGETS = frozenset(('atlas:physical:CAN-103:QUE', 'atlas:physical:CAN-114:NFL'))


def encoded(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()


def complete_world(inputs):
    index = inputs.json(Q+'input-index.json')
    aliases = [a for a in index['aliases'] if a['group']=='complete-current-world']
    paths = [a['original']['path'] for a in aliases]
    if len(paths)!=37 or len(set(paths))!=37 or 'data/world-index.json' not in paths:
        raise ValueError('Complete 37 original world aliases required')
    by_path = {a['original']['path']:a for a in aliases}
    manifest = json.loads(inputs.alias(Q,by_path['data/world-index.json']))
    if len(manifest['parts'])!=36 or len(set(manifest['parts']))!=36 or set(paths)!=set(['data/'+p for p in manifest['parts']]+['data/world-index.json']):
        raise ValueError('Every original world part must be present exactly once')
    from reader import gunzip, sha
    report=inputs.json(Q+'run-one/report.json')
    descriptors={p['path']:p for p in report['outputs']}
    if len(descriptors)!=len(report['outputs']):
        raise ValueError('Duplicate approved output descriptor')
    def accepted_output(name):
        pin=descriptors[name];raw=inputs.read(Q+'run-one/'+name)
        if len(raw)!=pin['bytes'] or sha(raw)!=pin['sha256']:
            raise ValueError('Approved output encoded binding drift')
        decoded=gunzip(raw,pin['decoded_bytes'])
        if sha(decoded)!=pin['decoded_sha256']:
            raise ValueError('Approved output decoded binding drift')
        return raw,decoded
    proposal_raw,decoded=accepted_output('proposed-part-29.json.gz')
    proposed=json.loads(decoded)
    replacement={f['id']:f for f in proposed['features']}
    if len(replacement)!=len(proposed['features']):
        raise ValueError('Duplicate proposed feature')
    crosswalk_raw,crosswalk_decoded=accepted_output('crosswalk.json.gz')
    crosswalk=json.loads(crosswalk_decoded)
    if report['counts']['world']!=49625 or report['counts']['changed']!=2 or report['counts']['unchanged']!=49623:
        raise ValueError('Approved complete geometry scope required')
    before_hash=report['before_footprints_sha256'];after_hash=report['after_footprints_sha256']
    if crosswalk['before_footprints_sha256']!=before_hash or crosswalk['after_footprints_sha256']!=after_hash:
        raise ValueError('Approved proposal/crosswalk footprint binding')
    changes=crosswalk.get('changed_ids')
    if not isinstance(changes,list) or len(changes)!=2 or set(changes)!=TARGETS:
        raise ValueError('Exact two approved targets required')
    seen=set();targets={};roster=[];hashes=[];proposed_part_seen=False
    for relative in manifest['parts']:
        raw=inputs.alias(Q,by_path['data/'+relative]);features=json.loads(raw)['features']
        after_raw=raw
        if relative=='geography/part-29.json':
            if {f['id'] for f in features}!=set(replacement):
                raise ValueError('Proposed complete part identity roster differs')
            after_raw=decoded;proposed_part_seen=True
        hashes.append(hashlib.sha256(after_raw).hexdigest())
        for f in features:
            id=f['id']
            if not isinstance(id,str) or id in seen or f['properties'].get('id',id)!=id or not f['geometry']:
                raise ValueError('Original whole world identity/pointset defect')
            seen.add(id);after=replacement[id] if relative=='geography/part-29.json' else f
            if id in TARGETS:
                if relative!='geography/part-29.json' or encoded({k:v for k,v in f.items() if k!='geometry'})!=encoded({k:v for k,v in after.items() if k!='geometry'}) or encoded(f['geometry'])==encoded(after['geometry']):
                    raise ValueError('Only approved existing geometry may change')
                targets[id]={'before':f['geometry'],'after':after['geometry']}
            elif encoded(after)!=encoded(f):
                raise ValueError('Every other full feature must remain unchanged')
            roster.append({'id':id,'original_feature_sha256':hashlib.sha256(encoded(f)).hexdigest(),
                           'after_feature_sha256':hashlib.sha256(encoded(after)).hexdigest(),
                           'original_geometry_sha256':hashlib.sha256(encoded(f['geometry'])).hexdigest(),
                           'after_geometry_sha256':hashlib.sha256(encoded(after['geometry'])).hexdigest()})
    if len(seen)!=49625 or set(targets)!=TARGETS or not proposed_part_seen:
        raise ValueError('Complete 49625 original/after scope required')
    if crosswalk.get('removed_ids')!=[] or crosswalk.get('added_ids')!=[] or set(crosswalk.get('reused_ids',[]))!=seen-TARGETS or len(crosswalk['reused_ids'])!=49623 or crosswalk.get('history_transfer') is not False or crosswalk.get('historical_claims_transferred') is not False:
        raise ValueError('Complete reused/identity/history crosswalk continuity')
    return {'ids':seen,'targets':targets,'roster':roster,'before_footprints_sha256':before_hash,
            'after_footprints_sha256':after_hash,'migration_receipt':crosswalk,
            'migration_receipt_sha256':hashlib.sha256(crosswalk_raw).hexdigest(),
            'after_geography_sha256':hashlib.sha256(''.join(hashes).encode()).hexdigest(),
            'full_footprint_hash_vintage':'accepted PR1317 exact original/proposed Node serialized-world proof; no fresh global numerical audit claimed'}
