import random
import unittest
import numpy as np
from seed_runtime import RuleIndex


def expected(mask,offsets,records,rules):
    by_root={row[0]:row[1:] for row in rules};height,width=mask.shape
    values=np.zeros_like(mask);inside=[0]*len(rules);outside=[0]*len(rules);categories=[0]*6
    positions={rule[0]:i for i,rule in enumerate(rules)}
    for y in range(height):
        for start,end,root in records[offsets[y]:offsets[y+1]]:
            if root not in by_root:continue
            bit,a,b=by_root[root];p=positions[root]
            for x in range(start,end):
                hit=bit==0 or bool(int(mask[y,x]) & bit);code=a if hit else b
                values[y,x]=code;categories[code-17]+=1
                if hit:inside[p]+=1
                else:outside[p]+=1
    pairs=[];counts=[]
    for row in values:
        current=[]
        for x,code in enumerate(row,1):
            if current and current[-1][1]==int(code):current[-1]=(x,int(code))
            else:current.append((x,int(code)))
        counts.append(len(current));pairs.extend(current)
    return np.asarray(pairs,dtype='<u4'),counts,inside,outside,categories


class SeedRuntimeTests(unittest.TestCase):
    def compare(self, mask, rows, rules):
        offsets=[0];flat=[]
        for row in rows:flat.extend(row);offsets.append(len(flat))
        records=np.asarray(flat,dtype='<u4').reshape(-1,3);offsets=np.asarray(offsets,dtype='<u4')
        actual=RuleIndex(rules).strip(mask,offsets,records)
        wanted=expected(mask,offsets,records,rules)
        for a,b in zip(actual,wanted):np.testing.assert_array_equal(a,b)

    def test_random_masks_and_roots_match_independent_cell_oracle(self):
        rng=random.Random(102941)
        for width,height in ((1,1),(2,3),(7,4),(17,5),(31,2)):
            for _ in range(12):
                rules=[(0,0,17,17),(19,1,18,19),(0xffffffff,2,22,20),(7,128,21,21)]
                rng.shuffle(rules)
                rows=[]
                for y in range(height):
                    row=[];x=0
                    while x<width:
                        stop=min(width,x+rng.randrange(1,5));root=rng.choice([0,19,7,0xffffffff,100])
                        if rng.choice((True,False)):row.append((x,stop,root))
                        x=stop
                    rows.append(row)
                mask=np.asarray([[rng.randrange(256) for x in range(width)] for y in range(height)],dtype=np.uint8)
                self.compare(mask,rows,rules)

    def test_empty_components_and_mask_transitions_on_row_boundaries(self):
        self.compare(np.asarray([[1,1,0],[0,1,1],[1,0,0]],dtype=np.uint8),
                     [[(0,3,1)],[],[(0,1,1),(1,3,2)]],[(1,1,17,18),(2,0,19,19)])
        self.compare(np.zeros((3,4),dtype=np.uint8),[[],[],[]],[(1,1,17,18)])

    def test_every_region_bit_and_all_equal_labels_preserve_population(self):
        mask=np.asarray([[0,255,85,170]],dtype=np.uint8)
        for bit in (1,2,4,8,16,32,64,128):
            self.compare(mask,[[(0,4,913)]],[(913,bit,22,22)])

    def test_validation_rejects_overlaps_offsets_duplicate_and_invalid_rules(self):
        mask=np.zeros((1,4),dtype=np.uint8);runtime=RuleIndex([(1,1,17,18)])
        with self.assertRaisesRegex(ValueError,'overlapping'):
            runtime.strip(mask,np.asarray([0,2]),np.asarray([[0,3,1],[2,4,1]],dtype='u4'))
        with self.assertRaisesRegex(ValueError,'offsets'):
            runtime.strip(mask,np.asarray([1,2]),np.asarray([[0,4,1],[0,4,1]],dtype='u4'))
        for rules in ([],[(1,3,17,18)],[(1,0,17,18)],[(1,0,17,17),(1,1,18,19)],[(True,0,17,17)]):
            with self.subTest(rules=rules),self.assertRaises(ValueError):RuleIndex(rules)


if __name__=='__main__':unittest.main()
