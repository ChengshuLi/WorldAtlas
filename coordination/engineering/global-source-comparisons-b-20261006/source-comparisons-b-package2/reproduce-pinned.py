"""Future invocation guard for the exact reviewed producer; not a past execution."""
import argparse,pathlib,re,subprocess,sys,importlib.util
PIN='c0bb4c62a725f9d170a9c26db4baa1c477cbc905'
CASE=pathlib.Path(__file__).resolve().parent;ROOT=CASE.parents[3]
def pinned_commit(value):
 if not re.fullmatch('[0-9a-f]{40}',value or '') or value!=PIN:raise ValueError('Only the fixed complete reviewed producer commit is supported')
 return value
def command_for(value,output):
 pinned_commit(value);producer=CASE/'producer.py';relative=str(producer.relative_to(ROOT))
 if producer.is_symlink()or not producer.is_file():raise ValueError('Producer must be an ordinary local file')
 tree=subprocess.check_output(['git','ls-tree',value,'--',relative],cwd=ROOT)
 if tree.split()[0]not in(b'100644',b'100755'):raise ValueError('Frozen producer must be ordinary Git bytes')
 if subprocess.check_output(['git','show',value+':'+relative],cwd=ROOT)!=producer.read_bytes():raise ValueError('Executed original producer differs from fixed commit')
 return [sys.executable,str(producer),'--code-commit',value,'--output',str(output)]
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--code-commit',default=PIN);parser.add_argument('--output',required=True);args=parser.parse_args()
 pinned_commit(args.code_commit)
 spec=importlib.util.spec_from_file_location("restoration",CASE/"restore-inputs.py");module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.restore()
 subprocess.run(command_for(args.code_commit,args.output),cwd=ROOT,check=True)
