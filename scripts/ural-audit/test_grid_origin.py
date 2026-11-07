import os, tempfile, unittest
import numpy as np
from delta_divider_apply import apply

class GridOriginTests(unittest.TestCase):
    def test_scope_edge_land_fails_in_complete_grid_apply(self):
        cfg={'width':4,'height':4,'step_degrees':1,'west':0,'north':4,
             'land_codes':[18,19], 'asia_code':18, 'europe_code':19,
             'bounds':[.5,.5,3.5,3.5], 'europe_witness':[1,2], 'asia_witness':[3,2]}
        rows=np.arange(5,dtype='<u4')
        runs=np.array([[4,18]]*4,dtype='<u4').reshape(-1)
        phys=np.array([[4,17]]*4,dtype='<u4').reshape(-1)
        with tempfile.TemporaryDirectory() as d, self.assertRaisesRegex(ValueError,'scope boundary'):
            apply(rows,runs,rows,phys,[[2,4],[2,0]],cfg,os.path.join(d,'rows'),os.path.join(d,'runs'))

    def test_shifted_origin_and_scoped_application(self):
        cfg={'width':4,'height':4,'step_degrees':1,'west':10,'north':14,'land_codes':[17,18,19,20,21,22],'asia_code':18,'europe_code':19,
             'bounds':[10.1,10.1,13.9,13.9], 'europe_witness':[10.5,12], 'asia_witness':[13.5,12]}
        rows=np.arange(5,dtype='<u4');runs=np.array([[4,18]]*4,dtype='<u4').reshape(-1)
        phys=np.array([[4,17]]*4,dtype='<u4').reshape(-1)
        with tempfile.TemporaryDirectory() as d:
            counts=apply(rows,runs,rows,phys,[[12,14],[12,10]],cfg,os.path.join(d,'rows'),os.path.join(d,'runs'))
            self.assertEqual(counts['land_centers'],16)
            self.assertEqual(counts['asia_to_europe'],8)
            self.assertEqual(counts['europe_to_asia'],0)
    def test_scope_outside_grid_fails(self):
        cfg={'width':1,'height':1,'step_degrees':1,'west':10,'north':14,'land_codes':[17,18,19,20,21,22],'asia_code':18,'europe_code':19,
             'bounds':[8,10,12,15], 'europe_witness':[9,12], 'asia_witness':[11,12]}
        rows=np.array([0,1],dtype='<u4');runs=np.array([1,18],dtype='<u4');phys=np.array([1,17],dtype='<u4')
        with tempfile.TemporaryDirectory() as d, self.assertRaisesRegex(ValueError,'scope outside grid'):
            apply(rows,runs,rows,phys,[[10,16],[10,9]],cfg,os.path.join(d,'rows'),os.path.join(d,'runs'))

class SwappedCodecTests(unittest.TestCase):
    def test_apply_obeys_swapped_continent_codes(self):
        cfg={'width':4,'height':4,'step_degrees':1,'west':10,'north':14,
             'land_codes':[18,19,30], 'asia_code':19, 'europe_code':18,
             'bounds':[10.1,10.1,13.9,13.9], 'europe_witness':[10.5,12], 'asia_witness':[13.5,12]}
        rows=np.arange(5,dtype='<u4');runs=np.array([[4,19]]*4,dtype='<u4').reshape(-1)
        phys=np.array([[4,17]]*4,dtype='<u4').reshape(-1)
        with tempfile.TemporaryDirectory() as d:
            counts=apply(rows,runs,rows,phys,[[12,14],[12,10]],cfg,os.path.join(d,'rows'),os.path.join(d,'runs'))
            self.assertEqual(counts['asia_to_europe'],8)
            result=np.fromfile(os.path.join(d,'runs'),dtype='<u4').reshape(-1,2)
            self.assertTrue(np.all(result[::2,1]==18));self.assertTrue(np.all(result[1::2,1]==19))
