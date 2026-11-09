from contextlib import contextmanager
from io import BytesIO
import unittest
from unittest.mock import Mock
from federal_register_rectangle import rectangle_from_text

class RectangleTest(unittest.TestCase):
    def setUp(self):
        self.t='Section A\nID W. long. N. lat.\n1 .......... 100°00′00″ 12°00′00″\n2 .......... 99°00′00″ 12°00′00″\n3 .......... 99°00′00″ 11°00′00″\n4 .......... 100°00′00″ 11°00′00″\n1 .......... 100°00′00″ 12°00′00″\nSection B'
    def parse(self,t):return rectangle_from_text(t,'Section A','Section B')
    def test_parse(self):
        self.assertEqual(self.parse(self.t)['coordinates'][0],[[-100,12],[-99,12],[-99,11],[-100,11],[-100,12]])
    def test_duplicate_section_fails(self):
        with self.assertRaises(ValueError):self.parse(self.t+' Section A')
    def test_bad_closure_fails(self):
        with self.assertRaises(ValueError):self.parse(self.t.rsplit('100°00′00″',1)[0]+'98°00′00″ 12°00′00″\nSection B')
    def test_nonrectangle_fails(self):
        with self.assertRaises(ValueError):self.parse(self.t.replace('99°00′00″ 11°00′00″','98°00′00″ 11°00′00″'))
    def test_invalid_dms_fails(self):
        with self.assertRaises(ValueError):self.parse(self.t.replace('99°00′00″ 11°00′00″','99°61′00″ 11°00′00″'))
    def test_ambiguous_direction_fails(self):
        with self.assertRaises(ValueError):self.parse(self.t.replace('W. long. N. lat.','E. long. N. lat.'))
    def test_reordered_rows_fail(self):
        with self.assertRaises(ValueError):self.parse(self.t.replace('3 ..........','4 ..........'))
@contextmanager
def extracted(output):
    yield Mock(stdout=BytesIO(output), wait=Mock(return_value=0))


class PinnedSourceTest(unittest.TestCase):
    def test_source_and_geometry_pins(self):
        import tempfile,hashlib,json
        from pathlib import Path
        from unittest.mock import patch
        from federal_register_rectangle import extract_pdf_rectangle
        fixture=RectangleTest();fixture.setUp();text=fixture.t
        g=rectangle_from_text(text,'Section A','Section B')
        gh=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.pdf';p.write_bytes(b'%PDF-fake');ph=hashlib.sha256(p.read_bytes()).hexdigest();crop={'x':0,'y':0,'width':100,'height':100}
            with patch('stage_external.popen', side_effect=lambda *a, **k: extracted(text.encode())):
                self.assertEqual(extract_pdf_rectangle(p,ph,9,gh,1,crop,'Section A','Section B'),g)
                with self.assertRaises(ValueError):extract_pdf_rectangle(p,'0'*64,9,gh,1,crop,'Section A','Section B')
                with self.assertRaises(ValueError):extract_pdf_rectangle(p,ph,9,'0'*64,1,crop,'Section A','Section B')
                with self.assertRaises(ValueError):extract_pdf_rectangle(p,ph,8,gh,1,crop,'Section A','Section B')

    def test_oversized_and_mutating_inputs_fail_closed(self):
        import tempfile,hashlib,json,os,errno
        from pathlib import Path
        from unittest.mock import patch
        from federal_register_rectangle import extract_pdf_rectangle
        f=RectangleTest();f.setUp();text=f.t;g=rectangle_from_text(text,'Section A','Section B')
        gh=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest();crop={'x':0,'y':0,'width':100,'height':100}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.pdf';p.write_bytes(b'%PDF-fake');ph=hashlib.sha256(p.read_bytes()).hexdigest()
            def args():return (p,ph,9,gh,1,crop,'Section A','Section B')
            p.write_bytes(b'%PDF-fake'+b'x'*10000)
            with patch('stage_external.popen') as run:
                with self.assertRaises(ValueError):extract_pdf_rectangle(*args())
                run.assert_not_called()
            p.write_bytes(b'%PDF-fake')
            with patch('stage_external.popen', side_effect=lambda *a, **k: extracted(b'x'*10_000_001)):
                with self.assertRaises(ValueError):extract_pdf_rectangle(*args())
            def swap(*a,**k):
                self.assertEqual(k['stdin'].read(),b'%PDF-fake')
                with self.assertRaises(OSError) as exc:os.write(k['stdin'].fileno(),b'changed')
                self.assertEqual(exc.exception.errno,errno.EBADF)
                p.write_bytes(b'%PDF-evil')
                return extracted(text.encode())
            with patch('stage_external.popen',side_effect=swap):
                with self.assertRaises(ValueError):extract_pdf_rectangle(*args())

if __name__=='__main__':unittest.main()
