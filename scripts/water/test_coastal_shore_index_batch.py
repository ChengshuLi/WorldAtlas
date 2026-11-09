import unittest
from unittest.mock import patch
import numpy as np

from coastal_shore_index import CoastalShoreIndex
from coastal_shore_index_batch import BatchedCoastalShoreIndex
from test_shore_throughput import rle


class BatchIndexTests(unittest.TestCase):
    def compare(self,physical,land,rows_per_batch):
        height,width=physical.shape;p,l=rle(physical),rle(land)
        expected=CoastalShoreIndex(p,l,width,height)
        actual=BatchedCoastalShoreIndex(p,l,width,height,rows_per_batch=rows_per_batch)
        for key in ('offsets','starts','ends','codes'):
            a,b=getattr(actual,key),getattr(expected,key)
            self.assertEqual(a.dtype,b.dtype);self.assertEqual(a.tobytes(),b.tobytes())
        return actual

    def test_arbitrary_grids_categories_seams_poles_and_batch_boundaries(self):
        rng=np.random.default_rng(20261111)
        for trial in range(120):
            width=int(rng.integers(1,80));height=int(rng.integers(1,45))
            physical=np.where(rng.random((height,width))<rng.uniform(0,1),1,17).astype(np.uint32)
            land=np.where(physical==17,rng.integers(17,23,(height,width)),0).astype(np.uint32)
            with self.subTest(trial=trial):self.compare(physical,land,int(rng.integers(1,height+3)))

    def test_all_land_all_water_and_single_cell(self):
        for height,width in ((1,1),(1,8),(8,1),(3,5)):
            for code in (1,17):
                p=np.full((height,width),code,dtype=np.uint32);l=np.where(p==17,22,0)
                for batch in (1,2,100):self.compare(p,l,batch)

    def test_invalid_codes_are_checked_before_narrowing(self):
        p=np.ones((4,8),dtype=np.uint32);p[1,2]=17;l=np.where(p==17,18,0).astype(np.uint32)
        for changed,at in ((p,(2,5)),(l,(1,2))):
            original=int(changed[at]);changed[at]=273
            with self.assertRaisesRegex(ValueError,'invalid physical or land'):
                BatchedCoastalShoreIndex(rle(p),rle(l),8,4,rows_per_batch=2)
            changed[at]=original
        l[2,5]=273  # On physical water this category is not used by either index.
        self.compare(p,l,2)

    def test_noncoalesced_rle_and_readonly_inputs_are_not_special_cased(self):
        p=np.asarray([[17,17,1,1,1,17,1],[1,17,17,1,17,17,1],[1,1,1,1,1,1,1]],dtype=np.uint32)
        l=np.where(p==17,18,0).astype(np.uint32);height,width=p.shape
        def cells(array):
            offsets=np.arange(height+1,dtype=np.uint32)*width
            runs=np.column_stack((np.tile(np.arange(1,width+1,dtype=np.uint32),height),array.ravel())).ravel()
            return offsets,runs
        for physical in (rle(p),cells(p)):
            for land in (rle(l),cells(l)):
                for array in (*physical,*land):array.flags.writeable=False
                old=CoastalShoreIndex(physical,land,width,height)
                new=BatchedCoastalShoreIndex(physical,land,width,height,rows_per_batch=2)
                for key in ('offsets','starts','ends','codes'):
                    self.assertEqual(getattr(old,key).tobytes(),getattr(new,key).tobytes())

    def test_query_method_is_the_unchanged_reference_method(self):
        self.assertIs(BatchedCoastalShoreIndex.centers_for_crop,CoastalShoreIndex.centers_for_crop)

    def test_empty_batches_between_polar_shores_preserve_row_offsets(self):
        p=np.ones((21,9),dtype=np.uint32);p[0,:]=p[-1,:]=17
        l=np.zeros_like(p);l[0,:]=17;l[-1,:]=22
        for batch in (1,2,4,8,21,100):
            actual=self.compare(p,l,batch)
            self.assertEqual(len(actual.starts),2)
            self.assertEqual(actual.offsets[1:-1].tolist(),[1]*20)

    def test_common_cut_ranks_avoid_binary_search_and_pixel_expansion(self):
        width=2**32-1;half=width//2
        offsets=np.asarray([0,2,3,5],dtype=np.uint32)
        physical=(offsets,np.asarray([half,17,width,1,width,1,half,1,width,17],dtype=np.uint32))
        land=(offsets,np.asarray([half,18,width,0,width,0,half,0,width,22],dtype=np.uint32))
        expected=CoastalShoreIndex(physical,land,width,3)
        with patch.object(np,'searchsorted',side_effect=AssertionError('reuse common cut ranks')):
            actual=BatchedCoastalShoreIndex(physical,land,width,3,rows_per_batch=2)
        for key in ('offsets','starts','ends','codes'):
            self.assertEqual(getattr(expected,key).tobytes(),getattr(actual,key).tobytes())
        self.assertEqual(len(actual.starts),2)


if __name__=='__main__':unittest.main()
