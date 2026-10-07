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
# Execute real exclusive creation on the final fresh-directory layout.
with tempfile.TemporaryDirectory()as tmp:
 root=pathlib.Path(tmp);(root/'case/i').mkdir(parents=True);body=gzip.compress(b'fresh\n',mtime=0);(root/'case/i/000.gz').write_bytes(body)
 row={'original_path':'case/inputs/immutable/original.gz','delivered_path':'case/i/000.gz','bytes':len(body),'sha256':m.sha(body),'decoded_bytes':6,'decoded_sha256':m.sha(b'fresh\n')}
 assert not(root/'case/inputs').exists();m.validate(root,[row],{row['original_path']},lambda p:body,'case','case/i/');created=m.create_rows(root,[row]);assert created==[row['original_path']]and(root/row['original_path']).read_bytes()==body
 assert m.create_rows(root,[row])==[];results.append({'name':'fresh absent original directories created exclusively and full readback; exact repeat is idempotent','passed':True})
with tempfile.TemporaryDirectory()as tmp:
 root=pathlib.Path(tmp);(root/'case/i').mkdir(parents=True);(root/'outside').mkdir();(root/'case/inputs').symlink_to(root/'outside',target_is_directory=True);(root/'case/i/000.gz').write_bytes(body)
 try:m.create_rows(root,[row])
 except ValueError as e:results.append({'name':'symlink original parent rejected before create','passed':True,'rejection':str(e)})
 else:raise AssertionError('symlink original parent accepted')
 assert list((root/'outside').iterdir())==[]
with tempfile.TemporaryDirectory()as tmp:
 root=pathlib.Path(tmp);(root/'case/i').mkdir(parents=True);(root/'case/inputs').write_bytes(b'ordinary file');(root/'case/i/000.gz').write_bytes(body)
 try:m.validate(root,[row],{row['original_path']},lambda p:body,'case','case/i/')
 except ValueError as e:results.append({'name':'non-directory original parent rejected during complete prevalidation','passed':True,'rejection':str(e)})
 else:raise AssertionError('non-directory parent accepted')
 assert(root/'case/inputs').read_bytes()==b'ordinary file'
print(json.dumps({'controls':results,'complete_controls':len(results),'science_executed':False},sort_keys=True,indent=2))
