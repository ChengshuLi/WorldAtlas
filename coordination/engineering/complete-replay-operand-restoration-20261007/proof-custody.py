"""1394 complete campaign proof byte custody and explicit original-path inverse.

Only an explicit frozen campaign-proof roster is accepted. Whole original encoded
bytes are retained in bounded base64 JSONL gzip groups. No absolute historical
path is rewritten: restoration emits a separate original-to-fresh-path mapping.
All functions run inside a caller-created, prospectively admitted actual Phase.
The caller freezes this code, supplies the actual runtime/project closure and
runs one group per detached process. No science or source acquisition occurs.
"""
import base64
import gzip
import json
import os
from pathlib import Path
import re
import stat
import subprocess

OWNED = 'coordination/engineering/complete-replay-operand-restoration-20261007/'
ROLES = {'publication', 'inventory', 'control', 'actual-report', 'history', 'freeze',
         'plan', 'execution-log', 'logical-index'}
CHUNK = 1048576
SHARD = 8388608


def need(ok, message):
    if not ok:
        raise ValueError(message)


def unique(pins, acq):
    result = {}
    for pin in pins:
        key = acq.Phase.key(pin)
        need(key not in result or result[key] == pin, 'Conflicting whole proof descriptor')
        result[key] = pin
    return list(result.values())


def roster(body, acq):
    value = json.loads(body)
    need(value.get('kind') == 'complete1394-campaign-proof-roster' and value.get('version') == 1 and
         value.get('issue') == 1394, 'Explicit original1394 campaign proof roster required')
    need(re.fullmatch('[a-f0-9]{40}', value.get('execution_commit', '')) is not None,
         'Frozen proof packer execution vintage required')
    files = value['files']; logical = set(); physical = set(); membership = {}
    need(type(files) is list and files, 'Empty actual campaign proof roster')
    for ordinal, row in enumerate(files):
        need(row['ordinal'] == ordinal and type(row['ordinal']) is int, 'Noncontiguous proof roster ordinal')
        name = row['original_logical_path']; pin = row['file']
        need(type(name) is str and name and '\\' not in name and
             all(p not in ('', '.', '..') for p in (name.split('/')[1:] if name.startswith('/') else name.split('/'))) and
             '..' not in Path(name).parts and name not in logical, 'Unsafe/duplicate original logical proof path')
        need(row['role'] in ROLES and row['mode'] in (0o644, 0o755) and type(row['mode']) is int and
             re.fullmatch('[a-f0-9]{40}', row['execution_commit']) is not None,
             'Missing role/mode/exact original execution vintage')
        acq.bounds(pin)
        key = acq.Phase.key(pin)
        need(key not in physical and row.get('source_relation') == {'kind':'whole-campaign-proof-file', 'pin':pin},
             'Duplicate proof body or missing complete original source relation')
        need(name == pin['path'], 'Original logical path must equal actual original whole path')
        logical.add(name); physical.add(key)
        if row['role'] in ('publication', 'inventory'):
            stage = row.get('stage_id')
            need(type(stage) is str and stage and '/' not in stage and '..' not in stage,
                 'Original stage proof membership required')
            need(row['role'] not in membership.setdefault(stage, set()), 'Duplicate stage proof role')
            membership[stage].add(row['role'])
    stages = value['required_stage_ids']
    need(type(stages) is list and stages == sorted(set(stages)) and
         set(membership) == set(stages) and all(v == {'publication','inventory'} for v in membership.values()),
         'Mandatory complete stage publication/inventory roster omitted')
    return value



def checked_read(phase,pin,acq):
    if not pin.get('commit') and 'mode' in pin:
        path=acq.ordinary(pin['path']);info=path.lstat()
        need(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and
             stat.S_IMODE(info.st_mode)==pin['mode'],'Actual custody input mode/link drift')
    return phase.read(pin)


def completed(phase,pair,acq):
    for pin in pair:
        if not pin.get('commit') and 'mode' in pin:
            path=acq.ordinary(pin['path']);info=path.lstat()
            need(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and
                 stat.S_IMODE(info.st_mode)==pin['mode'],'Custody completion mode/link drift')
    return acq.completed_inventory(phase,*pair)


def pack_inputs(group,roster_pin,codec_pin,plan_pin,plan_pair,acq):
    return unique([*group['input_descriptors'],roster_pin,codec_pin,plan_pin,*plan_pair],acq)


def restore_inputs(roster_pin,codec_pin,index_pin,pack_pair,transport_pins,acq):
    return unique([roster_pin,codec_pin,index_pin,*pack_pair,*transport_pins],acq)


def restore_reserve(original_rows,acq):
    return sum(acq.cost(r['file']) for r in original_rows)+4*len(acq.canonical(original_rows))+1048576


def join_inputs(roster_pin,codec_pin,plan_pin,plan_pair,pack_pairs,index_pins,acq):
    return unique([roster_pin,codec_pin,plan_pin,*plan_pair,*index_pins,
                   *[p for pair in pack_pairs for p in pair]],acq)


def binding(phase, roster_pin, codec_pin, acq):
    raw = checked_read(phase,roster_pin,acq); value = roster(raw, acq)
    code = checked_read(phase,codec_pin,acq)
    need(Path(codec_pin['path']).name == 'proof-custody.py' and value['codec_pin'] == codec_pin and
         code == Path(__file__).read_bytes() and
         (not codec_pin.get('commit') or codec_pin['commit']==value['execution_commit']),
         'Frozen actual proof inverse source/code binding differs')
    return raw, value


def budget(rows, fixed_pins, *, runtime_bytes, acq):
    """Conservative transport + logical index + inventory reserve, before reads."""
    need(type(runtime_bytes) is int and runtime_bytes>0 and rows, 'Actual positive proof runtime/group accounting required')
    originals = [r['file'] for r in rows]
    inputs = unique([*fixed_pins, *originals], acq)
    metadata = len(acq.canonical(rows))
    # Base64 <=4*ceil(n/3); both opaque output gzip and its consumed decoded body
    # are bounded above by twice the JSONL size, plus compression framing/slack.
    encoded = sum(p['bytes'] for p in originals)
    chunks = sum(max(1, (p['bytes']+CHUNK-1)//CHUNK) for p in originals)
    transport = 4*((encoded+2*len(rows)+2)//3)+chunks*512
    reserve = 2*transport+4*metadata+1048576
    total = sum(acq.cost(p) for p in inputs)+runtime_bytes+reserve+acq.RECEIPT
    # Worst case one transport shard per chunk, plus index/inventory/publication.
    need(len(inputs)+chunks+3 <= 512 and total <= acq.PHASE,
         'Complete proof input/runtime/transport/index phase cannot fit')
    return {'input_descriptors':inputs, 'output_reserve':reserve, 'prospective_phase_bytes':total}


def plan_groups(phase, *, roster_pin, codec_pin, project_pins, runtime_bytes, acq, before_finish):
    need(runtime_bytes==phase.runtime_bytes,'Proof planning runtime differs from actual admitted Phase')
    _, value = binding(phase, roster_pin, codec_pin, acq)
    fixed = unique([roster_pin,codec_pin,*project_pins], acq)
    groups=[]; current=[]
    for row in value['files']:
        try:
            proposed=budget([*current,row],fixed,runtime_bytes=runtime_bytes,acq=acq)
        except ValueError:
            need(current, 'One whole original proof cannot fit custody Phase')
            admitted=budget(current,fixed,runtime_bytes=runtime_bytes,acq=acq)
            groups.append({'ordinal':len(groups),'file_ordinals':[r['ordinal'] for r in current],**admitted})
            current=[row]; budget(current,fixed,runtime_bytes=runtime_bytes,acq=acq)
        else:
            current.append(row)
    if current:
        groups.append({'ordinal':len(groups),'file_ordinals':[r['ordinal'] for r in current],
                       **budget(current,fixed,runtime_bytes=runtime_bytes,acq=acq)})
    plan={'kind':'complete1394-campaign-proof-custody-plan','version':1,'issue':1394,
          'roster_pin':roster_pin,'codec_pin':codec_pin,'logical_files':len(value['files']),
          'required_stage_ids':value['required_stage_ids'],'runtime_bytes':runtime_bytes,'groups':groups}
    phase.output('proof-custody-plan.json.gz',acq.canonical(plan),compress=True)
    before_finish()
    return finish_modes(phase,{'operation':'complete1394-proof-custody-plan','logical_files':len(value['files']),
                              'groups':len(groups)}, {},acq)


def original_encoded(phase, row, acq):
    """One actual whole read; original decoded bytes independently verified too."""
    pin=row['file'];key=acq.Phase.key(pin)
    need(phase.pins.get(key)==pin,'Undeclared changed whole original proof')
    if pin.get('commit'):
        need(re.fullmatch('[a-f0-9]{40}',pin['commit']) is not None and not pin['path'].startswith('/') and
             all(p not in ('','.','..') for p in pin['path'].split('/')),'Unsafe original proof Git source')
        actual=subprocess.check_output(['git','-C',str(phase.repo),'ls-tree','-z',pin['commit'],'--',pin['path']]).decode().rstrip('\0')
        need('\t' in actual,'Missing original whole proof')
        meta,name=actual.split('\t');mode,kind,blob=meta.split()
        need(name==pin['path'] and kind=='blob' and mode in ('100644','100755') and
             int(mode[-3:],8)==row['mode'] and pin.get('mode',mode)==mode and pin.get('blob',blob)==blob,
             'Changed original proof Git mode/body relation')
        need(int(subprocess.check_output(['git','-C',str(phase.repo),'cat-file','-s',blob]))==pin['bytes'],
             'Original encoded proof size drift')
        raw=subprocess.check_output(['git','-C',str(phase.repo),'cat-file','blob',blob])
    else:
        path=acq.ordinary(pin['path'])
        need(path.is_relative_to(phase.repo/'.cache'),'Proof source outside owned campaign storage')
        info=path.lstat()
        need(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and stat.S_IMODE(info.st_mode)==row['mode'] and
             info.st_size==pin['bytes'],'Original proof ordinary mode/size/link drift')
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            current=os.fstat(fd)
            need((current.st_dev,current.st_ino,current.st_size,current.st_mode)==
                 (info.st_dev,info.st_ino,info.st_size,info.st_mode),'Proof source changed before whole read')
            with os.fdopen(fd,'rb',closefd=False) as stream: raw=stream.read(pin['bytes']+1)
            after=os.fstat(fd)
            need((after.st_size,after.st_mtime_ns,after.st_ctime_ns)==
                 (current.st_size,current.st_mtime_ns,current.st_ctime_ns),'Proof source drifted during whole read')
        finally:os.close(fd)
    decoded=acq.decode(raw,pin)
    del decoded
    phase.reads.add(key)
    return raw


def finish_modes(phase,facts,modes,acq):
    """Phase's same complete boundary, with exact modes BEFORE publication."""
    need(phase.reads==set(phase.pins),'Declared whole proof input was not actually consumed')
    for name,(pin,raw) in phase.payloads.items():pin['mode']=modes.get(name,0o644)
    pins=[p for p,_ in phase.payloads.values()]
    need(len(phase.pins)+len(pins)+2<=512,'Proof inventory/publication descriptor bound')
    inventory={'version':1,'kind':'bounded-original-acquisition-stage','facts':facts,
               'input_descriptors':list(phase.pins.values()),'outputs':pins,
               'input_encoded_decoded_bytes':phase.input_bytes,'runtime_bytes':phase.runtime_bytes,
               'output_encoded_decoded_bytes':sum(acq.cost(p) for p in pins),
               'complete_phase_bytes':phase.input_bytes+phase.runtime_bytes+sum(acq.cost(p) for p in pins)}
    phase.output('stage-inventory.json.gz',acq.canonical(inventory),compress=True)
    phase.payloads['stage-inventory.json.gz'][0]['mode']=0o644
    receipt={'version':1,'inventory':phase.payloads['stage-inventory.json.gz'][0],
             'complete_phase_bytes':phase.input_bytes+phase.runtime_bytes+
                  sum(acq.cost(p) for p,_ in phase.payloads.values())+acq.RECEIPT,'complete':True}
    raw_receipt=acq.canonical(receipt)
    need(len(raw_receipt)<=acq.RECEIPT and receipt['complete_phase_bytes']<=acq.PHASE and
         len(phase.pins)+len(phase.payloads)+1<=512,'Complete proof publication bound')
    phase.destination.mkdir(exist_ok=False)
    for name,(pin,raw) in phase.payloads.items():
        path=phase.destination/name
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,pin['mode'])
        try:
            os.fchmod(fd,pin['mode'])
            with os.fdopen(fd,'wb',closefd=False) as stream:stream.write(raw);stream.flush()
        finally:os.close(fd)
        need(path.read_bytes()==raw and stat.S_IMODE(path.stat().st_mode)==pin['mode'],
             'Whole proof output byte/mode readback differs')
    with (phase.destination/'publication.json').open('xb') as stream:stream.write(raw_receipt)
    os.chmod(phase.destination/'publication.json',0o644)
    phase.payloads.clear()
    return receipt


def pack_group(phase, *, roster_pin,codec_pin,plan_pin,plan_pair,group_ordinal,acq,before_finish):
    _,value=binding(phase,roster_pin,codec_pin,acq)
    inv=completed(phase,plan_pair,acq)
    need(inv['facts']['operation']=='complete1394-proof-custody-plan' and plan_pin in inv['outputs'],
         'Unaccepted whole proof custody plan')
    plan=json.loads(checked_read(phase,plan_pin,acq))
    need(plan['roster_pin']==roster_pin and plan['codec_pin']==codec_pin and
         type(group_ordinal) is int and 0<=group_ordinal<len(plan['groups']),'Foreign proof packing group')
    group=plan['groups'][group_ordinal]
    need(group['ordinal']==group_ordinal,'Changed complete proof group order')
    need(group['file_ordinals']==sorted(set(group['file_ordinals'])) and group['file_ordinals'] and
         all(type(n) is int and 0<=n<len(value['files']) for n in group['file_ordinals']),
         'Duplicate/foreign original proof group ordinal')
    selected=[value['files'][n] for n in group['file_ordinals']]
    need(phase.reserve>=group['output_reserve'],'Actual proof outputs lack prospective planned reserve')
    entries=[];buffer=bytearray();pending=[];transports=[]
    def flush():
        if not buffer:return
        pin=phase.output(f'proof-transport-{len(transports):03}.jsonl.gz',bytes(buffer),compress=True)
        pin['mode']=0o644
        for entry,part in pending:part['transport_pin']=pin;entry['parts'].append(part)
        transports.append(pin);buffer.clear();pending.clear()
    for row in selected:
        raw=original_encoded(phase,row,acq)
        entry={'original':row,'parts':[]};entries.append(entry)
        for offset in range(0,max(1,len(raw)),CHUNK):
            chunk=raw[offset:offset+CHUNK]
            record={'file_ordinal':row['ordinal'],'offset':offset,'bytes':len(chunk),
                    'sha256':acq.sha(chunk),'encoded_base64':base64.b64encode(chunk).decode('ascii')}
            line=acq.canonical(record)
            if buffer and len(buffer)+len(line)>SHARD:flush()
            part={'transport_row_ordinal':len(pending),'offset':offset,'bytes':len(chunk),'sha256':acq.sha(chunk)}
            buffer.extend(line);pending.append((entry,part))
        del raw
    flush()
    index={'kind':'complete1394-whole-proof-containing-index','version':1,'issue':1394,
           'execution_commit':value['execution_commit'],'roster_pin':roster_pin,'codec_pin':codec_pin,
           'plan_pin':plan_pin,'group_ordinal':group_ordinal,'transports':transports,'files':entries}
    phase.output('logical-proof-files.json.gz',acq.canonical(index),compress=True)
    before_finish()
    return finish_modes(phase,{'operation':'complete1394-whole-proof-custody-group','group_ordinal':group_ordinal,
                              'logical_files':len(entries),'original_encoded_bytes':sum(r['file']['bytes'] for r in selected),
                              'original_consumed_decoded_bytes':sum(r['file'].get('uncompressed_bytes',0) for r in selected)}, {},acq)


def restore_group(phase, *, roster_pin,codec_pin,index_pin,pack_pair,transport_pins,acq,before_finish):
    _,value=binding(phase,roster_pin,codec_pin,acq)
    inv=completed(phase,pack_pair,acq)
    need(inv['facts']['operation']=='complete1394-whole-proof-custody-group' and index_pin in inv['outputs'],
         'Unaccepted whole proof inverse containing index')
    index=json.loads(checked_read(phase,index_pin,acq))
    need(index['kind']=='complete1394-whole-proof-containing-index' and index['roster_pin']==roster_pin and
         index['codec_pin']==codec_pin and index['execution_commit']==value['execution_commit'] and
         transport_pins==index['transports'] and transport_pins==[p for p in inv['outputs']
                     if Path(p['path']).name.startswith('proof-transport-')], 'Omitted/foreign whole opaque proof transport')
    rows={};used=set();modes={};mapping=[]
    for pin in transport_pins:
        body=checked_read(phase,pin,acq)
        lines=[]
        for line in body.splitlines(keepends=True):
            row=json.loads(line)
            need(acq.canonical(row)==line,'Noncanonical whole proof transport row')
            lines.append(row)
        rows[pin['path']]=lines
    seen=set()
    for entry in index['files']:
        original=entry['original'];ordinal=original['ordinal']
        need(type(ordinal) is int and 0<=ordinal<len(value['files']) and original==value['files'][ordinal] and
             ordinal not in seen,'Changed/duplicate logical proof inverse source')
        seen.add(ordinal);encoded=bytearray()
        for part in entry['parts']:
            pin=part['transport_pin'];key=(pin['path'],part['transport_row_ordinal'])
            need(type(part['transport_row_ordinal']) is int and
                 0<=part['transport_row_ordinal']<len(rows.get(pin['path'],[])) and
                 pin in transport_pins and key not in used and part['offset']==len(encoded),
                 'Duplicate/foreign/reordered whole proof encoded chunk')
            record=rows[pin['path']][part['transport_row_ordinal']]
            need(record['file_ordinal']==ordinal and all(record[k]==part[k] for k in ('offset','bytes','sha256')),
                 'Changed proof inverse chunk coordinates')
            chunk=base64.b64decode(record['encoded_base64'],validate=True)
            need(len(chunk)==part['bytes'] and acq.sha(chunk)==part['sha256'],'Changed whole proof chunk bytes')
            encoded.extend(chunk);used.add(key)
        raw=bytes(encoded);decoded=acq.decode(raw,original['file'])
        name=f'restored-proof-{ordinal:06}.bin'
        output=phase.output(name,decoded,compress='uncompressed_bytes' in original['file'],
                            encoded=raw if 'uncompressed_bytes' in original['file'] else None)
        modes[name]=original['mode'];output['mode']=original['mode']
        mapping.append({'kind':'explicit-whole-original-proof-restoration','original_logical_path':original['original_logical_path'],
                        'original_execution_commit':original['execution_commit'],'original_mode':original['mode'],
                        'original_file':original['file'],'restored_file':output,'role':original['role']})
        del raw,decoded,encoded
    need(len(used)==sum(len(v) for v in rows.values()),'Opaque proof transport contains omitted/unmapped bytes')
    need(len(mapping)==inv['facts']['logical_files'],'Omitted logical proof inverse file')
    phase.output('original-to-restored.json.gz',acq.canonical({'kind':'complete1394-explicit-proof-restoration-map',
                 'original_paths_rewritten':False,'roster_pin':roster_pin,'codec_pin':codec_pin,
                 'original_containing_index':index_pin,'original_pack_publication':pack_pair[0],
                 'original_pack_inventory':pack_pair[1],'mapping':mapping}),compress=True)
    before_finish()
    return finish_modes(phase,{'operation':'complete1394-whole-proof-byte-restoration','logical_files':len(mapping),
                              'original_paths_rewritten':False},modes,acq)



def inverse_read(phase, *, original_pin,restored_pin,mapping_pin,restoration_pair,codec_pin,acq,encoded=False):
    """Typed whole-file read. Declare ALL arguments in Phase before calling.

    Historical JSON and its absolute descriptor references remain exact bytes.
    This explicit mapping is a separate physical location relation; no original
    descriptor is silently rewritten and no original hash stands in for a body.
    """
    code=checked_read(phase,codec_pin,acq)
    need(code==Path(__file__).read_bytes(),'Actual frozen inverse reader code differs')
    inv=completed(phase,restoration_pair,acq)
    need(inv['facts']['operation']=='complete1394-whole-proof-byte-restoration' and
         mapping_pin in inv['outputs'],'Unaccepted actual whole proof restoration map')
    mapping=json.loads(checked_read(phase,mapping_pin,acq))
    need(mapping['kind']=='complete1394-explicit-proof-restoration-map' and mapping['codec_pin']==codec_pin and
         mapping['original_paths_rewritten'] is False,'Changed typed original proof mapping/source binding')
    matches=[]
    for row in mapping['mapping']:
        actual=row['original_file']
        if actual['path']!=original_pin['path'] or actual.get('commit')!=original_pin.get('commit'):continue
        need(all(actual.get(k)==v for k,v in original_pin.items()) and
             set(actual)<=set(original_pin)|{'mode'},'Changed complete original proof descriptor relation')
        matches.append(row)
    need(len(matches)==1 and matches[0]['restored_file']==restored_pin and restored_pin in inv['outputs'],
         'Missing/ambiguous actual containing-byte proof inverse')
    row=matches[0]
    need(row['original_logical_path']==original_pin['path'] and restored_pin['mode']==row['original_mode'] and
         all(restored_pin.get(k)==row['original_file'].get(k) for k in
             ('bytes','sha256','uncompressed_bytes','uncompressed_sha256')),
         'Restored whole proof body/mode differs from unchanged original')
    need(type(encoded) is bool,'Explicit inverse encoding choice required')
    if encoded:
        return original_encoded(phase,{'file':restored_pin,'mode':row['original_mode']},acq)
    return checked_read(phase,restored_pin,acq)


def join_groups(phase, *, roster_pin,codec_pin,plan_pin,plan_pair,pack_pairs,index_pins,acq,before_finish):
    roster_raw,value=binding(phase,roster_pin,codec_pin,acq)
    plan_inv=completed(phase,plan_pair,acq)
    need(plan_inv['facts']['operation']=='complete1394-proof-custody-plan' and plan_pin in plan_inv['outputs'],
         'Unaccepted complete proof group plan')
    plan=json.loads(checked_read(phase,plan_pin,acq))
    need(plan['roster_pin']==roster_pin and plan['codec_pin']==codec_pin and
         len(pack_pairs)==len(index_pins)==len(plan['groups']),'Omitted complete mandatory proof custody group')
    files={};groups=[]
    for ordinal,(pair,pin) in enumerate(zip(pack_pairs,index_pins)):
        inv=completed(phase,pair,acq)
        need(inv['facts']['operation']=='complete1394-whole-proof-custody-group' and
             inv['facts']['group_ordinal']==ordinal and pin in inv['outputs'],'Foreign proof group/index publication')
        index=json.loads(checked_read(phase,pin,acq))
        need(index['roster_pin']==roster_pin and index['codec_pin']==codec_pin and index['plan_pin']==plan_pin and
             index['group_ordinal']==ordinal and [e['original']['ordinal'] for e in index['files']]==
             plan['groups'][ordinal]['file_ordinals'],'Changed complete proof group containing roster')
        need(index['transports']==[p for p in inv['outputs'] if Path(p['path']).name.startswith('proof-transport-')],
             'Missing actual whole proof transport in complete delivery')
        for entry in index['files']:
            need(all(part['transport_pin'] in index['transports'] for part in entry['parts']),
                 'Proof inverse references undeclared containing transport')
            row=entry['original'];number=row['ordinal']
            need(number not in files and row==value['files'][number],'Duplicate/changed original logical proof delivery')
            files[number]={'original':row,'containing_index':pin,'group_ordinal':ordinal}
        groups.append({'publication':pair[0],'inventory':pair[1],'index':pin,'transports':index['transports']})
    need(set(files)==set(range(len(value['files']))),'Mandatory original stage proof/history/control/report omitted')
    index={'kind':'complete1394-logical-proof-custody-delivery','version':1,'issue':1394,'codec_pin':codec_pin,
           'roster_pin':roster_pin,'original_roster_encoded_base64':base64.b64encode(roster_raw).decode('ascii'),
           'required_stage_ids':value['required_stage_ids'],'groups':groups,'files':[files[n] for n in sorted(files)],
           'inverse':'proof-custody.restore_group; exact original bytes/modes and explicit restored path mapping'}
    phase.output('complete-logical-proof-index.json.gz',acq.canonical(index),compress=True)
    before_finish()
    return finish_modes(phase,{'operation':'complete1394-mandatory-whole-proof-custody-join',
                              'logical_files':len(files),'mandatory_stage_proofs':len(value['required_stage_ids']),
                              'custody_groups':len(groups),'numerical_complete':False}, {},acq)
