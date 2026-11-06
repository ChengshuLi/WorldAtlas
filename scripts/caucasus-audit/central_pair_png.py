import sys,base64,numpy as np,rasterio
from rasterio.io import MemoryFile
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from scipy.ndimage import binary_dilation
from caucasus_boundary_visuals import line,bounds_for,terrain_image,water_features
old=line(sys.argv[1]);new=line(sys.argv[2]);terrain=sys.argv[3];waterpath=sys.argv[4];output=sys.argv[5];bounds=bounds_for(old,new);background=terrain_image(terrain,bounds)
with MemoryFile(base64.b64decode(background)) as mem:
 with mem.open() as ds:bg=ds.read()
transform=from_bounds(*bounds,540,440);water=water_features([waterpath],bounds);mask=rasterize([(g,1) for g,_ in water],out_shape=(440,540),transform=transform,fill=0,dtype='uint8')>0;bg[:,mask]=np.array([90,170,197],dtype='uint8')[:,None];canvas=np.full((3,440,1090),245,dtype='uint8')
for i,(geom,color) in enumerate(((old,(211,65,50)),(new,(0,121,132)))):
 img=bg.copy();route=rasterize([(geom,1)],out_shape=(440,540),transform=transform,fill=0,dtype='uint8')>0;halo=binary_dilation(route,iterations=4);stroke=binary_dilation(route,iterations=2);img[:,halo]=255;img[:,stroke]=np.array(color,dtype='uint8')[:,None];canvas[:,:,i*550:i*550+540]=img
with rasterio.open(output,'w',driver='PNG',width=1090,height=440,count=3,dtype='uint8') as ds:ds.write(canvas)
print('bounds',bounds)
