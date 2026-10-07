"""Verify or restore the whole official MLIT archive, whose 242 MB body exceeds the ordinary-file limit."""
import hashlib,json,pathlib,urllib.request,os
ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=ROOT.parents[2]
URL='https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2017/N03-170101_GML.zip'
CACHE=REPO/'.cache/source-downloads/N03-170101_GML.zip'
def sha_file(path):
 h=hashlib.sha256();n=0
 with pathlib.Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block);n+=len(block)
 return n,h.hexdigest()
def restore(source_path=None, download=False):
 manifest=json.loads((ROOT/'sources/mlit/n03-2017-source-manifest.json').read_bytes())
 if manifest.get('version')!=1 or manifest.get('url')!=URL or 'parts' in manifest:
  raise ValueError('Unexpected restoration-only source manifest/version')
 path=pathlib.Path(source_path) if source_path else CACHE
 if not path.exists() and download:
  path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.download')
  request=urllib.request.Request(URL,headers={'User-Agent':'WorldAtlas research source restoration'})
  with urllib.request.urlopen(request,timeout=120) as response,tmp.open('wb') as out:
   while True:
    block=response.read(1024*1024)
    if not block:break
    out.write(block)
  os.replace(tmp,path)
 if path.is_symlink() or not path.is_file():
  raise FileNotFoundError(f'Exact source not in local custody; restore from {URL} to {path}, then rerun with --archive {path}')
 n,h=sha_file(path)
 if n!=manifest['http_content_length'] or h!=manifest['archive_sha256']:
  raise ValueError('Whole restored official source archive differs from captured length/SHA256')
 return path,manifest
if __name__=='__main__':
 import argparse,zipfile
 ap=argparse.ArgumentParser();ap.add_argument('--archive');ap.add_argument('--download',action='store_true');args=ap.parse_args()
 path,manifest=restore(args.archive,args.download)
 with zipfile.ZipFile(path) as z:
  listed={x.filename:x for x in z.infolist()}
  if set(listed)!={x['name'] for x in manifest['archive_members']}:raise ValueError('Official archive member roster differs')
  member_receipts=[]
  for x in manifest['archive_members']:
   info=listed[x['name']]
   if info.file_size!=x['uncompressed_bytes'] or f'{info.CRC:08x}'!=x['crc32']:raise ValueError('Member size/CRC differs from whole ZIP manifest')
   member_receipts.append({'name':x['name'],'bytes':info.file_size,'crc32':f'{info.CRC:08x}','sha256':x['uncompressed_sha256']})
 receipt={'status':'PASS','comparison_performed':False,'retention':'restoration-only','archive_bytes':manifest['http_content_length'],'archive_sha256':manifest['archive_sha256'],'archive_members':member_receipts,'local_archive_path_private':True}
 (ROOT/'receipts/mlit-archive-restoration.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':'PASS','archive_bytes':manifest['http_content_length'],'archive_sha256':manifest['archive_sha256'],'members':len(member_receipts),'retention':'restoration-only'}))
