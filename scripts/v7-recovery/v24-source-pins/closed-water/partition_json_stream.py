"""Parser for a top-level JSON object with a streamed components array."""
import json


def unique_object(pairs):
 out={}
 for k,v in pairs:
  if k in out:raise ValueError(f'duplicate JSON key: {k}')
  out[k]=v
 return out


class Reader:
 def __init__(self,f):
  self.f=f;self.buf='';self.pos=0;self.eof=False
  self.decoder=json.JSONDecoder(object_pairs_hook=unique_object)
 def compact(self):
  if self.pos:self.buf=self.buf[self.pos:];self.pos=0
 def fill(self):
  self.compact()
  if self.eof:return False
  chunk=self.f.read(65536)
  if not chunk:self.eof=True;return False
  self.buf+=chunk
  return True
 def space(self):
  while True:
   while self.pos<len(self.buf) and self.buf[self.pos].isspace():self.pos+=1
   if self.pos<len(self.buf) or self.eof:return
   self.fill()
 def char(self,ch):
  self.space()
  if self.pos==len(self.buf) or self.buf[self.pos]!=ch:raise ValueError(f'expected {ch!r} in partition JSON')
  self.pos+=1
 def peek(self):
  self.space();return self.buf[self.pos] if self.pos<len(self.buf) else None
 def value(self):
  self.space();self.compact()
  while True:
   try:
    value,end=self.decoder.raw_decode(self.buf)
    # A number at the current buffer end might have more digits.
    if end==len(self.buf) and not self.eof:
     self.fill();continue
    self.pos=end;return value
   except json.JSONDecodeError as e:
    if self.eof:raise ValueError('malformed partition JSON') from e
    self.fill()


def read_partition(path,on_component):
 """Return metadata; invoke callback once per component, never retaining array."""
 with open(path,'r',encoding='utf8') as f:
  r=Reader(f);r.char('{');meta={};seen=set();components_seen=False
  if r.peek()=='}':r.char('}');raise ValueError('missing components')
  while True:
   key=r.value()
   if not isinstance(key,str) or key in seen:raise ValueError('invalid or duplicate partition key')
   seen.add(key);r.char(':')
   if key=='components':
    components_seen=True;r.char('[')
    if r.peek()!=']':
     while True:
      value=r.value()
      if not isinstance(value,dict):raise ValueError('component must be an object')
      on_component(value)
      if r.peek()==',':r.char(',');continue
      break
    r.char(']')
   else:
    value=r.value();meta[key]=value
   if r.peek()==',':r.char(',');continue
   break
  r.char('}');r.space()
  if r.peek() is not None:raise ValueError('trailing partition JSON')
  if not components_seen:raise ValueError('partition components missing')
  return meta
