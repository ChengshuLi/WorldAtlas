"""Read every retained roster row against its exact original member bytes."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import zipfile
import custody as c


def verify(repo, output):
    root=repo/c.OWNED
    catalogue=json.loads((root/'catalogue.json').read_bytes())
    def reader(name):
        path=repo/name
        c.require(path.resolve()==path and not path.is_symlink() and path.is_file(),'Require ordinary local input')
        c.require(path.stat().st_size<=c.LIMIT,'Local input bound')
        return path.read_bytes()
    whole=[]
    with tempfile.TemporaryDirectory(prefix='gshhg-readback-',dir=output.parent) as temp:
        original=Path(temp)/'original.zip'
        c.reconstruct(catalogue,reader,original)
        with zipfile.ZipFile(original) as archive:
            for label in ('run-one','run-two'):
                family=root/label
                report_raw=(family/'report.json').read_bytes();report=json.loads(report_raw)
                c.require(report['execution']['producer_commit']=='f778478cc6f4995b0e603dafb8560fce5436ab92','Unexpected actual producer vintage')
                c.require(report['execution']['producer_sha256']==c.digest(c.committed(repo,report['execution']['producer_commit'],c.OWNED+'/custody.py')),'Executed code binding mismatch')
                rows=0;size=0;ids=set();relations={};levels={};unclosed=[]
                products=report['products']
                c.require(len(products)==len({p['path'] for p in products}),'Duplicate output descriptor')
                roster_names=[]
                for part in products:
                    c.require('/' not in part['path'] and '\\' not in part['path'] and part['path'] not in ('','.','..'),'Unsafe output name')
                    encoded=reader(c.OWNED+'/'+label+'/'+part['path'])
                    c.require(len(encoded)==part['bytes'] and c.digest(encoded)==part['sha256'],'Delivered output bytes mismatch')
                    raw=encoded
                    if 'uncompressed_bytes' in part:
                        with gzip.GzipFile(fileobj=__import__('io').BytesIO(encoded)) as stream:raw=stream.read(c.LIMIT+1)
                        c.require(len(raw)<=c.LIMIT and len(raw)==part['uncompressed_bytes'] and c.digest(raw)==part['uncompressed_sha256'],'Delivered decoded bytes mismatch')
                    if part['path'].startswith('records-'):roster_names.append(part['path'])
                with archive.open(catalogue['member']) as source:
                    for name in sorted(roster_names):
                        raw=gzip.decompress((family/name).read_bytes())
                        for line in raw.splitlines():
                            row=json.loads(line);header=source.read(44);c.require(len(header)==44,'Missing native header')
                            fields=struct.unpack('>11i',header);points=source.read(fields[1]*8)
                            c.require(len(points)==fields[1]*8,'Missing native coordinates')
                            c.require(row['ordinal']==rows and row['offset']==size and row['header_int32']==list(fields),'Exact record position/header mismatch')
                            c.require(row['record_bytes']==44+len(points) and row['record_sha256']==c.digest(header+points) and row['coordinate_bytes_sha256']==c.digest(points),'Exact whole original record mismatch')
                            c.require(fields[0] not in ids and row['id']==fields[0] and row['n']==fields[1] and row['flag']==fields[2] and row['container']==fields[9] and row['ancestor']==fields[10],'Complete native identities/lineage mismatch')
                            flag=fields[2]
                            c.require(row['level']==flag&255 and row['version']==(flag>>8)&255 and row['seam_flags']==(flag>>16)&3 and row['source']==(flag>>24)&1 and row['river_lake']==(flag>>25)&1 and row['area_scale']==(flag>>26)&63,'Original raw flag decomposition mismatch')
                            xmin,ymin,xmax,ymax=2147483647,2147483647,-2147483648,-2147483648;out_of_range=False
                            for x,y in struct.iter_unpack('>2i',points):
                                xmin=min(xmin,x);ymin=min(ymin,y);xmax=max(xmax,x);ymax=max(ymax,y)
                                out_of_range |= not(-180000000<=x<=360000000 and -90000000<=y<=90000000)
                            first=list(struct.unpack('>2i',points[:8]));last=list(struct.unpack('>2i',points[-8:]))
                            c.require(row['native_bounds_microdegrees']==[xmin,ymin,xmax,ymax] and row['first_point']==first and row['last_point']==last and row['closed']==(first==last) and row['coordinate_out_of_range']==out_of_range,'Complete original coordinate-derived field mismatch')
                            ids.add(fields[0]);relations[fields[0]]=fields[9];level=fields[2]&255;levels[level]=levels.get(level,0)+1
                            if not row['closed']:unclosed.append(fields[0])
                            rows+=1;size+=44+len(points)
                    c.require(source.read(1)==b'' and size==catalogue['member_bytes'] and rows==c.EXPECTED_COUNT,'Whole native record closure mismatch')
                c.require(all(p==-1 or p in ids for p in relations.values()),'Missing original parent')
                c.require(report['counts']['records']==rows and report['counts']['unclosed']==len(unclosed),'Report/actual full-row mismatch')
                whole.append({'family':label,'records':rows,'member_bytes':size,'levels':levels,'unclosed':unclosed,'report_sha256':c.digest(report_raw),'all_original_record_bytes_verified':True})
    left={p.name:c.digest(p.read_bytes()) for p in (root/'run-one').iterdir()}
    right={p.name:c.digest(p.read_bytes()) for p in (root/'run-two').iterdir()}
    c.require(left==right,'Two complete delivered execution families differ')
    result={'outcome':'passed','verifier_sha256':c.digest(Path(__file__).read_bytes()),'families':whole,'byte_identical_complete_files':left,'source_archive_sha256':catalogue['original_sha256'],'member_sha256':catalogue['member_sha256'],'limits':['Custody readback only; physical/validity/date/accuracy remain unverified.']}
    output.open('xb').write((json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode())
    print('Complete original record readback passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--output',required=True);a=p.parse_args();verify(Path(a.repo).resolve(),Path(a.output).resolve())
