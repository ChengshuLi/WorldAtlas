import unittest
import numpy as np

from row_overlay import overlay,overlay_batch


def full(values):
    return np.asarray([(i+1,int(value)) for i,value in enumerate(values)
        if i+1==len(values) or values[i+1]!=value],dtype=np.uint32)


class RowOverlayTests(unittest.TestCase):
    def test_random_dense_oracle_retains_every_source_endpoint(self):
        rng=np.random.default_rng(197343)
        for width in (1,2,17,128):
            for _ in range(30):
                physical=rng.choice([1,17],width);seed=rng.choice([0,17,18,19,20,21,22],width)
                component=[];owner=np.full(width,-1,dtype=np.int64);x=0
                while x<width:
                    stop=min(width,x+int(rng.integers(1,6)))
                    if rng.integers(0,2):
                        owner[x:stop]=len(component);component.append((x,stop,int(rng.choice([0,913,0xffffffff]))))
                    x=stop
                components=np.asarray(component,dtype=np.uint32).reshape(-1,3);p=full(physical);s=full(seed)
                left,right,actual,pvalues,svalues=overlay(width,components,p,s)
                self.assertEqual(set(map(int,np.r_[left,right[-1]])),set([0,width,*components[:,:2].ravel(),*p[:,0],*s[:,0]]))
                for a,b,i,pv,sv in zip(left,right,actual,pvalues,svalues):
                    np.testing.assert_array_equal(owner[a:b],i)
                    np.testing.assert_array_equal(physical[a:b],pv)
                    np.testing.assert_array_equal(seed[a:b],sv)

    def test_noncanonical_equal_full_runs_are_retained(self):
        left,right,owners,physical,seed=overlay(4,np.empty((0,3),dtype='u4'),np.asarray([(2,1),(4,1)]),np.asarray([(1,0),(4,0)]))
        np.testing.assert_array_equal(left,[0,1,2]);np.testing.assert_array_equal(right,[1,2,4])
        np.testing.assert_array_equal(owners,[-1,-1,-1]);np.testing.assert_array_equal(physical,[1,1,1]);np.testing.assert_array_equal(seed,[0,0,0])

    def test_invalid_rows_rejected_before_overlay(self):
        empty=np.empty((0,3),dtype='u4');p=np.asarray([(4,1)]);s=np.asarray([(4,0)])
        cases=((0,empty,p,s),(4,np.asarray([(0,3,0),(2,4,913)]),p,s),
               (4,empty,np.asarray([(3,1)]),s),(4,empty,np.asarray([(0,1),(4,17)]),s),
               (4,empty,np.asarray([(4,19)]),s),(4,empty,p,np.asarray([(4,23)])),
               (4,np.asarray([(0,4,-1)]),p,s),(4,np.asarray([(0,5,0)]),p,s))
        for case in cases:
            with self.subTest(case=case),self.assertRaises(ValueError):overlay(*case)

    def test_batch_matches_independent_per_row_overlay_with_u64_positions(self):
        for width in (7,0xffffffff):
            groups=([[(0,3,0)],[],[(2,5,0xffffffff),(6,7,19)]],
                    [[(3,17),(width,1)],[(width,1)],[(2,1),(5,17),(6,1),(7,17)]+([] if width==7 else [(width,1)])],
                    [[(2,17),(3,18),(width,0)],[(width,0)],[(width,0)]])
            fields=[]
            for columns,rows in zip((3,2,2),groups):
                offsets=[0];records=[]
                for row in rows:records.extend(row);offsets.append(len(records))
                fields.extend((np.asarray(offsets),np.asarray(records,dtype='u4').reshape(-1,columns)))
            actual=overlay_batch(width,*fields);expected=[[] for _ in actual]
            for y in range(3):
                row=overlay(width,*(np.asarray(group[y],dtype='u4').reshape(-1,columns) for group,columns in zip(groups,(3,2,2))))
                for i,values in enumerate(row):
                    if i<2:values=values.astype(np.uint64)+np.uint64(y*width)
                    elif i==2:values=np.where(values<0,-1,values+fields[0][y])
                    expected[i].extend(values)
            for a,b in zip(actual,expected):np.testing.assert_array_equal(a,b)
            broken=list(fields);broken[2]=np.asarray([0,2,2,6])
            with self.assertRaises(ValueError):overlay_batch(width,*broken)


if __name__=='__main__':unittest.main()
