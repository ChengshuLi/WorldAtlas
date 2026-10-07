import datetime,hashlib,json,re,subprocess,sys,time
from pathlib import Path
root=Path.cwd();directory=root/'.cache/reference-native-preflight';ordinal=sys.argv[1]
if ordinal not in ('one','two'):raise ValueError('Exact actual run ordinal required')
freeze='b596ef836c51c5405baa8ceda770a2554ca12b7f'
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
if head!=freeze:raise ValueError('Actual scientific freeze changed before invocation')
name='reference-native-b596-run-'+ordinal
if (root/'.cache'/name).exists():raise ValueError('Fresh whole run destination required')
python='/Users/chengshuli/world-atlas-workspace/.cache/991-author-slot-preserved-20261006-44ed0b44/ignored-cache/reference-repair-991/runtime-rasterio-1.4.3-py312-arm64/bin/python'
command=['/usr/bin/time','-l',python,'coordination/engineering/reference-native-calculation-20261007/producer.py','--commit',freeze,'--name',name]
stdout=directory/(name+'.stdout');stderr=directory/(name+'.stderr-and-native-time')
start=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic_ns()
receipt={'actual_command':command,'working_directory':str(root),'environment_override':{'PYTHONDONTWRITEBYTECODE':'1'},'actual_start_utc':start,'actual_start_monotonic_ns':clock,'recorder_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'actual_method_freeze':freeze,'status':'RUNNING'}
record=directory/(name+'.actual-execution.json');record.write_text(json.dumps(receipt,indent=2)+'\n')
with stdout.open('xb') as out,stderr.open('xb') as err:
    result=subprocess.run(command,stdout=out,stderr=err)
end=datetime.datetime.now(datetime.timezone.utc).isoformat();duration=time.monotonic_ns()-clock
raw=stderr.read_bytes();m=re.search(rb'(\d+)\s+maximum resident set size',raw)
receipt.update(actual_exit_code=result.returncode,actual_end_utc=end,actual_elapsed_monotonic_ns=duration,status='PASS' if result.returncode==0 else 'FAILED',maximum_resident_set_size_native=int(m.group(1)) if m else None,maximum_resident_set_size_units='Darwin /usr/bin/time -l native bytes; not physical footprint or total swap',output=str(root/'.cache'/name),stdout={'path':str(stdout),'bytes':stdout.stat().st_size,'sha256':hashlib.sha256(stdout.read_bytes()).hexdigest()},stderr_and_statistics={'path':str(stderr),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
record.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));sys.exit(result.returncode)
