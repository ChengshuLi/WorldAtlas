"""Run the unchanged coverage/population contract tests against the prototype."""
from unittest import mock
import tempfile
import unittest
from pathlib import Path
import numpy as np

import numeric_preflight
import preflight
from test_preflight import Preflight,RulePopulation


class _NumericMixin:
    def setUp(self):
        super().setUp()
        patcher=mock.patch('test_preflight.validate',new=numeric_preflight.validate)
        patcher.start();self.addCleanup(patcher.stop)


class NumericCoverage(_NumericMixin,Preflight):pass
class NumericPopulation(_NumericMixin,RulePopulation):pass


class NumericDenseOracle(unittest.TestCase):
    def test_arbitrary_layouts_zero_and_max_roots_match_dense_counts(self):
        random=np.random.default_rng(928374)
        for width,height in ((2,3),(7,5),(20,7)):
            for _ in range(10):
                roots=random.choice([-1,0,19,0xffffffff],size=(height,width))
                roots.flat[:3]=[0,19,0xffffffff]
                physical=np.where(roots<0,1,17);seed=np.where(roots==0,17,np.where(roots==0xffffffff,22,0))
                streams=[([],[]),([],[]),([],[])]
                for y in range(height):
                    for number,row in enumerate((roots[y],physical[y],seed[y])):
                        offsets,records=streams[number]
                        if not offsets:offsets.append(0)
                        start=0
                        while start<width:
                            end=start+1
                            while end<width and row[end]==row[start]:end+=1
                            if number:records.append((end,int(row[start])))
                            elif row[start]>=0:records.append((start,end,int(row[start])))
                            start=end
                        offsets.append(len(records))
                with tempfile.TemporaryDirectory() as temp:
                    directory=Path(temp);paths=[]
                    for number,(offsets,records) in enumerate(streams):
                        rowpath=directory/f'{number}.rows';runpath=directory/f'{number}.runs'
                        np.asarray(offsets,dtype='<u4').tofile(rowpath);np.asarray(records,dtype='<u4').tofile(runpath);paths.extend((rowpath,runpath))
                    expected={'land_cells':int(np.count_nonzero(physical==17)),'nonseed_roots':1,
                        'seed_roots':[0,0xffffffff],'seed_codes':[17,22],
                        'seed_category_cells':{str(code):int(np.count_nonzero(seed==code)) for code in (17,22)}}
                    kwargs={'required_codes':[17,22],
                        'seed_rules':[{'component_id_current_generation_only':root,'region_id':None,'inside_code':code,'outside_code':code} for root,code in ((0,17),(0xffffffff,22))],
                        'expected_rule_population':{str(root):{'inside_cells':int(np.count_nonzero(roots==root)),'outside_cells':0} for root in (0,0xffffffff)},
                        'expected_category_counts':expected['seed_category_cells']}
                    for module in (preflight,numeric_preflight):
                        self.assertEqual(module.validate(width,height,*paths,np.asarray([19],dtype='u4'),[0,0xffffffff],**kwargs),expected)

    def test_maximum_width_sparse_row_is_not_pixel_expanded(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);width=0xffffffff;paths=[]
            for i,records in enumerate(([(0,1,0),(width-1,width,width)],[(1,17),(width-1,1),(width,17)],[(1,17),(width,0)])):
                rowpath=directory/f'{i}.rows';runpath=directory/f'{i}.runs'
                np.asarray([0,len(records)],dtype='<u4').tofile(rowpath);np.asarray(records,dtype='<u4').tofile(runpath);paths.extend((rowpath,runpath))
            reference=preflight.validate(width,1,*paths,np.asarray([width],dtype='u4'),[0],required_codes=[17])
            self.assertEqual(numeric_preflight.validate(width,1,*paths,np.asarray([width],dtype='u4'),[0],required_codes=[17]),reference)
            self.assertEqual(reference['land_cells'],2)
