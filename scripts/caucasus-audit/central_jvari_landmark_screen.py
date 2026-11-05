"""Research-only WGS84 landmark/terrain screen; no routed watershed inference."""
import json
from pyproj import Geod
import rasterio
from geodesic_line import GeodesicLine

line = GeodesicLine(json.load(open('caucasus-line.json'))['coordinates'])
landmarks = {'Marukh': (41+23/60+.984/3600,43+21/60+59.622/3600),
             'Mamison': (43+47/60+38.22/3600,42+42/60+20.232/3600),
             'Jvari-site': (44.45332,42.50435),
             'Jvari-Wikipedia-RU': (44+27/60+11/3600,42.5),
             'Jvari-Wikipedia-ES': (44.453937,42.504578)}
for name, p in landmarks.items():
    print(name, p, line.closest(p))
station = line.closest(landmarks['Jvari-site'])['station_m']
geod = Geod(ellps='WGS84')
with rasterio.open('central-jvari-cop30-dem.tif') as ds, rasterio.open('central-jvari-cop30-EDM.tif') as edm, rasterio.open('central-jvari-cop30-FLM.tif') as flm, rasterio.open('central-jvari-cop30-WBM.tif') as wbm:
    for shift in (-1000,-500,0,500,1000):
        p=line.point(station+shift)
        a=line.point(station+shift-20);b=line.point(station+shift+20)
        az=geod.inv(*a,*b)[0]
        points=[geod.fwd(*p,az-90,250)[:2],p,geod.fwd(*p,az+90,250)[:2]]
        print('station_delta_m',shift,'lonlat',p,'left_center_right_m',[float(v[0]) for v in ds.sample(points)],'EDM_FLM_WBM',[[int(next(mask.sample([q]))[0]) for mask in (edm,flm,wbm)] for q in points])
