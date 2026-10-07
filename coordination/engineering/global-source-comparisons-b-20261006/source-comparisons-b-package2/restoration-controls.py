"""Small directed transport controls; complete actual restoration is separate."""
import importlib.util,pathlib,tempfile,copy,json,hashlib,gzip
CASE=pathlib.Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('restoration',CASE/'restore-inputs.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
results=[]
def fixture(mutation=None):
 with tempfile.TemporaryDirectory()as tmp:
  root=pathlib.Path(tmp);(root/'case/inputs').mkdir(parents=True);b=gzip.compress(b'{"fixture":true}\n',mtime=0);p=root/'case/inputs/i000.json.gz';p.write_bytes(b)
  row={'original_path':'case/inputs/original.json.gz','delivered_path':'case/inputs/i000.json.gz','bytes':len(b),'sha256':m.sha(b),'decoded_bytes':17,'decoded_sha256':m.sha(gzip.decompress(b))};row['decoded_bytes']=len(gzip.decompress(b));rows=[row]
  if mutation:mutation(root,rows)
  return m.validate(root,rows,{'case/inputs/original.json.gz'},lambda p:b,'case')
fixture();results.append({'name':'positive exact complete transport fixture','passed':True})
mutations=[('changed-delivery',lambda r,a:(r/a[0]['delivered_path']).write_bytes(b'changed')),('missing-delivery',lambda r,a:(r/a[0]['delivered_path']).unlink()),('duplicate-original',lambda r,a:a.append(copy.deepcopy(a[0]))),('duplicate-delivered-distinct-original',lambda r,a:a.append(dict(a[0],original_path='case/inputs/second.json.gz'))),('unsafe-delivery',lambda r,a:a[0].update(delivered_path='case/inputs/../outside')),('wrong-existing-original',lambda r,a:(r/a[0]['original_path']).write_bytes(b'wrong')),('wrong-whole-pin',lambda r,a:a[0].update(sha256='0'*64)),('wrong-decoded-pin',lambda r,a:a[0].update(decoded_sha256='0'*64)),('symlink-delivery',lambda r,a:((r/a[0]['delivered_path']).unlink(),(r/a[0]['delivered_path']).symlink_to('/etc/hosts')))]
for name,change in mutations:
 try:fixture(change)
 except(ValueError,FileNotFoundError)as e:results.append({'name':name,'passed':True,'rejection':str(e)})
 else:raise AssertionError(name+' accepted')
print(json.dumps({'controls':results,'complete_controls':len(results),'science_executed':False},sort_keys=True,indent=2))
