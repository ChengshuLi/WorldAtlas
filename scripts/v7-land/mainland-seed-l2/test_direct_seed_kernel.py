"""Bounded direct-kernel checks on a synthetic 8-cell row."""
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path


class DirectKernelTest(unittest.TestCase):
    def test_direct_execution_and_truncated_input_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            binary = d / 'kernel'
            source = Path(__file__).parent / 'rasterizer' / 'seed_kernel.cpp'
            subprocess.run(['g++', '-O2', '-std=c++17', str(source), '-o', str(binary)], check=True)
            (d / 'rows').write_bytes(struct.pack('<II', 0, 1))
            (d / 'runs').write_bytes(struct.pack('<III', 0, 2, 1))
            (d / 'rules').write_text('1 0 17 17\n')
            args = [str(binary), str(d / 'rows'), str(d / 'runs'), str(d / 'rules'),
                    str(d / 'outrows'), str(d / 'outruns'), '8', '1']
            p = subprocess.run(args, input=bytes(8), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(p.returncode, 0, p.stderr.decode())
            self.assertEqual((d / 'outrows').read_bytes(), struct.pack('<II', 0, 2))
            self.assertEqual((d / 'outruns').read_bytes(), struct.pack('<IIII', 2, 17, 8, 0))
            p = subprocess.run(args, input=bytes(7), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn(b'truncated region raster stream', p.stderr)


if __name__ == '__main__':
    unittest.main()
