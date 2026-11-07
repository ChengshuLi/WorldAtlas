"""Exercise the actual publisher without importing optional GDAL modules."""
import ast
import ctypes
import errno
import os
import sys
import tempfile
import unittest
from pathlib import Path

source = Path(__file__).with_name('seed_producer.py').read_text()
module = ast.parse(source)
function = next(x for x in module.body if isinstance(x, ast.FunctionDef) and x.name == 'publish_no_replace')
namespace = {'ctypes': ctypes, 'os': os, 'sys': sys}
exec(compile(ast.Module(body=[function], type_ignores=[]), '<publisher>', 'exec'), namespace)
publish = namespace['publish_no_replace']

class AtomicPublication(unittest.TestCase):
 def test_publish_and_refuse_existing_output(self):
  with tempfile.TemporaryDirectory() as root:
   root = Path(root); source = root/'source'; target = root/'target'; source.mkdir()
   (source/'value').write_text('first')
   publish(source, target)
   self.assertFalse(source.exists());self.assertEqual((target/'value').read_text(),'first')
   source.mkdir();(source/'value').write_text('second')
   with self.assertRaises(OSError) as raised: publish(source,target)
   self.assertIn(raised.exception.errno,(errno.EEXIST,errno.ENOTEMPTY))
   self.assertEqual((target/'value').read_text(),'first');self.assertEqual((source/'value').read_text(),'second')

if __name__=='__main__':unittest.main()
