from pathlib import Path
import numpy as np,zlib,struct
P=Path(__file__).resolve().parent
# Only local display crops, no source pixel acquisition or resampling of observations.
def load(path):
 raw=path.read_bytes();pos=8;pieces=[]
 while pos<len(raw):
  n=struct.unpack('>I',raw[pos:pos+4])[0];t=raw[pos+4:pos+8];v=raw[pos+8:pos+8+n];pos+=12+n
  if t==b'IHDR':w,h=struct.unpack('>II',v[:8])
  if t==b'IDAT':pieces.append(v)
 a=np.frombuffer(zlib.decompress(b''.join(pieces)),dtype='uint8').reshape(h,w*3+1);assert np.all(a[:,0]==0);return a[:,1:].reshape(h,w,3)
def save(path,a):
 h,w,_=a.shape
 def chunk(t,v):return struct.pack('>I',len(v))+t+v+struct.pack('>I',zlib.crc32(t+v)&0xffffffff)
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+r.tobytes() for r in a)))+chunk(b'IEND',b''))
indices=[0,1,6,7,9,12,14,17,18,19,29,30,33,34,39,41,43,54,56,64,66,70,74,97,109,61,63,73,83,92]
pages={i:load(P/f'contact-{i:02d}.png') for i in range(1,7)}
for start in range(0,len(indices),6):
 a=np.full((1128,1200,3),245,dtype='uint8')
 for s,i in enumerate(indices[start:start+6]):
  old=pages[i//20+1];slot=i%20;x=(slot%4)*300;y=(slot//4)*188;cut=old[y:y+188,x:x+300];big=np.repeat(np.repeat(cut,2,axis=0),2,axis=1);a[(s//2)*376:(s//2+1)*376,(s%2)*600:(s%2+1)*600]=big
 save(P/f'enlarged-{start//6+1:02d}.png',a)
print('Local panel enlargements ready.')
