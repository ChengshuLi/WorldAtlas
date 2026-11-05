"""Screen grid-difference centers against an oriented coordinate-linear WGS84 GeoJSON line.

Numerical nearest-edge search has 0.02 m decision tolerance. A near-line center
is reported as 'on'; closest-segment ties can make side ambiguous. This is a
geometric diagnostic, not proof that the line is a watershed.
"""
import argparse, collections, json
from geodesic_line import GeodesicLine,SEARCH_TOLERANCE_M


def side(line,point,tangent_radius):
    result=line.closest(point)
    return ('ambiguous' if result['ambiguous'] else line.side(point,result['station_m'],tangent_radius)),result['distance_m']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spans',required=True);p.add_argument('--line',required=True)
    p.add_argument('--west',type=float,required=True);p.add_argument('--north',type=float,required=True)
    p.add_argument('--step',type=float,required=True);p.add_argument('--tangent-radius',type=float,default=5)
    args=p.parse_args()
    if args.step<=0 or args.tangent_radius<=0:p.error('step and tangent radius must be positive')
    coords=json.load(open(args.line))['coordinates'];line=GeodesicLine(coords)
    counts=collections.Counter();distances=[]
    for row,start,end,first,second in json.load(open(args.spans))['spans']:
        if end<=start:raise ValueError('invalid span')
        for col in range(start,end):
            point=(args.west+(col+.5)*args.step,args.north-(row+.5)*args.step)
            s,d=side(line,point,args.tangent_radius);counts[(first,second,s)]+=1;distances.append(d)
    print(json.dumps({'counts':[{'first':a,'second':b,'side':s,'cells':n} for (a,b,s),n in sorted(counts.items())], 'min_distance_m':min(distances) if distances else None,'max_distance_m':max(distances) if distances else None,'search_tolerance_m':SEARCH_TOLERANCE_M},indent=2))

if __name__=='__main__':main()
