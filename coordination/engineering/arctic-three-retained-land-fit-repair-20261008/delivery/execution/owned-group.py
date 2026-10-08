"""Carry freshly verified owned-group authority across the time wrapper's exit."""
import os,signal,time,subprocess

def snapshot():
    rows={}
    for line in subprocess.check_output(['ps','-axo','pid=,ppid=,pgid=,lstart='],text=True).splitlines():
        parts=line.split()
        if len(parts)>=8:
            pid,ppid,pgid=map(int,parts[:3]);rows[pid]={'ppid':ppid,'pgid':pgid,'started':' '.join(parts[3:])}
    return rows

class OwnedGroup:
    def __init__(self,process,identity):
        if identity is None or identity.get('pgid') != process.pid or snapshot().get(process.pid) != identity:
            raise RuntimeError('Fresh exact owned root identity required before acquiring group authority')
        self.process=process;self.group=process.pid;self.identity=dict(identity);self.captured={};self.events=[]
        self.survivors()
    def survivors(self):
        current=snapshot()
        for pid,row in current.items():
            if pid!=self.process.pid and row['pgid']==self.group and pid not in self.captured:
                self.captured[pid]=dict(row)
        return {pid:current[pid] for pid,old in self.captured.items() if pid in current
                and current[pid]['started']==old['started'] and current[pid]['pgid']==old['pgid']}
    def send(self,sig):
        for pid,identity in self.survivors().items():
            # Recheck the same PID/start/group immediately before each individual signal.
            row=snapshot().get(pid)
            if row and row['started']==identity['started'] and row['pgid']==identity['pgid']:
                try:os.kill(pid,sig);self.events.append({'pid':pid,'signal':sig,'identity':identity})
                except ProcessLookupError:pass
    def cleanup(self,grace=2):
        self.send(signal.SIGTERM);deadline=time.monotonic()+grace
        while self.survivors() and time.monotonic()<deadline:time.sleep(.05)
        deadline=time.monotonic()+10
        while self.survivors() and time.monotonic()<deadline:
            self.send(signal.SIGKILL);time.sleep(.05)
        self.process.wait(timeout=10)
        if self.survivors():raise RuntimeError('Owned group absence not proven after cleanup')
        return self.events
