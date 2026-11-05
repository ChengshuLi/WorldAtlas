"""Screen grid-difference centers relative to an oriented projected line.

This is a geometric diagnostic, not proof that the line is a watershed.
Input spans are [row, start_col, exclusive_end_col, first_label, second_label].
"""
import argparse, collections, json
from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.ops import transform


def side(line, point, tangent_radius):
    station = line.project(point)
    a = line.interpolate(max(0, station - tangent_radius))
    b = line.interpolate(min(line.length, station + tangent_radius))
    nearest = line.interpolate(station)
    cross = (b.x-a.x)*(point.y-nearest.y) - (b.y-a.y)*(point.x-nearest.x)
    return ('left' if cross > 0 else 'right' if cross < 0 else 'on'), point.distance(nearest)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spans', required=True); p.add_argument('--line', required=True)
    p.add_argument('--projected-crs', required=True)
    p.add_argument('--west', type=float, required=True); p.add_argument('--north', type=float, required=True)
    p.add_argument('--step', type=float, required=True); p.add_argument('--tangent-radius', type=float, default=5)
    args = p.parse_args()
    if args.step <= 0 or args.tangent_radius <= 0: p.error('step and tangent radius must be positive')
    coords = json.load(open(args.line))['coordinates']
    project = Transformer.from_crs(4326, args.projected_crs, always_xy=True)
    line = transform(project.transform, LineString(coords))
    counts=collections.Counter(); distances=[]
    for row, start, end, first, second in json.load(open(args.spans))['spans']:
        if end <= start: raise ValueError('invalid span')
        for col in range(start, end):
            lon=args.west+(col+.5)*args.step;lat=args.north-(row+.5)*args.step
            s,d=side(line,Point(project.transform(lon,lat)),args.tangent_radius)
            counts[(first,second,s)]+=1;distances.append(d)
    print(json.dumps({'counts':[{'first':a,'second':b,'side':s,'cells':n} for (a,b,s),n in sorted(counts.items())], 'min_distance_m':min(distances) if distances else None, 'max_distance_m':max(distances) if distances else None},indent=2))

if __name__=='__main__':main()
