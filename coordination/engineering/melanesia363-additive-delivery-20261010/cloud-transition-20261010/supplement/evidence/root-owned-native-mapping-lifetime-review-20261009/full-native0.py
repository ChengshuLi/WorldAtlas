import ast,importlib.util,json,gzip,subprocess,hashlib,struct,gc,time
from pathlib import Path
from shapely.geometry import mapping
from shapely.affinity import translate
W=Path('/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/3d62cf18b0b42e3ae3cd26d42f5e7ac90b65e45ead741649cedd79762724f9e7/work');P=W/'coordination/engineering/complete-replay-operand-restoration-20261007';C=Path(__file__).parent
sha=lambda b:hashlib.sha256(b).hexdigest();raw=subprocess.check_output(['git','-c','gc.auto=0','show','44c64776002bab7990e8f3eb1c4b7f1ef8e56320:coordination/engineering/gshhg-native-member-custody-20261007/results/native-00.bin.gz'],cwd=W);assert len(raw)==22743455 and sha(raw)=='99546c4a2bf41fe8f8a050fb425ab372c22e9c9821bf592d66ed9748b36301eb';body=gzip.decompress(raw);assert len(body)==33554432 and sha(body)=='020aa63a7bbd7e4945e99b96389f0e0580aad7204c91f631f4e92aeeddba3281';header=body[:44];count=struct.unpack('>3I4i2I2i',header)[1];record=body[:44+count*8];del raw,body;gc.collect()
spec=importlib.util.spec_from_file_location('literal_comparison',P/'methods/legacy/comparison.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);meta,g=mod.decode_record(record[:44],record[44:],0,0);assert meta['id']==0 and g is not None;del record;gc.collect()
node=next(n for n in ast.parse((P/'methods/kernel.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='ordinary_mapping');ns={'mapping':mapping,'json':json};exec(compile(ast.Module(body=[node],type_ignores=[]),str(P/'methods/kernel.py'),'exec'),ns)
canonical=lambda v:(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode();results=[]
for offset in (-360,0,360):
 h=translate(g,xoff=offset) if offset else g
 value=ns['ordinary_mapping'](h);old=canonical(value);del value;gc.collect();new=canonical(mapping(h));assert old==new
 results.append({'offset':offset,'whole_mapping_bytes':len(old),'whole_mapping_sha256':sha(old),'exact_whole_equal':True});del old,new,h;gc.collect()
result={'complete_native_points':count,'literal_native_record_sha256':meta['record_sha256'],'literal_decoded_pointset_sha256':meta['decoded_pointset_binary64_sha256'],'original_comparison_sha256':sha((P/'methods/legacy/comparison.py').read_bytes()),'original_kernel_sha256':sha((P/'methods/kernel.py').read_bytes()),'results':results,'scope':'Complete largest native record canonical serialization equivalence only; not numerical cohort execution or resource qualification.'};(C/'full-native0.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
