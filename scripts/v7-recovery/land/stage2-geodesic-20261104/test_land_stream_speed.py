"""Pure-Python row batching preserves every output byte and validation rule."""
import builtins
from pathlib import Path
import random
from unittest.mock import patch

from preflight import validate
import test_write_land_stream as fixture

U = fixture.U
from write_land_stream import _Rows, TRIPLE


class CountedFile:
    def __init__(self, stream):
        self.stream=stream
        self.read_sizes=[]
        self.write_sizes=[]
    def read(self, size=-1):
        self.read_sizes.append(size)
        return self.stream.read(size)
    def write(self, data):
        self.write_sizes.append(len(data))
        return self.stream.write(data)
    def __getattr__(self, name):
        return getattr(self.stream,name)


class BatchedLandTest(fixture.WriterTest):
    def test_run_reads_and_writes_are_batched_by_row(self):
        paths=self.pair('c',self.comp)
        source=_Rows(*paths,2,TRIPLE)
        try:
            counted=CountedFile(source.runs);source.runs=counted
            self.assertEqual(list(source.next()),self.comp[0])
            self.assertEqual(list(source.next()),self.comp[1])
            self.assertEqual(counted.read_sizes,[36,48])
            source.finish()
        finally:
            source.close()
        outputs=[]
        def opened(path,*args,**kwargs):
            stream=builtins.open(path,*args,**kwargs)
            if Path(path)==self.p/'out/runs.u32le':
                stream=CountedFile(stream);outputs.append(stream)
            return stream
        with patch('write_land_stream.open',side_effect=opened,create=True):
            result=self.run_writer()
        self.assertEqual(outputs[0].write_sizes,[40,32])
        self.assertEqual(result['runs'],9)
        self.assertEqual(self.output(),[(3,17),(4,18),(5,0),(7,20),(8,0),
                                       (4,19),(6,20),(7,0),(8,20)])

    def test_root_index_first_last_and_missing_entries(self):
        # Long, sparse root IDs exercise dictionary misses and the first entry
        # (position zero) without a truth-value shortcut.
        self.roots=[0,10,11,0xfffffffe]
        self.codes=[21,20,20,22]
        self.comp[0]=[(0,2,1),(2,4,2),(5,6,0),(6,7,10)]
        self.comp[1]=[(0,2,3),(2,4,4),(4,5,0xfffffffe),(5,6,10),(7,8,11)]
        report=self.run_writer()
        self.assertEqual(report['assigned_roots'],4)
        paths=[self.p/(name+suffix) for name in ('c','p','s') for suffix in ('rows','runs')]
        checked=validate(8,2,*paths,self.roots,[1,2,3,4],required_codes=[17,18,19])
        self.assertEqual(checked['land_cells'],13)
        with self.assertRaisesRegex(ValueError,'unknown nonseed root'):
            validate(8,2,*paths,self.roots[:-1],[1,2,3,4],required_codes=[17,18,19])

    def test_random_complete_output_matches_independent_dense_expectation(self):
        rng=random.Random(870321)
        width,height=128,129
        self.roots=list(range(100,160));self.codes=[17+i%6 for i in range(len(self.roots))]
        labels=dict(zip(self.roots,self.codes))
        self.comp=[];self.phys=[];self.seed=[];expected=[];expected_offsets=[0]
        land=0;seed_codes=set()
        def pairs(values):
            result=[]
            for x,value in enumerate(values,1):
                if result and result[-1][1]==value:result[-1]=(x,value)
                else:result.append((x,value))
            return result
        for y in range(height):
            ids=([1,2,3,4,*self.roots]+[0]*(width-64)) if y==0 else [rng.choice([0,1,2,3,4,*self.roots]) for _ in range(width)]
            codes=[rng.randrange(17,23) if root in (1,2,3,4) else 0 for root in ids]
            seed_codes.update(codes);physical=[17 if root else 1 for root in ids]
            components=[]
            for x,root in enumerate(ids):
                if not root:continue
                if components and components[-1][1]==x and components[-1][2]==root:
                    components[-1]=(components[-1][0],x+1,root)
                else:components.append((x,x+1,root))
            values=[codes[x] if 1<=root<=4 else labels.get(root,0) for x,root in enumerate(ids)]
            self.comp.append(components);self.phys.append(pairs(physical));self.seed.append(pairs(codes))
            expected.extend(pairs(values));expected_offsets.append(len(expected))
            land+=sum(root!=0 for root in ids)
        # Bypass the two-row convenience wrapper while using its input encoder.
        from write_land_stream import write_land_stream
        paths=[value for name,rows in (('c',self.comp),('p',self.phys),('s',self.seed)) for value in self.pair(name,rows)]
        (self.p/'roots').write_bytes(U(*self.roots));(self.p/'codes').write_bytes(bytes(self.codes))
        report=write_land_stream(width,height,*paths,self.p/'roots',self.p/'codes',[1,2,3,4],self.p/'out',disk_reserve_bytes=0)
        self.assertEqual((self.p/'out/rows.u32le').read_bytes(),U(*expected_offsets))
        self.assertEqual((self.p/'out/runs.u32le').read_bytes(),b''.join(U(*pair) for pair in expected))
        self.assertEqual(report['land_cells'],land)
        coverage=validate(width,height,*paths,self.roots,[1,2,3,4],required_codes=seed_codes-{0})
        self.assertEqual(coverage['land_cells'],land)
