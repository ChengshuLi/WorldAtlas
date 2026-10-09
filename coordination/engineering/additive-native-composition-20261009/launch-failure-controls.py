"""Actual tiny owned Popen cleanup; no bank or scientific command."""
import pathlib,importlib.util,subprocess,sys,time,json,types,os
here=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('supervisor',here/'supervise-current-rebind.py');s=importlib.util.module_from_spec(spec);exec(compile((here/'supervise-current-rebind.py').read_bytes(),str(here/'supervise-current-rebind.py'),'exec'),s.__dict__)
negative=0
for failure in ('missing','foreign-group','constructor'):
 p=subprocess.Popen([sys.executable,'-I','-B','-c','import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(10)'],start_new_session=True)
 time.sleep(.05)
 rows={} if failure=='missing' else {p.pid:{'pgid':p.pid+1 if failure=='foreign-group' else p.pid}}
 def constructor(*args):raise RuntimeError('Injected owned-authority construction failure')
 try:s.own_launched_process(p,types.SimpleNamespace(snapshot=lambda:rows),types.SimpleNamespace(OwnedGroup=constructor))
 except (AssertionError,RuntimeError):negative+=1
 else:raise AssertionError('Expected actual launch rejection')
 assert p.poll() is not None
 try:os.killpg(p.pid,0)
 except ProcessLookupError:pass
 else:raise AssertionError('Owned group survived launch refusal')
r={'version':1,'kind':'actual-owned-launch-failure-controls','negative_controls':negative,'owned_processes_remaining':0,'limits':['Three tiny real owned subprocesses and production cleanup entry. No scientific/bank qualification.']}
(here/'launch-failure-controls.json').write_bytes(s.contract.canonical(r));print(json.dumps(r))
