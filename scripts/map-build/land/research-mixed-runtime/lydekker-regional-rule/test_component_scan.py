import hashlib
import struct
import tempfile
import unittest
from pathlib import Path
from component_scan import scan
from regional_rule import Line


def pin(path):
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

class TestComponentScan(unittest.TestCase):
    def test_complete_and_partial_roots(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); rows=d/'rows'; runs=d/'runs'
            # Six columns and four rows; root 1 reaches outside region and
            # root 2 is a full island spanning the northern line endpoint.
            data=[[(0,3,1),(3,5,2)],[(0,2,1),(2,4,2),(5,6,3)],[(0,1,4),(2,4,5)],[(0,1,4),(4,6,6)]]
            offsets=[0]
            with runs.open('wb') as f:
                for row in data:
                    for run in row: f.write(struct.pack('<III',*run))
                    offsets.append(offsets[-1]+len(row))
            rows.write_bytes(struct.pack('<'+'I'*len(offsets),*offsets))
            grid={'width':6,'height':4,'west':-3,'north':2,'step':1}
            line=Line({'type':'LineString','coordinates':[[0,0.5],[0,-0.5]]})
            actual=scan(pin(rows),pin(runs),grid,[-2,-1,2,2],line)
            expected={}
            for y,row in enumerate(data):
                lat=grid['north']-(y+.5)*grid['step']
                for lo,hi,root in row:
                    for x in range(lo,hi):
                        lon=grid['west']+(x+.5)*grid['step']
                        if -2 <= lon <= 2 and -1 <= lat <= 2:
                            r=expected.setdefault(root,dict(total=0,in_scope=0,west=0,east=0,boundary=0,outside_latitude=0))
                            r['in_scope']+=1
                            side=line.side(lon,lat)
                            r['outside_latitude' if side is None else side]+=1
            for row in data:
                for lo,hi,root in row:
                    if root in expected: expected[root]['total']+=hi-lo
            self.assertEqual(actual,expected)
            self.assertEqual(actual[1]['total'],5)
            self.assertLess(actual[1]['in_scope'],actual[1]['total'])
            self.assertGreater(actual[2]['outside_latitude'],0)
            self.assertGreater(actual[2]['in_scope']-actual[2]['outside_latitude'],0)
    def test_corrupt_stream_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); rows=d/'rows'; runs=d/'runs'; rows.write_bytes(struct.pack('<II',0,2)); runs.write_bytes(struct.pack('<IIIIII',0,2,1,1,3,2))
            grid={'width':4,'height':1,'west':-2,'north':1,'step':1}
            line=Line({'type':'LineString','coordinates':[[0,1],[0,-1]]})
            with self.assertRaisesRegex(ValueError,'invalid component run'): scan(pin(rows),pin(runs),grid,[-2,-1,2,1],line)
            bad=pin(rows);bad['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'hash mismatch'): scan(bad,pin(runs),grid,[-2,-1,2,1],line)

if __name__=='__main__': unittest.main()
