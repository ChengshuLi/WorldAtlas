"""Project Pacific/Arctic division through the geographic Bering Strait.

NOAA describes the cape-to-cape strait as the Bering/Pacific–Chukchi/Arctic
 gateway. This project uses that gateway, rather than the older IHO sea-area
 Arctic-Circle limit. Continental waters still have priority.
"""
import numpy as np
WEST=(-169.65194,66.07917) # Cape Dezhnev
EAST=(-168.08472,65.59639) # Cape Prince of Wales
SOURCE='https://docs.iho.int/mtg_docs/rhc/ArHC/ArHC6/ARHC6-14B_Arctic_Nautical_Charting_Plan.pdf'
def north_of_strait(lon,lat):
 def xyz(p):
  x,y=np.deg2rad(p);return np.array([np.cos(y)*np.cos(x),np.cos(y)*np.sin(x),np.sin(y)])
 # The great-circle plane through both cape vectors; north side is positive.
 normal=np.cross(xyz(WEST),xyz(EAST));x,y=np.deg2rad(lon),np.deg2rad(lat)
 return normal[0]*np.cos(y)*np.cos(x)+normal[1]*np.cos(y)*np.sin(x)+normal[2]*np.sin(y)>=0
