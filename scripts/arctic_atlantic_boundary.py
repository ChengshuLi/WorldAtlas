"""Documented marginal-sea convention; no Arctic-Circle fallback in this sector."""
import numpy as np
# West-to-east anchors. Interior land links close the classifier; only existing
# ocean cells are changed. Coastal continental groups always retain priority.
ANCHORS=[
 ('Greenland interior',-45,70),('Cape Nansen',-29.5,68.25),
 ('Straumnes',-23.139322,66.430122),('Iceland interior west',-21,65.5),
 ('Iceland interior east',-17,65),('Gerpir',-13.5,65+5/60),
 ('Jan Mayen South Cape',-9,70+49/60+35/3600),
 ('Jan Mayen North Cape',-(7+58/60),71+9/60+35/3600),
 ('Sorkapp',16+37/60,76+28/60),('Bear Island North Cape',19.10,74.50),
 ('Bear Island Cape Bull',19+5/60,74+21/60),
 ('North Cape Norway',25+47/60+4/3600,71+10/60+21/3600),
 ('Norway interior',26,69),('Eurasia interior',30,68),('East closure',50,68)]

def boundary_curve():
    result=[]
    for (_,x1,y1),(_,x2,y2) in zip(ANCHORS,ANCHORS[1:]):
        def vec(x,y):
            x,y=np.deg2rad([x,y]);return np.array([np.cos(y)*np.cos(x),np.cos(y)*np.sin(x),np.sin(y)])
        a,b=vec(x1,y1),vec(x2,y2);angle=np.arccos(np.clip(a@b,-1,1));n=max(2,int(np.ceil(angle*6371.0088/2))+1);t=np.linspace(0,1,n)
        q=(np.sin((1-t)*angle)[:,None]*a+np.sin(t*angle)[:,None]*b)/np.sin(angle)
        lon=np.rad2deg(np.arctan2(q[:,1],q[:,0]));lat=np.rad2deg(np.arctan2(q[:,2],np.hypot(q[:,0],q[:,1])));result.extend(zip(lon,lat))
    # The tiny westward segment through Bear Island is inside its land/buffer;
    # sorting creates a single-valued ocean divider without changing that island.
    return np.array(sorted(result))
CURVE=boundary_curve()
def arctic_side(lon,lat):return lat>=np.interp(lon,CURVE[:,0],CURVE[:,1])
SOURCES=['https://iho.int/uploads/user/pubs/standards/s-23/S-23_Ed3_1953_EN.pdf','https://www.ncei.noaa.gov/archive/archive-management-system/OAS/bin/prd/jquery/seaname/details/96','https://www.government.is/library/04-Legislation/Act%20No%2041%201979%20as%20amended%20by%20Act%20No%2058%202017%20and%20Act%20No%2044%202018.pdf']
