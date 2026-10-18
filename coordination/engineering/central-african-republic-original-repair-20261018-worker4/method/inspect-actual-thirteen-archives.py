"""Complete original native ZIP custody and actual metadata extraction; no geometry operation."""
import pathlib,json,hashlib,zipfile,urllib.request,re,struct,datetime,concurrent.futures,shutil
S=pathlib.Path(__file__).resolve().parent;ROOT=S.parent.parent;A=json.load(open(S/'allocator-001.stdout.json'));P='coordination/engineering/central-african-republic-original-repair-20261018-worker4';T=pathlib.Path(A['path'])/P;O=T/'native-source-custody-002';assert not O.exists();O.mkdir();UP='9469f09592ced973a3448cf66b6100b741b64c0d'
initial=json.load(open(ROOT/'africa-workers-20261017/worker4-next-readiness/CAF-readiness.json'))
paths={r['key']:pathlib.Path(r['actual_zip_path']) for r in initial['initial_required_whole_families'] if not r['key'].startswith('CAF_')}
paths.update(CMR_ADM3=ROOT/'africa-workers-20261017/worker1-cmr/upstream-rights/CMR_ADM3.zip',COD_ADM2=ROOT/'africa-workers-20261018/worker6-cod/source-rights/COD_ADM2/COD_ADM2.zip',COG_ADM2=ROOT/'africa-workers-20261017/worker2-mdg/cog-original-20261018/actual-source-archives/COG_ADM2/COG_ADM2.zip',SDN_ADM1=ROOT/'africa-workers-20261017/worker4-sdn-preparation/source-rights/SDN_ADM1.zip',SDN_ADM2=ROOT/'africa-workers-20261017/worker4-sdn-preparation/source-rights/SDN_ADM2.zip',SSD_ADM1=ROOT/'africa-workers-20261017/worker1-sdn/additional-rights-001/SSD_ADM1.zip',SSD_ADM2=ROOT/'africa-workers-20261017/worker1-sdn/additional-rights-001/SSD_ADM2.zip',TCD_ADM2=ROOT/'africa-workers-20261017/worker1-sdn/additional-rights-001/TCD_ADM2.zip')
screen=json.load(open(T/'source-review/foreign-bounds-001/complete-foreign-bounds.json'));required=screen['whole_bounds_candidate_families'];assert len(paths)==len(required)==13 and {k.replace('_',':').replace(':ADM',':ADM') for k in paths}=={k[3:] for k in required}
byfamily={r['source_family']:r for r in screen['families']};started=datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def pointer(k):
 url='https://raw.githubusercontent.com/wmgeolab/geoBoundaries/'+UP+'/sourceData/gbOpen/'+k+'.zip';req=urllib.request.Request(url,headers={'User-Agent':'WorldAtlas-CAF-source-research'})
 with urllib.request.urlopen(req,timeout=45)as response:b=response.read(2048)
 text=b.decode();m=re.fullmatch(r'version https://git-lfs.github.com/spec/v1\noid sha256:([a-f0-9]{64})\nsize ([0-9]+)\n?',text);assert m,(k,text[:100]);return k,dict(url=url,observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),lfs_sha256=m.group(1),bytes=int(m.group(2)),content=text,pointer_sha256=sha(b))
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:fresh=dict(pool.map(pointer,sorted(paths)))
rows=[]
for k,p in sorted(paths.items()):
 assert p.is_file();b=p.read_bytes();pointer=fresh[k];assert len(b)==pointer['bytes'] and sha(b)==pointer['lfs_sha256'];D=O/k;D.mkdir();(D/(k+'.zip')).write_bytes(b);(D/'upstream-lfs-pointer.txt').write_text(pointer['content']);(D/'upstream-pointer.json').write_text(json.dumps(pointer,indent=2)+'\n');members=[];counts=[];texts=[];images=[]
 with zipfile.ZipFile(p)as z:
  names=[i.filename for i in z.infolist()];assert len(names)==len(set(names))
  for i in z.infolist():
   assert not i.is_dir() and not pathlib.PurePosixPath(i.filename).is_absolute() and '..'not in pathlib.PurePosixPath(i.filename).parts
   data=z.read(i);m=dict(name=i.filename,bytes=len(data),compressed_bytes=i.compress_size,sha256=sha(data));suffix=pathlib.PurePosixPath(i.filename).suffix.lower()
   if pathlib.PurePosixPath(i.filename).name==k+'.dbf':counts.append(struct.unpack('<I',data[4:8])[0]);m['dbf_records']=counts[-1]
   if suffix in ['.txt','.prj','.qpj','.xml','.qmd','.png','.jpg','.jpeg']:
    n=pathlib.PurePosixPath(i.filename).name;assert not (D/n).exists();(D/n).write_bytes(data);m['retained_path']=str((D/n).relative_to(T))
    if pathlib.PurePosixPath(i.filename).name.startswith('._'):m['appledouble_resource_fork']=True
    elif suffix in ['.png','.jpg','.jpeg']:images.append(m['retained_path'])
    else:texts.append(m['retained_path'])
   members.append(m)
 family='gb:'+k.replace('_',':');f=byfamily[family];assert len(counts)==1 and counts[0]==f['complete_features']
 rows.append(dict(source_family=family,native_name=k,whole_family_features=f['complete_features'],conservative_contact_features=len(f['selected_features']),reused_archive_path=str(p),owned_archive_path=str((D/(k+'.zip')).relative_to(T)),zip_bytes=len(b),zip_sha256=sha(b),fresh_immutable_pointer=pointer,member_count=len(members),complete_member_hashes=members,native_dbf_records=counts[0],actual_text_paths=texts,actual_license_image_paths=images,native_geometry_not_modified=True))
out=dict(kind='complete-thirteen-whole-native-archive-custody',started_utc=started,completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),upstream_commit=UP,whole_family_count=13,whole_native_features=sum(r['whole_family_features']for r in rows),contact_features=sum(r['conservative_contact_features']for r in rows),actual_zip_bytes=sum(r['zip_bytes']for r in rows),all_archive_bytes_reused=True,all_fresh_immutable_pointers_match=True,all_members_read_and_crc_checked=True,families=rows,limits=['Custody is not substantive source/right/vintage/CRS/ancestry approval; actual statements require separate review.','Complete whole-family native feature counts, not only69contacts, govern this inventory.','No native/source geometry processing, source-evidence, physical or native authority ran.'])
(O/'complete-thirteen-native-archive-custody.json').write_text(json.dumps(out,indent=2)+'\n');(S/'actual-thirteen-native-archive-custody.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['whole_family_count','whole_native_features','contact_features','actual_zip_bytes','all_archive_bytes_reused','all_fresh_immutable_pointers_match']}))
