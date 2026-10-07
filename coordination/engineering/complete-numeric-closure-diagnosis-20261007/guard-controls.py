"""Directed actual partial-witness controls; no global operation cohort."""
import argparse,copy
from pathlib import Path
from shapely.geometry import Polygon,MultiPolygon
import kernel,reader,verify

def run():
    candidate=Polygon([(-1,-1),(4,-1),(4,4),(-1,4),(-1,-1)])
    residue=MultiPolygon([Polygon([(0,0),(1,0),(0,1),(0,0)]),Polygon([(2,0),(3,0),(2,1),(2,0)])])
    class FailureInMiddle:
        __geo_interface__=candidate.__geo_interface__
        def __init__(self):self.calls=0
        def covers(self,p):
            self.calls+=1
            if self.calls==4:raise RuntimeError('directed failure after first complete triangle')
            return candidate.covers(p)
        def contains(self,p):return candidate.contains(p)
    probe=kernel.point_diagnostics(FailureInMiddle(),residue)
    g=kernel.ordinary_mapping(residue);c=kernel.ordinary_mapping(candidate)
    assert probe['status']=='unknown-operation-failed' and len(probe['vertices'])==3 and len(probe['triangles'])==1
    verify.probe_structure(probe,g,c)
    outcomes=[dict(name='actual-kernel-failure-in-middle-valid-prefix',outcome='passed')]
    def negative(name,change,geometry=g,context=c):
        x=copy.deepcopy(probe);change(x)
        try:verify.probe_structure(x,geometry,context)
        except (ValueError,KeyError,TypeError) as error:
            outcomes.append(dict(name=name,outcome='passed',rejection=str(error)));return
        raise AssertionError('Accepted tampering: '+name)
    for status in ('invalid','unsupported','unknown'):
        negative(status+'-cannot-carry-query-witness',lambda x,s=status:x.update(status=s,reason='directed-guard'))
    negative('invented-polygon-99999',lambda x:x['triangles'][0].update(polygon=99999))
    negative('changed-rational-centroid',lambda x:x['triangles'][0]['exact_rational_centroid'][0].update(numerator='99999'))
    negative('skipped-original-prefix-vertex',lambda x:x['vertices'].pop(0))
    negative('reordered-original-prefix',lambda x:x['vertices'].reverse())
    negative('partial-cannot-claim-global-completion',lambda x:x.update(complete_query_count=8))
    negative('partial-missing-operation-error',lambda x:x.pop('exception_message'))
    invalid={'type':'Polygon','coordinates':[[[0,0],[1,1],[0,1],[1,0],[0,0]]]}
    negative('partial-invalid-whole-residue',lambda x:None,invalid)
    negative('partial-invalid-whole-candidate',lambda x:None,g,invalid)
    empty=kernel.point_diagnostics(candidate,Polygon())
    assert empty['status']!='diagnostic'
    verify.probe_structure(empty,kernel.ordinary_mapping(Polygon()),c)
    outcomes.append(dict(name='actual-empty-guarded-positive',outcome='passed'))
    invented=copy.deepcopy(empty);invented['triangles']=[dict(probe['triangles'][0],polygon=99999)]
    try:verify.probe_structure(invented,kernel.ordinary_mapping(Polygon()),c)
    except ValueError as error:outcomes.append(dict(name='actual-empty-invented-triangle',outcome='passed',rejection=str(error)))
    else:raise AssertionError('Accepted EMPTY invented witness')
    return dict(status='PASS',count=len(outcomes),controls=outcomes,actual_partial_probe=probe,
        complete_candidate=c,complete_residue=g,limits=['Bounded actual unchanged kernel fixtures only; no third global operator or predicate cohort.'])
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',required=True);a=parser.parse_args()
    with Path(a.receipt).open('xb') as h:h.write(reader.canonical(run()))
    print('PASS directed guarded-prefix controls')
