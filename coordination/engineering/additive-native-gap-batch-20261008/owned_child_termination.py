"""Terminate only descendants owned by the supervised time process; keep time alive."""
import os,signal,subprocess,time

def snapshot():
    rows={}
    for line in subprocess.check_output(['ps','-axo','pid=,ppid=,pgid=,lstart=']).decode().splitlines():
        fields=line.split()
        if len(fields)>=8:
            try:pid,ppid,pgid=map(int,fields[:3])
            except ValueError:continue
            rows[pid]={'ppid':ppid,'pgid':pgid,'started':' '.join(fields[3:])}
    return rows

def owned_descendants(parent,identity,rows):
    if rows.get(parent)!=identity:return {}
    depths={parent:0}
    changed=True
    while changed:
        changed=False
        for pid,row in rows.items():
            if pid not in depths and row['ppid'] in depths and row['pgid']==identity['pgid']:
                depths[pid]=depths[row['ppid']]+1;changed=True
    return {pid:(rows[pid],depth) for pid,depth in depths.items() if pid!=parent}

def terminate_owned(p,identity,grace=10):
    assert identity['pgid']==p.pid,'Supervisor must own a freshly isolated process group'
    initial=snapshot()
    if initial.get(p.pid)!=identity:raise RuntimeError('Owned root identity absent or changed before termination')
    captured=owned_descendants(p.pid,identity,initial);events=[]
    def survivors():
        current=snapshot()
        # The fresh isolated group remains owned after time exits. Discover late forks.
        for pid,record in current.items():
            if pid!=p.pid and record['pgid']==identity['pgid'] and pid not in captured:
                captured[pid]=(record,1)
        # PPID may change when a parent exits; PID/start/group binds the same owned process.
        return {pid:(current[pid],depth) for pid,(record,depth) in captured.items()
                if pid in current and current[pid]['started']==record['started']
                and current[pid]['pgid']==record['pgid'] and pid!=p.pid}
    def send(sig):
        for pid,(record,depth) in sorted(survivors().items(),key=lambda item:item[1][1],reverse=True):
            try:os.kill(pid,sig);events.append({'pid':pid,'signal':sig,'identity':record})
            except ProcessLookupError:pass
    send(signal.SIGTERM)
    deadline=time.monotonic()+grace
    while survivors() and time.monotonic()<deadline:time.sleep(.05)
    if survivors():send(signal.SIGKILL)
    p.wait(timeout=10)
    deadline=time.monotonic()+10
    while survivors() and time.monotonic()<deadline:
        send(signal.SIGKILL);time.sleep(.05)
    if survivors():raise RuntimeError('Owned descendants remain after termination')
    return events
