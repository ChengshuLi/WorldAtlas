"""Bound one proof process group and retain observed terminal membership."""
import json, os, pathlib, signal, subprocess, sys, time
out = pathlib.Path(sys.argv[1]).resolve()
assert not out.exists() and not out.is_symlink()
out.mkdir()
command = sys.argv[2:]
assert command
started = time.monotonic()
with (out/'stdout.log').open('xb') as stdout, (out/'stderr.log').open('xb') as stderr:
    child = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True,
                             env={**os.environ,'PROOF_DIR':str(out),'NODE_V8_COVERAGE':str(out/'coverage')})
    pgid = child.pid
    def members():
        rows=[]
        body=subprocess.check_output(['ps','-eo','pid=,ppid=,pgid=,rss=,args='],text=True)
        for line in body.splitlines():
            fields=line.strip().split(None,4)
            if len(fields) == 5 and int(fields[2]) == pgid:
                rows.append({'pid':int(fields[0]),'ppid':int(fields[1]),'pgid':int(fields[2]),'rss_bytes':int(fields[3])*1024,'command':fields[4]})
        return {'observed_monotonic_seconds':time.monotonic()-started,'command':['ps','-eo','pid=,ppid=,pgid=,rss=,args='],'members':rows}
    samples=[]; peak=0; failure=None; errors=[]; terminal=None; cleanup=None; returncode=None
    try:
        while child.poll() is None:
            scan=members(); usage=sum(row['rss_bytes'] for row in scan['members']); peak=max(peak,usage)
            samples.append({'seconds':scan['observed_monotonic_seconds'],'rss_bytes':usage,'pids':[row['pid'] for row in scan['members']]})
            if usage > 2*1024**3 or time.monotonic()-started > 420:
                failure='group-memory' if usage > 2*1024**3 else 'wall-time'
                break
            time.sleep(.2)
    except BaseException as error:
        failure='supervisor-exception'
        errors.append({'stage':'monitor','type':type(error).__name__,'message':str(error)})
    finally:
        # Once Popen succeeds, every path owns this exact group until cleanup.
        # A failed ps/read/monitor never bypasses the kill, wait and final scan.
        try:
            terminal=members()
        except BaseException as error:
            errors.append({'stage':'terminal-scan','type':type(error).__name__,'message':str(error)})
        try:
            os.killpg(pgid,signal.SIGKILL)
        except ProcessLookupError:
            pass
        except BaseException as error:
            errors.append({'stage':'group-kill','type':type(error).__name__,'message':str(error)})
        try:
            returncode=child.wait(timeout=5)
        except BaseException as error:
            errors.append({'stage':'child-wait','type':type(error).__name__,'message':str(error)})
        try:
            cleanup=members()
        except BaseException as error:
            errors.append({'stage':'cleanup-scan','type':type(error).__name__,'message':str(error)})
    result={'command':command,'pgid':pgid,'returncode':returncode,'elapsed_seconds':time.monotonic()-started,
            'sampled_process_group_peak_rss_bytes':peak,'group_reservation_bytes':2*1024**3,
            'wall_limit_seconds':420,'failure':failure,'errors':errors,'samples':samples,
            'terminal_group_scan':terminal,'cleanup_group_scan':cleanup,
            'complete':returncode==0 and failure is None and not errors and cleanup is not None and not cleanup['members']}
    (out/'operating.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['complete'], result
