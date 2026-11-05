import unittest
import numpy as np
from delta_component_screen import screen

class ComponentTest(unittest.TestCase):
    def test_diagonal_cells_split_under_four_neighbor_rule(self):
        rowlist=[];offsets=[0]
        for y in range(5):
            vals=[1]*10
            if y==2:vals[4]=17
            if y==3:vals[5]=17
            for x in range(10):
                if x==9 or vals[x]!=vals[x+1]:rowlist.append((x+1,vals[x]))
            offsets.append(len(rowlist))
        rows=np.array(offsets,dtype='uint32');runs=np.array(rowlist,dtype='uint32').ravel()
        differences={'test':[{'x':4,'y':2},{'x':5,'y':3}]}
        a=screen(rows,runs,(-100,-70,100,70),differences,10,5,36,0,4)
        b=screen(rows,runs,(-100,-70,100,70),differences,10,5,36,0,8)
        self.assertEqual(len(a['groups']['test']['groups']),2)
        self.assertEqual(len(b['groups']['test']['groups']),1)

if __name__=='__main__':unittest.main()
