"""North Sea outer limits through named Orkney/Shetland capes, NOAA/IHO."""
from matplotlib.path import Path as PolygonPath
# Intermediate land-crossing segments only close the water polygon; land mask
# supplies the actual coast. Skagerrak/Baltic/Channel have separate sea masks.
WEST=[(-3.375,58.672222),(-3.291667,58.777778),(-3.394444,58.925),(-3.352778,58.963889),(-3.213889,59.154167),(-3.021667,59.279167),(-2.956944,59.359722),(-2.877778,59.386111),(-2.386111,59.398333),(-1.316667,59.85),(-1.306944,60.638889),(-1.154167,60.658333),(-1.073333,60.733333),(-.956944,60.744444),(-.897222,60.841667),(-.883333,60.856667),(-.883333,61)]
NORTH_SEA=PolygonPath([*WEST,(6,61),(10,59),(12,55),(10,53),(6,50),(1.5,50.95),(0,52),(-2,54),WEST[0]])
SOURCE='https://www.ncei.noaa.gov/archive/archive-management-system/OAS/bin/prd/jquery/seaname/details/94'
