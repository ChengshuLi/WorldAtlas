import gzip
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from benchmark_closed import compare_closed
from benchmark_stage import digest


class ClosedComparisonTests(unittest.TestCase):
    def fixture(self,root,code=1):
        root.mkdir()
        assignment=root/'closed-water-assignments.jsonl.gz'
        assignment.write_bytes(gzip.compress(json.dumps({'row':1,'spans':[{'start':2,'end':3,'code':code}]}).encode()))
        pending=root/'pending-components.jsonl.gz';pending.write_bytes(gzip.compress(b''))
        db=sqlite3.connect(root/'work.sqlite3')
        db.executescript('CREATE TABLE components(root,code); CREATE TABLE spans(y,a,b,root); CREATE TABLE mixed(y,a,b,code,root);')
        db.execute('INSERT INTO components VALUES(1,?)',(code,));db.execute('INSERT INTO spans VALUES(1,2,3,1)')
        db.commit();db.close()
        manifest={'schema':'worldatlas-full-water-assignment-tiles-v1','status':'completed_unverified_candidate_not_published',
                  'assigned_cells':1,'pending_cells':0,'span_count':1,
                  'pending_file':{'path':pending.name,'sha256':digest(pending)},
                  'work_database':{'path':'work.sqlite3','sha256':digest(root/'work.sqlite3')},
                  'tiles':[{'span_file':{'path':assignment.name,'sha256':digest(assignment)}}]}
        (root/'manifest.json').write_text(json.dumps(manifest))

    def test_complete_bytes_and_work_decisions(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for name in ('reference','candidate'):self.fixture(root/name)
            result=compare_closed(root/'reference',root/'candidate')
            self.assertEqual(result['work_table_rows'],{'components':1,'spans':1,'mixed':0})
            self.fixture(root/'changed',2)
            with self.assertRaisesRegex(ValueError,'decompressed bytes differ'):
                compare_closed(root/'reference',root/'changed')
            db=sqlite3.connect(root/'candidate/work.sqlite3');db.execute('UPDATE components SET code=2');db.commit();db.close()
            path=root/'candidate/manifest.json';manifest=json.loads(path.read_text())
            manifest['work_database']['sha256']=digest(root/'candidate/work.sqlite3');path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'work decisions differ'):
                compare_closed(root/'reference',root/'candidate')

    def test_mutated_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for name in ('reference','candidate'):self.fixture(root/name)
            (root/'candidate/pending-components.jsonl.gz').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'artifact hash mismatch'):
                compare_closed(root/'reference',root/'candidate')


if __name__=='__main__':unittest.main()
