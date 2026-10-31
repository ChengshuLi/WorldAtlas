import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_mediterranean import gates
class MediterraneanTest(unittest.TestCase):
    def test_gibraltar(self):
        self.assertTrue(gates(np.array([-5.8]),np.array([36.0]))[0])
        self.assertFalse(gates(np.array([-6.2]),np.array([36.0]))[0])
    def test_dardanelles(self):
        self.assertTrue(gates(np.array([26.15]),np.array([40.01]))[0])
        self.assertFalse(gates(np.array([26.22]),np.array([40.05]))[0])
    def test_suez(self):
        self.assertFalse(gates(np.array([32.33]),np.array([31.2]))[0])
        self.assertTrue(gates(np.array([32.33]),np.array([31.32]))[0])
    def test_reported_corners(self):
        self.assertTrue(gates(np.array([1.91986,6.05072]),np.array([37.88910,38.74054])).all())
if __name__=='__main__':unittest.main()
