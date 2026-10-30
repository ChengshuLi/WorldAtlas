"""Cell-center continent assignment along the mapped main Suez Canal."""
import json
from pathlib import Path
import numpy as np
from matplotlib.path import Path as PolygonPath
from scipy.ndimage import binary_erosion
from scipy.spatial import cKDTree

SOURCE=Path(__file__).resolve().parents[1]/'data/geography/suez-canal.geojson'
CANAL=json.loads(SOURCE.read_text())['geometry']['coordinates']
GULF=[(32.55,29.85),(32.52,29.6),(32.60,29.47),(32.72,29.32),
      (32.80,29.2),(32.9,29),(33,28.8),(33.05,28.6),(33.25,28.4),
      (33.42,28.2),(33.63,28),(33.75,27.9),(33.85,27.8),(34,27.6),
      (34.2,27.3),(34.5,26.5)]
SINAI=[(CANAL[0][0],33),*CANAL,*GULF,(37,26.5),(37,33)]

def xyz(lon,lat):
    lo=np.deg2rad(lon);la=np.deg2rad(lat)
    return np.column_stack((np.cos(la)*np.cos(lo),np.cos(la)*np.sin(lo),np.sin(la)))

def patch_suez(region,step):
    x0,y0,a=region((30.5,26.5,36.5,32.2));old=a.copy()
    lon=-180+(x0+np.arange(a.shape[1])+.5)*step;lat=90-(y0+np.arange(a.shape[0])+.5)*step
    xx,yy=np.meshgrid(lon,lat)
    east=PolygonPath(SINAI+[SINAI[0]]).contains_points(np.column_stack((xx.ravel(),yy.ravel()))).reshape(a.shape)
    land=np.isin(a,[17,18]);a[land]=np.where(east[land],18,17)
    edge=land&~binary_erosion(land);rr,cc=np.where(edge);groups=a[rr,cc]&15
    tree=cKDTree(xyz(lon[cc],lat[rr]));rr,cc=np.where(np.isin(a,[1,2]))
    _,ii=tree.query(xyz(lon[cc],lat[rr]),workers=4);a[rr,cc]=groups[ii]
    # Lakes and canal-side waters follow the canal separator, not an unrelated
    # nearest coast across a lake or a simplified shoreline.
    corridor=(yy>=CANAL[-1][1])&(yy<=CANAL[0][1])&(xx>=31.8)&(xx<=32.9)&np.isin(a,[1,2])
    a[corridor]=np.where(east[corridor],2,1)
    assert np.array_equal(old>=16,a>=16)
    audit={'land_cells_changed':int(np.count_nonzero(land&(a!=old))),
           'water_cells_changed':int(np.count_nonzero((old<16)&(a!=old))),
           'source':'https://www.openstreetmap.org/relation/7719838',
           'source_way_ids':[5038117,925360882],
           'method':'Mapped main canal centerline; cell-center affiliation. Gulf separator stays offshore; Gulf and adjoining coastal water assigned by corrected shore proximity. Canal lakes follow canal side.'}
    return (x0,y0,a),audit
