"""Native regression coordinates, checksums, coverage and unchanged-land proof."""
import json,gzip,hashlib,numpy as np
from pathlib import Path
import argparse
parser=argparse.ArgumentParser();parser.add_argument('candidate',type=Path);parser.add_argument('baseline',type=Path);parser.add_argument('--allow-land-affiliation-changes',action='store_true');args=parser.parse_args()
p=args.candidate;m=json.loads((p/'proposal.json').read_text());rb=gzip.decompress((p/'rows.u32.gz').read_bytes());vb=gzip.decompress((p/'runs.u32.gz').read_bytes());r=np.frombuffer(rb,'<u4');v=np.frombuffer(vb,'<u4').reshape(-1,2)
assert hashlib.sha256(rb).hexdigest()==m['local_grid']['rows_sha256'];assert hashlib.sha256(vb).hexdigest()==m['local_grid']['runs_sha256'];assert len(r)==m['height']+1
for y in range(m['height']):
 a=v[r[y]:r[y+1]];assert a[-1,0]==65536;assert (np.diff(a[:,0].astype('int64'))>0).all()
def at(x,y):
 a=v[r[y]:r[y+1]];return int(a[np.searchsorted(a[:,0],x,side='right'),1])
def geo(lo,la):return at(int((lo+180)*65536/360),int((90-la)*65536/360))
islands=[(57221,16246),(56662,16190),(56646,15829),(56761,15843),(56838,15418),(57259,15028),(57291,14912),(57920,14648),(58350,14605),(59126,13925),(59202,13809),(59301,13614),(59283,13403),(59310,13084),(59287,12964),(59148,12643),(60793,11958)]
checks=[(x,y,22) for x,y in islands]+[(20348,12119,7),(20360,10732,7),(20394,8581,7),(59610,25043,8),(42953,13885,9),(43243,13816,9),(38875,11304,17),(38745,11045,18),(38729,11018,18),(38719,10994,18),(38702,10932,18),(38645,10703,1),(38944,11372,17),(33117,9486,3),(33869,9331,1),(30280,5902,7),(31630,7944,7)]
for x,y,e in checks:assert at(x,y)==e,(x,y,e,at(x,y))
for lo,la,e in [(2,60.9,3),(2,61.3,7),(4,55,3),(20,57,3),(-5,53,3),(-3,50,3),(37,65,3),(40,75,10),(80,76,10),(65,15,9),(88,14,9),(96,11,2)]:assert geo(lo,la)&15==e,(lo,la,geo(lo,la),e)
print('PASS rows, hashes,',len(checks),'reported regressions and bounded/open sea examples')

newchecks=[(44995,3731,18),(44948,3723,18),(44941,3691,18),(44971,3678,18),(44965,3635,18),(44913,3560,18),(44964,3447,18),(44934,3371,2),(45602,3027,18),(46332,3088,18),(46558,3007,18),(46736,1903,18),(2134,4359,10),(41262,4131,10),(58556,8662,8),(18140,4450,4),(3116,4292,4),(20603,5497,4),(20776,4994,4),(4953,5585,4),(4677,5848,4),(4663,5851,4),(4638,5856,4),(3458,5915,4),(2883,4756,4),(15501,12715,4),(16755,13395,4),(35206,4085,3)]
for x,y,e in newchecks:assert at(x,y)==e,(x,y,e,at(x,y))
for lo,la,e in [(-55,62,10),(-55,58,7),(-10,50,7),(121,39,2),(107,20,2),(99,4,2),(-125,45,8)]:assert geo(lo,la)&15==e,(lo,la,geo(lo,la),e)
print('PASS',len(newchecks),'new user coordinates; ocean/bounded basin controls')
if 'eurasia_boundary_audit' in m:
 for x,y,e in [(43680,6024,19),(40871,8636,19),(41599,8854,19),(42121,7069,18),(42798,6972,18),(42210,7806,19),(42221,7806,18),(43508,6662,19),(43526,6662,18),(40864,8651,18),(41074,8670,19),(41622,8987,18),(39998,8449,18),(39882,8355,18),(39561,8211,19),(44825,3916,19)]:
  assert at(x,y)==e,(x,y,e,at(x,y))
 print('PASS 16 Eurasian river/watershed controls')
if 'turkish_straits_audit' in m:
 for x,y,e in [(37576,9074,18),(37626,9039,18),(37649,9047,18),(38055,8905,19),(37790,8991,18),(37512,9134,18),(37482,9071,19)]:
  assert at(x,y)==e,(x,y,e,at(x,y))
 print('PASS 7 Turkish strait/island controls')
if 'independent_review_repairs' in m and 'verified_connector_refinement' not in m:
 for x,y,e in [(44998,3876,19),(44998,3875,19),(45024,3862,19),(45019,3861,19),(35061,9920,17),(35109,9855,19),(34948,9686,19),(41604,8729,3),(2013,4407,4),(1985,4436,2),(35831,2490,7),(36376,2901,7)]:
  assert at(x,y)==e,(x,y,e,at(x,y))
 print('PASS 12 independent-review regression cells')
if 'verified_connector_refinement' in m:
 for x,y,e in [(44998,3876,18),(44998,3875,18),(44999,3876,18),(44830,3919,19),(45019,3861,19),(45024,3862,19),(39616,8242,18),(39561,8211,19),(35061,9920,17),(35109,9855,19),(34948,9686,19),(41604,8729,3),(2013,4407,4),(1985,4436,2),(35831,2490,7),(36376,2901,7)]:
  assert at(x,y)==e,(x,y,e,at(x,y))
 assert hashlib.sha256((p/'eurasia-boundary-reference.geojson').read_bytes()).hexdigest()==m['verified_connector_refinement']['reference_sha256']
 print('PASS 16 connector/review controls and current reference checksum')
# Independently compare complete land assignments from v14 and final candidate.
oldp=args.baseline
orows=np.frombuffer(gzip.decompress((oldp/'rows.u32.gz').read_bytes()),'<u4');oruns=np.frombuffer(gzip.decompress((oldp/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
changed=0;land_changed=0;ocean_changed=0
for y in range(m['height']):
 a=v[r[y]:r[y+1]];b=oruns[orows[y]:orows[y+1]];aa=np.repeat(a[:,1],np.diff(np.r_[0,a[:,0]])).astype('uint8');bb=np.repeat(b[:,1],np.diff(np.r_[0,b[:,0]])).astype('uint8')
 assert np.array_equal(aa>=16,bb>=16)
 if 'eurasia_boundary_audit' in m and 'independent_review_repairs' not in m:
  ocean=np.isin(bb,[7,8,9,10]);assert np.array_equal(aa[ocean],bb[ocean])
 land_changed+=int(np.count_nonzero((aa!=bb)&(bb>=16)))
 if not args.allow_land_affiliation_changes:assert np.array_equal(aa[bb>=16],bb[bb>=16])
 changed+=int(np.count_nonzero(aa!=bb))
 ocean_changed+=int(np.count_nonzero((aa!=bb)&np.isin(bb,[7,8,9,10])))
print('PASS whole-world land/water mask unchanged; land affiliation changes:',land_changed,'water affiliation changes:',changed-land_changed)

if m['proposal_id']=='continent-20261031-v20' and json.loads((oldp/'proposal.json').read_text())['proposal_id']=='continent-20261031-v19':
 assert ocean_changed==2,ocean_changed
 print('PASS exactly two ocean-label precision corrections')

if m['proposal_id']=='continent-20261031-v21' and json.loads((oldp/'proposal.json').read_text())['proposal_id']=='continent-20261031-v20':
 assert ocean_changed==0,ocean_changed
 print('PASS ocean labels unchanged')
