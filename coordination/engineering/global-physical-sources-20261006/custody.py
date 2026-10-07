"""Issue1261: exact original ZIP custody and complete native GSHHG record inventory."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import zipfile

OWNED = 'coordination/engineering/global-physical-sources-20261006'
CODEC = 'scripts/evidence/immutable.py'
CODEC_SHA = 'b7ff607b7774595788396e94f08fc29d750e4032624eb93732a5735c1ddcf7fd'
LIMIT = 33554432
HEADER = struct.Struct('>11i')
EXPECTED_COUNT = 188612


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)


def committed(repo, commit, path):
    require(re.fullmatch('[a-f0-9]{40}', commit) is not None, 'Require full lowercase immutable commit')
    require(not path.startswith('/') and all(x not in ('', '.', '..') for x in path.split('/')) and '\\' not in path, 'Unsafe input path')
    row = git(repo, 'ls-tree', '-z', commit, '--', path).decode().rstrip('\0')
    require(row.startswith(('100644 ', '100755 ')) and row[row.find('\t') + 1:] == path, 'Require unique ordinary Git file')
    oid = row.split()[2]
    require(int(git(repo, 'cat-file', '-s', oid)) <= LIMIT, 'Oversized ordinary input')
    return git(repo, 'cat-file', 'blob', oid)


def environment(repo, commit):
    require(git(repo, 'rev-parse', '--verify', commit + '^{commit}').decode().strip() == commit, 'Execution commit mismatch')
    code = committed(repo, commit, OWNED + '/custody.py')
    require(Path(__file__).read_bytes() == code, 'Executed owned module differs from immutable producer')
    codec_raw = committed(repo, commit, CODEC)
    require(digest(codec_raw) == CODEC_SHA, 'Existing codec mismatch')
    path = repo / CODEC
    require(not path.is_symlink() and path.read_bytes() == codec_raw, 'Imported codec differs from declared immutable code')
    spec = importlib.util.spec_from_file_location('gshhg_existing_immutable', path)
    codec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(codec)
    require(Path(codec.__file__).read_bytes() == codec_raw, 'Imported codec closure mismatch')
    return codec, {'producer_commit': commit, 'producer_sha256': digest(code), 'codec_sha256': digest(codec_raw)}


def reconstruct(catalogue, reader, target):
    parts = catalogue['parts']
    require(parts and len(parts) == len({p['path'] for p in parts}), 'Missing/duplicate source fragment paths')
    offset = 0
    whole = hashlib.sha256()
    with target.open('xb') as stream:
        for ordinal, part in enumerate(parts):
            require(part['ordinal'] == ordinal and part['offset'] == offset, 'Wrong fragment order/offset')
            raw = reader(part['path'])
            require(len(raw) <= LIMIT and len(raw) == part['bytes'] and digest(raw) == part['sha256'], 'Fragment bytes/hash/size mismatch')
            stream.write(raw)
            whole.update(raw)
            offset += len(raw)
    require(offset == catalogue['original_bytes'] and whole.hexdigest() == catalogue['original_sha256'], 'Whole original ZIP mismatch')
    return {'bytes': offset, 'sha256': whole.hexdigest(), 'parts_read': len(parts)}


def parse_native(stream):
    offset = 0
    seen = set()
    while True:
        header = stream.read(44)
        if not header:
            break
        require(len(header) == 44, 'Truncated native header')
        values = HEADER.unpack(header)
        identity, count, flag, west, east, south, north, area, area_full, container, ancestor = values
        require(identity >= 0 and identity not in seen and count >= 3, 'Duplicate/invalid native ID or count')
        seen.add(identity)
        points = stream.read(count * 8)
        require(len(points) == count * 8, 'Truncated native coordinate bytes')
        coords = struct.iter_unpack('>2i', points)
        coordinate_out_of_range = False
        xmin, xmax, ymin, ymax = 2147483647, -2147483648, 2147483647, -2147483648
        first = last = None
        for x, y in coords:
            if first is None:
                first = [x, y]
            last = [x, y]
            coordinate_out_of_range |= not (-180000000 <= x <= 360000000 and -90000000 <= y <= 90000000)
            xmin, xmax, ymin, ymax = min(xmin, x), max(xmax, x), min(ymin, y), max(ymax, y)
        level = flag & 255
        require(level in (1, 2, 3, 4, 5, 6), 'Unknown native level')
        yield dict(ordinal=len(seen)-1, id=identity, offset=offset, record_bytes=44+len(points),
                   header_int32=list(values), n=count, flag=flag, level=level,
                   version=(flag >> 8) & 255, seam_flags=(flag >> 16) & 3,
                   source=(flag >> 24) & 1, river_lake=(flag >> 25) & 1,
                   area_scale=(flag >> 26) & 63, container=container, ancestor=ancestor,
                   record_sha256=digest(header+points), coordinate_bytes_sha256=digest(points),
                   native_bounds_microdegrees=[xmin,ymin,xmax,ymax],
                   first_point=first,last_point=last,closed=first==last,
                   coordinate_out_of_range=coordinate_out_of_range,
                   geometry_validity='not-evaluated; native byte custody is not polygon validity or physical approval')
        offset += 44 + len(points)


def run(repo, commit, output):
    codec, code = environment(repo, commit)
    catalogue_raw = committed(repo, commit, OWNED+'/catalogue.json')
    catalogue = json.loads(catalogue_raw)
    output.mkdir(parents=True, exist_ok=False)
    products = []
    def write(name, raw, compress=False):
        encoded = codec.deterministic_gzip(raw) if compress else raw
        require(len(encoded) <= LIMIT and len(raw) <= LIMIT, 'Output encoded/decoded bound')
        (output/name).open('xb').write(encoded)
        desc = codec.descriptor(name, encoded)
        if compress:
            desc.update(uncompressed_bytes=len(raw), uncompressed_sha256=digest(raw))
        products.append(desc)
    with tempfile.TemporaryDirectory(prefix='gshhg-original-', dir=output.parent) as temporary:
        original = Path(temporary)/'original.zip'
        receipt = reconstruct(catalogue, lambda p: committed(repo, commit, p), original)
        members = []
        with zipfile.ZipFile(original) as archive:
            names = archive.namelist()
            require(len(names)==18 and len(names)==len(set(names)), 'Complete unique original member roster required')
            for info in archive.infolist():
                require(not info.is_dir(), 'Nonordinary ZIP member')
                sha = hashlib.sha256(); size = 0
                with archive.open(info) as stream:
                    while True:
                        raw = stream.read(1048576)
                        if not raw: break
                        sha.update(raw); size += len(raw)
                require(size == info.file_size, 'Whole ZIP member size mismatch')
                members.append(dict(name=info.filename,bytes=size,sha256=sha.hexdigest(),
                                    compressed_bytes=info.compress_size,crc32=info.CRC,compression=info.compress_type))
                if info.filename == catalogue['member']:
                    require(size==catalogue['member_bytes'] and sha.hexdigest()==catalogue['member_sha256'], 'Whole native member identity mismatch')
            batch = []; batch_bytes = 0; roster = []; levels = Counter(); seams = Counter(); coordinates = 0; unclosed = 0
            with archive.open(catalogue['member']) as stream:
                for row in parse_native(stream):
                    raw = codec.canonical_json(row)
                    if batch and batch_bytes + len(raw) > 8*1024*1024:
                        write('records-%03d.jsonl.gz'%len([p for p in products if p['path'].startswith('records-')]), b''.join(batch), True)
                        batch = []; batch_bytes = 0
                    batch.append(raw); batch_bytes += len(raw)
                    roster.append((row['id'],row['level'],row['container']))
                    levels[row['level']] += 1; seams[row['seam_flags']] += 1; coordinates += row['n']; unclosed += not row['closed']
                require(stream.tell()==catalogue['member_bytes'], 'Native member complete byte consumption mismatch')
            if batch:
                write('records-%03d.jsonl.gz'%len([p for p in products if p['path'].startswith('records-')]), b''.join(batch), True)
            require(len(roster)==EXPECTED_COUNT, 'Complete original native record count mismatch')
            ids = {r[0] for r in roster}; by_id = {r[0]:r for r in roster}
            relations = []
            for identity, level, parent in roster:
                if parent != -1:
                    if parent not in ids:
                        relations.append(dict(id=identity,container=parent,status='missing-original-container'))
                    elif by_id[parent][1] != level-1:
                        relations.append(dict(id=identity,container=parent,status='nonconsecutive-original-level',parent_level=by_id[parent][1]))
            for name in ('README.TXT','LICENSE.TXT','COPYING.LESSERv3'):
                raw = archive.read(name)
                require(committed(repo,commit,OWNED+'/'+name)==raw,'Retained attribution differs from original')
            write('members.json', codec.canonical_json(members))
            write('container-unknowns.json', codec.canonical_json(relations))
    report = dict(version=1,execution=code,catalogue_sha256=digest(catalogue_raw),original=receipt,
                  member=dict(name=catalogue['member'],bytes=catalogue['member_bytes'],sha256=catalogue['member_sha256']),
                  counts=dict(records=len(roster),coordinate_pairs=coordinates,levels=dict(sorted(levels.items())),
                              seam_flags=dict(sorted(seams.items())),unclosed=unclosed,container_unknowns=len(relations),archive_members=len(members)),
                  products=products,
                  limits=['Custody only: no polygon validity, physical classification, political assignment or repair.',
                          'Original L5/L6 Antarctic alternatives retained, not conflated with ordinary L1 land.',
                          'Exact original integer coordinate bytes remain in the authenticated complete member; roster is not a substitute geometry.',
                          '2017 compiled archive includes much older WDBII lakes and uncertain registration/dates.',
                          'LICENSE.TXT says LGPLv3 or later; historical README says v3 or earlier; both exact originals retained.',
                          'LICENSE.TXT references COPYINGv3, absent from this actual18-member binary ZIP; no extra original member invented.'])
    write('report.json',codec.canonical_json(report))
    print(json.dumps(report['counts'],sort_keys=True),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',required=True)
    parser.add_argument('--commit',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    run(Path(args.repo).resolve(),args.commit,Path(args.output).resolve())
